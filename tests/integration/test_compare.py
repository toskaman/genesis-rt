# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: run-directory comparison (broken-vs-fixed story)."""
import copy
import json

import pytest

from genesis_rt.cli import main
from genesis_rt.compare import compare_runs, render_text
from genesis_rt.orchestrator import run_pipeline


def _run(ir_path, tmp_path, run_id, scenarios):
    return run_pipeline(ir_path, tmp_path / "runs", run_id=run_id,
                       scenarios=scenarios)


def test_compare_identical_run_is_empty(amr_ir_path, tmp_path):
    summary = _run(amr_ir_path, tmp_path, "run-same", ["nominal_navigation"])
    comp = compare_runs(summary["run_dir"], summary["run_dir"])
    assert comp["ir"]["ir_sha256_equal"] is True
    assert comp["generated"]["changed"] == []
    assert comp["generated"]["only_a"] == comp["generated"]["only_b"] == []
    assert comp["scenarios"]["status_changes"] == {}
    assert comp["verdict"]["changed"] is False
    assert "verdict changed: False" in render_text(comp)


def test_compare_two_machines(amr_ir_path, repo_root, tmp_path):
    a = _run(amr_ir_path, tmp_path, "run-amr", ["nominal_navigation"])
    conv_ir = repo_root / "examples" / "conveyor-demo" / "machine-ir.json"
    b = _run(conv_ir, tmp_path, "run-conv", ["nominal_navigation"])
    comp = compare_runs(a["run_dir"], b["run_dir"])
    assert comp["ir"]["machine_a"] == "amr-demo-01"
    assert comp["ir"]["machine_b"] == "conveyor-demo-01"
    assert comp["ir"]["ir_sha256_equal"] is False
    assert "genesis_config_gen.h" in comp["generated"]["changed"]
    diff = comp["generated"]["diffs"]["genesis_config_gen.h"]
    assert "1.2" in diff and "2.0" in diff  # the limit change, visible
    assert comp["run_a"] == "run-amr" and comp["run_b"] == "run-conv"


def test_compare_limit_mutation_same_machine(amr_ir_path, tmp_path):
    base = _run(amr_ir_path, tmp_path, "run-base", ["nominal_navigation"])
    ir = json.loads(amr_ir_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(ir)
    mutated["control"]["max_linear_speed_mps"] = 0.5
    mutated_path = tmp_path / "mutated-ir.json"
    mutated_path.write_text(json.dumps(mutated), encoding="utf-8")
    other = _run(mutated_path, tmp_path, "run-mut", ["nominal_navigation"])
    comp = compare_runs(base["run_dir"], other["run_dir"])
    assert comp["ir"]["machine_a"] == comp["ir"]["machine_b"] == "amr-demo-01"
    assert comp["ir"]["ir_sha256_equal"] is False
    diff = comp["generated"]["diffs"]["genesis_config_gen.h"]
    assert "-1.2" in diff or "1.2" in diff
    assert "0.5" in diff
    # same verdict shape on the nominal scenario; nothing silently dropped
    assert comp["verdict"]["a"]["verdict"] == comp["verdict"]["b"]["verdict"]


def test_compare_rejects_non_run_dir(tmp_path):
    with pytest.raises(ValueError, match="not a run directory"):
        compare_runs(tmp_path, tmp_path)


def test_cli_compare_text_and_json(amr_ir_path, tmp_path, capsys):
    a = _run(amr_ir_path, tmp_path, "run-ca", ["nominal_navigation"])
    b = _run(amr_ir_path, tmp_path, "run-cb", ["nominal_navigation"])
    assert main(["compare", a["run_dir"], b["run_dir"]]) == 0
    out = capsys.readouterr().out
    assert "run-ca" in out and "run-cb" in out
    assert main(["compare", "--json", a["run_dir"], b["run_dir"]]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["run_a"] == "run-ca"
    assert payload["verdict"]["changed"] is False
