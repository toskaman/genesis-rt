# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""W4: guided first-machine builder (example templates + validator).

Kills the 45-line-JSON entry funnel without touching the planner:
copies a guaranteed-valid bundled example, sets the machine id and
scalar control knobs, validates with the real validator BEFORE
writing (fail-closed). `robotic_arm_virtual` is deliberately NOT
offered: its verdicts would run on differential-drive physics until
arm physics lands (see limitations-and-safety.md).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ir import IRValidationError, validate_ir

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TEMPLATES = {
    "industrial_cell": "examples/cell-demo/cell-ir.json",
    "differential_drive_robot": "examples/amr-demo/machine-ir.json",
    "conveyor": "examples/conveyor-demo/machine-ir.json",
}
ALIASES = {
    "cell": "industrial_cell",
    "amr": "differential_drive_robot",
    "conveyor": "conveyor",
}
OFFERED_KINDS = tuple(sorted(TEMPLATES))
_ARM = "robotic_arm_virtual"


class NewMachineError(ValueError):
    """The requested machine cannot be built as asked."""


def resolve_kind(name: str) -> str:
    key = (name or "").strip()
    if key == _ARM:
        raise NewMachineError(
            f"{_ARM} is not offered: verdicts would run on "
            "differential-drive physics until arm physics lands.")
    full = ALIASES.get(key, key)
    if full not in TEMPLATES:
        raise NewMachineError(
            f"unknown kind {name!r} (choose: {', '.join(OFFERED_KINDS)})")
    return full


def _coerce(current: Any, raw: str, key: str) -> Any:
    if isinstance(current, bool):
        low = raw.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
        raise NewMachineError(f"knob {key!r}: {raw!r} is not a boolean")
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            return int(raw)
        except ValueError:
            raise NewMachineError(
                f"knob {key!r}: {raw!r} is not an integer") from None
    if isinstance(current, float):
        try:
            return float(raw)
        except ValueError:
            raise NewMachineError(
                f"knob {key!r}: {raw!r} is not a number") from None
    if isinstance(current, str):
        return raw
    raise NewMachineError(f"knob {key!r}: only scalar knobs can be set")


def build_machine_ir(kind: str, machine_id: str,
                     overrides: dict[str, str],
                     out_path: str | Path) -> dict[str, Any]:
    """Build, validate, then write a Machine IR. Raises NewMachineError."""
    full = resolve_kind(kind)
    if not (machine_id or "").strip():
        raise NewMachineError("machine id must be non-empty")
    template = json.loads(
        (REPO_ROOT / TEMPLATES[full]).read_text(encoding="utf-8"))
    control = template["control"]
    for key, raw in overrides.items():
        if key not in control:
            raise NewMachineError(
                f"unknown knob {key!r} "
                f"(control has: {', '.join(sorted(control))})")
        control[key] = _coerce(control[key], raw, key)
    template["machine"]["id"] = machine_id.strip()
    try:
        validated = validate_ir(template)
    except IRValidationError as exc:
        raise NewMachineError(f"built IR invalid: {exc}") from None
    out = Path(out_path)
    out.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    return validated
