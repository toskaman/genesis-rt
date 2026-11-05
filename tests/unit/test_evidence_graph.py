# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: Evidence Graph model, compare, text render, CLI."""
import copy
import json

import pytest

from genesis_rt import evidence, faultlab, gate
from genesis_rt.evidence_graph import (GraphTooLarge, InvalidPassport,
                                       build_graph, compare_graphs,
                                       render_graph_text)


@pytest.fixture()
def full(amr_ir):
    return list(amr_ir["verification"]["scenarios"])


def _passport(amr_ir, bound_evidence, scenarios, tag, tgt="__host__",
              ir_override=None, mutate=None):
    results = faultlab.run_all(ir_override or amr_ir, scenarios)
    if mutate is not None:
        mutate(results)
    p = evidence.build_passport(
        f"run-{tag}", ir_override or amr_ir, bound_evidence["manifest"],
        results, bound_evidence["build"],
        None if tgt == "__host__" else tgt)
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios))


def _by_id(graph):
    return {n["id"]: n for n in graph["nodes"]}


def test_host_graph_shape_and_no_dangling_edges(amr_ir, bound_evidence, full):
    g = build_graph(_passport(amr_ir, bound_evidence, full, "shape"))
    assert g["chain_valid"] is True and g["bound"] is False
    assert g["ir_attached"] is False and g["requirements"] == 0
    by_id = _by_id(g)
    assert by_id["verdict"]["data"]["verdict"] == "PASS"
    assert by_id["ir"]["data"]["machine"]["id"] == "amr-demo-01"
    assert by_id["target"]["status"] == "missing"
    assert by_id["scenario:nominal_navigation"]["status"] == "verified"
    assert by_id["check:speed_command_over_limit:over_limit_denied"]["status"] \
        == "verified"
    kinds = {n["type"] for n in g["nodes"]}
    assert {"verdict", "ir", "limit", "file", "build", "binary", "target",
            "scenario", "check", "observation"} <= kinds
    for e in g["edges"]:
        assert e["from"] in by_id and e["to"] in by_id, e
    assert g["counts"]["nodes"] == len(g["nodes"])


def test_v2_requirements_resolve_to_scenarios(amr_ir, bound_evidence, full,
                                              repo_root):
    p = _passport(amr_ir, bound_evidence, full, "req")
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
                     ).read_text(encoding="utf-8"))
    g = build_graph(p, v2)
    assert g["ir_attached"] is True and g["requirements"] == 2
    by_id = _by_id(g)
    req = by_id["req:REQ-AMR-01"]
    assert req["status"] == "verified"
    assert "Over-limit" in req["label"]
    assert ("req:REQ-AMR-01", "verified_by",
            "scenario:speed_command_over_limit") in [
                (e["from"], e["predicate"], e["to"]) for e in g["edges"]]


def test_requirement_unverified_when_scenario_not_run(amr_ir, bound_evidence,
                                                      repo_root):
    p = _passport(amr_ir, bound_evidence, ["nominal_navigation"], "subset")
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
                     ).read_text(encoding="utf-8"))
    g = build_graph(p, v2)
    by_id = _by_id(g)
    assert by_id["req:REQ-AMR-01"]["status"] == "unverified"
    assert by_id["req:REQ-AMR-01"]["data"]["scenario_status"] == "not_run"


def _fail_dropped(results):
    for res in results:
        if res["scenario"] == "dropped_message":
            res["checks"][0]["passed"] = False
            res["status"] = "fail"


def test_failing_check_marks_failed_by_trace(amr_ir, bound_evidence, full):
    # The oracle fails before chaining, so the passport stays valid and the
    # graph must report the failure (not reject the passport).
    p = _passport(amr_ir, bound_evidence, full, "failcase",
                  mutate=_fail_dropped)
    assert evidence.verify_chain(p) == []
    g = build_graph(p)
    by_id = _by_id(g)
    cid = "check:dropped_message:gap_detected"
    assert by_id[cid]["status"] == "failed"
    assert (cid, "failed_by", "trace:dropped_message") in [
        (e["from"], e["predicate"], e["to"]) for e in g["edges"]]
    assert by_id["scenario:dropped_message"]["status"] == "failed"
    assert by_id["verdict"]["data"]["verdict"] == "FAIL"


