# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""§9 Counterexample Explorer: bounded search for invariant violations.

Given an invariant and a bounded script space, the explorer runs
deterministic, seeded simulations through the same guard + virtual
device components as the fault lab (``guard_policy.decide`` plus the
``simulator`` machines) and reports reproducible violation scripts
with minimal reproducers.

Tiers are never collapsed: every finding starts as
``host-discovered``. C-conformance replay re-runs the recorded
command vectors through the compiled ``guard_vector`` harness;
native-QNX replay stays an explicit, separate rung. Simulation
only: this module has no target, network or actuation imports.
"""
from __future__ import annotations

import copy
import math
import random
import time
from typing import Any, Callable

from . import guard_policy as gp
from .codegen import ir_sha256
from .faultlab import KNOWN_FAULTS
from .ir import IRValidationError, guard_limits
from .projects import validate_any
from .simulator import BeltConfig, BeltSim, DiffDriveSim, SimConfig

EXPLORER_VERSION = 1

# Hard input caps (fail-closed; the API clamps to the same values).
MAX_TICKS = 3000
MAX_FAULTS = 8
MAX_COMMANDS = 64
MAX_TRACE_EVENTS = 5000
MAX_SCRIPTS_HARD = 5000
MAX_FINDINGS_HARD = 25
MAX_SECONDS_HARD = 300
MAX_TICKS_TOTAL_HARD = 2_000_000

_DEFAULT_BUDGETS = {"max_scripts": 200, "max_findings": 5,
                    "max_ticks_total": 200_000, "max_seconds": 30}

_RESET_POLICIES = ("auto", "never")

# Fault kinds the single-stream driver implements. "none" is rejected
# in scripts (a no-op fault step is meaningless); "jam" needs a belt.
_SCRIPT_FAULTS = frozenset(k for k in KNOWN_FAULTS if k != "none")


class ExplorerInputError(ValueError):
    """A script, invariant, param or budget failed strict validation."""


class ExplorerUnsupported(ValueError):
    """A supported-shape request the v1 driver cannot execute (cell)."""


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    return _is_num(value) and math.isfinite(float(value))


def invariants() -> list[str]:
    """Names of the registered invariants (stable, sorted)."""
    return sorted(_INVARIANTS)


def explore_strategies() -> list[str]:
    """Names of the available search strategies (stable, sorted)."""
    return sorted(_STRATEGIES)


def _validate_script(script: Any, kind: str) -> dict[str, Any]:
    if not isinstance(script, dict):
        raise ExplorerInputError("script must be an object")
    unknown = set(script) - {"ticks", "seed", "faults", "commands",
                             "resets"}
    if unknown:
        raise ExplorerInputError(f"unknown script key(s): {sorted(unknown)}")
    ticks = script.get("ticks")
    if not _is_int(ticks) or not 1 <= ticks <= MAX_TICKS:
        raise ExplorerInputError(f"'ticks' must be int 1..{MAX_TICKS}")
    seed = script.get("seed")
    if not _is_int(seed):
        raise ExplorerInputError("'seed' must be an int")
    faults = script.get("faults", [])
    if not isinstance(faults, list) or len(faults) > MAX_FAULTS:
        raise ExplorerInputError(f"'faults' must be a list of <={MAX_FAULTS}")
    for i, fault in enumerate(faults):
        where = f"faults[{i}]"
        if not isinstance(fault, dict):
            raise ExplorerInputError(f"{where} must be an object")
        if set(fault) - {"kind", "start_tick", "end_tick"}:
            raise ExplorerInputError(f"{where} has unknown keys")
        if fault.get("kind") not in _SCRIPT_FAULTS:
            raise ExplorerInputError(
                f"{where}.kind must be one of {sorted(_SCRIPT_FAULTS)}")
        start = fault.get("start_tick")
        end = fault.get("end_tick")
        if not _is_int(start) or not _is_int(end):
            raise ExplorerInputError(f"{where} needs int start/end ticks")
        if not 0 <= start < end <= ticks:
            raise ExplorerInputError(
                f"{where} needs 0 <= start < end <= ticks")
        if fault["kind"] == "jam" and kind != "conveyor":
            raise ExplorerInputError(
                f"{where}: 'jam' needs a conveyor machine")
    commands = script.get("commands", [])
    if not isinstance(commands, list) or len(commands) > MAX_COMMANDS:
        raise ExplorerInputError(
            f"'commands' must be a list of <={MAX_COMMANDS}")
    allowed_cmd = {"tick", "linear_mps", "angular_radps",
                   "deadline_offset_ms", "magic", "version", "req_state",
                   "sensor_age_ms", "sim_connected", "estop_engaged",
                   "seq_jump"}
    for i, cmd in enumerate(commands):
        where = f"commands[{i}]"
        if not isinstance(cmd, dict):
            raise ExplorerInputError(f"{where} must be an object")
        if set(cmd) - allowed_cmd:
            raise ExplorerInputError(f"{where} has unknown keys")
        tick = cmd.get("tick")
        if not _is_int(tick) or not 0 <= tick < ticks:
            raise ExplorerInputError(f"{where}.tick out of range")
        for key in ("linear_mps", "angular_radps"):
            if key in cmd and not _finite(cmd[key]):
                raise ExplorerInputError(f"{where}.{key} must be finite")
        for key in ("deadline_offset_ms", "magic", "version", "req_state",
                    "sensor_age_ms", "estop_engaged", "seq_jump"):
            if key in cmd and not _is_int(cmd[key]):
                raise ExplorerInputError(f"{where}.{key} must be an int")
        if "sim_connected" in cmd and not isinstance(
                cmd["sim_connected"], bool):
            raise ExplorerInputError(f"{where}.sim_connected must be bool")
    resets = script.get("resets", "auto")
    if resets not in _RESET_POLICIES:
        raise ExplorerInputError(f"'resets' must be one of {_RESET_POLICIES}")
    return {"ticks": ticks, "seed": seed, "faults": list(faults),
            "commands": [dict(c) for c in commands], "resets": resets}


def _fault_at(faults: list[dict[str, Any]], tick: int) -> str:
    """Fault kind active at a tick; first listed step wins on overlap."""
    for fault in faults:
        if fault["start_tick"] <= tick < fault["end_tick"]:
            return str(fault["kind"])
    return "none"


def _cmds_at(commands: list[dict[str, Any]],
             tick: int) -> list[dict[str, Any]]:
    return [c for c in commands if c["tick"] == tick]


def run_script(ir_doc: Any, script: Any, invariant: str | None = None,
               params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run one explicit script through guard + virtual device.

    Mirrors the fault-lab loop (controller -> guard -> device) tick by
    tick. Returns stats, a bounded trace with the full command per
    tick (conformance-replayable), per-invariant checks and an
    overall status. Never raises for oracle failures; raises
    IRValidationError / ExplorerInputError / ExplorerUnsupported for
    malformed input.
    """
    if invariant is not None and invariant not in _INVARIANTS:
        raise ExplorerInputError(f"unknown invariant: {invariant!r}")
    clean_params = _validate_params(params or {})
    _version, ir = validate_any(ir_doc)
    kind = ir["machine"]["kind"]
    if kind == "industrial_cell":
        raise ExplorerUnsupported(
            "industrial_cell needs the two-stream driver (roadmap); "
            "v1 explores differential-drive and conveyor machines")
    if kind not in ("differential_drive_robot", "conveyor"):
        raise ExplorerInputError(f"unsupported machine kind: {kind!r}")
    steps = _validate_script(script, kind)
    limits = guard_limits(ir)
    period = int(limits["period_ms"])
    if kind == "conveyor":
        sim: Any = BeltSim(BeltConfig(dt=period / 1000.0))
    else:
        sim = DiffDriveSim(SimConfig(dt=period / 1000.0))
    jam_capable = hasattr(sim, "set_jam")
    sim.reset(int(steps["seed"]))
    ctx = gp.GuardContext()
    seq = 0
    sensor_last_update = 0
    reset_done = False
    fault_end_ms = max(
        (f["end_tick"] * period for f in steps["faults"]), default=0)

    trace: list[dict[str, Any]] = []
    vectors: list[dict[str, Any]] = []
    allows = denies = 0
    deny_reasons: dict[str, int] = {}
    stop_latched_at: int | None = None
    truncated = False

    def emit(event: dict[str, Any]) -> None:
        nonlocal truncated
        if len(trace) >= MAX_TRACE_EVENTS:
            truncated = True
            return
        trace.append(event)

    for tick in range(steps["ticks"]):
        t = tick * period
        fault = _fault_at(steps["faults"], tick)
        if jam_capable and any(f["kind"] == "jam" for f in steps["faults"]):
            sim.set_jam(fault == "jam")
        if fault in ("crash", "dropped"):
            sim.stopped()
            emit({"t": t + period, "tick": tick, "kind": "planner_gap",
                  "fault": fault, **sim.snapshot()})
            continue
        seq += 1
        v, w = 0.5, 0.0
        magic, version = gp.PROTOCOL_MAGIC, gp.PROTOCOL_VERSION
        deadline = t + period + 20
        if fault == "over_limit":
            v = float(limits["max_linear_speed_mps"]) * 3.0
        elif fault == "delayed":
            deadline = t - 50
        elif fault == "corrupted":
            magic = 0xDEADBEEF
        if fault == "stale":
            sensor_age = t - sensor_last_update
        else:
            sensor_last_update = t
            sensor_age = 0
        cmd: dict[str, Any] = {
            "magic": magic, "version": version, "size_ok": True,
            "seq": seq, "now_ms": t, "deadline_ms": deadline,
            "linear_mps": v, "angular_radps": w,
            "req_state": gp.ST_NOMINAL,
            "sensor_age_ms": sensor_age,
            "sim_connected": fault != "disconnect",
            "estop_engaged": 1 if fault == "estop" else 0,
        }
        for override in _cmds_at(steps["commands"], tick):
            if "linear_mps" in override:
                cmd["linear_mps"] = float(override["linear_mps"])
            if "angular_radps" in override:
                cmd["angular_radps"] = float(override["angular_radps"])
            if "deadline_offset_ms" in override:
                cmd["deadline_ms"] = int(cmd["deadline_ms"])
                cmd["deadline_ms"] += int(override["deadline_offset_ms"])
            for key in ("magic", "version", "req_state", "sensor_age_ms",
                        "estop_engaged", "seq_jump"):
                if key in override:
                    cmd[key if key != "seq_jump" else "seq"] = int(
                        override[key])
            if "sim_connected" in override:
                cmd["sim_connected"] = bool(override["sim_connected"])
        if cmd.get("seq", seq) != seq:
            seq = int(cmd["seq"])
        if (steps["resets"] == "auto" and not reset_done
                and steps["faults"] and t >= fault_end_ms
                and ctx.state == gp.ST_SAFE_STOP):
            ctx.reset_armed = True
            reset_done = True
            emit({"t": t, "tick": tick, "kind": "supervisor_reset_armed"})
        state_in = ctx.state
        reset_armed = ctx.reset_armed
        last_seq_in = ctx.last_seq
        verdict = gp.decide(cmd, ctx, limits)
        if verdict["decision"] == gp.ALLOW:
            allows += 1
            ctx.state = verdict["state_out"]
            sim.apply(float(cmd["linear_mps"]), float(cmd["angular_radps"]))
        else:
            denies += 1
            reason = verdict["reason"]
            deny_reasons[reason] = deny_reasons.get(reason, 0) + 1
            ctx.state = verdict["state_out"]
            sim.stopped()
            if verdict["state_out"] == gp.ST_SAFE_STOP \
                    and stop_latched_at is None:
                stop_latched_at = t
        vectors.append({"tick": tick, "t": t, "cmd": dict(cmd),
                        "state_in": state_in,
                        "reset_armed": reset_armed,
                        "last_seq_in": last_seq_in,
                        "decision": verdict["decision"],
                        "reason": verdict["reason"],
                        "state_out": verdict["state_out"]})
        emit({"t": t, "tick": tick, "kind": "tick", "fault": fault,
              "decision": verdict["decision"], "reason": verdict["reason"],
              "state": ctx.state, "cmd": dict(cmd), **sim.snapshot()})
    stats = {"allows": allows, "denies": denies,
             "deny_reasons": deny_reasons, "final_state": ctx.state,
             "stop_latched_at": stop_latched_at,
             "ticks": len([e for e in trace if e["kind"] == "tick"]),
             **sim.final_stats()}
    checks = {name: fn(stats, trace, limits, clean_params).as_dict()
              for name, fn in _INVARIANTS.items()}
    if invariant is not None:
        status = "pass" if checks[invariant]["passed"] else "fail"
    else:
        status = "pass" if all(c["passed"] for c in checks.values()) \
            else "fail"
    return {"machine": {"id": ir["machine"]["id"],
                        "kind": ir["machine"]["kind"]},
            "ir_sha256": ir_sha256(ir), "status": status, "checks": checks,
            "stats": stats, "trace": trace, "vectors": vectors,
            "trace_truncated": truncated, "ticks": steps["ticks"],
            "seed": steps["seed"]}


