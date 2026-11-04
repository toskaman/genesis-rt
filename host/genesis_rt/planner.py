# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Constrained intent planner (deterministic, offline, AI-optional).

Converts short constrained requests into Machine IR *proposals* that
must still pass strict validation. Unknown or unbounded requests are
rejected with guidance instead of guessed. An optional external LLM
provider may supply proposals through the same validated path; no
provider is bundled and none is required.
"""

from __future__ import annotations

import re
from typing import Any

from .ir import validate_ir

_PRESETS: dict[str, dict[str, Any]] = {
    "differential_drive_robot": {
        "actuators": [
            {"id": "left-motor", "type": "velocity_command"},
            {"id": "right-motor", "type": "velocity_command"},
        ],
        "sensors": [
            {"id": "proximity", "type": "distance_m", "freshness_limit_ms": 100},
            {"id": "odometry", "type": "odometry", "freshness_limit_ms": 100},
        ],
    },
    "conveyor": {
        "actuators": [{"id": "belt", "type": "belt_speed_command"}],
        "sensors": [
            {"id": "belt-speed", "type": "belt_speed_mps", "freshness_limit_ms": 200},
            {"id": "estop", "type": "estop_bool", "freshness_limit_ms": 50},
        ],
    },
    "robotic_arm_virtual": {
        "actuators": [
            {"id": "joint-1", "type": "position_command"},
            {"id": "joint-2", "type": "position_command"},
            {"id": "gripper", "type": "gripper_command"},
        ],
        "sensors": [
            {"id": "joint-feedback", "type": "joint_rad", "freshness_limit_ms": 100},
            {"id": "estop", "type": "estop_bool", "freshness_limit_ms": 50},
        ],
    },
}

_DEFAULT_CONTRACTS = [
    {"name": "stale-proximity-stop", "if": "proximity_is_stale", "then": "command_virtual_stop"},
    {"name": "speed-limit", "if": "speed_exceeds_limit", "then": "reject_command"},
    {"name": "simulator-watchdog", "if": "simulator_disconnected", "then": "command_virtual_stop"},
]

_KIND_HINTS = (
    (("robot", "rover", "amr", "mobile", "differential"), "differential_drive_robot"),
    (("conveyor", "belt", "line"), "conveyor"),
    (("arm", "gripper", "manipulator"), "robotic_arm_virtual"),
)

_AMR_SCENARIOS = (
    "nominal_navigation",
    "speed_command_over_limit",
    "stale_proximity_150ms",
    "planner_process_crash",
    "delayed_command",
    "dropped_message",
    "corrupted_message",
    "simulator_disconnect",
)
_CONVEYOR_SCENARIOS = (
    "nominal_navigation",
    "speed_command_over_limit",
    "delayed_command",
    "belt_jam",
)
_KIND_SCENARIOS = {
    "differential_drive_robot": _AMR_SCENARIOS,
    "conveyor": _CONVEYOR_SCENARIOS,
    "robotic_arm_virtual": _AMR_SCENARIOS,
}

_PERIOD_RE = re.compile(r"(\d+)\s*ms")
_SPEED_RE = re.compile(r"(\d+(?:\.\d+)?)\s*m/s")


class PlannerRejection(ValueError):
    """Raised when a request cannot be mapped to a safe IR proposal."""


def propose(request: str, machine_id: str = "machine-01") -> dict[str, Any]:
    """Build a validated IR proposal from a short constrained request."""
    text = (request or "").strip().lower()
    if len(text) < 8:
        raise PlannerRejection("request too short; describe the machine kind and limits")
    if len(text) > 2000:
        raise PlannerRejection("request too long; keep it under 2000 characters")

    kind: str | None = None
    words = set(re.findall(r"[a-z0-9]+", text))
    for hints, candidate in _KIND_HINTS:
        # Whole-word match: "robotic arm" must not fire the "robot" hint,
        # and "alarm" must not fire "arm".
        if any(h in words for h in hints):
            kind = candidate
            break
    if kind is None:
        raise PlannerRejection(
            "unknown machine kind; mention one of: robot/rover/AMR, conveyor/belt, arm/gripper")

    period_ms = 10
    m = _PERIOD_RE.search(text)
    if m:
        period_ms = int(m.group(1))
    if not 1 <= period_ms <= 1000:
        raise PlannerRejection(f"period {period_ms}ms out of range 1..1000")

    max_linear = 1.2
    m = _SPEED_RE.search(text)
    if m:
        max_linear = float(m.group(1))
    if not 0.0 < max_linear <= 10.0:
        raise PlannerRejection(f"max speed {max_linear} m/s out of range (0, 10]")

    preset = _PRESETS[kind]
    proposal = {
        "schema_version": 1,
        "machine": {"id": machine_id, "kind": kind,
                    "execution_target": "qnx8_x86_64_qemu", "simulation_only": True},
        "actuators": [dict(a) for a in preset["actuators"]],
        "sensors": [dict(s) for s in preset["sensors"]],
        "control": {"period_ms": period_ms, "max_linear_speed_mps": max_linear,
                    "max_angular_speed_radps": 1.0, "guarded_state_transitions": True},
        "safety_contracts": [dict(c) for c in _DEFAULT_CONTRACTS],
        "verification": {"scenarios": list(_KIND_SCENARIOS[kind])},
    }
    return validate_ir(proposal)  # proposals must pass the same strict gate
