# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Fault-lab tests: every scenario passes its oracle; seeds recorded."""
import copy

from genesis_rt import faultlab


def test_records_name_their_physics(amr_ir):
    """Wave 10 Sprint E1: every scenario record names the host physics
    that ran, so an aliased kind can never pass as native behavior."""
    results = faultlab.run_all(amr_ir)
    assert results
    for r in results:
        assert r["physics"] == "diffdrive-corridor"
        assert "physics_note" not in r


def test_arm_kind_records_physics_aliasing(amr_ir):
    """robotic_arm_virtual has no arm kinematics; it runs on the
    diffdrive corridor, and the record must say so."""
    arm = copy.deepcopy(amr_ir)
    arm["machine"]["kind"] = "robotic_arm_virtual"
    arm["machine"]["id"] = "arm-alias-probe"
    results = faultlab.run_all(arm)
    assert results
    for r in results:
        assert r["physics"] == "diffdrive-corridor"
        assert "no arm-specific physics" in r["physics_note"]


def test_all_scenarios_pass_with_oracles(amr_ir):
    # "All" means all scenarios the IR declares (machines declare
    # kind-meaningful lists; the global registry may hold more).
    results = faultlab.run_all(amr_ir)
    assert {r["scenario"] for r in results} == set(
        amr_ir["verification"]["scenarios"])
    for r in results:
        assert r["status"] == "pass", (r["scenario"], r["checks"])
        assert r["seed"] == faultlab.DEFAULT_SEEDS[r["scenario"]]
        assert all(c["passed"] for c in r["checks"])
        assert len(r["trace"]) > 0


def test_conveyor_subset_passes(repo_root):
    from genesis_rt.ir import load_ir_file
    ir = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    assert ir["verification"]["scenarios"] == sorted([
        "nominal_navigation", "speed_command_over_limit",
        "delayed_command", "belt_jam", "estop_pressed"])  # validate_ir sorts
    results = faultlab.run_all(ir)
    assert {r["scenario"] for r in results} == set(
        ir["verification"]["scenarios"])
    assert [(r["scenario"], r["status"], r["checks"]) for r in results
            if r["status"] != "pass"] == []
    jam = next(r for r in results if r["scenario"] == "belt_jam")
    assert {c["name"] for c in jam["checks"]} == {
        "jam_observed", "zero_creep", "recovery", "decided_every_tick"}
    estop = next(r for r in results if r["scenario"] == "estop_pressed")
    assert {c["name"] for c in estop["checks"]} == {
        "all_denied_estop", "safe_stop_latched", "no_motion_while_estop",
        "reset_armed_once", "recovered_allows"}


def _estop_trace(window, decisions=("DENY",), reason="ESTOP", state=3,
                 frozen=True, kind="diff"):
    ticks = []
    for i, t in enumerate(range(window.start_ms, window.end_ms, 20)):
        snap = {"position": 1.0, "speed": 0.0, "jammed": False} if kind == "belt" \
            else {"x": 1.0 if frozen or i == 0 else 1.0 + i * 0.01,
                  "y": 0.0, "theta": 0.0}
        ticks.append({"t": t, "kind": "tick", "fault": "estop",
                      "decision": decisions[0] if len(decisions) == 1
                      else decisions[i % len(decisions)],
                      "reason": reason, "state": state, **snap})
    return ticks


def test_estop_oracle_catches_allow_and_motion():
    """An in-window ALLOW fails all_denied_estop; drift fails
    no_motion_while_estop."""
    from genesis_rt.faultlab import FaultWindow, _o_estop
    window = FaultWindow("estop", 1000, 1500)
    allowed = _estop_trace(window, decisions=("ALLOW",), reason="OK", state=1)
    stats = {"stop_latched_at": None, "final_state": 1}
    assert _check_map(_o_estop(stats, allowed, None, window))[
        "all_denied_estop"].passed is False
    drifting = _estop_trace(window, frozen=False)
    stats = {"stop_latched_at": 1000, "final_state": 1}
    assert _check_map(_o_estop(stats, drifting, None, window))[
        "no_motion_while_estop"].passed is False


def test_estop_oracle_requires_reset_and_recovery():
    from genesis_rt.faultlab import FaultWindow, _o_estop
    window = FaultWindow("estop", 1000, 1500)
    ticks = _estop_trace(window)
    stats = {"stop_latched_at": 1000, "final_state": 3}
    assert _check_map(_o_estop(stats, ticks, None, window))[
        "reset_armed_once"].passed is False
    assert _check_map(_o_estop(stats, ticks, None, window))[
        "recovered_allows"].passed is False


def test_estop_pressed_passes_on_both_sims(amr_ir, repo_root):
    """estop is guard-level: identical oracle contract on DiffDriveSim
    and BeltSim (AMR IR need not declare it)."""
    from genesis_rt.ir import load_ir_file
    conv = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    for ir in (amr_ir, conv):
        res = faultlab.run_scenario(ir, "estop_pressed")
        assert res["status"] == "pass", (ir["machine"]["kind"], res["checks"])
        assert {c["name"] for c in res["checks"]} == {
            "all_denied_estop", "safe_stop_latched", "no_motion_while_estop",
            "reset_armed_once", "recovered_allows"}


def test_unknown_scenario_rejected(amr_ir):
    import pytest
    with pytest.raises(ValueError):
        faultlab.run_scenario(amr_ir, "nope")


def _check_map(checks):
    return {c.name: c for c in checks}