def _validate_params(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ExplorerInputError("'params' must be an object")
    unknown = set(params) - {"max_allow_linear", "max_allow_angular"}
    if unknown:
        raise ExplorerInputError(f"unknown param(s): {sorted(unknown)}")
    clean: dict[str, Any] = {}
    for key in ("max_allow_linear", "max_allow_angular"):
        if key in params:
            value = params[key]
            if not _finite(value) or float(value) <= 0:
                raise ExplorerInputError(
                    f"param '{key}' must be a positive finite number")
            clean[key] = float(value)
    return clean


class _Check:
    def __init__(self, name: str, passed: bool, detail: str) -> None:
        self.name = name
        self.passed = passed
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed,
                "detail": self.detail}


def _inv_no_over_limit_allow(stats: dict[str, Any],
                             trace: list[dict[str, Any]],
                             limits: dict[str, Any],
                             params: dict[str, Any]) -> _Check:
    """No ALLOW authorizes motion above the (possibly strict) bound."""
    max_lin = float(params.get("max_allow_linear",
                               limits["max_linear_speed_mps"]))
    max_ang = float(params.get("max_allow_angular",
                               limits["max_angular_speed_radps"]))
    for event in trace:
        if event.get("kind") != "tick":
            continue
        if event.get("decision") != gp.ALLOW:
            continue
        cmd = event.get("cmd", {})
        lin = abs(float(cmd.get("linear_mps", 0.0)))
        ang = abs(float(cmd.get("angular_radps", 0.0)))
        if lin > max_lin:
            return _Check("no_over_limit_allow", False,
                          f"tick {event['tick']}: ALLOW linear={lin} "
                          f"above max_allow_linear={max_lin}")
        if ang > max_ang:
            return _Check("no_over_limit_allow", False,
                          f"tick {event['tick']}: ALLOW angular={ang} "
                          f"above max_allow_angular={max_ang}")
    return _Check("no_over_limit_allow", True,
                  f"all ALLOWs within linear<={max_lin} angular<={max_ang}")


