# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: BeltSim physics + MachineSim protocol conformance."""
from genesis_rt.simulator import (
    BeltConfig,
    BeltSim,
    DiffDriveSim,
    MachineSim,
    SimConfig,
)


def _belt(dt=0.02):
    sim = BeltSim(BeltConfig(dt=dt))
    sim.reset(7)
    return sim


def test_both_sims_satisfy_protocol():
    assert isinstance(DiffDriveSim(SimConfig()), MachineSim)
    assert isinstance(BeltSim(BeltConfig()), MachineSim)


def test_belt_integrates_and_ignores_w():
    sim = _belt()
    sim.apply(1.0, 999.0)
    assert sim.state.position_m == 0.02
    assert sim.state.speed_mps == 1.0


def test_belt_jam_freezes_position_and_decays_speed():
    sim = _belt()
    sim.apply(2.0, 0.0)
    sim.set_jam(True)
    frozen = sim.state.position_m
    sim.apply(2.0, 0.0)
    sim.apply(2.0, 0.0)
    assert sim.state.position_m == frozen  # exact freeze, zero creep
    assert sim.state.speed_mps == 0.5  # 2.0 * 0.5^2
    for _ in range(60):
        sim.apply(2.0, 0.0)
    assert sim.state.speed_mps == 0.0  # snapped, never denormal drift
    sim.set_jam(False)
    sim.apply(2.0, 0.0)
    assert sim.state.position_m > frozen  # motion resumes after clear


def test_belt_stopped_zeroes_speed():
    sim = _belt()
    sim.apply(1.5, 0.0)
    sim.stopped()
    assert sim.state.speed_mps == 0.0


def test_belt_snapshot_and_final_stats_shape():
    sim = _belt()
    sim.apply(1.0, 0.0)
    assert sim.snapshot() == {"position": 0.02, "speed": 1.0, "jammed": False}
    assert sim.final_stats() == {"final_position": 0.02, "final_speed": 1.0,
                                 "final_x": 0.02, "final_y": 0.0,
                                 "collision": False, "wall_hit": False}


def test_belt_deterministic():
    a, b = _belt(), _belt()
    for _ in range(50):
        a.apply(1.2, 0.3)
        b.apply(1.2, 0.3)
    a.set_jam(True)
    b.set_jam(True)
    for _ in range(10):
        a.apply(1.2, 0.3)
        b.apply(1.2, 0.3)
    assert a.snapshot() == b.snapshot()