def test_over_limit_oracle_requires_speed_deny():
    """No SPEED_OVER_LIMIT deny in stats => oracle must fail."""
    from genesis_rt.faultlab import _o_over_limit
    stats = {"deny_reasons": {}, "stop_latched_at": None,
             "final_state": 0, "collision": False}
    checks = _check_map(_o_over_limit(stats, [], None, None))
    assert checks["over_limit_denied"].passed is False


def test_nominal_oracle_rejects_denials_and_stall():
    from genesis_rt.faultlab import _o_nominal
    stats = {"denies": 2, "collision": False, "wall_hit": False,
             "final_x": 5.0, "final_state": 0}
    assert _check_map(_o_nominal(stats, [], None, None))["no_denials"].passed is False
    stats = {"denies": 0, "collision": False, "wall_hit": False,
             "final_x": 0.1, "final_state": 0}
    assert _check_map(_o_nominal(stats, [], None, None))["progress"].passed is False


def test_delayed_oracle_requires_overdue_deny():
    from genesis_rt.faultlab import _o_delayed
    stats = {"deny_reasons": {}, "stop_latched_at": None, "final_state": 0}
    checks = _check_map(_o_delayed(stats, [], None, None))
    assert checks["overdue_denied"].passed is False


def _jam_trace(positions, window, decision="ALLOW", speed=0.0, jammed=True):
    return [{"t": t, "kind": "tick", "fault": "jam", "decision": decision,
             "reason": "OK", "state": 1, "position": p, "speed": speed,
             "jammed": jammed}
            for t, p in zip(range(window.start_ms, window.end_ms, 20),
                            positions)]


def test_jam_oracle_catches_creep_and_stall():
    """Belt motion during full-jam ticks fails zero_creep; no stalled
    ALLOW ticks fails jam_observed."""
    from genesis_rt import guard_policy as gp
    from genesis_rt.faultlab import FaultWindow, _o_belt_jam
    window = FaultWindow("jam", 1000, 1500)
    creeping = _jam_trace([i * 0.01 for i in range(25)], window)
    assert _check_map(_o_belt_jam({}, creeping, None, window))[
        "zero_creep"].passed is False
    moving = _jam_trace([1.0] * 25, window, speed=0.5)
    assert _check_map(_o_belt_jam({}, moving, None, window))[
        "jam_observed"].passed is False
    assert gp.ALLOW == "ALLOW"  # oracle uses real guard verdict strings


def test_jam_oracle_requires_recovery():
    from genesis_rt.faultlab import FaultWindow, _o_belt_jam
    window = FaultWindow("jam", 1000, 1500)
    stuck = _jam_trace([1.0] * 25, window)
    assert _check_map(_o_belt_jam({}, stuck, None, window))[
        "recovery"].passed is False


def test_belt_jam_rejected_on_diff_drive(amr_ir):
    """belt_jam on a non-conveyor machine fails loudly, never passes."""
    res = faultlab.run_scenario(amr_ir, "belt_jam")
    assert res["status"] == "crash"
    assert "conveyor" in res["error"]


def test_belt_and_diffdrive_traces_differ_structurally(amr_ir, repo_root):
    from genesis_rt.ir import load_ir_file
    conv = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    amr_tick = next(e for e in faultlab.run_scenario(
        amr_ir, "nominal_navigation")["trace"] if e["kind"] == "tick")
    belt_tick = next(e for e in faultlab.run_scenario(
        conv, "nominal_navigation")["trace"] if e["kind"] == "tick")
    assert {"x", "y", "theta"} <= set(amr_tick)
    assert {"position", "speed", "jammed"} <= set(belt_tick)
    assert "position" not in amr_tick and "theta" not in belt_tick


def test_stale_oracle_requires_detection_and_latch():
    from genesis_rt.faultlab import _o_stale, FaultWindow
    window = FaultWindow("stale", 1000, 1500)
    stats = {"deny_reasons": {}, "stop_latched_at": None, "final_state": 0}
    checks = _check_map(_o_stale(stats, [], {"freshness_limit_ms": 100}, window))
    assert checks["stale_detected"].passed is False
    assert checks["safe_stop_latched"].passed is False


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


def test_always_allow_guard_mutant_fails_scenarios_and_gate(amr_ir, monkeypatch, tmp_path):
    """Disabled guard (all-ALLOW mutant) => fault scenarios fail, gate FAIL.

    Every deny-dependent oracle must bite: a guard that approves an
    over-limit, stale, overdue, corrupted or disconnected command is a
    broken safety function, and the pipeline must refuse PASS / release.
    """
    from genesis_rt import codegen, evidence, gate, guard_policy

    def always_allow(cmd, ctx, limits):
        return {"decision": guard_policy.ALLOW, "reason": guard_policy.R_OK,
                "state_out": guard_policy.ST_NOMINAL}

    monkeypatch.setattr(guard_policy, "decide", always_allow)
    deny_scenarios = ["speed_command_over_limit", "stale_proximity_150ms",
                      "delayed_command", "corrupted_message",
                      "simulator_disconnect"]
    results = faultlab.run_all(amr_ir, deny_scenarios)
    for res in results:
        assert res["status"] == "fail", (res["scenario"], res["checks"])

    manifest = codegen.generate(amr_ir, tmp_path / "mutant-gen")
    passport = evidence.build_passport(
        "run-guard-mutant", amr_ir, manifest, results,
        {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, deny_scenarios)
    assert verdict["verdict"] == "FAIL"
    assert verdict["level"] == "NONE"
    assert verdict["release_eligible"] is False
