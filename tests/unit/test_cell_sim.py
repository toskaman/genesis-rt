# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: CellSim phases, interlock, abort and recovery policy."""
import pytest

from genesis_rt.simulator import (
    CELL_AT_STATION,
    CELL_COMPLETE,
    CELL_ENROUTE,
    CELL_IDLE,
    CELL_SAFE,
    CELL_TRANSFERRING,
    CellConfig,
    CellSim,
    cell_transfer_allowed,
)


def _drive_to_station(sim, v=0.5, cap=2000):
    for _ in range(cap):
        sim.apply(v, 0.0)
        if sim.state.phase >= CELL_AT_STATION:
            return sim.state
    raise AssertionError("never reached the station")


def _transfer(sim, v=0.5, cap=700):
    for _ in range(cap):
        sim.apply_transfer(v)
        if sim.state.phase in (CELL_COMPLETE, CELL_SAFE):
            return sim.state
    raise AssertionError("transfer never settled")


def test_nominal_cycle_completes_one_transfer():
    sim = CellSim()
    sim.reset(1042)
    assert sim.state.phase == CELL_IDLE
    _drive_to_station(sim)
    assert sim.state.phase == CELL_AT_STATION
    assert sim.state.presence is True
    _transfer(sim)
    assert sim.state.phase == CELL_COMPLETE
    assert sim.state.transfers_completed == 1
    assert sim.state.transfer_done_ticks == sim.config.transfer_ticks


def test_phases_visit_in_order():
    sim = CellSim()
    sim.reset(1)
    seen = [sim.state.phase]
    _drive_to_station(sim)
    seen.append(sim.state.phase)
    sim.apply_transfer(0.5)
    seen.append(sim.state.phase)
    _transfer(sim)
    seen.append(sim.state.phase)
    assert seen == [CELL_IDLE, CELL_AT_STATION, CELL_TRANSFERRING,
                    CELL_COMPLETE]


def test_amr_frozen_after_docking():
    sim = CellSim()
    sim.reset(2)
    _drive_to_station(sim)
    x_docked = sim.amr.state.x
    _transfer(sim)
    assert sim.amr.state.x == pytest.approx(x_docked)
    assert sim.state.phase == CELL_COMPLETE


def test_belt_frozen_outside_transfer():
    sim = CellSim()
    sim.reset(3)
    sim.apply_transfer(0.5)  # too early: still IDLE/ENROUTE
    assert sim.belt.state.position_m == 0.0
    assert sim.state.inhibited is True
    assert sim.state.transfer_done_ticks == 0


def test_jam_aborts_and_supervised_recovery_completes():
    sim = CellSim()
    sim.reset(4)
    _drive_to_station(sim)
    sim.apply_transfer(0.5)
    assert sim.state.phase == CELL_TRANSFERRING
    sim.set_jam(True)
    sim.apply_transfer(0.5)
    assert sim.state.phase == CELL_SAFE
    assert sim.state.transfers_completed == 0
    assert sim.request_recovery() is False  # still jammed
    sim.set_jam(False)
    assert sim.request_recovery() is True
    assert sim.state.phase == CELL_AT_STATION
    assert sim.state.transfer_done_ticks == 0  # restarted from zero
    _transfer(sim)
    assert sim.state.phase == CELL_COMPLETE
    assert sim.state.transfers_completed == 1
    assert sim.state.recovered is True


def test_estop_latches_safe_and_forbids_recovery():
    sim = CellSim()
    sim.reset(5)
    _drive_to_station(sim)
    sim.apply_transfer(0.5)
    sim.set_estop(True)
    sim.apply_transfer(0.5)
    assert sim.state.phase == CELL_SAFE
    sim.set_estop(False)  # fault clears...
    assert sim.request_recovery() is False  # ...but the latch holds
    assert sim.state.phase == CELL_SAFE
    belt_frozen = sim.belt.state.position_m
    amr_frozen = sim.amr.state.x
    for _ in range(10):
        sim.stopped()
    assert sim.belt.state.position_m == belt_frozen
    assert sim.amr.state.x == amr_frozen


def test_stale_presence_aborts_and_recovers():
    sim = CellSim()
    sim.reset(6)
    _drive_to_station(sim)
    sim.apply_transfer(0.5)
    sim.freeze_presence(True)
    sim.apply_transfer(0.5)
    assert sim.state.phase == CELL_SAFE
    assert sim.request_recovery() is False  # presence not fresh
    sim.freeze_presence(False)
    assert sim.request_recovery() is True
    _transfer(sim)
    assert sim.state.phase == CELL_COMPLETE


def test_recovery_refused_outside_safe():
    sim = CellSim()
    sim.reset(7)
    assert sim.request_recovery() is False  # IDLE, nothing to recover
    _drive_to_station(sim)
    assert sim.request_recovery() is False  # AT_STATION, nothing to recover


def test_interlock_truth_table():
    assert cell_transfer_allowed(CELL_TRANSFERRING, True, True, False, False)
    assert not cell_transfer_allowed(CELL_AT_STATION, True, True, False, False)
    assert not cell_transfer_allowed(CELL_TRANSFERRING, False, True, False, False)
    assert not cell_transfer_allowed(CELL_TRANSFERRING, True, False, False, False)
    assert not cell_transfer_allowed(CELL_TRANSFERRING, True, True, True, False)
    assert not cell_transfer_allowed(CELL_TRANSFERRING, True, True, False, True)
    assert not cell_transfer_allowed(CELL_COMPLETE, True, True, False, False)
    assert not cell_transfer_allowed(CELL_SAFE, True, True, False, False)


def test_deterministic_replay():
    def run():
        sim = CellSim()
        sim.reset(1042)
        out = []
        _drive_to_station(sim)
        for _ in range(60):
            sim.apply_transfer(0.5)
            out.append((sim.snapshot()["belt_pos"],
                        sim.snapshot()["cell_phase"]))
        return out
    assert run() == run()
