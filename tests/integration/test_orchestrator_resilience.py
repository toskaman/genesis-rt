# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: pipeline failures leave evidence and FAIL (never silent)."""
import json

import pytest

from genesis_rt import evidence, gate
from genesis_rt.ir import IRValidationError
from genesis_rt.orchestrator import PipelineError, run_pipeline


def test_bad_ir_writes_failure_and_raises(amr_ir_path, tmp_path):
    bad = tmp_path / "bad-ir.json"
    bad.write_text('{"schema_version": 1}', encoding="utf-8")
    with pytest.raises(IRValidationError):
        run_pipeline(bad, tmp_path / "runs", run_id="run-bad-ir")
    failure = json.loads((tmp_path / "runs" / "run-bad-ir" / "failure.json").read_text())
    assert failure["failure"]["step"] == "validate"
    assert failure["steps"]["validate"]["status"] == "error"


def test_unknown_scenario_partial_passport_and_fail(amr_ir_path, tmp_path):
    summary = run_pipeline(amr_ir_path, tmp_path / "runs",
                           run_id="run-bad-scenario", scenarios=["nope"])
    assert summary["verdict"] == "FAIL"
    assert summary["failure"]["step"] == "verification"
    assert summary["steps"]["verification"]["status"] == "error"
    passport = evidence.load_passport(summary["passport"])
    assert evidence.verify_chain(passport) == []
    kinds = [r["kind"] for r in passport["chain"]]
    assert "pipeline_error" in kinds and "gate_verdict" in kinds
    assert passport["gate"] == "FAIL"


def test_malformed_target_record_fails_gate(amr_ir_path, tmp_path):
    evil = tmp_path / "target.json"
    evil.write_text('["not", "a", "record"]', encoding="utf-8")
    summary = run_pipeline(amr_ir_path, tmp_path / "runs",
                           run_id="run-bad-target",
                           scenarios=["nominal_navigation"],
                           target_record=evil)
    assert summary["verdict"] == "FAIL"
    assert summary["failure"]["step"] == "qnx_target"
    assert summary["steps"]["qnx_target"]["status"] == "error"
    passport = evidence.load_passport(summary["passport"])
    assert evidence.verify_chain(passport) == []
    assert any("pipeline error" in r for r in
               gate.evaluate(passport, ["nominal_navigation"])["reasons"])


def test_failed_scenario_truthful_verification_status(amr_ir_path, tmp_path, monkeypatch):
    from genesis_rt.simulator import DiffDriveSim
    monkeypatch.setattr(DiffDriveSim, "stopped",
                        lambda self: self.apply(0.5, 0.0))  # broken watchdog
    summary = run_pipeline(amr_ir_path, tmp_path / "runs",
                           run_id="run-watchdog",
                           scenarios=["planner_process_crash"])
    assert summary["steps"]["verification"]["status"] == "fail"
    assert summary["steps"]["verification"]["scenarios"] == {
        "planner_process_crash": "fail"}
    assert summary["verdict"] == "FAIL"
    assert summary["failure"] is None  # honest scenario fail, not a pipeline error


def test_run_id_collision_refused(amr_ir_path, tmp_path):
    first = run_pipeline(amr_ir_path, tmp_path / "runs",
                         run_id="run-fixed", scenarios=["nominal_navigation"])
    assert first["verdict"] == "PASS"
    with pytest.raises(PipelineError, match="collision"):
        run_pipeline(amr_ir_path, tmp_path / "runs",
                     run_id="run-fixed", scenarios=["nominal_navigation"])


def test_success_path_reports_no_failure(amr_ir_path, tmp_path):
    summary = run_pipeline(amr_ir_path, tmp_path / "runs",
                           scenarios=["nominal_navigation"])
    assert summary["verdict"] == "PASS"
    assert summary["failure"] is None
    assert summary["steps"]["verification"]["status"] == "ok"
