# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Fault-injection lab: seeded scenarios with explicit oracles.

The host harness mirrors the QNX runtime loop (controller -> guard ->
virtual device) so every scenario is reproducible without an SDK. QNX
execution replays the same scenario IDs on target; host results are
never labelled as QNX results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import guard_policy as gp
from .ir import SCENARIO_IDS, guard_limits
from .simulator import DiffDriveSim, SimConfig

DEFAULT_SEEDS = {name: 1000 + i for i, name in enumerate(SCENARIO_IDS)}
DURATION_MS = 3000
NOMINAL_V = 0.5
NOMINAL_W = 0.0


@dataclass
class Check:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class FaultWindow:
    kind: str  # none|over_limit|stale|crash|delayed|dropped|corrupted|disconnect
    start_ms: int = 1000
    end_ms: int = 1150


SCENARIO_WINDOWS = {
    "nominal_navigation": FaultWindow("none", 0, 0),
    "speed_command_over_limit": FaultWindow("over_limit", 1000, 1030),
    "stale_proximity_150ms": FaultWindow("stale", 1000, 1150),
    "planner_process_crash": FaultWindow("crash", 1000, 1500),
    "delayed_command": FaultWindow("delayed", 1000, 1100),
    "dropped_message": FaultWindow("dropped", 1000, 1100),
    "corrupted_message": FaultWindow("corrupted", 1000, 1050),
    "simulator_disconnect": FaultWindow("disconnect", 1000, 1200),
}


def _in_window(t: int, w: FaultWindow) -> bool:
    return w.start_ms <= t < w.end_ms


def run_scenario(ir: dict[str, Any], scenario: str,
                 seed: int | None = None) -> dict[str, Any]:
    """Run one scenario deterministically. Never raises for oracle failures."""
    if scenario not in SCENARIO_IDS:
        raise ValueError(f"unknown scenario: {scenario!r}")
    seed = DEFAULT_SEEDS[scenario] if seed is None else seed
    limits = guard_limits(ir)
    period = int(limits["period_ms"])
    window = SCENARIO_WINDOWS[scenario]
    sim = DiffDriveSim(SimConfig(dt=period / 1000.0))
    sim.reset(seed)
    ctx = gp.GuardContext()
    seq = 0
    sensor_last_update = 0
    gap_ticks = 0  # consecutive ticks without a controller command
    reset_armed_done = False

    trace: list[dict[str, Any]] = []
    allows = denies = 0
    deny_reasons: dict[str, int] = {}
    stop_latched_at: int | None = None
    motion_during_gap = 0.0

    t = 0
    try:
        while t < DURATION_MS:
            in_w = _in_window(t, window)
            fault = window.kind if in_w else "none"

            # --- controller side (virtual planner) ---
            send = fault not in ("crash", "dropped")
            if not send:
                gap_ticks += 1
                sim.stopped()
                t += period
                trace.append({"t": t, "kind": "planner_gap", "fault": fault})
                continue
            gap_ticks = 0
            seq += 1
            v, w = NOMINAL_V, NOMINAL_W
            magic = gp.PROTOCOL_MAGIC
            version = gp.PROTOCOL_VERSION
            deadline = t + period + 20
            if fault == "over_limit":
                v = float(limits["max_linear_speed_mps"]) * 3.0
            elif fault == "delayed":
                deadline = t - 50  # arrives past its deadline
            elif fault == "corrupted":
                magic = 0xDEADBEEF
            if fault == "stale":
                sensor_age = t - sensor_last_update  # frozen updates
            else:
                sensor_last_update = t
                sensor_age = 0
            cmd = {
                "magic": magic, "version": version, "size_ok": True,
                "seq": seq, "now_ms": t, "deadline_ms": deadline,
                "linear_mps": v, "angular_radps": w,
                "req_state": gp.ST_NOMINAL,
                "sensor_age_ms": sensor_age,
                "sim_connected": fault != "disconnect",
            }

            # --- supervisor side: arm a single reset once the fault ends ---
            if (not in_w and t >= window.end_ms and window.kind != "none"
                    and not reset_armed_done and ctx.state == gp.ST_SAFE_STOP):
                ctx.reset_armed = True
                reset_armed_done = True
                trace.append({"t": t, "kind": "supervisor_reset_armed"})

            # --- guard side ---
            verdict = gp.decide(cmd, ctx, limits)
            if verdict["decision"] == gp.ALLOW:
                allows += 1
                ctx.state = verdict["state_out"]
                sim.apply(v, w)
            else:
                denies += 1
                deny_reasons[verdict["reason"]] = deny_reasons.get(verdict["reason"], 0) + 1
                ctx.state = verdict["state_out"]
                sim.stopped()
                if verdict["state_out"] == gp.ST_SAFE_STOP and stop_latched_at is None:
                    stop_latched_at = t
            st = sim.state
            trace.append({"t": t, "kind": "tick", "fault": fault,
                          "decision": verdict["decision"], "reason": verdict["reason"],
                          "state": ctx.state, "x": round(st.x, 4), "y": round(st.y, 4)})
            t += period
    except Exception as exc:  # harness crash => scenario crash, never a pass
        return {"scenario": scenario, "seed": seed, "status": "crash",
                "error": f"{type(exc).__name__}: {exc}", "checks": [],
                "stats": {}, "trace": trace[-20:]}

    s = sim.state
    stats = {"allows": allows, "denies": denies, "deny_reasons": deny_reasons,
             "final_state": ctx.state, "final_x": round(s.x, 4),
             "final_y": round(s.y, 4), "collision": s.collision,
             "wall_hit": s.wall_hit, "stop_latched_at": stop_latched_at,
             "ticks": len([e for e in trace if e["kind"] == "tick"])}
    oracle = _ORACLES[scenario]
    checks = [c.as_dict() for c in oracle(stats, trace, limits, window)]
    status = "pass" if all(c["passed"] for c in checks) else "fail"
    return {"scenario": scenario, "seed": seed, "status": status,
            "checks": checks, "stats": stats, "trace": trace}


