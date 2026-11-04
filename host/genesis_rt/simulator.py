# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic 2D differential-drive simulator (host side, non-real-time).

Fixed time step, seeded noise, virtual corridor with obstacle zones.
Simulation only: nothing here commands physical hardware, and simulator
timing is never presented as QNX timing.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


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
