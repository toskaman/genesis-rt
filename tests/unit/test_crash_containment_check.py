# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: controller_crash + device_crash containment steps.

controller_crash: killed source freezes device AND guard log, guard survives.
device_crash: killed sink freezes device log, guard keeps deciding,
controller + guard survive.
"""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_cc", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _ctrl_body(before=81, after=83, gbefore=82, gafter=83, nonguard=0,
               calive=0, galive=1):
    return "\n".join([f"BEFORE={before}", f"GBEFORE={gbefore}",
                      f"AFTER={after}", f"GAFTER={gafter}",
                      f"NONGUARD={nonguard}", f"CALIVE={calive}",
                      f"GALIVE={galive}"])


def _dev_body(before=81, after=82, gbefore=82, gafter=144, nonguard=0,
              dalive=0, calive=1, galive=1):
    return "\n".join([f"BEFORE={before}", f"GBEFORE={gbefore}",
                      f"AFTER={after}", f"GAFTER={gafter}",
                      f"NONGUARD={nonguard}", f"DALIVE={dalive}",
                      f"CALIVE={calive}", f"GALIVE={galive}"])


def test_ctrl_accepts_live_shape(qt):
    assert qt._matrix_check("controller_crash", _ctrl_body(), 0)["passed"] is True


def test_ctrl_rejects_runaway_device(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(before=81, after=120), 0)["passed"] is False


def test_ctrl_rejects_phantom_guard_traffic(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(gbefore=82, gafter=140), 0)["passed"] is False


def test_ctrl_rejects_dead_chain_before_kill(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(before=3, after=3, gbefore=3, gafter=3),
        0)["passed"] is False


def test_ctrl_rejects_bypass(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(nonguard=1), 0)["passed"] is False


def test_ctrl_rejects_controller_survivor(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(calive=1), 0)["passed"] is False


def test_ctrl_rejects_guard_casualty(qt):
    assert qt._matrix_check(
        "controller_crash", _ctrl_body(galive=0), 0)["passed"] is False


def test_dev_accepts_live_shape(qt):
    assert qt._matrix_check("device_crash", _dev_body(), 0)["passed"] is True


def test_dev_rejects_runaway_device(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(before=81, after=120), 0)["passed"] is False


def test_dev_rejects_guard_stall(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(gbefore=82, gafter=83), 0)["passed"] is False


def test_dev_rejects_dead_chain_before_kill(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(before=3, after=3), 0)["passed"] is False


def test_dev_rejects_bypass(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(nonguard=1), 0)["passed"] is False


def test_dev_rejects_device_survivor(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(dalive=1), 0)["passed"] is False


def test_dev_rejects_controller_casualty(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(calive=0), 0)["passed"] is False


def test_dev_rejects_guard_casualty(qt):
    assert qt._matrix_check(
        "device_crash", _dev_body(galive=0), 0)["passed"] is False


def test_steps_ordered_before_guard_crash(qt):
    names = [name for name, _ in qt.TARGET_MATRIX]
    assert len(names) == 16
    assert names[-1] == "cell_policy"
    assert names.index("controller_crash") < names.index("device_crash")
    assert names.index("device_crash") == names.index("guard_crash") - 1
    assert names.index("guard_crash") == names.index("cell_policy") - 1
    assert "slay -9 genesis_controller" in dict(qt.TARGET_MATRIX)["controller_crash"]
    assert "slay -9 genesis_device" in dict(qt.TARGET_MATRIX)["device_crash"]


def test_crash_steps_use_substring_pidin_match(qt):
    # Same pidin lesson as guard_crash: no anchored ^...$ patterns.
    cmds = dict(qt.TARGET_MATRIX)
    for step in ("controller_crash", "device_crash", "guard_crash"):
        assert "^genesis_" not in cmds[step]
    assert "grep -c genesis_controller" in cmds["controller_crash"]
    assert "grep -c genesis_device" in cmds["device_crash"]
