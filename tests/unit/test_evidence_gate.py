# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: evidence chain build/verify/tamper + gate fail-closed."""
import copy

from genesis_rt import codegen, evidence, faultlab, gate


def _passport(amr_ir, tmp_path, scenarios=None):
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    results = faultlab.run_all(amr_ir, scenarios or ["nominal_navigation"])
    return evidence.build_passport("run-test", amr_ir, manifest, results,
                                   {"status": "blocked", "verified_on_target": False})


def test_chain_valid(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    assert evidence.verify_chain(p) == []


def test_chain_deterministic(amr_ir, tmp_path):
    p1 = _passport(amr_ir, tmp_path / "a")
    p2 = _passport(amr_ir, tmp_path / "b")
    h1 = [r["hash"] for r in p1["chain"]]
    h2 = [r["hash"] for r in p2["chain"]]
    assert h1 == h2  # wall clock excluded from hashes


def test_tamper_detected(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    p["chain"][3]["body"]["status"] = "pass"
    p["chain"][3]["body"]["seed"] = 12345  # mutate a scenario record
    assert evidence.verify_chain(p) != []


def test_save_load_roundtrip(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    path = evidence.save_passport(p, tmp_path / "p.json")
    q = evidence.load_passport(path)
    assert evidence.verify_chain(q) == []
    assert q["run_id"] == "run-test"


def test_gate_pass_and_verdict_chained(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    verdict = gate.evaluate(p, ["nominal_navigation"])
    assert verdict["verdict"] == "PASS"
    assert verdict["qnx_verified"] is False
    evidence.attach_verdict(p, verdict)
    assert evidence.verify_chain(p) == []
    assert p["gate"] == "PASS"


def test_gate_qnx_verified_from_target_record(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    assert gate.evaluate(p, ["nominal_navigation"])["qnx_verified"] is False
    rec = {"status": "ok", "verified_on_target": True,
           "checks": [{"name": "a", "passed": True, "detail": "x"}]}
    p2 = evidence.build_passport(
        "run-t", amr_ir, codegen.generate(amr_ir, tmp_path / "g2"),
        faultlab.run_all(amr_ir, ["nominal_navigation"]),
        {"status": "ok", "verified_on_target": False}, rec)
    v = gate.evaluate(p2, ["nominal_navigation"])
    assert (v["verdict"], v["qnx_verified"]) == ("PASS", True)
    rec["checks"][0]["passed"] = False
    p3 = evidence.build_passport(
        "run-t3", amr_ir, codegen.generate(amr_ir, tmp_path / "g3"),
        faultlab.run_all(amr_ir, ["nominal_navigation"]),
        {"status": "ok", "verified_on_target": False}, rec)
    v3 = gate.evaluate(p3, ["nominal_navigation"])
    assert (v3["verdict"], v3["qnx_verified"]) == ("PASS", False)


def test_gate_fails_closed(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    # missing scenario
    v = gate.evaluate(p, ["nominal_navigation", "stale_proximity_150ms"])
    assert v["verdict"] == "FAIL"
    # empty required set refuses vacuous pass
    v = gate.evaluate(p, [])
    assert v["verdict"] == "FAIL"
    # tampered chain
    bad = copy.deepcopy(p)
    bad["chain"][1]["body"]["ir_sha256"] = "0" * 64
    v = gate.evaluate(bad, ["nominal_navigation"])
    assert v["verdict"] == "FAIL"
    # missing qnx record
    bad = copy.deepcopy(p)
    bad["chain"] = [r for r in bad["chain"] if r["kind"] != "qnx_build"]
    v = gate.evaluate(bad, ["nominal_navigation"])
    assert v["verdict"] == "FAIL"


def test_gate_rejects_pipeline_error_record(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    results = faultlab.run_all(amr_ir, ["nominal_navigation"])
    p = evidence.build_passport(
        "run-err", amr_ir, manifest, results,
        {"status": "blocked", "verified_on_target": False},
        pipeline_error={"step": "qnx_target", "error": "ValueError: boom"})
    v = gate.evaluate(p, ["nominal_navigation"])
    assert v["verdict"] == "FAIL"
    assert any("qnx_target" in r for r in v["reasons"])


def test_gate_rejects_duplicate_kinds(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    dup = copy.deepcopy(p["chain"][4])
    p["chain"].append(dup)  # second scenario record, same kind
    v = gate.evaluate(p, ["nominal_navigation"])
    assert v["verdict"] == "FAIL"
    assert any("duplicate" in r for r in v["reasons"])