def _pose_of(event: dict[str, Any]) -> tuple[Any, ...]:
    if "position" in event:  # belt snapshot
        return (event.get("position"),)
    return (event.get("x"), event.get("y"), event.get("theta"))


def _inv_no_motion_without_allow(stats: dict[str, Any],
                                 trace: list[dict[str, Any]],
                                 limits: dict[str, Any],
                                 params: dict[str, Any]) -> _Check:
    """Denied/gap ticks freeze the virtual device exactly."""
    prev: tuple[Any, ...] | None = None
    for event in trace:
        kind = event.get("kind")
        if kind == "tick" and event.get("decision") == gp.ALLOW:
            prev = _pose_of(event)
            continue
        if kind not in ("tick", "planner_gap"):
            continue
        pose = _pose_of(event)
        if prev is not None and pose != prev:
            return _Check("no_motion_without_allow", False,
                          f"tick {event.get('tick')}: device moved "
                          f"without ALLOW ({prev} -> {pose})")
        prev = pose
    return _Check("no_motion_without_allow", True,
                  "no motion outside ALLOW ticks")


_KNOWN_REASONS = frozenset({
    gp.R_OK, gp.R_BAD_MAGIC, gp.R_BAD_VERSION, gp.R_BAD_SIZE,
    gp.R_STALE_SEQ, gp.R_OVERDUE_DEADLINE, gp.R_STALE_SENSOR,
    gp.R_SIM_DISCONNECTED, gp.R_SPEED_OVER_LIMIT,
    gp.R_ANGULAR_OVER_LIMIT, gp.R_BAD_TRANSITION, gp.R_MALFORMED,
    gp.R_ESTOP})


