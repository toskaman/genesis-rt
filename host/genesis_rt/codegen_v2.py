# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Machine-specific C generation from Machine IR v2.

Renders ``genesis_machine_gen.{h,c}``: state/event/command/fault/telemetry
enums plus generated ``switch`` query logic (transitions, command field
bounds, fault responses, actuator bounds, sensor models). Two machines
with different IR produce structurally different C sources.

Determinism: IR array order is preserved, LF only, no timestamps.
Fail-closed: v2 C identifiers that collide after C-ification abort with
``ValueError`` naming both ids; the input is re-validated on entry.
Config header + makefile reuse v1 ``codegen.generate`` unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from string import Template
from typing import Any

from . import __version__ as GENERATOR_VERSION
from . import codegen as codegen_v1
from .ir import canonical_json
from .ir_v2 import validate_v2

TEMPLATE_VERSION = "2.1"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

MACHINE_FILES = (
    ("genesis_machine_gen.h.tmpl", "genesis_machine_gen.h"),
    ("genesis_machine_gen.c.tmpl", "genesis_machine_gen.c"),
)


def c_ident(v2id: str, infix: str) -> str:
    """Map a v2 id to a collision-resistant C identifier fragment."""
    return f"GENESIS_M_{infix}_{v2id.upper().replace('-', '_')}"


def _c_syms(ids: list[str], infix: str, kind: str) -> list[str]:
    seen: dict[str, str] = {}
    out = []
    for i in ids:
        sym = c_ident(i, infix)
        if sym in seen:
            raise ValueError(
                f"codegen-v2: {kind} C-identifier collision: "
                f"'{seen[sym]}' vs '{i}' (both -> {sym})"
            )
        seen[sym] = i
        out.append(sym)
    return out


def _ordered_unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _num(value: Any) -> str:
    return repr(float(value))


def _wire_map(states: list[dict[str, Any]]) -> dict[str, int]:
    """Map v2 state ids to wire-protocol state numbers (genesis_ipc.h).

    initial -> 0 (INIT), safe -> 3 (SAFE_STOP), other states in IR order
    -> 1 (NOMINAL), 2 (DEGRADED). Only two middle slots exist on the
    wire, so more than two middle states fail closed here with a loud
    error instead of an ambiguous runtime mapping. An initial+safe
    state maps to 0 (boot identity wins).
    """
    middle = [s["id"] for s in states
              if not s["initial"] and not s["safe"]]
    if len(middle) > 2:
        raise ValueError(
            "codegen-v2: states "
            f"{', '.join(repr(m) for m in middle)} cannot share wire "
            "states 1..2 (initial->0, safe->3); the v2 runtime supports "
            "at most two non-initial non-safe states"
        )
    wire: dict[str, int] = {}
    for s in states:
        if s["safe"]:
            wire[s["id"]] = 3
    for s in states:
        if s["initial"]:
            wire[s["id"]] = 0
    for i, mid in enumerate(middle):
        wire[mid] = 1 + i
    return wire


def _render(name: str, mapping: dict[str, str]) -> str:
    text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    return Template(text).substitute(mapping)


