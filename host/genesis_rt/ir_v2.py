# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Machine IR v2: strict loader + semantic validation + deterministic v1 migration.

v2 closes the gaps of v1 (unvalidated command/telemetry/scheduling surface,
untyped actuator/sensor units, implicit fault responses). Rules:

- closed world: every id, unit, event, fault and action comes from a
  whitelist; unknown keys are rejected;
- v1 superset: v2 machine kinds, condition ids, action ids and scenario ids
  include every v1 value, so migration never renames user vocabulary;
  the one exception is ``industrial_cell`` (and its coordination block),
  which v2 explicitly rejects: no v2 cell semantics exist yet, so a loud
  IRValidationError replaces a silent drop or a raw KeyError;
- cross-references resolve: transitions/commands/telemetry/fault_responses
  must point at declared components, and fault entry states must be safe;
- no silent invention: ``migrate_v1_to_v2`` derives every v2-only field
  from v1 through a documented table and tags each derived entry with
  ``"origin": "migrated-v1"`` so reviewers can audit the derivation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .ir import (
    ACTUATOR_TYPES,
    EXECUTION_TARGET,
    MACHINE_KINDS,
    SENSOR_TYPES,
    IF_IDS as V1_IF_IDS,
    THEN_IDS as V1_THEN_IDS,
    SCENARIO_IDS,
    IRValidationError,
    canonical_json,
)

SCHEMA_VERSION = 2
MIGRATED_ORIGIN = "migrated-v1"

ARCHES = ("x86_64",)

# Same component-id shape as v1 (ir._ID_RE, duplicated to avoid a private import).
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-_]{0,63}$")

# unit compatibility per actuator / sensor type (closed world)
ACTUATOR_UNITS: dict[str, tuple[str, ...]] = {
    "velocity_command": ("mps",),
    "position_command": ("m", "rad"),
    "gripper_command": ("pct", "bool"),
    "belt_speed_command": ("mps",),
}
SENSOR_UNITS: dict[str, tuple[str, ...]] = {
    "distance_m": ("m",),
    "odometry": ("m_rad",),
    "joint_rad": ("rad",),
    "belt_speed_mps": ("mps",),
    "estop_bool": ("bool",),
    "presence_bool": ("bool",),
}
FIELD_UNITS = ("m", "mps", "rad", "radps", "m_rad", "pct", "bool", "ms", "hz")

SCHEDULING_POLICIES = ("periodic", "sporadic", "fifo")
TRANSITION_EVENTS = (
    "start",
    "stop",
    "estop",
    "reset",
    "fault_detected",
    "fault_cleared",
    "watchdog_timeout",
    "deadline_miss",
)
FAULT_IDS = (
    "stale_sensor",
    "deadline_miss",
    "command_rejected",
    "simulator_disconnect",
    "planner_crash",
    "device_fault",
    "corrupted_message",
    "dropped_message",
)
# v2 conditions/actions are strict supersets of v1: migration copies v1
# contract vocabulary verbatim and it must validate.
IF_IDS = V1_IF_IDS + ("planner_crashed", "deadline_missed")
THEN_IDS = V1_THEN_IDS

REQUIRED_TOP = (
    "schema_version",
    "machine",
    "actuators",
    "sensors",
    "control",
    "states",
    "transitions",
    "commands",
    "telemetry",
    "safety_contracts",
    "fault_responses",
    "verification",
    "simulation",
)

# Total map: every v1 contract condition implies one v2 fault id.
# The v2 fault_responses action is the v1 contract's own `then` (verbatim).
V1_IF_FAULT_MAP: dict[str, str] = {
    "proximity_is_stale": "stale_sensor",
    "speed_exceeds_limit": "command_rejected",
    "simulator_disconnected": "simulator_disconnect",
    "command_overdue": "deadline_miss",
    "sequence_regressed": "dropped_message",
    "message_malformed": "corrupted_message",
    "device_fault": "device_fault",
}


