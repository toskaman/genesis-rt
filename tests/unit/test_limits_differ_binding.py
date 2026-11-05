# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: limits_differ pins the slot-1 guard to the bound IR.

When verify runs with --ir, the slot-1 banner must carry the bound
machine id + linear limit (e.g. the cell guard), not the legacy AMR
machine. Unattested runs keep the legacy AMR pin. Bad geometry
(bound limit >= probe 1.5) fails closed.
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


def _body(slot1_banner):
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


CELL = {"machine_id": "cell-demo-01", "ir_sha256": "00" * 32,
        "linear_limit_mps": 1.2}
AMR = {"machine_id": "amr-demo-01", "ir_sha256": "11" * 32,
       "linear_limit_mps": 1.2}


def test_bound_cell_banner_passes(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is True


def test_bound_amr_banner_passes(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, AMR)["passed"] is True


def test_legacy_unattested_keeps_amr_pin(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0)["passed"] is True


def test_legacy_rejects_cell_banner(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0)["passed"] is False


def test_rejects_wrong_machine_id(qt):
    body = _body("guard: machine=amr-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is False


def test_rejects_wrong_limit(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.500 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, CELL)["passed"] is False


def test_rejects_limit_at_probe_geometry(qt):
    bound = dict(CELL, linear_limit_mps=1.6)
    body = _body("guard: machine=cell-demo-01 limits linear=1.600 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, bound)["passed"] is False


def test_rejects_conveyor_as_slot1(qt):
    bound = dict(CELL, machine_id="conveyor-demo-01",
                 linear_limit_mps=1.2)
    body = _body("guard: machine=conveyor-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, bound)["passed"] is False


def test_rejects_malformed_bound(qt):
    body = _body("guard: machine=cell-demo-01 limits linear=1.200 angular=1.000 freshness=50ms")
    assert qt._matrix_check("limits_differ", body, 0, {})["passed"] is False


def test_binding_carries_linear_limit(repo_root):
    qt = _load_qnx_target(repo_root)
    bound = qt._ir_binding(str(repo_root / "examples/cell-demo/cell-ir.json"))
    assert bound["machine_id"] == "cell-demo-01"
    assert bound["linear_limit_mps"] == pytest.approx(1.2)
    assert len(bound["ir_sha256"]) == 64
