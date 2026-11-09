# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Machine IR v1 loading, strict validation and normalization.

Stdlib-only. Accepts JSON always; YAML when PyYAML is installed.
Validation is a strict whitelist: unknown keys, kinds, units or
contract identifiers are rejected, never guessed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
EXECUTION_TARGET = "qnx8_x86_64_qemu"

MACHINE_KINDS = ("differential_drive_robot", "conveyor", "robotic_arm_virtual",
                 "industrial_cell")
ACTUATOR_TYPES = ("velocity_command", "position_command", "gripper_command", "belt_speed_command")
SENSOR_TYPES = ("distance_m", "odometry", "joint_rad", "belt_speed_mps", "estop_bool",
                "presence_bool")
IF_IDS = (
    "proximity_is_stale",
    "speed_exceeds_limit",
    "simulator_disconnected",
    "command_overdue",
    "sequence_regressed",
    "message_malformed",
    "device_fault",
)
THEN_IDS = (
    "command_virtual_stop",
    "reject_command",
    "enter_safe_state",
    "hold_last_valid",
    "raise_telemetry_alarm",
)
SCENARIO_IDS = (
    "nominal_navigation",
    "speed_command_over_limit",
    "stale_proximity_150ms",
    "planner_process_crash",
    "delayed_command",
    "dropped_message",
    "corrupted_message",
    "simulator_disconnect",
    "belt_jam",
    "estop_pressed",
    "cell_nominal_transfer",
    "cell_transfer_jam",
    "cell_estop_during_transfer",
    "cell_stale_presence",
)

CELL_SCENARIO_IDS = (
    "cell_nominal_transfer",
    "cell_transfer_jam",
    "cell_estop_during_transfer",
    "cell_stale_presence",
)

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-_]{0,63}$")


class IRValidationError(ValueError):
    """Raised when a Machine IR document violates the v1 contract."""


