# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §5: contract-aware native oracle.

Hand-derived reference vectors (each float32 derivation verified in
the Wave 11 baseline session), a mutation test proving the vectors
are not vacuous, probe-plan coverage, and oracle-vs-guard parity.
"""
import struct

import pytest

from genesis_rt import guard_policy as gp
from genesis_rt import native_oracle as no


def _f32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


# (kind, limit, probe, estop, verdict, decision, reason, state, note)
VECTORS = [
    # The flagship flip: same probe, valid contract change.
    ("differential_drive_robot", 1.2, 1.5, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1, "BEFORE"),
    ("differential_drive_robot", 1.6, 1.5, False,
     no.EXPECTED_ALLOW, "ALLOW", "OK", 1, "AFTER"),
    # float32 boundary traps (f32(decimal) vs the decimal limit).
    ("differential_drive_robot", 1.2, 1.2, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1,
     "f32(1.2)=1.2000000476… exceeds"),
    ("differential_drive_robot", 2.0, 2.0, False,
     no.EXPECTED_ALLOW, "ALLOW", "OK", 1, "2.0 exact in f32"),
    ("differential_drive_robot", 0.3, 0.3, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1,
     "f32(0.3)=0.3000000119… exceeds"),
    ("differential_drive_robot", 0.5, 0.5, False,
     no.EXPECTED_ALLOW, "ALLOW", "OK", 1, "0.5 exact in f32"),
    ("differential_drive_robot", 1.6, 1.6, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1,
     "f32(1.6)=1.6000000238… exceeds"),
    ("differential_drive_robot", 0.3, 0.15, False,
     no.EXPECTED_ALLOW, "ALLOW", "OK", 1, "below-limit plan probe"),
    ("differential_drive_robot", 1.6, 2.1, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1,
     "above-limit plan probe"),
    ("conveyor", 2.0, 1.5, False,
     no.EXPECTED_ALLOW, "ALLOW", "OK", 1, "conv slot legacy probe"),
    ("conveyor", 2.0, 2.5, False,
     no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1, "conv over limit"),
    # Estop dominates speed, latches safe-stop.
    ("differential_drive_robot", 1.6, 0.5, True,
     no.EXPECTED_SAFE_STOP, "DENY", "ESTOP", 3, "estop dominates"),
    # Unsupported / inconclusive inputs (fail closed, never guessed).
    ("robot_arm", 1.2, 0.5, False,
     no.UNSUPPORTED, None, None, None, "unknown kind"),
    ("differential_drive_robot", 0.0, 0.5, False,
     no.INCONCLUSIVE, None, None, None, "limit not positive"),
    ("differential_drive_robot", 11.0, 0.5, False,
     no.INCONCLUSIVE, None, None, None, "limit above schema"),
    ("differential_drive_robot", 1.2, float("inf"), False,
     no.INCONCLUSIVE, None, None, None, "probe not finite"),
]


@pytest.mark.parametrize("kind,limit,probe,estop,verdict,dec,reason,state,note",
                         VECTORS)
def test_hand_vectors(kind, limit, probe, estop, verdict, dec, reason,
                      state, note):
    got = no.expect_linear_probe(machine_kind=kind, limit_mps=limit,
                                 probe_mps=probe, estop=estop)
    assert (got.verdict, got.decision, got.reason, got.state_out) == \
        (verdict, dec, reason, state), note


def test_vectors_are_not_vacuous_mutation():
    """A deliberately wrong oracle (float64 compare, no wire
    narrowing) must FAIL at least one vector — proving the table can
    catch a real semantic error."""
    def _wrong(kind, limit, probe):
        if probe > limit:  # float64, no f32 narrowing
            return (no.EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1)
        return (no.EXPECTED_ALLOW, "ALLOW", "OK", 1)
    mismatches = [v for v in VECTORS
                  if v[4] in (no.EXPECTED_DENY, no.EXPECTED_ALLOW)
                  and _wrong(v[0], v[1], v[2]) != (v[4], v[5], v[6], v[7])]
    assert mismatches, "vectors cannot catch the float64 mutant"
    assert any(v[8].startswith("f32(") for v in mismatches)


@pytest.mark.parametrize("limit,plan", [
    (0.3, [0.15, 0.3, 0.8, 1.5]),
    (0.5, [0.25, 0.5, 1.0, 1.5]),
    (1.2, [0.6, 1.2, 1.5, 1.7]),
    (1.5, [0.75, 1.5, 2.0]),
    (1.6, [0.8, 1.5, 1.6, 2.1]),
    (2.0, [1.0, 1.5, 2.0, 2.5]),
])
def test_probe_plans(limit, plan):
    assert no.plan_probes(limit) == plan
    assert 1.5 in plan  # the iconic reference probe is always present
    assert _f32(plan[0]) < limit  # first probe truly below on the wire
    assert _f32(plan[-1]) > limit  # last probe truly above on the wire


def test_probe_plan_rejects_degenerate_limits():
    assert no.plan_probes(0.0) is None
    assert no.plan_probes(0.001) is None
    assert no.plan_probes(float("nan")) is None


def _probe_cmd(linear, estop=False):
    return {"magic": gp.PROTOCOL_MAGIC, "version": gp.PROTOCOL_VERSION,
            "size_ok": True, "seq": 1, "now_ms": 1000,
            "deadline_ms": 1030, "linear_mps": linear,
            "angular_radps": 0.0, "req_state": 1, "sensor_age_ms": 0,
            "sim_connected": True, "estop_engaged": 1 if estop else 0}


@pytest.mark.parametrize("limit,probe,estop", [
    (lim, pr, es) for lim in (0.3, 0.5, 1.2, 1.5, 1.6, 2.0)
    for pr in (round(0.5 * lim, 3), lim, round(lim + 0.5, 3))
    for es in (False, True)
])
def test_oracle_agrees_with_guard_policy(limit, probe, estop):
    """Oracle-vs-Python-guard parity on every planned probe: the two
    independent implementations of the wire semantics must agree."""
    limits = {"max_linear_speed_mps": limit,
              "max_angular_speed_radps": 1.0, "freshness_limit_ms": 100}
    ctx = gp.GuardContext(last_seq=0, state=1, reset_armed=False)
    g = gp.decide(_probe_cmd(probe, estop), ctx, limits)
    o = no.expect_linear_probe(machine_kind="differential_drive_robot",
                               limit_mps=limit, probe_mps=probe,
                               estop=estop)
    assert o.verdict in (no.EXPECTED_ALLOW, no.EXPECTED_DENY,
                         no.EXPECTED_SAFE_STOP)
    assert (g["decision"], g["reason"], g["state_out"]) == \
        (o.decision, o.reason, o.state_out), (limit, probe, estop)
