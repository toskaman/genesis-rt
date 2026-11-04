# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Fault-lab tests: every scenario passes its oracle; seeds recorded."""
from genesis_rt import faultlab
from genesis_rt.ir import SCENARIO_IDS


def test_all_scenarios_pass_with_oracles(amr_ir):
    results = faultlab.run_all(amr_ir)
    assert {r["scenario"] for r in results} == set(SCENARIO_IDS)
    for r in results:
        assert r["status"] == "pass", (r["scenario"], r["checks"])
        assert r["seed"] == faultlab.DEFAULT_SEEDS[r["scenario"]]
        assert all(c["passed"] for c in r["checks"])
        assert len(r["trace"]) > 0


def test_conveyor_subset_passes(repo_root):
    from genesis_rt.ir import load_ir_file
    ir = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    results = faultlab.run_all(ir)
    assert all(r["status"] == "pass" for r in results)


def test_unknown_scenario_rejected(amr_ir):
    import pytest
    with pytest.raises(ValueError):
        faultlab.run_scenario(amr_ir, "nope")
