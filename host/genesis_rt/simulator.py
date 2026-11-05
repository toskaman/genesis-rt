# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic host-side machine simulators (non-real-time).

Fixed time step, seeded noise. Simulation only: nothing here commands
physical hardware, and simulator timing is never presented as QNX timing.

Every simulator satisfies the ``MachineSim`` protocol so the fault lab
can drive any machine kind through one loop: ``reset(seed)``,
``apply(v, w)``, ``stopped()``, ``snapshot()`` (per-tick trace motion),
``final_stats()`` (oracle inputs).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MachineSim(Protocol):
    """Structural interface for fault-lab simulators."""

    def reset(self, seed: int) -> Any: ...
    def apply(self, v: float, w: float) -> Any: ...
    def stopped(self) -> Any: ...
    def snapshot(self) -> dict[str, Any]: ...
    def final_stats(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SimConfig:
    dt: float = 0.01
    corridor_half_width: float = 1.0
    corridor_length: float = 12.0
    robot_radius: float = 0.15
    sensor_range_m: float = 5.0
    obstacles: tuple[tuple[float, float, float], ...] = (
        (4.0, 0.45, 0.25),
        (8.0, -0.45, 0.25),
    )


@dataclass
class SimState:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    v: float = 0.0
    w: float = 0.0
    t_ms: int = 0
    collision: bool = False
    wall_hit: bool = False


class DiffDriveSim:
    """Fixed-step kinematic robot in a virtual corridor."""

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()
        self.state = SimState()
        self.rng = random.Random(0)

    def reset(self, seed: int) -> SimState:
        self.state = SimState()
        self.rng = random.Random(seed)
        return self.state

    def proximity_m(self) -> float:
        """Forward distance reading with tiny deterministic noise."""
        c, s = self.config, self.state
        best = c.sensor_range_m
        dx, dy = math.cos(s.theta), math.sin(s.theta)
        for ox, oy, r in c.obstacles:
            rx, ry = ox - s.x, oy - s.y
            ahead = rx * dx + ry * dy
            if ahead <= 0:
                continue
            lateral = abs(rx * dy - ry * dx)
            if lateral < r + c.robot_radius:
                best = min(best, max(0.0, ahead - (r + c.robot_radius)))
        # Walls: distance along ray to y = +/-half_width.
        if abs(dy) > 1e-9:
            for wall_y in (c.corridor_half_width, -c.corridor_half_width):
                t = (wall_y - s.y) / dy
                if t > 0:
                    best = min(best, t)
        noise = (self.rng.random() - 0.5) * 0.002  # +/-1mm seeded noise
        return round(max(0.0, min(c.sensor_range_m, best + noise)), 4)

    def apply(self, v: float, w: float) -> SimState:
        """Advance one fixed step with a (guard-authorized) command."""
        c, s = self.config, self.state
        dt_ms = int(round(c.dt * 1000))
        s.t_ms += dt_ms
        s.v, s.w = v, w
        s.x += v * math.cos(s.theta) * c.dt
        s.y += v * math.sin(s.theta) * c.dt
        s.theta += w * c.dt
        if abs(s.y) >= c.corridor_half_width - c.robot_radius:
            s.wall_hit = True
        for ox, oy, r in c.obstacles:
            if math.hypot(s.x - ox, s.y - oy) < r + c.robot_radius:
                s.collision = True
        return s

    def stopped(self) -> SimState:
        """Advance one fixed step with zero velocity (safe state)."""
        return self.apply(0.0, 0.0)

    def snapshot(self) -> dict[str, Any]:
        """Per-tick trace motion (rounded exactly as the fault lab logs)."""
        s = self.state
        return {"x": round(s.x, 4), "y": round(s.y, 4),
                "theta": round(s.theta, 4)}

    def final_stats(self) -> dict[str, Any]:
        """Oracle inputs describing the end of a run."""
        s = self.state
        return {"final_x": round(s.x, 4), "final_y": round(s.y, 4),
                "collision": s.collision, "wall_hit": s.wall_hit}


@dataclass(frozen=True)
class BeltConfig:
    dt: float = 0.01


@dataclass
class BeltState:
    position_m: float = 0.0  # loop odometer (unbounded, never wraps)
    speed_mps: float = 0.0
    jammed: bool = False
    t_ms: int = 0


class BeltSim:
    """Fixed-step 1D conveyor belt with jam physics.

    While jammed, applied commands are ignored (no integration, exact
    position freeze) and the felt speed decays geometrically; ``w`` is
    always ignored (a belt has one axis).
    """

    def __init__(self, config: BeltConfig | None = None) -> None:
        self.config = config or BeltConfig()
        self.state = BeltState()
        self.rng = random.Random(0)

    def reset(self, seed: int) -> BeltState:
        self.state = BeltState()
        self.rng = random.Random(seed)  # parity hook for future belt noise
        return self.state

    def set_jam(self, jammed: bool) -> BeltState:
        self.state.jammed = bool(jammed)
        return self.state

    def apply(self, v: float, w: float) -> BeltState:
        """Advance one fixed step with a (guard-authorized) command."""
        del w  # one axis: angular component is meaningless on a belt
        s = self.state
        s.t_ms += int(round(self.config.dt * 1000))
        if s.jammed:
            s.speed_mps *= 0.5
            if abs(s.speed_mps) < 1e-12:
                s.speed_mps = 0.0
        else:
            s.speed_mps = v
            s.position_m += v * self.config.dt
        return s

    def stopped(self) -> BeltState:
        """Advance one fixed step with zero velocity (safe state)."""
        return self.apply(0.0, 0.0)

    def snapshot(self) -> dict[str, Any]:
        s = self.state
        return {"position": round(s.position_m, 4),
                "speed": round(s.speed_mps, 4), "jammed": s.jammed}

    def final_stats(self) -> dict[str, Any]:
        s = self.state
        return {"final_position": round(s.position_m, 4),
                "final_speed": round(s.speed_mps, 4),
                # primary-axis odometry aliases: generic oracles (progress,
                # denial counts) apply unchanged to belt machines.
                "final_x": round(s.position_m, 4), "final_y": 0.0,
                "collision": False, "wall_hit": False}


# --- GENESIS CELL: AMR + conveyor + transfer interlock -------------------

CELL_IDLE = 0
CELL_ENROUTE = 1
CELL_AT_STATION = 2
CELL_TRANSFERRING = 3
CELL_COMPLETE = 4
CELL_SAFE = 5

CELL_PHASE_NAMES = ("IDLE", "ENROUTE", "AT_STATION", "TRANSFERRING",
                    "COMPLETE", "SAFE")


def cell_transfer_allowed(phase: int, presence_fresh: bool,
                          presence: bool, jammed: bool,
                          estop: bool) -> bool:
    """Pure transfer interlock (mirrored by genesis_cellcheck on QNX).

    The belt may run for transfer only while the transfer phase holds
    with live presence proof and no jam or e-stop. Anything else
    inhibits the transfer; the caller latches the safe phase.
    """
    return (phase == CELL_TRANSFERRING and presence_fresh and presence
            and not jammed and not estop)


@dataclass(frozen=True)
class CellConfig:
    dt: float = 0.01
    station_x_m: float = 6.0
    transfer_ticks: int = 50
    station_tol_m: float = 0.15


@dataclass
class CellState:
    phase: int = CELL_IDLE
    transfer_done_ticks: int = 0
    transfers_completed: int = 0
    estop: bool = False
    estop_latched: bool = False
    jammed: bool = False
    presence: bool = False
    presence_fresh: bool = True
    inhibited: bool = False
    recovered: bool = False
    t_ms: int = 0


class CellSim:
    """Fixed-step industrial cell: AMR leg + belt leg + interlock.

    The AMR drives to the transfer station, docks, and the belt runs
    exactly ``transfer_ticks`` guarded ticks. E-stop latches the safe
    phase permanently for the run; jam and stale-presence abort the
    transfer but allow ONE supervised recovery (re-qualify presence,
    restart the transfer). Deterministic: motion integrates without
    noise; only the proximity sensor carries seeded noise.
    """

    def __init__(self, config: CellConfig | None = None) -> None:
        self.config = config or CellConfig()
        self.amr = DiffDriveSim(SimConfig(dt=self.config.dt))
        self.belt = BeltSim(BeltConfig(dt=self.config.dt))
        self.state = CellState()
        self.rng = random.Random(0)

    def reset(self, seed: int) -> CellState:
        self.amr.reset(seed)
        self.belt.reset(seed)
        self.state = CellState()
        self.rng = random.Random(seed)
        return self.state

    def set_jam(self, jammed: bool) -> CellState:
        self.state.jammed = bool(jammed)
        self.belt.set_jam(jammed)
        return self.state

    def set_estop(self, engaged: bool) -> CellState:
        self.state.estop = bool(engaged)
        if engaged:
            self.state.estop_latched = True  # manual reset only, never auto
        return self.state

    def freeze_presence(self, frozen: bool) -> CellState:
        self.state.presence_fresh = not frozen
        return self.state

    def apply(self, v: float, w: float) -> CellState:
        """Advance the AMR leg (ignored unless ENROUTE)."""
        s, c = self.state, self.config
        s.t_ms += int(round(c.dt * 1000))
        if s.phase in (CELL_IDLE, CELL_ENROUTE):
            if s.phase == CELL_IDLE:
                s.phase = CELL_ENROUTE
            self.amr.apply(v, w)
        else:
            self.amr.stopped()  # docked/aborted/complete: no AMR motion
        self.belt.stopped()  # belt only moves via apply_transfer
        self._update(s, c)
        return s

    def apply_transfer(self, v: float) -> CellState:
        """Advance the belt leg for transfer (interlock-gated)."""
        s, c = self.state, self.config
        s.t_ms += int(round(c.dt * 1000))
        self.amr.stopped()  # docked: the AMR never moves during transfer
        if cell_transfer_allowed(s.phase, s.presence_fresh, s.presence,
                                 s.jammed, s.estop):
            s.inhibited = False
            self.belt.apply(v, 0.0)
            s.transfer_done_ticks += 1
            if s.transfer_done_ticks >= c.transfer_ticks:
                s.phase = CELL_COMPLETE
                s.transfers_completed += 1
        else:
            s.inhibited = True
            self.belt.stopped()
        self._update(s, c)
        return s

    def stopped(self) -> CellState:
        """Advance one fixed step with both legs frozen."""
        s, c = self.state, self.config
        s.t_ms += int(round(c.dt * 1000))
        self.amr.stopped()
        self.belt.stopped()
        self._update(s, c)
        return s

    def _update(self, s: CellState, c: CellConfig) -> None:
        if s.phase == CELL_SAFE or s.phase == CELL_COMPLETE:
            return
        if s.estop:
            s.phase = CELL_SAFE
            return
        at_station = self.amr.state.x >= c.station_x_m - c.station_tol_m
        if s.presence_fresh:
            s.presence = at_station
        if s.phase == CELL_ENROUTE and at_station:
            s.phase = CELL_AT_STATION
        elif s.phase == CELL_AT_STATION:
            if s.presence_fresh and s.presence:
                s.phase = CELL_TRANSFERRING
        elif s.phase == CELL_TRANSFERRING:
            if s.jammed or not s.presence_fresh or not s.presence:
                s.phase = CELL_SAFE  # aborted transfer, supervised recovery only

    def request_recovery(self) -> bool:
        """Supervised re-arm after jam/stale abort. Never after e-stop.

        Returns True when the cell re-enters AT_STATION to re-qualify
        presence and restart the transfer from tick zero.
        """
        s = self.state
        if s.phase != CELL_SAFE or s.estop or s.estop_latched:
            return False
        if s.jammed or not s.presence_fresh:
            return False
        s.phase = CELL_AT_STATION
        s.transfer_done_ticks = 0
        s.recovered = True
        return True

    def snapshot(self) -> dict[str, Any]:
        s = self.state
        return {"cell_phase": CELL_PHASE_NAMES[s.phase],
                "presence": s.presence, "presence_fresh": s.presence_fresh,
                "transfers": s.transfers_completed,
                "transfer_ticks": s.transfer_done_ticks,
                "inhibited": s.inhibited,
                "amr_x": round(self.amr.state.x, 4),
                "belt_pos": round(self.belt.state.position_m, 4),
                "belt_jammed": s.jammed}

    def final_stats(self) -> dict[str, Any]:
        s = self.state
        a = self.amr.state
        return {"cell_phase": CELL_PHASE_NAMES[s.phase],
                "transfers_completed": s.transfers_completed,
                "recovered": s.recovered,
                "belt_final_position": round(
                    self.belt.state.position_m, 4),
                # primary-axis aliases for generic oracles.
                "final_x": round(a.x, 4), "final_y": round(a.y, 4),
                "collision": a.collision, "wall_hit": a.wall_hit}