def _build_mapping(v2: dict[str, Any]) -> dict[str, str]:
    states = [s["id"] for s in v2["states"]]
    state_syms = _c_syms(states, "STATE", "state")
    used_events = _ordered_unique(t["event"] for t in v2["transitions"])
    event_syms = _c_syms(used_events, "EVENT", "event")
    event_of = dict(zip(used_events, event_syms))
    state_of = dict(zip(states, state_syms))

    commands = [c["id"] for c in v2["commands"]]
    cmd_syms = _c_syms(commands, "CMD", "command")

    faults = _ordered_unique(f["fault"] for f in v2["fault_responses"])
    fault_syms = _c_syms(faults, "FAULT", "fault")
    fault_of = dict(zip(faults, fault_syms))
    actions = _ordered_unique(
        [f["action"] for f in v2["fault_responses"]]
    )
    action_syms = _c_syms(actions, "ACTION", "action")
    action_of = dict(zip(actions, action_syms))

    actuators = [a["id"] for a in v2["actuators"]]
    act_syms = _c_syms(actuators, "ACT", "actuator")
    sensors = [s["id"] for s in v2["sensors"]]
    sens_syms = _c_syms(sensors, "SENS", "sensor")
    telemetries = [t["id"] for t in v2["telemetry"]]
    tm_syms = _c_syms(telemetries, "TM", "telemetry")

    def enum_block(syms: list[str], count_sym: str) -> str:
        lines = [f"    {s} = {i}," for i, s in enumerate(syms)]
        lines.append(f"    {count_sym} = {len(syms)}")
        return "\n".join(lines)

    # transition cases grouped by source state, IR order preserved
    by_src: dict[str, list[dict[str, Any]]] = {s: [] for s in states}
    for t in v2["transitions"]:
        by_src[t["from"]].append(t)
    trans_cases = []
    for s, sym in zip(states, state_syms):
        outs = by_src[s]
        if not outs:
            trans_cases.append(f"    case {sym}:\n        return 0;")
            continue
        conds = " ||\n               ".join(
            f"(to_state == {state_of[t['to']]} && event == {event_of[t['event']]})"
            for t in outs
        )
        trans_cases.append(f"    case {sym}:\n        return {conds};")

    # command field-bounds switch
    cmd_cases = []
    cmd_counts = []
    for c, sym in zip(v2["commands"], cmd_syms):
        fields = c["fields"]
        cmd_counts.append(f"    case {sym}:\n        return {len(fields)};")
        field_cases = "\n".join(
            f"        case {j}: *min_out = {_num(f['min'])}; "
            f"*max_out = {_num(f['max'])}; return 0;"
            for j, f in enumerate(fields)
        )
        cmd_cases.append(
            f"    case {sym}:\n"
            f"        switch (field) {{\n{field_cases}\n"
            f"        default: return -1;\n        }}"
        )

    # fault responses: first entry in IR order wins per fault (documented)
    first: dict[str, dict[str, Any]] = {}
    for f in v2["fault_responses"]:
        first.setdefault(f["fault"], f)
    fault_cases = "\n".join(
        f"    case {fault_of[name]}: "
        f"*state_out = {state_of[e['enter_state']]}; "
        f"*action_out = {action_of[e['action']]}; return 0;"
        for name, e in first.items()
    )

    # actuator bounds
    act_cases = "\n".join(
        f"    case {sym}: *min_out = {_num(a['bounds']['min'])}; "
        f"*max_out = {_num(a['bounds']['max'])}; return 0;"
        for a, sym in zip(v2["actuators"], act_syms)
    )

    # sensor freshness (+ range when declared)
    sens_fresh = "\n".join(
        f"    case {sym}: *ms_out = {_num(s['freshness_limit_ms'])}; return 0;"
        for s, sym in zip(v2["sensors"], sens_syms)
    )
    sens_range = "\n".join(
        f"    case {sym}: *min_out = {_num(s['range']['min'])}; "
        f"*max_out = {_num(s['range']['max'])}; return 0;"
        if "range" in s else
        f"    case {sym}: return -1;"
        for s, sym in zip(v2["sensors"], sens_syms)
    )

    # wire-protocol state map (v2 ordinal -> 0..3), IR order preserved
    wire = _wire_map(v2["states"])
    wire_cases = "\n".join(
        f"    case {sym}: return {wire[sid]};"
        for sid, sym in zip(states, state_syms)
    )

    # declared-fault/action macros: let the shared guard source probe
    # for a fault id or action at compile time (#ifdef) and fall back
    # when the IR omits it
    has_fault_macros = "\n".join(
        f"#define GENESIS_M_HAS_FAULT_{name.upper().replace('-', '_')} 1"
        for name in faults
    )
    has_action_macros = "\n".join(
        f"#define GENESIS_M_HAS_ACTION_{name.upper().replace('-', '_')} 1"
        for name in actions
    )

    # telemetry tables (ids are v2 _ID_RE: safe unescaped in C strings)
    tm_rates = "\n".join(
        f"    case {sym}: *rate_out = {_num(t['rate_hz'])}; return 0;"
        for t, sym in zip(v2["telemetry"], tm_syms)
    )
    tm_names = "\n".join(
        f'    case {sym}: return "{t["id"]}";'
        for t, sym in zip(v2["telemetry"], tm_syms)
    )
    tm_sources = "\n".join(
        f'    case {sym}: return "{t["source"]}";'
        for t, sym in zip(v2["telemetry"], tm_syms)
    )

    return {
        "machine_id": v2["machine"]["id"],
        "machine_kind": v2["machine"]["kind"],
        "generator_version": GENERATOR_VERSION,
        "template_version": TEMPLATE_VERSION,
        "ir_sha256": hashlib.sha256(canonical_json(v2).encode("utf-8")).hexdigest(),
        "enum_states": enum_block(state_syms, "GENESIS_M_STATE_COUNT"),
        "enum_events": enum_block(event_syms, "GENESIS_M_EVENT_COUNT"),
        "enum_commands": enum_block(cmd_syms, "GENESIS_M_CMD_COUNT"),
        "enum_faults": enum_block(fault_syms, "GENESIS_M_FAULT_COUNT"),
        "enum_actions": enum_block(action_syms, "GENESIS_M_ACTION_COUNT"),
        "enum_actuators": enum_block(act_syms, "GENESIS_M_ACT_COUNT"),
        "enum_sensors": enum_block(sens_syms, "GENESIS_M_SENS_COUNT"),
        "enum_telemetry": enum_block(tm_syms, "GENESIS_M_TM_COUNT"),
        "transition_cases": "\n".join(trans_cases),
        "wire_cases": wire_cases,
        "has_fault_macros": has_fault_macros,
        "has_action_macros": has_action_macros,
        "cmd_field_count_cases": "\n".join(cmd_counts),
        "cmd_bounds_cases": "\n".join(cmd_cases),
        "fault_cases": fault_cases,
        "actuator_cases": act_cases,
        "sensor_freshness_cases": sens_fresh,
        "sensor_range_cases": sens_range,
        "tm_rate_cases": tm_rates,
        "tm_name_cases": tm_names,
        "tm_source_cases": tm_sources,
    }