def _inv_deny_reasons_known(stats: dict[str, Any],
                            trace: list[dict[str, Any]],
                            limits: dict[str, Any],
                            params: dict[str, Any]) -> _Check:
    """Every verdict carries a reason from the wire vocabulary."""
    for event in trace:
        if event.get("kind") != "tick":
            continue
        reason = event.get("reason")
        if reason not in _KNOWN_REASONS:
            return _Check("deny_reasons_known", False,
                          f"tick {event['tick']}: unknown reason {reason!r}")
    return _Check("deny_reasons_known", True,
                  "all reasons in the wire vocabulary")


def _inv_estop_latches_stop(stats: dict[str, Any],
                            trace: list[dict[str, Any]],
                            limits: dict[str, Any],
                            params: dict[str, Any]) -> _Check:
    """E-stop stimulus is denied ESTOP and latches SAFE_STOP."""
    estop_ticks = [e for e in trace if e.get("kind") == "tick"
                   and (e.get("fault") == "estop"
                        or e.get("cmd", {}).get("estop_engaged") == 1)]
    if not estop_ticks:
        return _Check("estop_latches_stop", True, "no estop stimulus")
    bad = [e for e in estop_ticks
           if e["decision"] != gp.DENY or e["reason"] != gp.R_ESTOP]
    if bad:
        return _Check("estop_latches_stop", False,
                      f"tick {bad[0]['tick']}: estop stimulus not "
                      f"denied ESTOP ({bad[0]['decision']}/"
                      f"{bad[0]['reason']})")
    latched = stats.get("stop_latched_at")
    if latched is None:
        return _Check("estop_latches_stop", False,
                      "estop denied but SAFE_STOP never latched")
    return _Check("estop_latches_stop", True,
                  f"{len(estop_ticks)} estop ticks denied, "
                  f"latched at t={latched}")


