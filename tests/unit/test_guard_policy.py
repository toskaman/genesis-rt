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
            "sim_connected": True}
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
    ("deadline_ms", -1, gp.R_OVERDUE_DEADLINE, False),
    ("sensor_age_ms", 101, gp.R_STALE_SENSOR, True),
    ("sim_connected", False, gp.R_SIM_DISCONNECTED, True),
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