def generate_v2(v2: dict[str, Any], out_dir: str | Path,
                genesis_src: str = "../../target/qnx8") -> dict[str, Any]:
    """Render the per-machine v2 build directory. Returns the manifest."""
    v2 = validate_v2(v2)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mapping = _build_mapping(v2)
    files: dict[str, str] = {}
    templates: dict[str, str] = {}
    for tmpl_name, out_name in MACHINE_FILES:
        rendered = _render(tmpl_name, mapping).replace("\r\n", "\n")
        if not rendered.endswith("\n"):
            rendered += "\n"
        (out / out_name).write_text(rendered, encoding="utf-8", newline="\n")
        files[out_name] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        templates[tmpl_name] = hashlib.sha256(
            (TEMPLATES_DIR / tmpl_name).read_bytes()).hexdigest()
    base = codegen_v1.generate(v2, out, genesis_src=genesis_src)
    _link_machine_module(out)
    base["files"].update(files)
    base["files"]["genesis_build_gen.mk"] = hashlib.sha256(
        (out / "genesis_build_gen.mk").read_bytes()).hexdigest()
    base["templates"].update(templates)
    base["machine_template_version"] = TEMPLATE_VERSION
    base["schema_version"] = 2
    return base


_GUARD_LINK_ANCHOR = (
    "$(GENESIS_SRC)/guard/genesis_guard.c"
)


def _link_machine_module(out: Path) -> None:
    """Link genesis_machine_gen.c into the genesis_guard rule.

    The shared v1 makefile template is left untouched (v1 dirs have no
    machine module); v2 dirs patch their own copy. The guard rule also
    gains -DGENESIS_MACHINE_V2 so the shared guard_policy.c compiles
    its generated-table tail; every other rule keeps the fixed v1 tail.
    """
    mk = out / "genesis_build_gen.mk"
    text = mk.read_text(encoding="utf-8")
    anchor = f"-o genesis_guard $(GENESIS_SRC)/common/guard_policy.c {_GUARD_LINK_ANCHOR}"
    if anchor not in text:
        raise ValueError(
            "codegen-v2: guard link anchor not found in generated makefile; "
            "v1 template drifted, update codegen-v2 pin"
        )
    patched = text.replace(
        anchor, "-DGENESIS_MACHINE_V2 " + anchor + " ./genesis_machine_gen.c", 1
    )
    marker = ("# v2: machine module linked into genesis_guard; the guard rule\n"
              "# compiles guard_policy.c with -DGENESIS_MACHINE_V2 so the\n"
              "# generated transition/fault tables drive its decisions.\n")
    mk.write_text(marker + patched, encoding="utf-8", newline="\n")