def _inv_safe_stop_needs_reset(stats: dict[str, Any],
                               trace: list[dict[str, Any]],
                               limits: dict[str, Any],
                               params: dict[str, Any]) -> _Check:
    """SAFE_STOP is left only across a supervisor reset event."""
    latched_at: int | None = None
    for event in trace:
        kind = event.get("kind")
        if kind == "supervisor_reset_armed":
            latched_at = None
            continue
        if kind != "tick":
            continue
        if event.get("state") == gp.ST_SAFE_STOP and latched_at is None:
            latched_at = event.get("tick")
        elif (latched_at is not None
                and event.get("state") != gp.ST_SAFE_STOP):
            return _Check("safe_stop_needs_reset", False,
                          f"SAFE_STOP left at tick {event.get('tick')} "
                          f"without a supervisor reset "
                          f"(latched at tick {latched_at})")
    return _Check("safe_stop_needs_reset", True,
                  "every SAFE_STOP exit crossed a supervisor reset")


def _inv_no_allow_past_deadline(stats: dict[str, Any],
                                trace: list[dict[str, Any]],
                                limits: dict[str, Any],
                                params: dict[str, Any]) -> _Check:
    """No ALLOW serves a command past its deadline (strict >)."""
    for event in trace:
        if event.get("kind") != "tick":
            continue
        if event.get("decision") != gp.ALLOW:
            continue
        cmd = event.get("cmd", {})
        if int(cmd.get("now_ms", 0)) > int(cmd.get("deadline_ms", 0)):
            return _Check("no_allow_past_deadline", False,
                          f"tick {event['tick']}: ALLOW with now_ms="
                          f"{cmd['now_ms']} past deadline_ms="
                          f"{cmd['deadline_ms']}")
    return _Check("no_allow_past_deadline", True,
                  "no ALLOW past its deadline")


_INVARIANTS: dict[str, Callable[..., _Check]] = {
    "no_over_limit_allow": _inv_no_over_limit_allow,
    "no_motion_without_allow": _inv_no_motion_without_allow,
    "deny_reasons_known": _inv_deny_reasons_known,
    "estop_latches_stop": _inv_estop_latches_stop,
    "safe_stop_needs_reset": _inv_safe_stop_needs_reset,
    "no_allow_past_deadline": _inv_no_allow_past_deadline,
}


def _validate_budgets(budgets: Any) -> dict[str, Any]:
    if budgets is None:
        budgets = {}
    if not isinstance(budgets, dict):
        raise ExplorerInputError("'budgets' must be an object")
    unknown = set(budgets) - set(_DEFAULT_BUDGETS)
    if unknown:
        raise ExplorerInputError(f"unknown budget(s): {sorted(unknown)}")
    clean = dict(_DEFAULT_BUDGETS)
    for key, hard in (("max_scripts", MAX_SCRIPTS_HARD),
                      ("max_findings", MAX_FINDINGS_HARD),
                      ("max_ticks_total", MAX_TICKS_TOTAL_HARD),
                      ("max_seconds", MAX_SECONDS_HARD)):
        if key in budgets:
            value = budgets[key]
            if not _is_int(value) or not 1 <= value <= hard:
                raise ExplorerInputError(
                    f"budget '{key}' must be int 1..{hard}")
            clean[key] = value
    return clean


def _base_script(seed: int, ticks: int = 120) -> dict[str, Any]:
    return {"ticks": ticks, "seed": seed, "faults": [], "commands": [],
            "resets": "auto"}


def _strat_boundary(ir: dict[str, Any], seed: int,
                    kind: str) -> Any:
    """Single commands at limit/deadline/freshness/seq boundaries."""
    limits = guard_limits(ir)
    max_lin = float(limits["max_linear_speed_mps"])
    max_ang = float(limits["max_angular_speed_radps"])
    fresh = int(limits["freshness_limit_ms"])
    tick = 50
    cases: list[dict[str, Any]] = []
    for factor in (0.99, 1.0, 1.01):
        cases.append({"linear_mps": round(max_lin * factor, 6)})
        cases.append({"angular_radps": round(max_ang * factor, 6)})
    cases.append({"linear_mps": -round(max_lin * 1.01, 6)})
    cases.append({"deadline_offset_ms": -1000})
    cases.append({"deadline_offset_ms": -1})
    cases.append({"sensor_age_ms": fresh - 1})
    cases.append({"sensor_age_ms": fresh})
    cases.append({"sensor_age_ms": fresh + 1})
    cases.append({"seq_jump": (1 << 32) - 1})
    for i, override in enumerate(cases):
        script = _base_script(seed + i)
        script["commands"] = [dict({"tick": tick}, **override)]
        yield script


