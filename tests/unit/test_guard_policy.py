# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit + adversarial tests: guard policy mirror (fail-closed)."""
import pytest

from genesis_rt import guard_policy as gp
from genesis_rt.ir import guard_limits

LIMITS = {"period_ms": 10, "max_linear_speed_mps": 1.2,
          "max_angular_speed_radps": 1.0, "freshness_limit_ms": 100}


def _cmd(**over):
    base = {"magic": gp.PROTOCOL_MAGIC, "version": 1, "size_ok": True,
            "seq": 1, "now_ms": 0, "deadline_ms": 50,
            "linear_mps": 0.5, "angular_radps": 0.0,
            "req_state": gp.ST_NOMINAL, "sensor_age_ms": 0,
            "sim_connected": True, "estop_engaged": 0}
    base.update(over)
    return base


def test_allow_nominal():
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(), ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"], v["applied"]) == ("ALLOW", "OK", 1, True)


def test_limits_come_from_ir(amr_ir):
    assert guard_limits(amr_ir) == LIMITS


@pytest.mark.parametrize("field,value,reason,latch", [
    ("magic", 0xDEAD, gp.R_BAD_MAGIC, True),
    ("version", 99, gp.R_BAD_VERSION, True),
    ("size_ok", False, gp.R_BAD_SIZE, True),
    ("now_ms", 60, gp.R_OVERDUE_DEADLINE, False),
    ("sensor_age_ms", 101, gp.R_STALE_SENSOR, True),
    ("sim_connected", False, gp.R_SIM_DISCONNECTED, True),
    ("estop_engaged", 1, gp.R_ESTOP, True),
    ("linear_mps", 1.21, gp.R_SPEED_OVER_LIMIT, False),
    ("linear_mps", -5.0, gp.R_SPEED_OVER_LIMIT, False),
    ("angular_radps", 1.01, gp.R_ANGULAR_OVER_LIMIT, False),
    ("linear_mps", float("nan"), gp.R_MALFORMED, True),
    ("angular_radps", float("inf"), gp.R_MALFORMED, True),
    ("req_state", 3, gp.R_BAD_TRANSITION, False),
    ("req_state", 99, gp.R_BAD_TRANSITION, False),
])
def test_deny_matrix(field, value, reason, latch):
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(**{field: value}), ctx, LIMITS)
    assert v["decision"] == gp.DENY and v["reason"] == reason
    assert v["state_out"] == (gp.ST_SAFE_STOP if latch else gp.ST_NOMINAL)


def test_seq_wraparound_accepted():
    """uint32 wrap (2^32-1 -> 0) is a fresh command, not a replay."""
    ctx = gp.GuardContext(last_seq=(1 << 32) - 1)
    v = gp.decide(_cmd(seq=0), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.ALLOW, gp.R_OK)
    assert ctx.last_seq == 0


def test_seq_old_replay_denied():
    ctx = gp.GuardContext(last_seq=100)
    v = gp.decide(_cmd(seq=50), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_STALE_SEQ)
    assert ctx.last_seq == 100  # denied commands never advance the cursor


def test_seq_delta_max_forward_accepted():
    """Delta exactly 2^31-1 is the largest forward step: ACCEPT
    (RFC 1982 boundary; delta >= 2^31 denies)."""
    ctx = gp.GuardContext(last_seq=0)
    v = gp.decide(_cmd(seq=(1 << 31) - 1), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.ALLOW, gp.R_OK)
    assert ctx.last_seq == (1 << 31) - 1


def test_seq_huge_forward_jump_denied():
    """A jump >= 2^31 is indistinguishable from a replay: deny fail-closed."""
    ctx = gp.GuardContext(last_seq=0)
    v = gp.decide(_cmd(seq=1 << 31), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_STALE_SEQ)


def test_replay_rejected():
    ctx = gp.GuardContext()
    assert gp.decide(_cmd(seq=7), ctx, LIMITS)["decision"] == gp.ALLOW
    v = gp.decide(_cmd(seq=7), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_STALE_SEQ)
    v = gp.decide(_cmd(seq=3), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_STALE_SEQ)


