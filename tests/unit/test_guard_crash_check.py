# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: guard_crash containment step (killed guard freezes device)."""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_gc", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _body(before=82, after=84, nonguard=0, alive=0, failed=True):
    lines = [f"BEFORE={before}", f"AFTER={after}", f"NONGUARD={nonguard}",
             f"ALIVE={alive}", "---CTRL-GC-TAIL---",
             "controller: seq=84 decision=ALLOW reason=0 state=1"]
    if failed:
        lines.append("controller: MsgSend failed: Bad file descriptor")
    return "\n".join(lines)


def test_accepts_live_shape(qt):
    assert qt._matrix_check("guard_crash", _body(), 0)["passed"] is True


def test_accepts_zero_growth(qt):
    assert qt._matrix_check(
        "guard_crash", _body(before=40, after=40), 0)["passed"] is True


def test_rejects_runaway_device(qt):
    assert qt._matrix_check(
        "guard_crash", _body(before=82, after=140), 0)["passed"] is False


def test_rejects_dead_chain_before_kill(qt):
    assert qt._matrix_check(
        "guard_crash", _body(before=3, after=3), 0)["passed"] is False


def test_rejects_bypass(qt):
    assert qt._matrix_check(
        "guard_crash", _body(nonguard=2), 0)["passed"] is False


def test_rejects_guard_survivor(qt):
    assert qt._matrix_check(
        "guard_crash", _body(alive=1), 0)["passed"] is False


def test_rejects_silent_controller(qt):
    assert qt._matrix_check(
        "guard_crash", _body(failed=False), 0)["passed"] is False


def test_step_present_before_cell_policy(qt):
    names = [name for name, _ in qt.TARGET_MATRIX]
    assert len(names) == 16
    assert names.index("guard_crash") == names.index("cell_policy") - 1
    assert "slay -9 genesis_guard" in dict(qt.TARGET_MATRIX)["guard_crash"]


def test_alive_uses_substring_pidin_match(qt):
    # pidin -F %n prints `./genesis_guard` + padding: an anchored
    # ^...$ grep never fires (always-ALIVE=0, vacuous proof).
    cmd = dict(qt.TARGET_MATRIX)["guard_crash"]
    assert "grep -c genesis_guard" in cmd
    assert "^genesis_guard$" not in cmd