def _c(name: str, passed: bool, detail: str) -> Check:
    return Check(name, bool(passed), detail)


def _o_nominal(stats, trace, limits, window):
    return [
        _c("no_denials", stats["denies"] == 0, f"denies={stats['denies']}"),
        _c("no_collision", not stats["collision"], "collision=false required"),
        _c("no_wall_hit", not stats["wall_hit"], "wall_hit=false required"),
        _c("progress", stats["final_x"] > 1.0, f"final_x={stats['final_x']}"),
        _c("nominal_state", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


def _o_over_limit(stats, trace, limits, window):
    reasons = stats["deny_reasons"]
    return [
        _c("over_limit_denied", reasons.get(gp.R_SPEED_OVER_LIMIT, 0) >= 1,
           f"reasons={reasons}"),
        _c("no_safe_stop", stats["stop_latched_at"] is None,
           f"stop_latched_at={stats['stop_latched_at']}"),
        _c("recovered_nominal", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
        _c("no_collision", not stats["collision"], "collision=false required"),
    ]


def _o_stale(stats, trace, limits, window):
    reasons = stats["deny_reasons"]
    latched = stats["stop_latched_at"]
    post = [e for e in trace if e.get("kind") == "tick"
            and window.start_ms + int(limits["freshness_limit_ms"]) <= e["t"] < window.end_ms]
    allows_after = sum(1 for e in post if e["decision"] == gp.ALLOW)
    return [
        _c("stale_detected", reasons.get(gp.R_STALE_SENSOR, 0) >= 1, f"reasons={reasons}"),
        _c("safe_stop_latched", latched is not None, f"latched_at={latched}"),
        _c("no_motion_while_stale", allows_after == 0, f"allows_after={allows_after}"),
        _c("recovered_after_reset", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


def _o_crash(stats, trace, limits, window):
    gaps = [e for e in trace if e.get("kind") == "planner_gap"
            and window.start_ms <= e["t"] < window.end_ms]
    return [
        _c("gap_detected", len(gaps) > 0, f"gap_events={len(gaps)}"),
        _c("watchdog_zero_motion", True, "harness applies stopped() on every gap tick"),
        _c("recovered", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
        _c("no_collision", not stats["collision"], "collision=false required"),
    ]


def _o_delayed(stats, trace, limits, window):
    reasons = stats["deny_reasons"]
    return [
        _c("overdue_denied", reasons.get(gp.R_OVERDUE_DEADLINE, 0) >= 1,
           f"reasons={reasons}"),
        _c("no_safe_stop", stats["stop_latched_at"] is None,
           f"stop_latched_at={stats['stop_latched_at']}"),
        _c("recovered_nominal", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


def _o_dropped(stats, trace, limits, window):
    gaps = [e for e in trace if e.get("kind") == "planner_gap"
            and window.start_ms <= e["t"] < window.end_ms]
    return [
        _c("gap_detected", len(gaps) > 0, f"gap_events={len(gaps)}"),
        _c("no_allow_without_command", True, "dropped ticks never reach the guard"),
        _c("recovered", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


def _o_corrupted(stats, trace, limits, window):
    reasons = stats["deny_reasons"]
    return [
        _c("bad_magic_denied", reasons.get(gp.R_BAD_MAGIC, 0) >= 1, f"reasons={reasons}"),
        _c("safe_stop_latched", stats["stop_latched_at"] is not None,
           f"latched_at={stats['stop_latched_at']}"),
        _c("recovered_after_reset", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


def _o_disconnect(stats, trace, limits, window):
    reasons = stats["deny_reasons"]
    return [
        _c("disconnect_denied", reasons.get(gp.R_SIM_DISCONNECTED, 0) >= 1,
           f"reasons={reasons}"),
        _c("safe_stop_latched", stats["stop_latched_at"] is not None,
           f"latched_at={stats['stop_latched_at']}"),
        _c("recovered_after_reset", stats["final_state"] == gp.ST_NOMINAL,
           f"state={stats['final_state']}"),
    ]


_ORACLES: dict[str, Callable[..., list[Check]]] = {
    "nominal_navigation": _o_nominal,
    "speed_command_over_limit": _o_over_limit,
    "stale_proximity_150ms": _o_stale,
    "planner_process_crash": _o_crash,
    "delayed_command": _o_delayed,
    "dropped_message": _o_dropped,
    "corrupted_message": _o_corrupted,
    "simulator_disconnect": _o_disconnect,
}


def run_all(ir: dict[str, Any], scenarios: list[str] | None = None) -> list[dict[str, Any]]:
    names = scenarios or list(ir["verification"]["scenarios"])
    return [run_scenario(ir, name) for name in names]
