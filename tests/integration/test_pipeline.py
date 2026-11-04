# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: full pipeline + planner + CLI surface."""
import json
import subprocess
import sys

from genesis_rt import evidence, gate
from genesis_rt.orchestrator import run_pipeline
from genesis_rt.planner import PlannerRejection, propose


def test_pipeline_pass_host(amr_ir_path, tmp_path):
    summary = run_pipeline(amr_ir_path, tmp_path)
    assert summary["verdict"] == "PASS"
    assert summary["qnx_verified"] is False
    assert summary["steps"]["qnx_build"]["status"] in ("blocked", "ok", "error")
    passport = evidence.load_passport(summary["passport"])
    assert evidence.verify_chain(passport) == []
    assert summary["steps"]["host_cc_check"]["status"] in ("ok", "blocked")


def test_pipeline_all_scenarios_present(amr_ir, amr_ir_path, tmp_path):
    summary = run_pipeline(amr_ir_path, tmp_path)
    got = set(summary["steps"]["verification"]["scenarios"])
    assert got == set(amr_ir["verification"]["scenarios"])


def test_planner_accepts_robot_rejects_gibberish():
    ir = propose("differential drive robot, 10ms period, max 1.2 m/s")
    assert ir["machine"]["kind"] == "differential_drive_robot"
    assert ir["control"]["period_ms"] == 10
    try:
        propose("make me something cool")
    except PlannerRejection:
        pass
    else:
        raise AssertionError("planner must reject unbounded requests")


def test_cli_validate_and_faults(amr_ir_path, repo_root):
    repo = repo_root
    env = {"PYTHONPATH": str(repo / "host")}
    import os
    merged = dict(os.environ, **env)
    r = subprocess.run([sys.executable, "-m", "genesis_rt.cli", "validate", str(amr_ir_path)],
                       capture_output=True, text=True, timeout=60, env=merged)
    assert r.returncode == 0 and "valid:" in r.stdout
    r = subprocess.run([sys.executable, "-m", "genesis_rt.cli", "faults", str(amr_ir_path)],
                       capture_output=True, text=True, timeout=120, env=merged)
    assert r.returncode == 0 and "8/8 scenarios passed" in r.stdout


def test_gate_blocks_known_bad_revision(amr_ir, tmp_path):
    """Deliberately break a revision: gate must refuse release."""
    from genesis_rt import codegen, faultlab
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    results = faultlab.run_all(amr_ir)
    idx = next(i for i, r in enumerate(results) if r["scenario"] == "nominal_navigation")
    results[idx] = dict(results[idx], status="fail",
                        checks=[{"name": "sabotaged", "passed": False, "detail": "injected"}])
    passport = evidence.build_passport("run-bad", amr_ir, manifest, results,
                                       {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, amr_ir["verification"]["scenarios"])
    assert verdict["verdict"] == "FAIL"
    assert any("nominal_navigation=fail" in f for f in verdict["failed"])
