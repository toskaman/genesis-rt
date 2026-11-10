# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: W1 demo-break (seal -> mutate -> STALE in seconds)."""
import json

from genesis_rt.breakdemo import BUDGET_S, run_break_demo
from genesis_rt.cli import main


def test_run_break_demo_stale_names_binary(tmp_path):
    report = run_break_demo(tmp_path / "ws")
    assert report["stale"]["verdict"] == "STALE"
    assert report["stale"]["stale_binaries"] == ["genesis_guard"]
    assert report["elapsed_s"] >= 0.0
    assert report["elapsed_s"] < BUDGET_S


def test_run_break_demo_fresh_stage_consistent(tmp_path):
    report = run_break_demo(tmp_path / "ws")
    assert report["fresh"]["verdict"] == "CONSISTENT"
    assert report["binaries"] == ["genesis_controller", "genesis_guard"]


def test_cli_demo_break_exit_zero(capsys):
    rc = main(["demo-break"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STALE" in out
    assert "genesis_guard" in out
    assert "the wrong binary cannot pass" in out


def test_cli_demo_break_json(capsys):
    rc = main(["demo-break", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    body = json.loads(out)
    assert body["stale"]["verdict"] == "STALE"
