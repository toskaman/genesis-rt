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
    (("robot", "robots", "rover", "rovers", "amr", "amrs", "mobile",
      "mobiles", "differential"), "differential_drive_robot"),
    (("conveyor", "conveyors", "belt", "belts", "line", "lines"),
     "conveyor"),
    (("arm", "arms", "gripper", "grippers", "manipulator",
      "manipulators"), "robotic_arm_virtual"),
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
    "estop_pressed",
)
_KIND_SCENARIOS = {
    "differential_drive_robot": _AMR_SCENARIOS,
    "conveyor": _CONVEYOR_SCENARIOS,
    "robotic_arm_virtual": _AMR_SCENARIOS,
}

_PERIOD_RE = re.compile(r"(-?\d+)\s*ms")
_SPEED_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*m/s")
# Wrong-but-plausible units: rejected with guidance instead of silently
# defaulted, so "5 km/h" never becomes an unasked-for 1.2 m/s machine.
_WRONG_SPEED_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(km/h|kph|mph|cm/s|mm/s|m/min|ft/s)\b")
_WRONG_PERIOD_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:seconds?|sec|s|minutes?|min)\b")
# A control rate in Hz is a frequency, not a period: refuse rather than convert.
_HZ_RE = re.compile(r"(\d+(?:\.\d+)?)\s*hz\b")
_PERIOD_WORDS = ("period", "cycle", "control")
_PERIOD_CTX = r"period|cycle|loop|control|tick|servo|update"


class PlannerRejection(ValueError):
    """Raised when a request cannot be mapped to a safe IR proposal."""


def propose(request: str, machine_id: str = "machine-01") -> dict[str, Any]:
    """Build a validated IR proposal from a short constrained request."""
    text = (request or "").strip().lower()
    if len(text) < 8:
        raise PlannerRejection("request too short; describe the machine kind and limits")
    if len(text) > 2000:
        raise PlannerRejection("request too long; keep it under 2000 characters")

    # Value screening runs BEFORE kind matching (Wave 10 jury D):
    # a contradictory / wrong-unit / out-of-range request refuses here,
    # so it can never exit as "unknown machine kind" and reach the
    # model, which would otherwise resurrect it by guessing a kind.
    # Contradictory requirements (holdout v1, 7 Nov 2026). Only values tied
    # to control-period words count ("10 ms control, logs every 100 ms" is
    # fine); two different tied periods or two different speeds are refused.
    tied, loose = set(), set()
    for m in _PERIOD_RE.finditer(text):
        ctx = text[max(0, m.start() - 12):m.end() + 12]
        (tied if re.search(_PERIOD_CTX, ctx) else loose).add(int(m.group(1)))
    periods = tied or loose
    speeds = {float(x) for x in _SPEED_RE.findall(text)}
    # Coordinated values ("20 ms and 50 ms", "period 20 and 50 ms") name
    # two periods for one machine even when only one sits next to a
    # period word (the ±12-char tied/loose window misses the other).
    # Contrastive conjunctions ("25 ms but 60 ms") coordinate too.
    for first, second in re.findall(
            r"(-?\d+)\s*(?:ms\s*)?(?:and|or|,|/|but|yet)\s*(-?\d+)\s*ms",
            text):
        if first != second:
            raise PlannerRejection(
                f"contradictory periods [{first}, {second}] ms; "
                "state exactly one")
    # Same rule for speeds: "0.8 and 1.6 m/s" states two maxima for
    # one machine (the bare first number inherits the unit).
    for first, second in re.findall(
            r"(-?\d+(?:\.\d+)?)\s*(?:m/s\s*)?(?:and|or|,|/|but|yet)\s*"
            r"(-?\d+(?:\.\d+)?)\s*m/s", text):
        if float(first) != float(second):
            raise PlannerRejection(
                f"contradictory speeds [{first}, {second}] m/s; "
                "state exactly one")
    if len(periods) > 1:
        raise PlannerRejection(
            f"contradictory periods {sorted(periods)} ms; state exactly one")
    if len(speeds) > 1:
        raise PlannerRejection(
            f"contradictory speeds {sorted(speeds)} m/s; state exactly one")
    hz = _HZ_RE.search(text)
    if hz and not periods and re.search(_PERIOD_CTX, text):
        raise PlannerRejection(
            f"{hz.group(1)} Hz is a rate, not a period; "
            "state the control period in ms (1..1000)")

    period_ms = 10
    if periods:
        period_ms = next(iter(periods))
    else:
        w = _WRONG_PERIOD_RE.search(text)
        if w and any(pw in text for pw in _PERIOD_WORDS):
            raise PlannerRejection(
                f"period {w.group(0)} is not milliseconds; "
                "state the control period in ms (1..1000)")
    if not 1 <= period_ms <= 1000:
        raise PlannerRejection(f"period {period_ms}ms out of range 1..1000")

    max_linear = 1.2
    m = _SPEED_RE.search(text)
    if m:
        max_linear = float(m.group(1))
    else:
        w = _WRONG_SPEED_RE.search(text)
        if w:
            raise PlannerRejection(
                f"speed {w.group(1)} {w.group(2)} is not m/s; "
                "state speeds in m/s within (0, 10]")
    if not 0.0 < max_linear <= 10.0:
        raise PlannerRejection(f"max speed {max_linear} m/s out of range (0, 10]")

    matched: list[str] = []
    words = set(re.findall(r"[a-z0-9]+", text))
    # Compound noun first: one adjacent "robot arm" / "robotic arm"
    # names a single manipulator, not a mobile robot plus an arm.
    # Two robot-family mentions ("robot arm and robot") stay ambiguous.
    if (re.search(r"\brobot(?:s|ic)?[\s-]+arms?\b", text)
            and len(re.findall(r"\brobot(?:s|ic|ics)?\b", text)) == 1):
        words.discard("robot")
        words.discard("robots")
    for hints, candidate in _KIND_HINTS:
        # Whole-word match: "robotic arm" must not fire the "robot" hint,
        # and "alarm" must not fire "arm".
        if any(h in words for h in hints):
            matched.append(candidate)
    if not matched:
        raise PlannerRejection(
            "unknown machine kind; mention one of: robot/rover/AMR, conveyor/belt, arm/gripper")
    if len(matched) > 1:
        raise PlannerRejection(
            f"ambiguous machine kind ({', '.join(sorted(matched))}); "
            "name exactly one machine in the request")
    kind = matched[0]

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
