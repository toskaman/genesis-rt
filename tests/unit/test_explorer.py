# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: §9 Counterexample Explorer (bounded search + replay)."""
import ast
import copy
import json
from pathlib import Path

import pytest

from genesis_rt import faultlab, guard_policy as gp
from genesis_rt.ir import IRValidationError
from genesis_rt.explorer import (
    ExplorerInputError,
    ExplorerUnsupported,
    explore,
    explore_strategies,
    invariants,
    replay,
    run_script,
    shrink,
)


def _nominal_script(ticks=300, seed=1000):
    return {"ticks": ticks, "seed": seed, "faults": [], "commands": [],
            "resets": "auto"}


def test_driver_matches_scenario_oracle_on_nominal(amr_ir_dict):
    mine = run_script(amr_ir_dict, _nominal_script())
    theirs = faultlab.run_scenario(amr_ir_dict, "nominal_navigation")
    assert mine["status"] == theirs["status"] == "pass"
    assert mine["stats"]["denies"] == 0
    assert mine["checks"]["no_over_limit_allow"]["passed"] is True


def test_default_invariants_hold_on_nominal(amr_ir_dict):
    out = run_script(amr_ir_dict, _nominal_script())
    for name, check in out["checks"].items():
        assert check["passed"] is True, (name, check)


def test_over_limit_script_denied_not_allowed(amr_ir_dict):
    script = _nominal_script()
    script["faults"] = [{"kind": "over_limit", "start_tick": 100,
                         "end_tick": 103}]
    out = run_script(amr_ir_dict, script)
    assert out["checks"]["no_over_limit_allow"]["passed"] is True
    assert out["stats"]["deny_reasons"].get(gp.R_SPEED_OVER_LIMIT, 0) >= 1


def test_strict_invariant_is_violated_by_boundary_command(amr_ir_dict):
    script = _nominal_script()
    script["commands"] = [{"tick": 50, "linear_mps": 1.0}]
    out = run_script(amr_ir_dict, script,
                     invariant="no_over_limit_allow",
                     params={"max_allow_linear": 0.9})
    check = out["checks"]["no_over_limit_allow"]
    assert check["passed"] is False
    assert "1.0" in check["detail"]


def test_boundary_strategy_finds_strict_violation(amr_ir_dict):
    report = explore(amr_ir_dict, invariant="no_over_limit_allow",
                     params={"max_allow_linear": 0.9},
                     strategies=["boundary"],
                     budgets={"max_scripts": 200, "max_findings": 3},
                     seed=7)
    assert report["findings"], "boundary search must find the 0.9 violation"
    rec = report["findings"][0]
    assert rec["tier"] == "host-discovered"
    assert rec["ir_sha256"] is not None
    assert rec["machine"]["id"] == "amr-demo-01"
    assert rec["shrunk_script"]["commands"], "minimal reproducer required"
    assert "trace_excerpt" in rec and rec["trace_excerpt"]


def test_explore_honest_empty_when_invariant_holds(amr_ir_dict):
    report = explore(amr_ir_dict, invariant="no_over_limit_allow",
                     strategies=["boundary"],
                     budgets={"max_scripts": 50, "max_findings": 3},
                     seed=7)
    assert report["findings"] == []
    assert report["budget_exhausted"] is False
    assert report["scripts_run"] > 0


def test_explore_is_deterministic(amr_ir_dict):
    kw = dict(invariant="no_over_limit_allow",
              params={"max_allow_linear": 0.9}, strategies=["mutate"],
              budgets={"max_scripts": 60, "max_findings": 2}, seed=11)
    a = explore(copy.deepcopy(amr_ir_dict), **kw)
    b = explore(copy.deepcopy(amr_ir_dict), **kw)
    assert json.dumps(a["findings"], sort_keys=True) == json.dumps(
        b["findings"], sort_keys=True)


def test_budgets_are_enforced(amr_ir_dict):
    report = explore(amr_ir_dict, invariant="no_over_limit_allow",
                     strategies=["pairs"],
                     budgets={"max_scripts": 5},
                     seed=3)
    assert report["scripts_run"] <= 5
    assert report["budget_exhausted"] is True