def test_missing_field_malformed_latches():
    ctx = gp.GuardContext()
    cmd = _cmd()
    del cmd["seq"]
    v = gp.decide(cmd, ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"]) == (gp.DENY, gp.R_MALFORMED, 3)


def test_denied_seq_not_consumed():
    """Only ACCEPTED seqs advance last_seq (retry-with-fix stays legal)."""
    ctx = gp.GuardContext()
    assert gp.decide(_cmd(seq=5, linear_mps=9.0), ctx, LIMITS)["decision"] == gp.DENY
    v = gp.decide(_cmd(seq=5), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.ALLOW, gp.R_OK)


def test_safe_stop_needs_supervisor_reset():
    ctx = gp.GuardContext()
    gp.decide(_cmd(magic=0xDEAD), ctx, LIMITS)
    ctx.state = gp.ST_SAFE_STOP
    v = gp.decide(_cmd(seq=2), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_BAD_TRANSITION)
    ctx.reset_armed = True
    v = gp.decide(_cmd(seq=2), ctx, LIMITS)
    assert (v["decision"], v["state_out"]) == (gp.ALLOW, gp.ST_NOMINAL)
    assert ctx.reset_armed is False  # single-use reset


def test_reset_cannot_request_safe_stop_directly():
    ctx = gp.GuardContext(state=gp.ST_SAFE_STOP, reset_armed=True)
    v = gp.decide(_cmd(req_state=gp.ST_SAFE_STOP), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_BAD_TRANSITION)


@pytest.mark.parametrize("field,value", [
    ("now_ms", float("inf")),
    ("deadline_ms", float("-inf")),
    ("seq", float("inf")),
    ("sensor_age_ms", float("inf")),
    ("linear_mps", 10 ** 309),  # float() overflows past ~1.8e308
    ("angular_radps", 10 ** 309),
])
def test_overflow_inputs_denied_not_raised(field, value):
    """OverflowError paths must DENY MALFORMED, never propagate."""
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(**{field: value}), ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"]) == (gp.DENY, gp.R_MALFORMED, 3)


@pytest.mark.parametrize("field,value", [
    ("magic", -1),
    ("version", -1),
    ("seq", -5),
    ("now_ms", -1),
    ("deadline_ms", -1),
    ("req_state", -1),
    ("sensor_age_ms", -1),  # negative age must not pass as fresh
    ("magic", 1 << 32),
    ("version", 1 << 16),
    ("seq", 1 << 40),
    ("req_state", 1 << 16),
    ("sensor_age_ms", 1 << 33),
    ("seq", True),  # booleans are never valid numerics
    ("magic", True),
    ("linear_mps", False),
])
def test_out_of_wire_range_denied_malformed(field, value):
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(**{field: value}), ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"]) == (gp.DENY, gp.R_MALFORMED, 3)


@pytest.mark.parametrize("bad_limits", [
    {},
    {"freshness_limit_ms": 100},  # missing speeds
    {"freshness_limit_ms": "soon", "max_linear_speed_mps": 1.2,
     "max_angular_speed_radps": 1.0},
    {"freshness_limit_ms": 100, "max_linear_speed_mps": None,
     "max_angular_speed_radps": 1.0},
    {"freshness_limit_ms": float("inf"), "max_linear_speed_mps": 1.2,
     "max_angular_speed_radps": 1.0},
])
def test_malformed_limits_denied_not_raised(bad_limits):
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(), ctx, bad_limits)
    assert (v["decision"], v["reason"], v["state_out"]) == (gp.DENY, gp.R_MALFORMED, 3)


def test_estop_dominates_speed_but_not_integrity():
    """ESTOP is the first safety-content check: it wins over speed
    limits, but a corrupt frame still reports its integrity reason."""
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(estop_engaged=1, linear_mps=9.0), ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"]) == (
        gp.DENY, gp.R_ESTOP, gp.ST_SAFE_STOP)
    v = gp.decide(_cmd(estop_engaged=1, magic=0xDEAD), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_BAD_MAGIC)


def test_estop_latch_needs_supervisor_reset():
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(estop_engaged=1), ctx, LIMITS)
    assert v["state_out"] == gp.ST_SAFE_STOP
    ctx.state = v["state_out"]  # caller applies the latch
    v = gp.decide(_cmd(estop_engaged=0), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_BAD_TRANSITION)
    ctx.reset_armed = True  # supervisor path only
    v = gp.decide(_cmd(estop_engaged=0), ctx, LIMITS)
    assert (v["decision"], v["reason"], v["state_out"]) == (
        gp.ALLOW, gp.R_OK, gp.ST_NOMINAL)


def test_estop_malformed_values_denied():
    """Non-0/1 estop bytes are fail-closed; a missing field is too."""
    ctx = gp.GuardContext()
    for bad in (True, 2, 256, -1):
        v = gp.decide(_cmd(estop_engaged=bad), ctx, LIMITS)
        assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_MALFORMED), bad
    cmd = _cmd()
    del cmd["estop_engaged"]
    v = gp.decide(cmd, ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_MALFORMED)


def test_bad_magic_wins_over_nan_c_parity_order():
    """Check order matches guard_policy.c: magic before NaN."""
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(magic=0xDEAD, linear_mps=float("nan")), ctx, LIMITS)
    assert (v["decision"], v["reason"]) == (gp.DENY, gp.R_BAD_MAGIC)


def test_state_out_requires_caller_writeback_documented():
    """decide() never mutates ctx.state (C parity); caller applies state_out."""
    ctx = gp.GuardContext()
    v = gp.decide(_cmd(magic=0xDEAD), ctx, LIMITS)
    assert v["state_out"] == gp.ST_SAFE_STOP
    assert ctx.state == gp.ST_NOMINAL  # unchanged until the caller applies it
