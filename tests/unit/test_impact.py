# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: change-impact analysis, release comparison, CLI."""
import copy
import json

import pytest

from genesis_rt import evidence, faultlab, gate
from genesis_rt.impact import (analyze_impact, release_status,
                               render_impact_text, render_release_text)
from genesis_rt.ir import IRValidationError


@pytest.fixture()
def v2pair(repo_root):
    path = repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
    before = json.loads(path.read_text(encoding="utf-8"))
    return before, copy.deepcopy(before)


def _passport(ir, bound_evidence, tag, build=None, target=None):
    scenarios = list(ir["verification"]["scenarios"])
    results = faultlab.run_all(ir, scenarios)
    p = evidence.build_passport(
        f"run-{tag}", ir, bound_evidence["manifest"], results,
        build if build is not None else bound_evidence["build"], target)
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios))


def test_limit_change_retests_all_and_moves_files(amr_ir_dict):
    before = amr_ir_dict
    after = copy.deepcopy(before)
    after["control"]["max_linear_speed_mps"] = 0.9
    r = analyze_impact(before, after)
    assert r["same_machine"] is True
    assert r["limits"]["changed"] == [
        {"key": "max_linear_speed_mps", "before": 1.2, "after": 0.9}]
    assert {f["name"] for f in r["files"]["changed"]} >= {
        "genesis_config_gen.h", "genesis_build_gen.mk"}
    assert len(r["retest"]) == 8 and r["evidence_invalidated"] is True
    assert r["before"]["ir_sha256"] != r["after"]["ir_sha256"]
    assert "conservative" in r["impacted"][0]["reasons"][0]


def test_requirement_claim_maps_precisely(v2pair):
    before, after = v2pair
    after["verification"]["requirements"][0]["claim"] += " (loudly)"
    r = analyze_impact(before, after)
    assert r["requirements"]["changed"] == ["REQ-AMR-01"]
    assert r["retest"] == ["speed_command_over_limit"]
    assert r["impacted"] == [
        {"scenario": "speed_command_over_limit",
         "reasons": ["requirement REQ-AMR-01 changed"]}]


def test_requirement_relink_covers_both_scenarios(v2pair):
    before, after = v2pair
    after["verification"]["requirements"][0]["scenario"] = "dropped_message"
    r = analyze_impact(before, after)
    assert r["retest"] == ["dropped_message", "speed_command_over_limit"]


def test_no_change_needs_no_retest(amr_ir_dict, v2pair):
    r = analyze_impact(amr_ir_dict, copy.deepcopy(amr_ir_dict))
    assert r["retest"] == [] and r["evidence_invalidated"] is False
    assert r["files"]["changed"] == []
    before, _ = v2pair
    r = analyze_impact(before, copy.deepcopy(before))
    assert r["retest"] == []


def test_machine_swap_is_full_impact(amr_ir_dict):
    after = copy.deepcopy(amr_ir_dict)
    after["machine"]["id"] = "other-01"
    r = analyze_impact(amr_ir_dict, after)
    assert r["same_machine"] is False
    assert len(r["retest"]) == 8
    assert "different machine" in r["impacted"][0]["reasons"][0]


def test_simulation_tweak_is_conservative_global(v2pair):
    before, after = v2pair
    after["simulation"]["seed"] = 7
    r = analyze_impact(before, after)
    assert r["extras_changed"] == ["simulation"]
    assert len(r["retest"]) == 8


def test_scenario_removal_listed_not_retested(amr_ir_dict):
    after = copy.deepcopy(amr_ir_dict)
    after["verification"]["scenarios"].remove("dropped_message")
    r = analyze_impact(amr_ir_dict, after)
    assert r["scenarios"]["removed"] == ["dropped_message"]
    assert r["retest"] == []


def test_invalid_ir_rejected(amr_ir_dict):
    with pytest.raises(IRValidationError):
        analyze_impact({"schema_version": 1}, amr_ir_dict)
    with pytest.raises(IRValidationError):
        analyze_impact(amr_ir_dict, {"schema_version": 99})
    with pytest.raises(IRValidationError):
        release_status(amr_ir_dict, {"nope": True}, {})


