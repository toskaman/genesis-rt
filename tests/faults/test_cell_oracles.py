# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Fault-lab tests: cell scenarios pass; oracles catch sabotage."""
import pytest

from genesis_rt import faultlab
from genesis_rt.faultlab import FaultWindow


def _cell_ir(repo_root):
    from genesis_rt.ir import load_ir_file
    return load_ir_file(repo_root / "examples" / "cell-demo" / "cell-ir.json")


def test_cell_scenarios_pass_with_oracles(repo_root):
    ir = _cell_ir(repo_root)
    assert ir["verification"]["scenarios"] == sorted([
        "cell_nominal_transfer", "cell_transfer_jam",
        "cell_estop_during_transfer", "cell_stale_presence"])
    results = faultlab.run_all(ir)
    assert {r["scenario"] for r in results} == set(
        ir["verification"]["scenarios"])
    for r in results:
        assert r["status"] == "pass", (r["scenario"], r["checks"])
        assert r["seed"] == faultlab.DEFAULT_SEEDS[r["scenario"]]
        assert all(c["passed"] for c in r["checks"])
        assert len(r["trace"]) > 0
        assert r["physics"] == "cell"
        assert "physics_note" not in r


def test_cell_check_names_pinned(repo_root):
    results = {r["scenario"]: r
               for r in faultlab.run_all(_cell_ir(repo_root))}
    assert {c["name"] for c in results["cell_nominal_transfer"]["checks"]} == {
        "transfer_completed", "exact_transfer_ticks", "amr_reached_station",
        "phases_in_order", "no_denials", "belt_moved", "no_collision"}
    assert {c["name"] for c in results["cell_transfer_jam"]["checks"]} == {
        "safe_abort_on_jam", "belt_frozen_in_window",
        "transfer_frozen_in_window", "inhibit_observed",
        "single_supervised_recovery", "transfer_completed_after_recovery"}
    assert {c["name"] for c in results["cell_estop_during_transfer"]["checks"]} == {
        "all_denied_estop", "safe_latched", "never_completed",
        "no_motion_after_estop", "no_recovery_after_estop",
        "estop_denials_recorded"}
    assert {c["name"] for c in results["cell_stale_presence"]["checks"]} == {
        "safe_abort_on_stale", "transfer_frozen_in_window",
        "stale_sensor_denials", "single_supervised_recovery",
        "transfer_completed_after_recovery", "guard_exited_safe_stop"}


def test_kind_gating_both_ways(amr_ir, repo_root):
    cell = _cell_ir(repo_root)
    r = faultlab.run_scenario(amr_ir, "cell_nominal_transfer")
    assert r["status"] == "crash"
    assert "industrial_cell" in r["error"]
    r = faultlab.run_scenario(cell, "nominal_navigation")
    assert r["status"] == "crash"
    assert "cell scenarios only" in r["error"]


def _map(checks):
    return {c.name: c for c in checks}


def _tick(t, **kw):
    base = {"t": t, "kind": "tick", "fault": "none", "leg": "belt",
            "decision": "ALLOW", "reason": "OK", "guard_state": 1,
            "cell_phase": "TRANSFERRING", "presence": True,
            "presence_fresh": True, "transfers": 0, "transfer_ticks": 10,
            "inhibited": False, "amr_x": 6.0, "belt_pos": 1.0,
            "belt_jammed": False}
    base.update(kw)
    return base


def test_nominal_oracle_catches_missing_transfer_and_denials():
    from genesis_rt.faultlab import _o_cell_nominal
    trace = [_tick(0, cell_phase="ENROUTE"),
             _tick(10, cell_phase="AT_STATION"),
             _tick(20, cell_phase="TRANSFERRING", transfer_ticks=50),
             _tick(30, cell_phase="COMPLETE", transfers=1,
                   transfer_ticks=50)]
    stats = {"cell_phase": "COMPLETE", "transfers_completed": 0,
             "transfer_ticks_expected": 50, "station_x_m": 6.0,
             "final_x": 6.0, "denies": 0, "belt_final_position": 1.0,
             "collision": False, "wall_hit": False}
    assert _map(_o_cell_nominal(stats, trace, None, None))[
        "transfer_completed"].passed is False
    stats["transfers_completed"] = 1
    stats["denies"] = 2
    assert _map(_o_cell_nominal(stats, trace, None, None))[
        "no_denials"].passed is False


def test_jam_oracle_catches_belt_creep_and_missing_recovery():
    from genesis_rt.faultlab import _o_cell_jam
    window = FaultWindow("jam", 100, 200)
    creeping = [_tick(100, belt_pos=1.0, inhibited=True),
                _tick(150, belt_pos=1.5, inhibited=True)]
    stats = {"cell_phase": "COMPLETE", "transfers_completed": 1,
             "recovered": True}
    assert _map(_o_cell_jam(stats, creeping, None, window))[
        "belt_frozen_in_window"].passed is False
    frozen = [_tick(100, belt_pos=1.0, inhibited=True),
              _tick(150, belt_pos=1.0, inhibited=True)]
    assert _map(_o_cell_jam(stats, frozen, None, window))[
        "single_supervised_recovery"].passed is False  # no reset event


def test_estop_oracle_catches_allow_motion_and_recovery():
    from genesis_rt.faultlab import _o_cell_estop
    window = FaultWindow("estop", 100, 200)
    allowed = [_tick(100, decision="ALLOW", reason="OK")]
    stats = {"cell_phase": "SAFE", "transfers_completed": 0,
             "recovered": False, "deny_reasons": {"ESTOP": 3}}
    assert _map(_o_cell_estop(stats, allowed, None, window))[
        "all_denied_estop"].passed is False
    denied = [_tick(100, decision="DENY", reason="ESTOP"),
              _tick(150, decision="DENY", reason="ESTOP",
                    amr_x=6.5, belt_pos=2.0)]
    assert _map(_o_cell_estop(stats, denied, None, window))[
        "no_motion_after_estop"].passed is False
    frozen = [_tick(100, decision="DENY", reason="ESTOP"),
              _tick(150, decision="DENY", reason="ESTOP")]
    stats["recovered"] = True
    assert _map(_o_cell_estop(stats, frozen, None, window))[
        "no_recovery_after_estop"].passed is False


def test_stale_oracle_catches_missing_denials_and_latched_guard():
    from genesis_rt.faultlab import _o_cell_stale
    window = FaultWindow("stale", 100, 200)
    trace = [_tick(100, transfer_ticks=5), _tick(150, transfer_ticks=5),
             {"t": 250, "kind": "supervisor_reset_armed",
              "recovered": True}]
    stats = {"cell_phase": "COMPLETE", "transfers_completed": 1,
             "deny_reasons": {}, "final_state_belt": 1}
    assert _map(_o_cell_stale(stats, trace, None, window))[
        "stale_sensor_denials"].passed is False
    stats["deny_reasons"] = {"STALE_SENSOR": 4}
    stats["final_state_belt"] = 3
    assert _map(_o_cell_stale(stats, trace, None, window))[
        "guard_exited_safe_stop"].passed is False


def test_cell_runs_are_deterministic(repo_root):
    ir = _cell_ir(repo_root)
    a = faultlab.run_scenario(ir, "cell_transfer_jam", seed=4242)
    b = faultlab.run_scenario(ir, "cell_transfer_jam", seed=4242)
    assert a["status"] == b["status"] == "pass"
    key = lambda r: [(e["t"], e["belt_pos"], e["cell_phase"])
                     for e in r["trace"] if e["kind"] == "tick"]
    assert key(a) == key(b)