def _strat_pairs(ir: dict[str, Any], seed: int, kind: str) -> Any:
    """Ordered pairs of distinct fault kinds in adjacent windows."""
    kinds = ["over_limit", "stale", "delayed", "dropped", "corrupted",
             "disconnect", "estop", "crash"]
    if kind == "conveyor":
        kinds.append("jam")
    i = 0
    for first in kinds:
        for second in kinds:
            if first == second:
                continue
            script = _base_script(seed + i)
            script["faults"] = [
                {"kind": first, "start_tick": 40, "end_tick": 43},
                {"kind": second, "start_tick": 43, "end_tick": 46},
            ]
            i += 1
            yield script


def _strat_windows(ir: dict[str, Any], seed: int, kind: str) -> Any:
    """One fault slid over start x length grid (schedule variation)."""
    kinds = ["over_limit", "estop", "stale"]
    i = 0
    for fault_kind in kinds:
        for start in (10, 60, 100):
            for length in (1, 3, 10):
                script = _base_script(seed + i, ticks=140)
                script["faults"] = [{"kind": fault_kind,
                                     "start_tick": start,
                                     "end_tick": start + length}]
                i += 1
                yield script


def _strat_mutate(ir: dict[str, Any], seed: int, kind: str,
                  count: int) -> Any:
    """Seeded random perturbations near the guard boundary."""
    limits = guard_limits(ir)
    max_lin = float(limits["max_linear_speed_mps"])
    max_ang = float(limits["max_angular_speed_radps"])
    fresh = int(limits["freshness_limit_ms"])
    fault_kinds = ["over_limit", "stale", "delayed", "dropped",
                   "corrupted", "disconnect", "estop", "crash"]
    if kind == "conveyor":
        fault_kinds.append("jam")
    rng = random.Random(seed)
    for i in range(count):
        script = _base_script(seed + i)
        if rng.random() < 0.6:
            start = rng.randrange(0, 100)
            script["faults"] = [{
                "kind": rng.choice(fault_kinds), "start_tick": start,
                "end_tick": start + rng.randrange(1, 8)}]
        commands = []
        for _ in range(rng.randrange(0, 3)):
            cmd: dict[str, Any] = {"tick": rng.randrange(0, 120)}
            roll = rng.random()
            if roll < 0.4:
                cmd["linear_mps"] = round(
                    rng.uniform(0.5 * max_lin, 1.5 * max_lin), 4)
            elif roll < 0.6:
                cmd["angular_radps"] = round(
                    rng.uniform(0.5 * max_ang, 1.5 * max_ang), 4)
            elif roll < 0.75:
                cmd["deadline_offset_ms"] = rng.randrange(-60, 5)
            elif roll < 0.9:
                cmd["sensor_age_ms"] = fresh + rng.randrange(-2, 5)
            else:
                cmd["seq_jump"] = rng.choice(
                    [0, 1, (1 << 32) - 2, (1 << 32) - 1])
            commands.append(cmd)
        script["commands"] = commands
        yield script


_STRATEGIES: dict[str, str] = {
    "boundary": "single commands at limit/deadline/freshness/seq edges",
    "pairs": "ordered pairs of distinct fault kinds",
    "windows": "one fault over a start x length grid",
    "mutate": "seeded random perturbations near the boundary",
}


def _strategy_scripts(name: str, ir: dict[str, Any], seed: int,
                      kind: str, mutate_count: int) -> Any:
    if name == "boundary":
        yield from _strat_boundary(ir, seed, kind)
    elif name == "pairs":
        yield from _strat_pairs(ir, seed, kind)
    elif name == "windows":
        yield from _strat_windows(ir, seed, kind)
    elif name == "mutate":
        yield from _strat_mutate(ir, seed, kind, mutate_count)
    else:
        raise ExplorerInputError(
            f"unknown strategy: {name!r} (pick from "
            f"{sorted(_STRATEGIES)})")


def _excerpt(trace: list[dict[str, Any]], focus_tick: int | None,
             limit: int = 25) -> list[dict[str, Any]]:
    """Bounded trace window around the violation tick + latch events."""
    if focus_tick is None:
        return trace[:limit]
    window = [e for e in trace
              if abs(e.get("tick", -10**9) - focus_tick) <= 2]
    extra = [e for e in trace
             if e.get("kind") == "supervisor_reset_armed"]
    out = window + [e for e in extra if e not in window]
    return out[:limit]


