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
      "mobiles", "differential", "agv", "agvs", "chariot", "roboter"),
     "differential_drive_robot"),
    (("conveyor", "conveyors", "belt", "belts", "line", "lines",
      "convoyeur", "bande", "tapis", "cinta"),
     "conveyor"),
    (("arm", "arms", "gripper", "grippers", "manipulator",
      "manipulators", "bras", "brazo"), "robotic_arm_virtual"),
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
# Omega3 §5.3 adds compound rates ("90 feet per minute" class): the new
# alternatives are non-capturing, so the message uses group(0) — which
# renders byte-identical text for the original alternatives.
_WRONG_SPEED_RE = re.compile(
    r"(?:\d+(?:\.\d+)?)\s*(?:km/h|kph|mph|cm/s|mm/s|m/min|ft/s)\b"
    r"|(?:\d+(?:\.\d+)?)\s*(?:feet|foot|ft|inches?|yards?|miles?|knots?)"
    r"\s*(?:per|/)\s*(?:minute|min|second|sec|hour|h|ms)\b"
    r"|(?:\d+(?:\.\d+)?)\s*per\s*(?:minute|min|second|sec|hour)s?\b"
    # Hardening-2: bare rate units ("3 knots" is nautical mph, not
    # m/s) and throughput rates ("400 totes per hour" states no
    # speed). The time-word anchor keeps "10 ms period" safe.
    r"|(?:\d+(?:\.\d+)?)\s*knots?\b"
    r"|(?:\d+(?:\.\d+)?)\s*[a-z]+\s+per\s+"
    r"(?:minute|min|second|sec|hour|h)\b")
# Hardening-2: a unitless decimal inside a contrast frame next to a
# stated speed ("0.4 m/s normally, 1.4 when hurried") is a second
# speed without a unit — ambiguous, never last-wins. Versions
# ("v2.0") are excluded by the lookbehind; plain integers stay a
# documented residual.
_BARE_DECIMAL_RE = re.compile(r"(?<![\w.])\d+\.\d+(?!\s*(?:ms|m/s)\b)")
_SPEED_CONTRAST_RE = re.compile(
    r"\b(?:normally|usually|hurr\w*|rush\w*|surge|boost"
    r"|eco(?:\s*mode)?|night|days?|dayshift|otherwise|instead"
    r"|but|while|whereas|weekend|dark)\b")
_WRONG_PERIOD_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:seconds?|sec|s|minutes?|min)\b")
# A control rate in Hz is a frequency, not a period: refuse rather than convert.
_HZ_RE = re.compile(r"(\d+(?:\.\d+)?)\s*hz\b")
# Fractional milliseconds ("0.2 ms") must refuse: _PERIOD_RE would
# otherwise match the fractional digit as an integer period.
_FRACTIONAL_PERIOD_RE = re.compile(r"(\d+\.\d+)\s*ms\b")
_PERIOD_WORDS = ("period", "cycle", "control", "periode")
_PERIOD_CTX = r"period|cycle|loop|control|tick|servo|update"
# Multi-word coordinations ("and also", "as well as", ...) join two
# values for one machine exactly like "and" (longest first).
_COORD_CONJ = (r"and\s+also|as\s+well\s+as|along\s+with|together\s+with"
               r"|plus|and|or|but|yet|/|,")
