# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: §16 wrap-safe deadline arithmetic + version pinning."""
import pytest

from genesis_rt import guard_policy as gp

LIMITS = {"period_ms": 10, "max_linear_speed_mps": 1.2,
          "max_angular_speed_radps": 1.0, "freshness_limit_ms": 100}
M = 1 << 32
E = 0x47454E31


def _cmd(seq=1, now=0, dl=50, **kw):
    cmd = {"magic": E, "version": 1, "size_ok": True, "seq": seq,
           "now_ms": now, "deadline_ms": dl, "linear_mps": 0.5,
           "angular_radps": 0.0, "req_state": 1, "sensor_age_ms": 0,
           "sim_connected": True, "estop_engaged": 0}
    cmd.update(kw)
    return cmd


def _decide(cmd, last_seq=None):
    ctx = gp.GuardContext(
        last_seq=cmd["seq"] - 1 if last_seq is None else last_seq,
        state=gp.ST_NOMINAL)
    return gp.decide(cmd, ctx, LIMITS), ctx


@pytest.mark.parametrize(("now", "dl", "reason"), [
    (0, 50, gp.R_OK),
    (100, 50, gp.R_OVERDUE_DEADLINE),
    (50, 50, gp.R_OK),  # equal is not overdue
    (10, M - 5, gp.R_OVERDUE_DEADLINE),  # overdue across wrap
    (M - 10, 100, gp.R_OK),  # future across wrap
    (M - 1, M - 1, gp.R_OK),  # equal at the edge
    (M - 1, 30, gp.R_OK),  # long-run clock, near-term deadline
    ((1 << 31) - 1, 0, gp.R_OVERDUE_DEADLINE),  # max overdue delta
    (1 << 31, 0, gp.R_OK),  # ambiguity zone reads as future
])
def test_deadline_serial_arithmetic(now, dl, reason):
    verdict, _ctx = _decide(_cmd(now=now, dl=dl))
    assert verdict["reason"] == reason, (now, dl)
    assert verdict["decision"] == (
        gp.DENY if reason != gp.R_OK else gp.ALLOW)


def test_overdue_does_not_latch_and_recovers():
    ctx = gp.GuardContext(last_seq=10, state=gp.ST_NOMINAL)
    stale = gp.decide(_cmd(seq=11, now=100, dl=50), ctx, LIMITS)
    assert (stale["decision"], stale["reason"]) == (
        gp.DENY, gp.R_OVERDUE_DEADLINE)
    assert stale["state_out"] == gp.ST_NOMINAL
    fresh = gp.decide(_cmd(seq=12, now=100, dl=5000), ctx, LIMITS)
    assert (fresh["decision"], fresh["reason"]) == (gp.ALLOW, gp.R_OK)


def test_seq_wrap_with_deadline_interplay():
    ctx = gp.GuardContext(last_seq=M - 1, state=gp.ST_NOMINAL)
    wrapped = gp.decide(_cmd(seq=0, now=5, dl=100), ctx, LIMITS)
    assert (wrapped["decision"], wrapped["reason"]) == (gp.ALLOW, gp.R_OK)
    replay = gp.decide(_cmd(seq=0, now=6, dl=100), ctx, LIMITS)
    assert replay["reason"] == gp.R_STALE_SEQ


def test_sensor_age_is_duration_not_timestamp():
    verdict, _ctx = _decide(_cmd(sensor_age_ms=100))
    assert verdict["decision"] == gp.ALLOW
    verdict, _ctx = _decide(_cmd(sensor_age_ms=101))
    assert verdict["reason"] == gp.R_STALE_SENSOR


@pytest.mark.parametrize("version", [0, 2, 99, 1 << 16])
def test_mixed_versions_rejected(version):
    verdict, _ctx = _decide(_cmd(version=version))
    if version >= (1 << 16):
        assert verdict["reason"] == gp.R_MALFORMED
    else:
        assert verdict["reason"] == gp.R_BAD_VERSION
    assert verdict["state_out"] == gp.ST_SAFE_STOP