def _violation_tick(check: dict[str, Any]) -> int | None:
    detail = check.get("detail", "")
    if detail.startswith("tick "):
        try:
            return int(detail.split(":", 1)[0].split()[1])
        except (ValueError, IndexError):
            return None
    return None


def explore(ir_doc: Any, invariant: str = "no_over_limit_allow",
            params: dict[str, Any] | None = None,
            strategies: list[str] | None = None,
            budgets: dict[str, Any] | None = None,
            seed: int = 0) -> dict[str, Any]:
    """Bounded search for scripts violating an invariant.

    Runs strategies in order, shrinks each violation to a minimal
    reproducer, and stops at max_findings or budget exhaustion
    (reported honestly, never silently).
    """
    if invariant not in _INVARIANTS:
        raise ExplorerInputError(f"unknown invariant: {invariant!r}")
    if not _is_int(seed):
        raise ExplorerInputError("'seed' must be an int")
    names = list(strategies) if strategies else ["boundary"]
    if not names or any(n not in _STRATEGIES for n in names):
        raise ExplorerInputError(
            f"strategies must be a non-empty subset of "
            f"{sorted(_STRATEGIES)}")
    clean_budgets = _validate_budgets(budgets)
    clean_params = _validate_params(params or {})
    _version, ir = validate_any(ir_doc)
    kind = ir["machine"]["kind"]
    if kind == "industrial_cell":
        raise ExplorerUnsupported(
            "industrial_cell needs the two-stream driver (roadmap)")
    t0 = time.monotonic()
    findings: list[dict[str, Any]] = []
    scripts_run = ticks_run = 0
    exhausted = False
    shrink_budget = {"max_scripts": min(100, clean_budgets["max_scripts"])}
    for name in names:
        for script in _strategy_scripts(name, ir, seed, kind,
                                        clean_budgets["max_scripts"]):
            if len(findings) >= clean_budgets["max_findings"]:
                break
            if scripts_run >= clean_budgets["max_scripts"]:
                exhausted = True
                break
            if ticks_run >= clean_budgets["max_ticks_total"]:
                exhausted = True
                break
            if time.monotonic() - t0 > clean_budgets["max_seconds"]:
                exhausted = True
                break
            out = run_script(ir, script, invariant, clean_params)
            scripts_run += 1
            ticks_run += out["ticks"]
            check = out["checks"][invariant]
            if check["passed"]:
                continue
            small = shrink(ir, script, invariant, clean_params,
                           shrink_budget)
            small_out = run_script(ir, small, invariant, clean_params)
            scripts_run += 1
            ticks_run += small_out["ticks"]
            focus = _violation_tick(small_out["checks"][invariant])
            findings.append({
                "explorer_version": EXPLORER_VERSION,
                "machine": out["machine"], "ir_sha256": out["ir_sha256"],
                "invariant": invariant, "params": clean_params,
                "strategy": name, "seed": script["seed"],
                "script": script,
                "shrunk_script": small,
                "observed": small_out["checks"][invariant],
                "stats": small_out["stats"],
                "trace_excerpt": _excerpt(small_out["trace"], focus),
                "trace_events": len(small_out["trace"]),
                "vectors": small_out["vectors"],
                "tier": "host-discovered",
            })
    seconds = time.monotonic() - t0
    return {"invariant": invariant, "params": clean_params,
            "strategies": names, "seed": seed,
            "findings": findings, "scripts_run": scripts_run,
            "ticks_run": ticks_run,
            "budget_exhausted": exhausted or scripts_run >=
            clean_budgets["max_scripts"],
            "seconds": round(seconds, 3)}


def _still_violates(ir: dict[str, Any], script: dict[str, Any],
                    invariant: str,
                    params: dict[str, Any]) -> bool:
    out = run_script(ir, script, invariant, params)
    return not out["checks"][invariant]["passed"]