def load_ir_file(path: str | Path) -> dict[str, Any]:
    """Load a Machine IR document from a JSON or YAML file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IRValidationError(
                f"YAML support needs PyYAML installed (pip install pyyaml): {p}"
            ) from exc
        data = yaml.safe_load(text)
    else:
        raise IRValidationError(f"unsupported IR file suffix: {p.suffix} (use .json/.yaml)")
    if not isinstance(data, dict):
        raise IRValidationError("IR document root must be a mapping")
    return validate_ir(data)


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise IRValidationError(msg)


def _check_id(value: Any, what: str) -> str:
    _need(isinstance(value, str) and _ID_RE.match(value),
          f"{what} must match ^[a-z0-9][a-z0-9-_]*$ (1..64 chars), got {value!r}")
    return value


def validate_ir(data: dict[str, Any]) -> dict[str, Any]:
    """Strictly validate and normalize a Machine IR v1 mapping.

    Returns a normalized deep copy with sorted scenario lists and
    default-free explicit control fields. Raises IRValidationError.
    """
    _need(isinstance(data, dict), "IR root must be a mapping")
    allowed_top = {"schema_version", "machine", "actuators", "sensors",
                   "control", "safety_contracts", "verification", "cell",
                   "defaults_applied"}
    unknown = set(data) - allowed_top
    _need(not unknown, f"unknown top-level keys: {sorted(unknown)}")
    for key in allowed_top - {"cell", "defaults_applied"}:
        _need(key in data, f"missing required key: {key}")
    if "defaults_applied" in data:
        # Omega4 §3.2: bare-kind defaults stay accepted only with
        # output disclosure — 1..2 unique known field names.
        da = data["defaults_applied"]
        _need(isinstance(da, list) and 1 <= len(da) <= 2
              and all(isinstance(x, str) for x in da)
              and set(da) <= {"period_ms", "max_linear_speed_mps"}
              and len(set(da)) == len(da),
              "defaults_applied must be 1..2 unique items from "
              "[period_ms, max_linear_speed_mps]")
    _need(type(data["schema_version"]) is int
          and data["schema_version"] == SCHEMA_VERSION,
          f"schema_version must be exactly {SCHEMA_VERSION} (bool/float rejected)")

    m = data["machine"]
    _need(isinstance(m, dict), "machine must be a mapping")
    _need(set(m) == {"id", "kind", "execution_target", "simulation_only"},
          f"machine keys must be exactly id/kind/execution_target/simulation_only, got {sorted(m)}")
    _check_id(m["id"], "machine.id")
    _need(m["kind"] in MACHINE_KINDS, f"unknown machine kind: {m['kind']!r}")
    _need(m["execution_target"] == EXECUTION_TARGET,
          f"execution_target must be {EXECUTION_TARGET!r}")
    _need(m["simulation_only"] is True, "simulation_only must be true (MVP: simulation only)")

    actuators = data["actuators"]
    _need(isinstance(actuators, list) and 1 <= len(actuators) <= 16,
          "actuators must be a list of 1..16 entries")
    seen_act: set[str] = set()
    for i, a in enumerate(actuators):
        _need(isinstance(a, dict) and set(a) == {"id", "type"},
              f"actuators[{i}] keys must be exactly id/type")
        _check_id(a["id"], f"actuators[{i}].id")
        _need(a["id"] not in seen_act, f"duplicate actuator id: {a['id']!r}")
        seen_act.add(a["id"])
        _need(a["type"] in ACTUATOR_TYPES, f"unknown actuator type: {a['type']!r}")

    sensors = data["sensors"]
    _need(isinstance(sensors, list) and 1 <= len(sensors) <= 32,
          "sensors must be a list of 1..32 entries")
    seen_sen: set[str] = set()
    for i, s in enumerate(sensors):
        _need(isinstance(s, dict) and set(s) == {"id", "type", "freshness_limit_ms"},
              f"sensors[{i}] keys must be exactly id/type/freshness_limit_ms")
        _check_id(s["id"], f"sensors[{i}].id")
        _need(s["id"] not in seen_sen, f"duplicate sensor id: {s['id']!r}")
        seen_sen.add(s["id"])
        _need(s["type"] in SENSOR_TYPES, f"unknown sensor type: {s['type']!r}")
        _need(type(s["freshness_limit_ms"]) is int
              and 1 <= s["freshness_limit_ms"] <= 60000,
              f"sensors[{i}].freshness_limit_ms must be int 1..60000 (bool rejected)")

    c = data["control"]
    _need(isinstance(c, dict)
          and set(c) == {"period_ms", "max_linear_speed_mps",
                         "max_angular_speed_radps", "guarded_state_transitions"},
          f"control keys invalid: {sorted(c) if isinstance(c, dict) else c!r}")
    _need(type(c["period_ms"]) is int and 1 <= c["period_ms"] <= 1000,
          "control.period_ms must be int 1..1000 (bool rejected)")
    for key, hi in (("max_linear_speed_mps", 10.0), ("max_angular_speed_radps", 20.0)):
        v = c[key]
        _need(type(v) in (int, float) and 0.0 < float(v) <= hi,
              f"control.{key} must be a number in (0, {hi}] (bool rejected)")
    _need(c["guarded_state_transitions"] is True,
          "control.guarded_state_transitions must be true")

    contracts = data["safety_contracts"]
    _need(isinstance(contracts, list) and 1 <= len(contracts) <= 64,
          "safety_contracts must be a list of 1..64 entries")
    seen_ct: set[str] = set()
    for i, ct in enumerate(contracts):
        _need(isinstance(ct, dict) and set(ct) == {"name", "if", "then"},
              f"safety_contracts[{i}] keys must be exactly name/if/then")
        _check_id(ct["name"], f"safety_contracts[{i}].name")
        _need(ct["name"] not in seen_ct, f"duplicate contract name: {ct['name']!r}")
        seen_ct.add(ct["name"])
        _need(ct["if"] in IF_IDS, f"unknown contract if-id: {ct['if']!r}")
        _need(ct["then"] in THEN_IDS, f"unknown contract then-id: {ct['then']!r}")

    v = data["verification"]
    _need(isinstance(v, dict) and set(v) == {"scenarios"},
          "verification keys must be exactly {scenarios}")
    scenarios = v["scenarios"]
    _need(isinstance(scenarios, list) and 1 <= len(scenarios) <= 32,
          "verification.scenarios must be a list of 1..32 entries")
    for s in scenarios:
        _need(s in SCENARIO_IDS, f"unknown scenario id: {s!r}")
    _need(len(set(scenarios)) == len(scenarios), "verification.scenarios has duplicates")

    is_cell = m["kind"] == "industrial_cell"
    _need(("cell" in data) == is_cell,
          "top-level 'cell' block is required for industrial_cell "
          "and forbidden otherwise")
    if is_cell:
        act_types = {a["id"]: a["type"] for a in data["actuators"]}
        sen_types = {s["id"]: s["type"] for s in data["sensors"]}
        _validate_cell(data["cell"], act_types, sen_types)

    # Normalized deep copy (JSON round-trip keeps only plain data).
    norm: dict[str, Any] = json.loads(json.dumps(data))
    norm["verification"]["scenarios"] = sorted(norm["verification"]["scenarios"])
    norm["actuators"] = sorted(norm["actuators"], key=lambda a: a["id"])
    norm["sensors"] = sorted(norm["sensors"], key=lambda s: s["id"])
    norm["safety_contracts"] = sorted(norm["safety_contracts"], key=lambda c: c["name"])
    # Numeric canonicalization: the int-or-float limit fields are stored as
    # float, so a JSON round-trip through a float-unaware producer (JS turns
    # 1.0 into 1) cannot change the digest. Strict-int fields (period_ms,
    # freshness_limit_ms, transfer_ticks) reject floats by construction, so
    # they are already canonical.
    norm["control"]["max_linear_speed_mps"] = float(
        norm["control"]["max_linear_speed_mps"])
    norm["control"]["max_angular_speed_radps"] = float(
        norm["control"]["max_angular_speed_radps"])
    if is_cell:
        norm["cell"]["station_x_m"] = float(norm["cell"]["station_x_m"])
    return norm


def _validate_cell(cell: Any, act_types: dict[str, str],
                   sen_types: dict[str, str]) -> None:
    """Validate the industrial_cell coordination block."""
    _need(isinstance(cell, dict)
          and set(cell) == {"station_x_m", "transfer_ticks",
                            "presence_sensor", "amr_actuator",
                            "belt_actuator"},
          f"cell keys invalid: {sorted(cell) if isinstance(cell, dict) else cell!r}")
    sx = cell["station_x_m"]
    _need(type(sx) in (int, float) and 0.0 < float(sx) <= 12.0,
          "cell.station_x_m must be a number in (0, 12] (bool rejected)")
    tt = cell["transfer_ticks"]
    _need(type(tt) is int and 1 <= tt <= 600,
          "cell.transfer_ticks must be int 1..600 (bool rejected)")
    _need(sen_types.get(cell["presence_sensor"]) == "presence_bool",
          "cell.presence_sensor must reference a presence_bool sensor")
    _need(act_types.get(cell["amr_actuator"]) == "velocity_command",
          "cell.amr_actuator must reference a velocity_command actuator")
    _need(act_types.get(cell["belt_actuator"]) == "belt_speed_command",
          "cell.belt_actuator must reference a belt_speed_command actuator")


def guard_limits(ir: dict[str, Any]) -> dict[str, Any]:
    """Extract the numeric guard limits codegen and policy share."""
    c = ir["control"]
    freshness = min(s["freshness_limit_ms"] for s in ir["sensors"])
    return {
        "period_ms": c["period_ms"],
        "max_linear_speed_mps": float(c["max_linear_speed_mps"]),
        "max_angular_speed_radps": float(c["max_angular_speed_radps"]),
        "freshness_limit_ms": freshness,
    }


def canonical_json(data: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8 safe."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
