# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: v2_transitions matrix parser (synthetic target transcripts).

The parser must accept exactly the verdict shape the v2 step produces
natively: bidirectional v1-vs-v2 contrast, ordered markers, the 9-check
suite on the v2 binary, and distinct binaries. Anything weaker fails.
"""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_v2", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _good_body():
    suite = "\n".join(f"PASS check-{i} decision=0 reason=0 state=1 (want 0/0/1)"
                      for i in range(9))
    return "\n".join([
        "DIFF_BIN",
        "---V1-STATE2---",
        "PROBE state=2 decision=ALLOW reason=OK state=2",
        "---V1-STATE3---",
        "PROBE state=3 decision=DENY reason=BAD_TRANSITION state=1",
        "---V2-STATE2---",
        "PROBE state=2 decision=DENY reason=BAD_TRANSITION state=1",
        "---V2-STATE3---",
        "PROBE state=3 decision=ALLOW reason=OK state=3",
        "---V2-SUITE---",
        suite,
        "ALL 9 CHECKS PASS",
        "FI_V2_EXIT=0",
        "---V2-LIMIT---",
        "PROBE linear=1.500 estop=0 decision=DENY reason=SPEED_OVER_LIMIT state=1",
        "---V2-ESTOP---",
        "PROBE linear=0.500 estop=1 decision=DENY reason=ESTOP state=3",
    ])


def test_v2_step_present_in_matrix(qt):
    names = [name for name, _ in qt.TARGET_MATRIX]
    assert "v2_transitions" in names
    assert names.index("v2_transitions") > names.index("supervisor_giveup")


def test_v2_check_accepts_good_transcript(qt):
    check = qt._matrix_check("v2_transitions", _good_body(), 0)
    assert check["passed"] is True


def test_v2_check_rejects_same_binary(qt):
    body = _good_body().replace("DIFF_BIN", "SAME_BIN")
    assert qt._matrix_check("v2_transitions", body, 0)["passed"] is False


def test_v2_check_rejects_missing_guard(qt):
    body = "MISSING_V2_GUARD\n" + _good_body()
    assert qt._matrix_check("v2_transitions", body, 0)["passed"] is False


def test_v2_check_rejects_swapped_sections(qt):
    """V1-ALLOW and V2-DENY in the wrong sections must not pass."""
    body = _good_body().replace(
        "---V1-STATE2---\nPROBE state=2 decision=ALLOW reason=OK state=2",
        "---V1-STATE2---\nPROBE state=2 decision=DENY reason=BAD_TRANSITION state=1")
    assert qt._matrix_check("v2_transitions", body, 0)["passed"] is False


def test_v2_check_rejects_short_suite(qt):
    body = _good_body().replace("PASS check-8", "FAIL check-8")
    assert qt._matrix_check("v2_transitions", body, 0)["passed"] is False


def test_v2_check_rejects_unordered_markers(qt):
    lines = _good_body().splitlines()
    i_estop = lines.index("---V2-ESTOP---")
    i_lim = lines.index("---V2-LIMIT---")
    lines[i_estop], lines[i_lim] = lines[i_lim], lines[i_estop]
    assert qt._matrix_check("v2_transitions", "\n".join(lines), 0)["passed"] is False
