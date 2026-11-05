# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: sched campaign command builder + pidin policy parser."""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_sched", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def test_configs_are_four_unique(qt):
    names = [n for n, _, _ in qt.SCHED_CONFIGS]
    assert names == ["baseline", "fifo_guard", "fifo_both", "rr_both"]


def test_baseline_has_no_on_flag(qt):
    cmd = qt._sched_command(None, None, 200)
    assert "on -p" not in cmd
    assert "bench 200" in cmd
    assert "---SCHED-PIDIN---" in cmd


def test_fifo_both_sets_both(qt):
    cmd = qt._sched_command("20f", "20f", 200)
    assert cmd.count("on -p 20f") == 2
    assert "bench 200" in cmd


def test_fifo_guard_sets_guard_only(qt):
    cmd = qt._sched_command("20f", None, 50)
    assert "on -p 20f ./genesis_guard" in cmd
    assert "on -p" not in cmd.split("bench")[1].split(";")[0]
    assert "bench 50" in cmd


def test_rr_policy_suffix_passes_through(qt):
    cmd = qt._sched_command("20r", "20r", 200)
    assert "on -p 20r ./genesis_guard" in cmd
    assert "on -p 20r ./genesis_faultinject" in cmd


def test_command_slays_secondaries_first(qt):
    cmd = qt._sched_command("20f", "20f", 200)
    assert "slay genesis_guard_conv" in cmd
    assert "slay genesis_guard_v2" in cmd


def test_parse_observed_fifo(qt):
    body = "---SCHED-PIDIN---\n24109083   1 ./genesis_guard               20f RECEIVE        1\n"
    assert qt._parse_sched_observed(body) == "20f"


def test_parse_observed_default_rr(qt):
    body = "24162331   1 ./genesis_guard               10r RECEIVE        1\n"
    assert qt._parse_sched_observed(body) == "10r"


def test_parse_observed_ignores_conv_guard(qt):
    body = ("24162331   1 ./genesis_guard_conv          10r RECEIVE        1\n"
            "24162332   1 ./genesis_guard_v2            10r RECEIVE        1\n")
    assert qt._parse_sched_observed(body) is None


def test_parse_observed_missing(qt):
    assert qt._parse_sched_observed("no pidin here\n") is None