def _fail(path: str, msg: str) -> IRValidationError:
    return IRValidationError(f"ir-v2: {path}: {msg}")


def _need_str(doc: dict[str, Any], key: str, path: str) -> str:
    val = doc.get(key)
    if not isinstance(val, str) or not val:
        raise _fail(path, f"'{key}' must be a non-empty string")
    return val


def _need_id(doc: dict[str, Any], key: str, path: str) -> str:
    val = _need_str(doc, key, path)
    if not _ID_RE.match(val):
        raise _fail(path, f"'{key}' must match ^[a-z0-9][a-z0-9-_]*$ (<=64 chars)")
    return val


def _need_num(doc: dict[str, Any], key: str, path: str) -> float:
    val = doc.get(key)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise _fail(path, f"'{key}' must be a number")
    val = float(val)
    if val != val or val in (float("inf"), float("-inf")):
        raise _fail(path, f"'{key}' must be finite")
    return val


def _reject_unknown(doc: dict[str, Any], allowed: tuple[str, ...], path: str) -> None:
    for key in doc:
        if key not in allowed:
            raise _fail(path, f"unknown key '{key}'")


def validate_v2(doc: Any) -> dict[str, Any]:
    """Strictly validate a parsed Machine IR v2 document. Returns it typed."""
    if not isinstance(doc, dict):
        raise _fail("$", "document must be an object")
    for key in REQUIRED_TOP:
        if key not in doc:
            raise _fail("$", f"missing required key '{key}'")
    _reject_unknown(doc, REQUIRED_TOP, "$")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise _fail("schema_version", f"must be {SCHEMA_VERSION}")

    _validate_machine(doc["machine"])
    actuators = _validate_components(
        doc["actuators"], "actuators", ACTUATOR_TYPES, ACTUATOR_UNITS,
        extra=("bounds", "rate_limit", "fault_response"),
    )
    sensors = _validate_components(
        doc["sensors"], "sensors", SENSOR_TYPES, SENSOR_UNITS,
        extra=("freshness_limit_ms", "range"),
    )
    _check_global_ids(actuators, sensors)
    _validate_control(doc["control"])
    states = _validate_states(doc["states"])
    for ref_id in [a["fault_response"] for a in actuators.values()]:
        if ref_id not in states:
            raise _fail("actuators", f"fault_response '{ref_id}' is not a declared state")
        if not states[ref_id]["safe"]:
            raise _fail("actuators", f"fault_response '{ref_id}' is not a safe state")
    _validate_transitions(doc["transitions"], states)
    _check_policy_within_capability(doc["control"], actuators)
    commands = _validate_commands(doc["commands"], actuators)
    _validate_telemetry(doc["telemetry"], actuators, sensors, commands)
    _validate_safety_contracts(doc["safety_contracts"])
    _validate_fault_responses(doc["fault_responses"], states)
    _validate_verification(doc["verification"])
    _validate_simulation(doc["simulation"])
    return doc


def _validate_machine(machine: Any) -> None:
    if not isinstance(machine, dict):
        raise _fail("machine", "must be an object")
    _reject_unknown(machine, ("id", "kind", "profile", "execution_target", "arch", "simulation_only"), "machine")
    _need_id(machine, "id", "machine")
    kind = _need_str(machine, "kind", "machine")
    if kind not in MACHINE_KINDS:
        raise _fail("machine.kind", f"unknown kind '{kind}'")
    if kind == "industrial_cell":
        raise _fail("machine.kind", "'industrial_cell' is v1-only in this release: "
                                    "v2 has no cell coordination semantics")
    _need_str(machine, "profile", "machine")
    target = _need_str(machine, "execution_target", "machine")
    if target != EXECUTION_TARGET:
        raise _fail("machine.execution_target", f"must be '{EXECUTION_TARGET}'")
    arch = _need_str(machine, "arch", "machine")
    if arch not in ARCHES:
        raise _fail("machine.arch", f"unsupported arch '{arch}'")
    if machine.get("simulation_only") is not True:
        raise _fail("machine", "'simulation_only' must be true "
                               "(this toolchain drives virtual devices only; "
                               "no IR may authorize real hardware)")