def test_bound_graph_shows_processes_and_matrix(amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "bound",
                  tgt=bound_evidence["target"])
    g = build_graph(p)
    assert g["bound"] is True
    by_id = _by_id(g)
    assert by_id["target"]["status"] == "verified"
    assert by_id["process:genesis_guard"]["status"] == "verified"
    assert by_id["process:genesis_guard"]["data"]["matched"] is True
    assert by_id["tcheck:limits_differ"]["status"] == "verified"
    assert by_id["tcheck:limits_differ"]["artifacts"][
        "transcript_sha256"] == "cd" * 32
    triples = [(e["from"], e["predicate"], e["to"]) for e in g["edges"]]
    assert ("process:genesis_guard", "executed_as",
            "binary:genesis_guard") in triples
    assert ("build", "verified_by", "target") in triples
    assert ("verdict", "derives_from", "target") in triples
    assert by_id["verdict"]["data"]["qnx_verified"] is True


def test_tampered_and_legacy_passports_rejected(amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "tamper")
    p["chain"][0]["body"]["ir_sha256"] = "0" * 64
    with pytest.raises(InvalidPassport, match="hash mismatch"):
        build_graph(p)
    legacy = _passport(amr_ir, bound_evidence, ["nominal_navigation"],
                       "legacy")
    legacy["passport_version"] = 0
    with pytest.raises(InvalidPassport, match="passport_version"):
        build_graph(legacy)
    with pytest.raises(InvalidPassport):
        build_graph({"chain": []})


def test_oversize_inputs_capped(amr_ir, bound_evidence, full):
    with pytest.raises(GraphTooLarge):
        build_graph({"chain": [], "pad": "x" * (3 * 1024 * 1024)})
    p = _passport(amr_ir, bound_evidence, ["nominal_navigation"], "big")
    with pytest.raises(GraphTooLarge):
        build_graph(p, {"pad": "x" * (300 * 1024)})


def test_compare_graphs_spots_limit_change(amr_ir, bound_evidence, full,
                                           amr_ir_dict):
    before = _passport(amr_ir, bound_evidence, full, "cmp-a")
    changed_ir = copy.deepcopy(amr_ir_dict)
    changed_ir["control"]["max_linear_speed_mps"] = 0.9
    from genesis_rt.ir import validate_ir
    after = _passport(amr_ir, bound_evidence, full, "cmp-b",
                      ir_override=validate_ir(changed_ir))
    diff = compare_graphs(build_graph(before), build_graph(after))
    assert diff["from_run"] == "run-cmp-a" and diff["to_run"] == "run-cmp-b"
    changed_ids = {c["id"] for c in diff["changed"]}
    assert "limit:max_linear_speed_mps" in changed_ids
    assert "verdict" not in changed_ids  # both runs PASS; graph is honest
    assert diff["added"] == [] and diff["removed"] == []
    assert diff["edges_added"] == [] and diff["edges_removed"] == []


def test_render_graph_text(amr_ir, bound_evidence, full, repo_root):
    p = _passport(amr_ir, bound_evidence, full, "text")
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
                     ).read_text(encoding="utf-8"))
    text = render_graph_text(build_graph(p, v2))
    assert "run-text" in text and "gate PASS" in text
    assert "REQ-AMR-01" in text and "Over-limit" in text
    assert "target (missing)" in text
    bare = render_graph_text(build_graph(p))
    assert "attach --ir" in bare


def test_cli_graph_command(amr_ir, bound_evidence, full, tmp_path, capsys,
                           repo_root):
    from genesis_rt.cli import main

    p = _passport(amr_ir, bound_evidence, full, "cli")
    pp = tmp_path / "passport.json"
    pp.write_text(json.dumps(p), encoding="utf-8")
    v2 = repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
    assert main(["graph", str(pp), "--ir", str(v2)]) == 0
    out = capsys.readouterr().out
    assert "REQ-AMR-01" in out and "gate PASS" in out
    assert main(["graph", str(pp), "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["run_id"] == "run-cli" and doc["counts"]["nodes"] > 50
    pp.write_text(json.dumps({"chain": []}), encoding="utf-8")
    assert main(["graph", str(pp)]) == 2
    assert "passport" in capsys.readouterr().err.lower()