def test_release_full_passport_current_and_targeted_complete(
        amr_ir_dict, bound_evidence, tmp_path):
    import genesis_rt.codegen as codegen
    from genesis_rt.ir import validate_ir

    after_dict = copy.deepcopy(amr_ir_dict)
    after_dict["control"]["max_linear_speed_mps"] = 0.9
    after = validate_ir(after_dict)
    manifest = codegen.generate(after, tmp_path / "gen-rel")
    scenarios = list(after["verification"]["scenarios"])
    results = faultlab.run_all(after, scenarios)
    p = evidence.build_passport("run-rel", after, manifest, results,
                                bound_evidence["build"])
    p = evidence.attach_verdict(p, gate.evaluate(p, scenarios))
    s = release_status(amr_ir_dict, after_dict, p)
    assert s["chain_ok"] is True and s["evidence_current"] is True
    assert s["targeted_complete"] is True and s["retest_pending"] == []
    assert s["verdict"] == "PASS" and s["level"] == "QNX_COMPILED"
    # Build ok, no target evidence: the gate still refuses release.
    assert s["release_eligible"] is False and s["qnx_verified"] is False
    assert s["source_changed"] is True
    assert s["binary_changed"] == {"known": False,
                                   "reason": "needs the before-run passport"}


def test_release_stale_passport_pending_and_tamper_finding(
        amr_ir, amr_ir_dict, bound_evidence):
    stale = _passport(amr_ir, bound_evidence, "rel-stale")
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    s = release_status(amr_ir_dict, after, stale)
    assert s["chain_ok"] is True and s["evidence_current"] is False
    assert len(s["retest_pending"]) == 8
    assert s["targeted_complete"] is False
    bad = copy.deepcopy(stale)
    bad["chain"][0]["body"]["ir_sha256"] = "0" * 64
    s = release_status(amr_ir_dict, after, bad)
    assert s["chain_ok"] is False and "hash mismatch" in s["chain_errors"][0]
    assert s["evidence_current"] is False


def test_release_binary_comparison_needs_both_sides(
        amr_ir, amr_ir_dict, bound_evidence):
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    p1 = _passport(amr_ir, bound_evidence, "rel-b1",
                   target=bound_evidence["target"])
    build2 = copy.deepcopy(bound_evidence["build"])
    build2["binaries"]["genesis_guard"]["sha256"] = "cc" * 32
    p2 = _passport(amr_ir, bound_evidence, "rel-b2", build=build2,
                   target=bound_evidence["target"])
    s = release_status(amr_ir_dict, after, p2, p1)
    assert s["binary_changed"]["known"] is True
    assert s["binary_changed"]["changed"] is True
    assert s["binary_changed"]["binaries"] == ["genesis_guard"]
    s = release_status(amr_ir_dict, after, p2, p2)
    assert s["binary_changed"]["changed"] is False
    host_only = _passport(amr_ir, bound_evidence, "rel-host",
                         build={"status": "missing"})
    s = release_status(amr_ir_dict, after, host_only, host_only)
    assert s["binary_changed"]["known"] is False


def test_renderers_cover_impact_and_release(amr_ir_dict):
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    text = render_impact_text(analyze_impact(amr_ir_dict, after))
    assert "max_linear_speed_mps: 1.2 -> 0.9" in text
    assert "genesis_config_gen.h" in text and "retest (8)" in text
    assert "full gate" in text
    status = release_status(amr_ir_dict, after, {"chain": []})
    text = render_release_text(status)
    assert "chain_ok=False" in text and "empty chain" in text


def test_cli_impact_command(amr_ir_dict, tmp_path, capsys):
    from genesis_rt.cli import main

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(amr_ir_dict), encoding="utf-8")
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    b.write_text(json.dumps(after), encoding="utf-8")
    assert main(["impact", str(a), str(b)]) == 0
    assert "retest (8)" in capsys.readouterr().out
    assert main(["impact", str(a), str(b), "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["retest"] and doc["limits"]["changed"][0]["key"] == \
        "max_linear_speed_mps"
    a.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    assert main(["impact", str(a), str(b)]) == 2