def _validate_components(
    items: Any,
    section: str,
    known_types: tuple[str, ...],
    unit_table: dict[str, tuple[str, ...]],
    extra: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise _fail(section, "must be a non-empty list")
    seen: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(items):
        path = f"{section}[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("id", "type", "unit", "origin") + extra, path)
        cid = _need_id(item, "id", path)
        if cid in seen:
            raise _fail(path, f"duplicate id '{cid}' in {section}")
        ctype = _need_str(item, "type", path)
        if ctype not in known_types:
            raise _fail(path, f"unknown type '{ctype}'")
        allowed = unit_table.get(ctype)
        if allowed is None:  # fail closed, never a raw KeyError
            raise _fail(path, f"type '{ctype}' has no v2 unit mapping")
        unit = _need_str(item, "unit", path)
        if unit not in allowed:
            raise _fail(path, f"unit '{unit}' incompatible with type '{ctype}'")
        if section == "actuators":
            bounds = item.get("bounds")
            if not isinstance(bounds, dict):
                raise _fail(path, "'bounds' must be an object")
            _reject_unknown(bounds, ("min", "max"), f"{path}.bounds")
            lo = _need_num(bounds, "min", f"{path}.bounds")
            hi = _need_num(bounds, "max", f"{path}.bounds")
            if not lo < hi:
                raise _fail(path, "'bounds.min' must be < 'bounds.max'")
            if "rate_limit" in item:
                rl = _need_num(item, "rate_limit", path)
                if rl <= 0:
                    raise _fail(path, "'rate_limit' must be > 0")
            _need_id(item, "fault_response", path)
        else:
            fresh = _need_num(item, "freshness_limit_ms", path)
            if fresh <= 0:
                raise _fail(path, "'freshness_limit_ms' must be > 0")
            if "range" in item:
                rng = item["range"]
                if not isinstance(rng, dict):
                    raise _fail(path, "'range' must be an object")
                _reject_unknown(rng, ("min", "max"), f"{path}.range")
                lo = _need_num(rng, "min", f"{path}.range")
                hi = _need_num(rng, "max", f"{path}.range")
                if not lo < hi:
                    raise _fail(path, "'range.min' must be < 'range.max'")
        seen[cid] = item
    return seen


def _check_global_ids(actuators: dict[str, Any], sensors: dict[str, Any]) -> None:
    overlap = set(actuators) & set(sensors)
    if overlap:
        raise _fail("sensors", f"id(s) already used by actuators: {sorted(overlap)}")


def _validate_control(control: Any) -> None:
    if not isinstance(control, dict):
        raise _fail("control", "must be an object")
    _reject_unknown(
        control,
        ("period_ms", "deadline_ms", "max_linear_speed_mps", "max_angular_speed_radps",
         "scheduling", "guarded_state_transitions"),
        "control",
    )
    period = _need_num(control, "period_ms", "control")
    if period <= 0:
        raise _fail("control", "'period_ms' must be > 0")
    if "deadline_ms" in control:
        dl = _need_num(control, "deadline_ms", "control")
        if dl <= 0:
            raise _fail("control", "'deadline_ms' must be > 0")
    for key in ("max_linear_speed_mps", "max_angular_speed_radps"):
        val = _need_num(control, key, "control")
        if val <= 0:
            raise _fail("control", f"'{key}' must be > 0")
    sched = control.get("scheduling")
    if not isinstance(sched, dict):
        raise _fail("control", "'scheduling' must be an object")
    _reject_unknown(sched, ("policy", "priority"), "control.scheduling")
    policy = _need_str(sched, "policy", "control.scheduling")
    if policy not in SCHEDULING_POLICIES:
        raise _fail("control.scheduling", f"unknown policy '{policy}'")
    prio = sched.get("priority")
    if isinstance(prio, bool) or not isinstance(prio, int) or not 1 <= prio <= 255:
        raise _fail("control.scheduling", "'priority' must be an int in 1..255")
    if control.get("guarded_state_transitions") is not True:
        raise _fail("control", "'guarded_state_transitions' must be true")


def _validate_states(states: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(states, list) or not states:
        raise _fail("states", "must be a non-empty list")
    seen: dict[str, dict[str, Any]] = {}
    initials = 0
    for i, item in enumerate(states):
        path = f"states[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("id", "safe", "initial", "origin"), path)
        sid = _need_id(item, "id", path)
        if sid in seen:
            raise _fail(path, f"duplicate state id '{sid}'")
        if not isinstance(item.get("safe"), bool):
            raise _fail(path, "'safe' must be a boolean")
        if not isinstance(item.get("initial"), bool):
            raise _fail(path, "'initial' must be a boolean")
        if item["initial"]:
            initials += 1
        seen[sid] = item
    if initials != 1:
        raise _fail("states", f"must declare exactly one initial state, found {initials}")
    if not any(s["safe"] for s in seen.values()):
        raise _fail("states", "must declare at least one safe state")
    return seen


def _validate_transitions(items: Any, states: dict[str, Any]) -> None:
    if not isinstance(items, list):
        raise _fail("transitions", "must be a list")
    seen: set[tuple[str, str, str]] = set()
    for i, item in enumerate(items):
        path = f"transitions[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("from", "to", "event", "origin"), path)
        src = _need_str(item, "from", path)
        dst = _need_str(item, "to", path)
        if src not in states:
            raise _fail(path, f"unknown state '{src}'")
        if dst not in states:
            raise _fail(path, f"unknown state '{dst}'")
        if src == dst:
            raise _fail(path, "self-transitions are rejected (from == to)")
        event = _need_str(item, "event", path)
        if event not in TRANSITION_EVENTS:
            raise _fail(path, f"unknown event '{event}'")
        key = (src, dst, event)
        if key in seen:
            raise _fail(path, f"duplicate transition {key}")
        seen.add(key)


def _check_policy_within_capability(control: dict[str, Any],
                                      actuators: dict[str, Any]) -> None:
    """The guard policy must fit inside the physical capability.

    The guard enforces ``control.max_linear_speed_mps``; every mps-unit
    actuator must be able to honor a policy-allowed command, otherwise a
    conforming build would saturate (or fault) on legal input. Only the
    symmetric magnitude is compared: policy p is consistent iff
    [-p, +p] fits inside every mps actuator's [min, max].
    """
    policy = float(control["max_linear_speed_mps"])
    for aid, act in actuators.items():
        if act["unit"] != "mps":
            continue
        lo = float(act["bounds"]["min"])
        hi = float(act["bounds"]["max"])
        if not (-policy >= lo and policy <= hi):
            raise _fail(
                "control",
                f"'max_linear_speed_mps' {policy} exceeds actuator '{aid}' "
                f"capability [{lo}, {hi}] (policy must fit inside capability)")


def _validate_commands(items: Any, actuators: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        raise _fail("commands", "must be a non-empty list")
    seen: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(items):
        path = f"commands[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("id", "actuator", "deadline_ms", "fields", "origin"), path)
        cid = _need_id(item, "id", path)
        if cid in seen:
            raise _fail(path, f"duplicate command id '{cid}'")
        act = _need_str(item, "actuator", path)
        if act not in actuators:
            raise _fail(path, f"unknown actuator '{act}'")
        dl = _need_num(item, "deadline_ms", path)
        if dl <= 0:
            raise _fail(path, "'deadline_ms' must be > 0")
        fields = item.get("fields")
        if not isinstance(fields, list) or not fields:
            raise _fail(path, "'fields' must be a non-empty list")
        for j, field in enumerate(fields):
            fpath = f"{path}.fields[{j}]"
            if not isinstance(field, dict):
                raise _fail(fpath, "must be an object")
            _reject_unknown(field, ("name", "unit", "min", "max"), fpath)
            _need_str(field, "name", fpath)
            unit = _need_str(field, "unit", fpath)
            if unit not in FIELD_UNITS:
                raise _fail(fpath, f"unknown unit '{unit}'")
            lo = _need_num(field, "min", fpath)
            hi = _need_num(field, "max", fpath)
            if not lo < hi:
                raise _fail(fpath, "'min' must be < 'max'")
            cap = actuators[act]
            if unit != cap["unit"]:
                raise _fail(fpath, f"unit '{unit}' mismatches actuator "
                                   f"'{act}' unit '{cap['unit']}'")
            if not (float(cap["bounds"]["min"]) <= lo
                    and hi <= float(cap["bounds"]["max"])):
                raise _fail(fpath, f"[{lo}, {hi}] exceeds actuator '{act}' "
                                   f"bounds [{cap['bounds']['min']}, "
                                   f"{cap['bounds']['max']}]")
        seen[cid] = item
    return seen


def _validate_telemetry(
    items: Any,
    actuators: dict[str, Any],
    sensors: dict[str, Any],
    commands: dict[str, Any],
) -> None:
    if not isinstance(items, list):
        raise _fail("telemetry", "must be a list")
    known = set(actuators) | set(sensors)
    seen: set[str] = set()
    for i, item in enumerate(items):
        path = f"telemetry[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("id", "source", "rate_hz", "origin"), path)
        tid = _need_id(item, "id", path)
        if tid in seen or tid in commands or tid in known:
            raise _fail(path, f"duplicate component id '{tid}'")
        src = _need_str(item, "source", path)
        if src not in known:
            raise _fail(path, f"unknown source '{src}'")
        rate = _need_num(item, "rate_hz", path)
        if not 0 < rate <= 1000:
            raise _fail(path, "'rate_hz' must be in (0, 1000]")
        seen.add(tid)


def _validate_safety_contracts(items: Any) -> None:
    if not isinstance(items, list) or not items:
        raise _fail("safety_contracts", "must be a non-empty list")
    for i, item in enumerate(items):
        path = f"safety_contracts[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("name", "if", "then", "origin"), path)
        _need_id(item, "name", path)
        cond = _need_str(item, "if", path)
        if cond not in IF_IDS:
            raise _fail(path, f"unknown condition '{cond}'")
        then = _need_str(item, "then", path)
        if then not in THEN_IDS:
            raise _fail(path, f"unknown action '{then}'")


def _validate_fault_responses(items: Any, states: dict[str, Any]) -> None:
    if not isinstance(items, list) or not items:
        raise _fail("fault_responses", "must be a non-empty list")
    for i, item in enumerate(items):
        path = f"fault_responses[{i}]"
        if not isinstance(item, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(item, ("fault", "enter_state", "action", "origin"), path)
        fault = _need_str(item, "fault", path)
        if fault not in FAULT_IDS:
            raise _fail(path, f"unknown fault '{fault}'")
        state = _need_str(item, "enter_state", path)
        if state not in states:
            raise _fail(path, f"unknown state '{state}'")
        if not states[state]["safe"]:
            raise _fail(path, f"enter_state '{state}' is not a safe state")
        action = _need_str(item, "action", path)
        if action not in THEN_IDS:
            raise _fail(path, f"unknown action '{action}'")


def _validate_verification(ver: Any) -> None:
    if not isinstance(ver, dict):
        raise _fail("verification", "must be an object")
    _reject_unknown(ver, ("scenarios", "requirements"), "verification")
    scenarios = ver.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise _fail("verification", "'scenarios' must be a non-empty list")
    for s in scenarios:
        if not isinstance(s, str) or not s:
            raise _fail("verification", "scenario names must be non-empty strings")
        if s not in SCENARIO_IDS:
            raise _fail("verification", f"unknown scenario id: '{s}'")
    reqs = ver.get("requirements", [])
    if not isinstance(reqs, list):
        raise _fail("verification", "'requirements' must be a list")
    for i, req in enumerate(reqs):
        path = f"verification.requirements[{i}]"
        if not isinstance(req, dict):
            raise _fail(path, "must be an object")
        _reject_unknown(req, ("id", "claim", "scenario", "origin"), path)
        _need_str(req, "id", path)
        claim = _need_str(req, "claim", path)
        if len(claim) > 256:
            raise _fail(path, "'claim' must be <= 256 chars")
        scenario = _need_str(req, "scenario", path)
        if scenario not in scenarios:
            raise _fail(path, f"unknown scenario '{scenario}'")


def _validate_simulation(sim: Any) -> None:
    if not isinstance(sim, dict):
        raise _fail("simulation", "must be an object")
    _reject_unknown(sim, ("dt_ms", "duration_ms", "seed"), "simulation")
    dt = _need_num(sim, "dt_ms", "simulation")
    if not 1 <= dt <= 100:
        raise _fail("simulation", "'dt_ms' must be in 1..100")
    dur = _need_num(sim, "duration_ms", "simulation")
    if not 0 < dur <= 600000:
        raise _fail("simulation", "'duration_ms' must be in (0, 600000]")
    seed = sim.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise _fail("simulation", "'seed' must be a non-negative int")


def load_ir_v2_file(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate a v2 IR file. Raises IRValidationError."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IRValidationError(f"ir-v2: {path}: invalid JSON: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema_version") != SCHEMA_VERSION:
        raise IRValidationError(f"ir-v2: {path}: not a schema_version={SCHEMA_VERSION} document")
    return validate_v2(doc)


def migrate_v1_to_v2(v1: dict[str, Any]) -> dict[str, Any]:
    """Deterministically migrate a validated v1 doc to v2.

    Every derived entry carries ``"origin": "migrated-v1"``. Contract
    vocabulary (name/if/then) is copied verbatim; the fault id is derived
    from the condition via V1_IF_FAULT_MAP (total over v1 conditions).
    """
    from .ir import validate_ir

    v1 = validate_ir(v1)
    machine = v1["machine"]
    if machine["kind"] == "industrial_cell":
        raise IRValidationError(
            "ir-v2: migrate: 'industrial_cell' is v1-only in this release: "
            "v2 has no cell coordination semantics (the v1 'cell' block "
            "cannot be migrated)"
        )
    control = v1["control"]
    max_lin = float(control["max_linear_speed_mps"])
    max_ang = float(control["max_angular_speed_radps"])

    def _default_unit(table: dict[str, tuple[str, ...]], ctype: str,
                      where: str) -> str:
        units = table.get(ctype)
        if units is None:  # fail closed, never a raw KeyError
            raise IRValidationError(
                f"ir-v2: migrate: {where} type '{ctype}' has no v2 unit mapping"
            )
        return units[0]

    actuators = [
        {
            "id": a["id"],
            "type": a["type"],
            "unit": _default_unit(ACTUATOR_UNITS, a["type"], "actuator"),
            "bounds": {"min": -max_lin, "max": max_lin}
            if a["type"] in ("velocity_command", "belt_speed_command")
            else {"min": -max_ang, "max": max_ang},
            "fault_response": "safe_stop",
            "origin": MIGRATED_ORIGIN,
        }
        for a in v1["actuators"]
    ]
    sensors = [
        {
            "id": s["id"],
            "type": s["type"],
            "unit": _default_unit(SENSOR_UNITS, s["type"], "sensor"),
            "freshness_limit_ms": float(s.get("freshness_limit_ms", 100)),
            "origin": MIGRATED_ORIGIN,
        }
        for s in v1["sensors"]
    ]
    contracts = [
        {"name": c["name"], "if": c["if"], "then": c["then"], "origin": MIGRATED_ORIGIN}
        for c in v1["safety_contracts"]
    ]
    fault_responses = []
    for c in v1["safety_contracts"]:
        fault = V1_IF_FAULT_MAP.get(c["if"])
        if fault is None:  # unreachable post-validate_ir; fail loud, never invent
            raise IRValidationError(
                f"ir-v2: migrate: condition '{c['if']}' has no v2 fault mapping"
            )
        fault_responses.append(
            {"fault": fault, "enter_state": "safe_stop", "action": c["then"],
             "origin": MIGRATED_ORIGIN}
        )
    commands = [
        {
            "id": f"{a['id']}-cmd",
            "actuator": a["id"],
            "deadline_ms": float(control["period_ms"]),
            "fields": [
                {"name": "value",
                 "unit": _default_unit(ACTUATOR_UNITS, a["type"], "actuator"),
                 "min": -max_lin, "max": max_lin}
            ],
            "origin": MIGRATED_ORIGIN,
        }
        for a in v1["actuators"]
    ]
    telemetry = [
        {"id": f"{s['id']}-tm", "source": s["id"], "rate_hz": 10.0,
         "origin": MIGRATED_ORIGIN}
        for s in v1["sensors"]
    ]
    doc = {
        "schema_version": SCHEMA_VERSION,
        "machine": {
            "id": machine["id"],
            "kind": machine["kind"],
            "profile": f"migrated-v1-{machine['kind']}",
            "execution_target": machine["execution_target"],
            "arch": "x86_64",
            "simulation_only": bool(machine["simulation_only"]),
        },
        "actuators": actuators,
        "sensors": sensors,
        "control": {
            "period_ms": float(control["period_ms"]),
            "deadline_ms": float(control["period_ms"]),
            "max_linear_speed_mps": max_lin,
            "max_angular_speed_radps": max_ang,
            "scheduling": {"policy": "periodic", "priority": 10},
            "guarded_state_transitions": True,
        },
        "states": [
            {"id": "init", "safe": False, "initial": True, "origin": MIGRATED_ORIGIN},
            {"id": "running", "safe": False, "initial": False, "origin": MIGRATED_ORIGIN},
            {"id": "safe_stop", "safe": True, "initial": False, "origin": MIGRATED_ORIGIN},
        ],
        "transitions": [
            {"from": "init", "to": "running", "event": "start", "origin": MIGRATED_ORIGIN},
            {"from": "running", "to": "safe_stop", "event": "fault_detected",
             "origin": MIGRATED_ORIGIN},
            {"from": "safe_stop", "to": "init", "event": "reset", "origin": MIGRATED_ORIGIN},
        ],
        "commands": commands,
        "telemetry": telemetry,
        "safety_contracts": contracts,
        "fault_responses": fault_responses,
        "verification": {
            "scenarios": list(v1["verification"]["scenarios"]),
            "requirements": [],
        },
        "simulation": {"dt_ms": 10.0, "duration_ms": 10000.0, "seed": 0},
    }
    return validate_v2(doc)


__all__ = [
    "ARCHES",
    "ACTUATOR_UNITS",
    "SENSOR_UNITS",
    "FIELD_UNITS",
    "SCHEDULING_POLICIES",
    "TRANSITION_EVENTS",
    "FAULT_IDS",
    "THEN_IDS",
    "IF_IDS",
    "MIGRATED_ORIGIN",
    "SCHEMA_VERSION",
    "V1_IF_FAULT_MAP",
    "canonical_json",
    "load_ir_v2_file",
    "migrate_v1_to_v2",
    "validate_v2",
]