# Non-control consumers: a loose ms value with one nearby is telemetry,
# not a second control period (the "logs every 100 ms" exemption).
_LOOSE_CONSUMERS = r"log|telemet|report|publish|sample|record|trace|diag"


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
    # Fractional milliseconds refuse first: the integer period regex
    # would otherwise match the fractional digit ("0.2 ms" -> 2).
    frac = _FRACTIONAL_PERIOD_RE.search(text)
    if frac:
        raise PlannerRejection(
            f"Fractional milliseconds ({frac.group(1)} ms) are not "
            "supported; state an integer period in ms (1..1000)")
    # Contradictory requirements (holdout v1, 7 Nov 2026). Only values tied
    # to control-period words count ("10 ms control, logs every 100 ms" is
    # fine); two different tied periods or two different speeds are refused.
    # Omega3 §5.3: a tied value plus an UNEXPLAINED loose value also
    # refuses ("15 ms and also 150 ms" silently kept one). Loose values
    # with a telemetry consumer nearby keep the logging exemption.
    tied, loose = set(), set()
    loose_raw: list[tuple[int, str]] = []
    for m in _PERIOD_RE.finditer(text):
        ctx = text[max(0, m.start() - 12):m.end() + 12]
        if re.search(_PERIOD_CTX, ctx):
            tied.add(int(m.group(1)))
        else:
            loose.add(int(m.group(1)))
            loose_raw.append((int(m.group(1)),
                              text[max(0, m.start() - 20):m.end() + 20]))
    unexplained = {v for v, ctx in loose_raw
                   if not re.search(_LOOSE_CONSUMERS, ctx)}
    if tied and unexplained and (unexplained - tied):
        raise PlannerRejection(
            f"contradictory periods {sorted(tied | unexplained)} ms; "
            "state exactly one")
    periods = tied or loose
    speeds = {float(x) for x in _SPEED_RE.findall(text)}
    # Hardening-2: a unitless decimal in a contrast frame
    # ("0.5 m/s normally, 1.1 when rushed") is an ambiguous second
    # speed — refuse rather than silently keep the first value.
    if _BARE_DECIMAL_RE.search(text) and _SPEED_CONTRAST_RE.search(text):
        raise PlannerRejection(
            "ambiguous speed requirement (a second value without a "
            "unit); state exactly one speed in m/s")
    # Coordinated values ("20 ms and 50 ms", "period 20 and 50 ms") name
    # two periods for one machine even when only one sits next to a
    # period word (the ±12-char tied/loose window misses the other).
    # Contrastive and multi-word conjunctions coordinate too.
    for first, second in re.findall(
            rf"(-?\d+)\s*(?:ms\s*)?(?:{_COORD_CONJ})\s*(-?\d+)\s*ms",
            text):
        if first != second:
            raise PlannerRejection(
                f"contradictory periods [{first}, {second}] ms; "
                "state exactly one")
    # Same rule for speeds: "0.8 and 1.6 m/s" states two maxima for
    # one machine (the bare first number inherits the unit).
    for first, second in re.findall(
            rf"(-?\d+(?:\.\d+)?)\s*(?:m/s\s*)?(?:{_COORD_CONJ})\s*"
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
                f"speed {w.group(0)} is not m/s; "
                "state speeds in m/s within (0, 10]")
    if not 0.0 < max_linear <= 10.0:
        raise PlannerRejection(f"max speed {max_linear} m/s out of range (0, 10]")

    # Omega3 §5.3: a named parameter with no usable value fails closed
    # ("speed TBD", "unknown period") instead of silently defaulting.
    # Bare-kind requests ("warehouse rover") and hyphenated modifiers
    # ("high-speed") carry no such marker and keep their defaults.
    _MISSING = (r"\b(?:no|without|missing|unknown|unspecified|tbd"
                r"|t\.b\.d\.|todo)\b")
    period_missing = (
        re.search(rf"(?:{_MISSING})\s+.{{0,12}}\bperiod\b", text)
        or re.search(r"\bperiod\s*[:=?]", text)
        or re.search(rf"\bperiod\b.{{0,15}}(?:{_MISSING})", text))
    speed_missing = (
        re.search(rf"(?:{_MISSING})\s+.{{0,12}}\b(?:speed|velocity)\b", text)
        or re.search(r"\b(?:speed|velocity)\s*[:=?]", text)
        or re.search(rf"\b(?:speed|velocity)\b.{{0,15}}(?:{_MISSING})",
                      text))
    if (period_missing and not periods) or (speed_missing and not speeds):
        which = ("period" if (period_missing and not periods)
                 else "speed")
        raise PlannerRejection(
            f"states {which} but gives no value; state it explicitly "
            "in ms (1..1000) or m/s (0, 10], or omit it for the default")

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
