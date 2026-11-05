# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: cell_policy matrix parser (synthetic target transcripts).

Accepts exactly the verdict shape the native cellcheck produces: 9
interlock vectors + 3 policy checks, CELL_POLICY PASS 12/12, exit 0.
Anything weaker fails.
"""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_cell", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _good_body():
    lines = [f"CELLCHECK vec-{i:02d} PASS (want 1 got 1)"
             for i in range(9)]
    lines += ["CELLCHECK policy_station PASS (station_x=6)",
              "CELLCHECK policy_ticks PASS (ticks=50)",
              "CELLCHECK policy_ids PASS",
              "CELL_POLICY: PASS 12/12",
              "CELL_EXIT=0"]
    return "\n".join(lines)


def test_cell_policy_matrix_step_exists(qt):
    names = [name for name, _ in qt.TARGET_MATRIX]
    assert names[-1] == "cell_policy"
    assert len(names) == 16
    assert names.index("guard_crash") == len(names) - 2


def test_accepts_native_shape(qt):
    assert qt._matrix_check("cell_policy", _good_body(), 0)["passed"] is True


def test_rejects_missing_binary(qt):
    body = "MISSING_CELLCHECK\nCELL_EXIT=3"
    assert qt._matrix_check("cell_policy", body, 3)["passed"] is False


def test_rejects_fail_summary(qt):
    body = _good_body().replace("CELL_POLICY: PASS 12/12",
                                "CELL_POLICY: FAIL 11/12")
    assert qt._matrix_check("cell_policy", body, 0)["passed"] is False


def test_rejects_short_count(qt):
    body = _good_body().replace("CELL_POLICY: PASS 12/12",
                                "CELL_POLICY: PASS 9/9")
    assert qt._matrix_check("cell_policy", body, 0)["passed"] is False


def test_rejects_nonzero_exit(qt):
    body = _good_body().replace("CELL_EXIT=0", "CELL_EXIT=1")
    assert qt._matrix_check("cell_policy", body, 0)["passed"] is False


def test_rejects_dropped_vector_line(qt):
    body = "\n".join(ln for ln in _good_body().splitlines()
                     if "vec-03" not in ln)
    assert qt._matrix_check("cell_policy", body, 0)["passed"] is False
