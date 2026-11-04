# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Acceptance: the golden demo story end to end (host side).

intent -> IR -> codegen -> host checks -> fault campaign -> passport ->
gate PASS; then a sabotaged revision -> gate FAIL; then a corrected
revision -> PASS again with a different chain. QNX on-target execution
is accepted as honestly-blocked without an SDK (never faked).
"""
from genesis_rt import codegen, evidence, faultlab, gate
from genesis_rt.build_adapter import probe
from genesis_rt.orchestrator import run_pipeline
from genesis_rt.planner import propose


def test_golden_demo_story(tmp_path):
    ir = propose("autonomous mobile robot, differential drive, 10ms, max 1.0 m/s",
                 machine_id="amr-demo-01")
    assert ir["control"]["max_linear_speed_mps"] == 1.0

    good = run_pipeline.__wrapped__ if hasattr(run_pipeline, "__wrapped__") else run_pipeline
    import json
    ir_path = tmp_path / "ir.json"
    ir_path.write_text(json.dumps(ir), encoding="utf-8")
    first = good(ir_path, tmp_path / "runs")
    assert first["verdict"] == "PASS"

    passport = evidence.load_passport(first["passport"])
    assert evidence.verify_chain(passport) == []
    kinds = [r["kind"] for r in passport["chain"]]
    assert "ir" in kinds and "codegen" in kinds and "qnx_build" in kinds
    assert "gate_verdict" in kinds
    assert sum(1 for k in kinds if k.startswith("scenario:")) == 8

    # QNX honesty: without an SDK the record is blocked, verdict unaffected but flagged.
    sdk = probe()
    qnx_body = next(r["body"] for r in passport["chain"] if r["kind"] == "qnx_build")
    if not sdk["sdk_present"]:
        assert qnx_body["status"] == "blocked"
    else:
        assert qnx_body["status"] == "ok"
    # Host-only run (no target record) can never be target-verified, SDK or not.
    assert first["qnx_verified"] is False


def test_break_then_fix_cycle(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    qnx = {"status": "blocked", "verified_on_target": False}

    broken_results = faultlab.run_all(amr_ir)
    idx = next(i for i, r in enumerate(broken_results)
               if r["scenario"] == "stale_proximity_150ms")
    broken_results[idx] = dict(broken_results[idx], status="crash",
                               error="injected crash")
    broken = evidence.build_passport("run-broken", amr_ir, manifest, broken_results, qnx)
    assert gate.evaluate(broken, amr_ir["verification"]["scenarios"])["verdict"] == "FAIL"

    fixed_results = faultlab.run_all(amr_ir)
    fixed = evidence.build_passport("run-fixed", amr_ir, manifest, fixed_results, qnx)
    verdict = gate.evaluate(fixed, amr_ir["verification"]["scenarios"])
    assert verdict["verdict"] == "PASS"

    # Evidence delta: same inputs hash, different run ids and verdicts.
    assert broken["chain"][0]["hash"] == fixed["chain"][0]["hash"]
    assert broken["run_id"] != fixed["run_id"]