def test_budget_over_hard_cap_rejected(amr_ir_dict):
    with pytest.raises(ExplorerInputError):
        explore(amr_ir_dict, budgets={"max_scripts": 10 ** 9})


def test_shrink_reduces_to_minimal_steps(amr_ir_dict):
    script = _nominal_script()
    script["faults"] = [{"kind": "delayed", "start_tick": 10, "end_tick": 12}]
    script["commands"] = [{"tick": 50, "linear_mps": 1.0},
                          {"tick": 60, "linear_mps": 0.5}]
    small = shrink(amr_ir_dict, script, invariant="no_over_limit_allow",
                   params={"max_allow_linear": 0.9},
                   budgets={"max_scripts": 50})
    out = run_script(amr_ir_dict, small, invariant="no_over_limit_allow",
                     params={"max_allow_linear": 0.9})
    assert out["checks"]["no_over_limit_allow"]["passed"] is False
    total = len(small["faults"]) + len(small["commands"])
    assert total == 1, small


def test_replay_reproduces_same_violation(amr_ir_dict):
    report = explore(amr_ir_dict, invariant="no_over_limit_allow",
                     params={"max_allow_linear": 0.9},
                     strategies=["boundary"],
                     budgets={"max_scripts": 200, "max_findings": 1},
                     seed=7)
    rec = report["findings"][0]
    again = replay(rec, amr_ir_dict)
    assert again["violated"] is True
    assert again["deterministic"] is True


def test_fix_replay_holds_after_limit_tightened(amr_ir_dict):
    report = explore(amr_ir_dict, invariant="no_over_limit_allow",
                     params={"max_allow_linear": 0.9},
                     strategies=["boundary"],
                     budgets={"max_scripts": 200, "max_findings": 1},
                     seed=7)
    rec = report["findings"][0]
    fixed = copy.deepcopy(amr_ir_dict)
    fixed["control"]["max_linear_speed_mps"] = 0.9
    result = replay(rec, fixed)
    assert result["violated"] is False, result["checks"]


def test_explorer_catches_mutated_guard(amr_ir_dict, monkeypatch):
    real = gp.decide

    def always_allow(cmd, ctx, limits):
        ctx.last_seq = int(cmd["seq"])
        return {"decision": gp.ALLOW, "reason": gp.R_OK,
                "state_out": gp.ST_NOMINAL, "applied": True}

    monkeypatch.setattr(gp, "decide", always_allow)
    try:
        script = _nominal_script()
        script["faults"] = [{"kind": "over_limit", "start_tick": 100,
                             "end_tick": 103}]
        out = run_script(amr_ir_dict, script)
        assert out["checks"]["no_over_limit_allow"]["passed"] is False
    finally:
        monkeypatch.setattr(gp, "decide", real)


def test_invalid_script_rejected(amr_ir_dict):
    with pytest.raises(ExplorerInputError):
        run_script(amr_ir_dict, {"ticks": 0, "seed": 1})
    with pytest.raises(ExplorerInputError):
        run_script(amr_ir_dict, {"ticks": 10, "seed": 1,
                                 "faults": [{"kind": "nope"}]})
    with pytest.raises(IRValidationError):
        run_script("not-a-dict", _nominal_script())


def test_cell_is_explicitly_unsupported(cell_ir_path):
    ir = json.loads(cell_ir_path.read_text(encoding="utf-8"))
    with pytest.raises(ExplorerUnsupported):
        run_script(ir, _nominal_script())


def test_unknown_invariant_rejected(amr_ir_dict):
    with pytest.raises(ExplorerInputError):
        run_script(amr_ir_dict, _nominal_script(), invariant="nope")


def test_registry_lists_documented_invariants():
    names = set(invariants())
    assert {"no_over_limit_allow", "no_motion_without_allow",
            "deny_reasons_known", "estop_latches_stop",
            "safe_stop_needs_reset", "no_allow_past_deadline"} <= names
    assert set(explore_strategies()) >= {"boundary", "pairs", "windows",
                                        "mutate"}


def test_explorer_has_no_target_imports():
    src = (Path(__file__).resolve().parents[2] / "host" / "genesis_rt" /
           "explorer.py").read_text(encoding="utf-8")
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert not ({"paramiko", "ssh", "socket", "subprocess", "build_adapter",
                 "qemu"} & mods), mods