def shrink(ir_doc: Any, script: dict[str, Any], invariant: str,
           params: dict[str, Any] | None = None,
           budgets: dict[str, Any] | None = None) -> dict[str, Any]:
    """Greedily minimize a violating script (fewest steps, then ticks).

    Drops faults/commands one at a time, narrows surviving windows,
    then trims trailing idle ticks. Deterministic; bounded re-runs.
    The input must already violate the invariant.
    """
    if invariant not in _INVARIANTS:
        raise ExplorerInputError(f"unknown invariant: {invariant!r}")
    clean_params = _validate_params(params or {})
    clean_budgets = _validate_budgets(budgets)
    _version, ir = validate_any(ir_doc)
    kind = ir["machine"]["kind"]
    steps = _validate_script(copy.deepcopy(script), kind)
    if not _still_violates(ir, steps, invariant, clean_params):
        raise ExplorerInputError(
            "shrink needs a script that violates the invariant")
    spent = 1
    limit = clean_budgets["max_scripts"]

    def attempt(candidate: dict[str, Any]) -> bool:
        nonlocal spent
        if spent >= limit:
            return False
        spent += 1
        try:
            return _still_violates(ir, candidate, invariant, clean_params)
        except (ExplorerInputError, IRValidationError):
            return False

    for i in reversed(range(len(steps["faults"]))):
        cand = copy.deepcopy(steps)
        del cand["faults"][i]
        if attempt(cand):
            steps = cand
    for i in reversed(range(len(steps["commands"]))):
        cand = copy.deepcopy(steps)
        del cand["commands"][i]
        if attempt(cand):
            steps = cand
    for fault in steps["faults"]:
        while fault["end_tick"] - fault["start_tick"] > 1:
            cand = copy.deepcopy(steps)
            for cand_fault in cand["faults"]:
                if cand_fault == fault:
                    cand_fault["end_tick"] -= 1
                    break
            if attempt(cand):
                steps = cand
                fault["end_tick"] -= 1
            else:
                break
    last_used = 0
    for fault in steps["faults"]:
        last_used = max(last_used, fault["end_tick"])
    for cmd in steps["commands"]:
        last_used = max(last_used, cmd["tick"] + 1)
    while steps["ticks"] > last_used + 5:
        cand = copy.deepcopy(steps)
        cand["ticks"] -= 5
        if attempt(cand):
            steps = cand
        else:
            break
    return steps


def replay(record: Any, ir_doc: Any) -> dict[str, Any]:
    """Re-run a finding's minimal script, same or fixed IR.

    Same IR digest -> determinism proof (must violate identically).
    Changed IR -> fix check (holds now?). The original record is
    returned untouched as regression evidence.
    """
    if not isinstance(record, dict):
        raise ExplorerInputError("record must be an object")
    for key in ("shrunk_script", "invariant", "ir_sha256", "observed"):
        if key not in record:
            raise ExplorerInputError(f"record misses '{key}'")
    invariant = record["invariant"]
    if invariant not in _INVARIANTS:
        raise ExplorerInputError(f"unknown invariant: {invariant!r}")
    params = _validate_params(record.get("params", {}))
    _version, ir = validate_any(ir_doc)
    digest = ir_sha256(ir)
    out = run_script(ir, record["shrunk_script"], invariant, params)
    violated = not out["checks"][invariant]["passed"]
    same_ir = digest == record["ir_sha256"]
    return {"violated": violated,
            "deterministic": bool(same_ir and violated),
            "same_ir": same_ir,
            "ir_sha256": digest,
            "record_sha256": record["ir_sha256"],
            "check": out["checks"][invariant],
            "expected": record["observed"],
            "stats": out["stats"],
            "trace_excerpt": _excerpt(
                out["trace"],
                _violation_tick(out["checks"][invariant])),
            "record": record}


def render_explore_text(report: dict[str, Any]) -> str:
    """One-screen textual summary of a search report."""
    lines = [
        f"explore: invariant={report['invariant']} "
        f"strategies={','.join(report['strategies'])} seed={report['seed']}",
        f"scripts={report['scripts_run']} ticks={report['ticks_run']} "
        f"seconds={report['seconds']} "
        f"budget_exhausted={report['budget_exhausted']}",
    ]
    if not report["findings"]:
        lines.append("findings: none (no violation within budget)")
        return "\n".join(lines)
    for i, rec in enumerate(report["findings"]):
        obs = rec["observed"]
        small = rec["shrunk_script"]
        lines.append(
            f"[{i}] {rec['tier']} {rec['strategy']} "
            f"machine={rec['machine']['id']} "
            f"ir={rec['ir_sha256'][:12]} violated={obs['name']}")
        lines.append(f"    observed: {obs['detail']}")
        lines.append(
            f"    minimal: ticks={small['ticks']} "
            f"faults={len(small['faults'])} "
            f"commands={len(small['commands'])} seed={small['seed']}")
    return "\n".join(lines)


def render_replay_text(result: dict[str, Any]) -> str:
    """One-screen textual summary of a replay result."""
    check = result["check"]
    lines = [
        f"replay: violated={result['violated']} "
        f"same_ir={result['same_ir']} "
        f"deterministic={result['deterministic']}",
        f"ir={result['ir_sha256'][:12]} "
        f"record={result['record_sha256'][:12]}",
        f"check: {check['name']} "
        f"{'FAIL' if not check['passed'] else 'PASS'}: {check['detail']}",
    ]
    if not result["same_ir"]:
        lines.append("fix check: reran the minimal script on a changed IR; "
                     "the original record is kept as regression evidence.")
    return "\n".join(lines)
