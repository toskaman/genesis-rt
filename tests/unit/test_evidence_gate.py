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


def test_gate_qnx_verified_from_target_record(amr_ir, tmp_path, bound_evidence):
    p = _passport(amr_ir, tmp_path)
    assert gate.evaluate(p, ["nominal_navigation"])["qnx_verified"] is False
    rec = bound_evidence["target"]
    p2 = evidence.build_passport(
        "run-t", amr_ir, bound_evidence["manifest"],
        faultlab.run_all(amr_ir, ["nominal_navigation"]),
        bound_evidence["build"], rec)
    v = gate.evaluate(p2, ["nominal_navigation"])
    assert (v["verdict"], v["qnx_verified"]) == ("PASS", True)
    rec["checks"][0]["passed"] = False
    p3 = evidence.build_passport(
        "run-t3", amr_ir, bound_evidence["manifest"],
        faultlab.run_all(amr_ir, ["nominal_navigation"]),
        bound_evidence["build"], rec)
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


def _passport_with(amr_ir, tmp_path, tag, qnx_build, qnx_target=None,
                   scenarios=None):
    return evidence.build_passport(
        f"run-{tag}", amr_ir, codegen.generate(amr_ir, tmp_path / f"g-{tag}"),
        faultlab.run_all(amr_ir, scenarios or ["nominal_navigation"]),
        qnx_build, qnx_target)


def test_gate_levels_host_to_compiled(amr_ir, tmp_path):
    # Host PASS with a blocked QNX build: honest HOST_TESTED tier, and a
    # host PASS must never read as release-eligible.
    p = _passport_with(amr_ir, tmp_path, "host",
                       {"status": "blocked", "verified_on_target": False})
    v = gate.evaluate(p, ["nominal_navigation"])
    assert (v["verdict"], v["level"], v["qnx_verified"],
            v["release_eligible"]) == ("PASS", "HOST_TESTED", False, False)
    assert any("QNX_COMPILED" in r for r in v["level_reasons"])
    # Real native build, no target run yet: compiled but not executed.
    p = _passport_with(amr_ir, tmp_path, "compiled",
                       {"status": "ok", "verified_on_target": False})
    v = gate.evaluate(p, ["nominal_navigation"])
    assert (v["verdict"], v["level"], v["release_eligible"]) == (
        "PASS", "QNX_COMPILED", False)


def test_gate_levels_executed_vs_behavior_verified(
        amr_ir, tmp_path, bound_evidence):
    build = {"status": "ok", "verified_on_target": False}
    # Target ran but a check failed: executed, not behavior-verified.
    tgt = {"status": "ok", "verified_on_target": False,
           "checks": [{"name": "a", "passed": True, "detail": "x"},
                      {"name": "b", "passed": False, "detail": "y"}]}
    v = gate.evaluate(_passport_with(amr_ir, tmp_path, "exec", build, tgt),
                      ["nominal_navigation"])
    assert (v["verdict"], v["level"], v["qnx_verified"],
            v["release_eligible"]) == ("PASS", "QNX_EXECUTED", False, False)
    # All target checks pass with FULL coverage AND full provenance
    # binding: behavior verified, release eligible. (§10: a subset must
    # never yield release eligibility; see
    # test_gate_reduced_coverage_blocks_release.)
    # Full coverage = IR-declared scenarios (belt_jam is conveyor-only and
    # is not declared by the AMR IR).
    full = list(amr_ir["verification"]["scenarios"])
    p = evidence.build_passport(
        "run-verified", amr_ir, bound_evidence["manifest"],
        faultlab.run_all(amr_ir, full),
        bound_evidence["build"], bound_evidence["target"])
    v = gate.evaluate(p, full)
    assert (v["verdict"], v["level"], v["qnx_verified"],
            v["release_eligible"]) == (
                "PASS", "QNX_BEHAVIOR_VERIFIED", True, True)
    assert v["coverage"]["omitted"] == []


def test_gate_binds_target_evidence_to_build(amr_ir, tmp_path):
    # Target evidence without a successful native build proves nothing:
    # behavior claims must bind to compiled artifacts.
    tgt = {"status": "ok", "verified_on_target": True,
           "checks": [{"name": "a", "passed": True, "detail": "x"}]}
    v = gate.evaluate(_passport_with(
        amr_ir, tmp_path, "unbound",
        {"status": "blocked", "verified_on_target": False}, tgt),
        ["nominal_navigation"])
    assert (v["level"], v["qnx_verified"],
            v["release_eligible"]) == ("HOST_TESTED", False, False)


def test_gate_reduced_coverage_blocks_release(amr_ir, tmp_path, bound_evidence):
    """Subset required + all-pass BOUND target evidence: the required
    scenarios did pass (verdict PASS), but release is REFUSED loudly:
    coverage is recorded and release_eligible is False. A caller must
    never silently shrink verification and still receive a full-release
    PASS."""
    p = evidence.build_passport(
        "run-reduced", amr_ir, bound_evidence["manifest"],
        faultlab.run_all(amr_ir, ["nominal_navigation"]),
        bound_evidence["build"], bound_evidence["target"])
    v = gate.evaluate(p, ["nominal_navigation"])
    declared = amr_ir["verification"]["scenarios"]
    assert v["verdict"] == "PASS"
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"
    assert v["release_eligible"] is False
    assert v["coverage"]["required"] == 1
    assert v["coverage"]["declared"] == len(declared)
    assert v["coverage"]["omitted"] == sorted(
        s for s in declared if s != "nominal_navigation")
    assert any("reduced coverage" in r for r in v["level_reasons"])


def test_gate_full_coverage_keeps_release(amr_ir, tmp_path, bound_evidence):
    full = list(amr_ir["verification"]["scenarios"])
    results = faultlab.run_all(amr_ir, full)
    p = evidence.build_passport(
        "run-full", amr_ir, bound_evidence["manifest"], results,
        bound_evidence["build"], bound_evidence["target"])
    v = gate.evaluate(p, full)
    assert (v["verdict"], v["level"], v["release_eligible"]) == (
        "PASS", "QNX_BEHAVIOR_VERIFIED", True)
    assert v["coverage"]["omitted"] == []


def test_gate_perf_record_earns_top_tier(amr_ir, tmp_path, bound_evidence):
    full = list(amr_ir["verification"]["scenarios"])
    results = faultlab.run_all(amr_ir, full)
    p = evidence.build_passport(
        "run-perf", amr_ir, bound_evidence["manifest"], results,
        bound_evidence["build"], bound_evidence["target"],
        qnx_perf=bound_evidence["perf"])
    assert evidence.verify_chain(p) == []
    v = gate.evaluate(p, full)
    assert (v["verdict"], v["level"], v["release_eligible"]) == (
        "PASS", "QNX_PERFORMANCE_MEASURED", True)
    assert [r["kind"] for r in p["chain"]].count("qnx_perf") == 1


def test_gate_level_none_on_failure(amr_ir, tmp_path):
    p = _passport(amr_ir, tmp_path)
    v = gate.evaluate(p, ["nominal_navigation", "stale_proximity_150ms"])
    assert (v["verdict"], v["level"],
            v["release_eligible"]) == ("FAIL", "NONE", False)
    bad = copy.deepcopy(p)
    bad["chain"][1]["body"]["ir_sha256"] = "0" * 64
    v = gate.evaluate(bad, ["nominal_navigation"])
    assert v["level"] == "NONE"
