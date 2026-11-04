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


def _check_map(checks):
    return {c.name: c for c in checks}


def test_watchdog_oracle_catches_motion_during_gap():
    """Sabotaged trace: drift during the crash gap must fail the oracle."""
    from genesis_rt.faultlab import _o_crash, FaultWindow
    window = FaultWindow("crash", 1000, 1500)
    stats = {"final_state": 1, "collision": False}
    trace = [
        {"t": 990, "kind": "tick", "decision": "ALLOW",
         "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1010, "kind": "planner_gap", "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1020, "kind": "planner_gap", "x": 1.5, "y": 0.0, "theta": 0.0},
    ]
    checks = _check_map(_o_crash(stats, trace, None, window))
    assert checks["watchdog_zero_motion"].passed is False
    assert "max_displacement=0.5" in checks["watchdog_zero_motion"].detail


def test_watchdog_oracle_passes_quiet_gap():
    from genesis_rt.faultlab import _o_crash, FaultWindow
    window = FaultWindow("crash", 1000, 1500)
    stats = {"final_state": 1, "collision": False}
    trace = [
        {"t": 990, "kind": "tick", "decision": "ALLOW",
         "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1010, "kind": "planner_gap", "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1020, "kind": "planner_gap", "x": 1.0, "y": 0.0, "theta": 0.0},
    ]
    checks = _check_map(_o_crash(stats, trace, None, window))
    assert checks["watchdog_zero_motion"].passed is True


def test_no_allow_oracle_catches_tick_during_drop():
    """Sabotaged trace: a command tick inside the drop window must fail."""
    from genesis_rt.faultlab import _o_dropped, FaultWindow
    window = FaultWindow("dropped", 1000, 1100)
    stats = {"final_state": 1}
    trace = [
        {"t": 990, "kind": "tick", "decision": "ALLOW",
         "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1000, "kind": "planner_gap", "x": 1.0, "y": 0.0, "theta": 0.0},
        {"t": 1010, "kind": "tick", "decision": "ALLOW",
         "x": 1.1, "y": 0.0, "theta": 0.0},
    ]
    checks = _check_map(_o_dropped(stats, trace, None, window))
    assert checks["no_allow_without_command"].passed is False


def test_watchdog_break_end_to_end_fails_scenario_and_gate(amr_ir, monkeypatch, tmp_path):
    """Broken watchdog (motion during gap) => scenario fail => gate FAIL."""
    from genesis_rt import codegen, evidence, gate
    from genesis_rt.simulator import DiffDriveSim

    def drifting_stopped(self):
        return self.apply(0.5, 0.0)  # watchdog failure: drift instead of stop

    monkeypatch.setattr(DiffDriveSim, "stopped", drifting_stopped)
    res = faultlab.run_scenario(amr_ir, "planner_process_crash")
    assert res["status"] == "fail"
    by_name = {c["name"]: c for c in res["checks"]}
    assert by_name["watchdog_zero_motion"]["passed"] is False

    manifest = codegen.generate(amr_ir, tmp_path / "sabotage-gen")
    passport = evidence.build_passport(
        "run-watchdog-broken", amr_ir, manifest, [res],
        {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, ["planner_process_crash"])
    assert verdict["verdict"] == "FAIL"


def test_forged_tick_in_real_drop_trace_detected(amr_ir):
    """A command smuggled into a real drop-window trace must be caught."""
    from genesis_rt.faultlab import _o_dropped, SCENARIO_WINDOWS
    res = faultlab.run_scenario(amr_ir, "dropped_message")
    assert res["status"] == "pass"
    window = SCENARIO_WINDOWS["dropped_message"]
    forged = list(res["trace"]) + [
        {"t": window.start_ms + 5, "kind": "tick", "decision": "ALLOW",
         "reason": "OK", "state": 1, "x": 9.9, "y": 0.0, "theta": 0.0}]
    checks = _check_map(_o_dropped(res["stats"], forged, None, window))
    assert checks["no_allow_without_command"].passed is False
