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


def test_compare_contract_limits_diff(amr_ir_path, tmp_path):
    base = _run(amr_ir_path, tmp_path, "run-ctra", ["nominal_navigation"])
    ir = json.loads(amr_ir_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(ir)
    mutated["control"]["max_linear_speed_mps"] = 0.5
    mutated_path = tmp_path / "mutated-ir.json"
    mutated_path.write_text(json.dumps(mutated), encoding="utf-8")
    other = _run(mutated_path, tmp_path, "run-ctrb", ["nominal_navigation"])
    comp = compare_runs(base["run_dir"], other["run_dir"])
    contract = comp["contract"]
    assert contract["limits_known"] is True
    assert contract["machine_changed"] is False
    assert contract["limits_changed"] == {
        "max_linear_speed_mps": [1.2, 0.5]}
    assert "max_linear_speed_mps: 1.2 -> 0.5" in render_text(comp)


def test_compare_broken_vs_fixed_cell(repo_root, tmp_path):
    broken_ir = (repo_root / "examples" / "cell-demo"
                 / "cell-ir-broken.json")
    fixed_ir = repo_root / "examples" / "cell-demo" / "cell-ir.json"
    a = _run(broken_ir, tmp_path, "run-broken", ["cell_nominal_transfer"])
    b = _run(fixed_ir, tmp_path, "run-fixed", ["cell_nominal_transfer"])
    comp = compare_runs(a["run_dir"], b["run_dir"])
    assert comp["contract"]["limits_changed"] == {
        "max_linear_speed_mps": [0.3, 1.2]}
    assert comp["scenarios"]["fixed"] == ["cell_nominal_transfer"]
    assert comp["scenarios"]["broken"] == []
    assert comp["verdict"]["changed"] is True
    text = render_text(comp)
    assert "fixed: ['cell_nominal_transfer']" in text
    assert "max_linear_speed_mps: 0.3 -> 1.2" in text


def _min_run(tmp_path, name, body_extra=None, binary=None):
    d = tmp_path / name
    (d / "generated").mkdir(parents=True)
    (d / "generated" / "genesis_config_gen.h").write_text(
        "// config\n", encoding="utf-8")
    if binary is not None:
        (d / "generated" / "genesis_guard").write_bytes(binary)
    chain = [
        {"kind": "ir", "body": {"ir_sha256": "aa" * 32,
                               "machine": {"id": "m", "kind": "amr"},
                               "scenarios": ["s1"]}},
        {"kind": "gate_verdict", "body": {"verdict": "PASS",
                                          "level": "NONE",
                                          "release_eligible": False}},
    ]
    if body_extra:
        chain.insert(1, body_extra)
    (d / "passport.json").write_text(
        json.dumps({"run_id": name, "gate": "PASS", "chain": chain}),
        encoding="utf-8")
    return d


def test_compare_measurements_delta(tmp_path):
    perf_a = {"kind": "qnx_perf",
              "body": {"status": "ok", "measurements": {
                  "ipc_roundtrip_us": {"count": 100, "p50": 300.0,
                                       "p95": 500.0, "p99": 600.0,
                                       "max": 800.0}}}}
    perf_b = {"kind": "qnx_perf",
              "body": {"status": "ok", "measurements": {
                  "ipc_roundtrip_us": {"count": 100, "p50": 250.0,
                                       "p95": 500.0, "p99": 600.0,
                                       "max": 800.0}}}}
    a = _min_run(tmp_path, "run-pa", perf_a)
    b = _min_run(tmp_path, "run-pb", perf_b)
    comp = compare_runs(a, b)
    assert comp["measurements"]["changed"] == {
        "ipc_roundtrip_us": {"p50": [300.0, 250.0]}}
    assert "ipc_roundtrip_us.p50: 300.0 -> 250.0" in render_text(comp)


def test_compare_measurements_absent_is_honest(tmp_path):
    a = _min_run(tmp_path, "run-ma")
    b = _min_run(tmp_path, "run-mb")
    comp = compare_runs(a, b)
    assert comp["measurements"] == {"only_a": [], "only_b": [],
                                    "changed": {}}
    assert "measurements changed: -" in render_text(comp)
    assert comp["contract"]["limits_known"] is False


def test_compare_binaries_hashed_not_dumped(tmp_path):
    a = _min_run(tmp_path, "run-ba", binary=b"\x7fELF\xff\xfe-broken")
    b = _min_run(tmp_path, "run-bb", binary=b"\x7fELF\xff\xfe-fixed!")
    comp = compare_runs(a, b)
    gen = comp["generated"]
    assert gen["changed"] == []
    assert gen["diffs"] == {}
    assert gen["binaries_changed"] == ["genesis_guard"]
    assert "binaries changed (sha256): ['genesis_guard']" in render_text(comp)


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
