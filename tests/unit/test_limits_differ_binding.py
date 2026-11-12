# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: limits_differ pins the slot-1 guard to the bound IR.

When verify runs with --ir, the slot-1 banner must carry the bound
machine id + linear limit, not the legacy AMR machine. Unattested
runs keep the legacy AMR pin.

Wave 11 §5: bound logs carry the oracle probe plan (below/at/
reference/above the bound limit) and the binding carries the machine
kind. A bound log in the old single-probe shape is malformed and
fails closed (truncation must never pass); kinds without oracle
support (robotic_arm_virtual) fail closed as UNSUPPORTED instead
of earning a vacuous PASS. industrial_cell gained oracle support in
T10 (shared guard sources, live native campaign): a correct cell log
passes, a lying cell guard still fails.
"""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_lim", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _probe(echo, decision, reason, state=1):
    return (f"PROBE linear={echo} estop=0 decision={decision} "
            f"reason={reason} state={state}")


# Hand-derived from guard semantics (at-limit DENYs on the float32
# compare); mirrors the BEFORE_12 vectors in test_limits_differ.py.
_PLAN12_SLOT1 = [
    _probe("0.600", "ALLOW", "OK"),
    _probe("1.200", "DENY", "SPEED_OVER_LIMIT"),
    _probe("1.500", "DENY", "SPEED_OVER_LIMIT"),
    _probe("1.700", "DENY", "SPEED_OVER_LIMIT"),
]
_PLAN12_CONV = [
    _probe("0.600", "ALLOW", "OK"),
    _probe("1.200", "ALLOW", "OK"),
    _probe("1.500", "ALLOW", "OK"),
    _probe("1.700", "ALLOW", "OK"),
]
# AFTER-shaped plan (1.6) whose guard lies at the 1.5 reference probe:
# a correct 1.6 guard must ALLOW 1.5.
_PLAN16_LYING_SLOT1 = [
    _probe("0.800", "ALLOW", "OK"),
    _probe("1.500", "DENY", "SPEED_OVER_LIMIT"),
    _probe("1.600", "DENY", "SPEED_OVER_LIMIT"),
    _probe("2.100", "DENY", "SPEED_OVER_LIMIT"),
]
_PLAN16_CONV = [
    _probe("0.800", "ALLOW", "OK"),
    _probe("1.500", "ALLOW", "OK"),
    _probe("1.600", "ALLOW", "OK"),
    _probe("2.100", "DENY", "SPEED_OVER_LIMIT"),
]


def _body(slot1_banner, slot1=_PLAN12_SLOT1, conv=_PLAN12_CONV):
    return "\n".join([
        "---PROBE-AMR---",
        *slot1,
        "---PROBE-CONV---",
        *conv,
        "---FI-VS-CONV---",
        "faultinject: ALL 9 CHECKS PASS",
        "FI_CONV_EXIT=0",
        "---GUARD-HEADERS---",
        slot1_banner,
        "guard: machine=conveyor-demo-01 limits linear=2.000 angular=1.000 freshness=50ms",
    ])


def _legacy_body(slot1_banner):
    """Pre-Wave-11 single-probe shape (unattested runs only)."""
    return "\n".join([
        "---PROBE-AMR---",
        "PROBE linear=1.500 estop=0 decision=DENY reason=SPEED_OVER_LIMIT state=1",
        "---PROBE-CONV---",
        "PROBE linear=1.500 estop=0 decision=ALLOW reason=OK state=1",
        "---FI-VS-CONV---",
        "faultinject: ALL 9 CHECKS PASS",
        "FI_CONV_EXIT=0",
        "---GUARD-HEADERS---",
        slot1_banner,
        "guard: machine=conveyor-demo-01 limits linear=2.000 angular=1.000 freshness=50ms",
    ])


CELL = {"machine_id": "cell-demo-01", "machine_kind": "industrial_cell",
        "ir_sha256": "00" * 32, "linear_limit_mps": 1.2}
AMR = {"machine_id": "amr-demo-01",
       "machine_kind": "differential_drive_robot",
       "ir_sha256": "11" * 32, "linear_limit_mps": 1.2}


ARM = {"machine_id": "arm-demo-01", "machine_kind": "robotic_arm_virtual",
       "ir_sha256": "22" * 32, "linear_limit_mps": 1.2}


def test_bound_cell_kind_passes_with_correct_probes(qt):
    # T10: industrial_cell compiles the shared guard_policy.c; its probe
    # verdicts are predicted exactly like the AMR guard's.
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is True


def test_bound_cell_lying_guard_still_fails(qt):
    lying = list(_PLAN12_SLOT1)
    lying[1] = _probe("1.200", "ALLOW", "OK")  # at-limit must DENY (f32)
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms",
                 slot1=lying)
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is False


def test_bound_cell_banner_must_match_bound_machine(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is False


def test_bound_unsupported_arm_kind_fails_closed(qt):
    body = _body("guard: machine=arm-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, ARM)["passed"] is False


def test_bound_amr_banner_passes(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, AMR)["passed"] is True


def test_legacy_unattested_keeps_amr_pin(qt):
    body = _legacy_body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0)["passed"] is True


def test_legacy_rejects_cell_banner(qt):
    body = _legacy_body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0)["passed"] is False


def test_bound_legacy_shaped_log_fails_closed(qt):
    # A bound run must carry the probe plan; a single-probe log under
    # a binding is malformed (indistinguishable from truncation).
    body = _legacy_body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, AMR)["passed"] is False


def test_rejects_wrong_machine_id(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, AMR)["passed"] is False


def test_rejects_wrong_limit(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.500 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, AMR)["passed"] is False


def test_rejects_guard_contradicting_bound_contract(qt):
    # Bound 1.6 with a guard that DENYs the 1.5 reference probe: the
    # oracle expects ALLOW, so the contradiction fails. (A correct
    # 1.6 guard passes -- see the AFTER campaign.)
    bound = dict(AMR, linear_limit_mps=1.6)
    body = _body("guard: machine=amr-demo-01 limits linear=1.600 angular=1.000 freshness=50ms",
                 slot1=_PLAN16_LYING_SLOT1, conv=_PLAN16_CONV)
    assert qt._matrix_check("limits_differ", body, 0, bound)["passed"] is False


def test_rejects_conveyor_as_slot1(qt):
    bound = {"machine_id": "conveyor-demo-01", "machine_kind": "conveyor",
             "ir_sha256": "22" * 32, "linear_limit_mps": 1.2}
    body = _body("guard: machine=conveyor-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, bound)["passed"] is False


def test_rejects_malformed_bound(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, {})["passed"] is False


def test_binding_carries_linear_limit(repo_root):
    qt = _load_qnx_target(repo_root)
    bound = qt._ir_binding(str(repo_root / "examples/cell-demo/cell-ir.json"))
    assert bound["machine_id"] == "cell-demo-01"
    assert bound["machine_kind"] == "industrial_cell"
    assert bound["linear_limit_mps"] == pytest.approx(1.2)
    assert len(bound["ir_sha256"]) == 64
