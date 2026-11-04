# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Guard policy mirror (host side).

This module is the exact behavioral mirror of
target/qnx8/common/guard_policy.c. Both are verified against the same
decision vectors (see tests + target/qnx8/host_tests/guard_vector).

Fail-closed: any unknown, malformed, stale or out-of-range input is
denied. Leaving SAFE_STOP requires an explicit supervisor reset, never
a normal command.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROTOCOL_MAGIC = 0x47454E31  # "GEN1"
PROTOCOL_VERSION = 1

# States
ST_INIT = 0
ST_NOMINAL = 1
ST_DEGRADED = 2
ST_SAFE_STOP = 3
STATES = (ST_INIT, ST_NOMINAL, ST_DEGRADED, ST_SAFE_STOP)

# Decisions / reasons (must match guard_policy.h)
ALLOW = "ALLOW"
DENY = "DENY"
R_OK = "OK"
R_BAD_MAGIC = "BAD_MAGIC"
R_BAD_VERSION = "BAD_VERSION"
R_BAD_SIZE = "BAD_SIZE"
R_STALE_SEQ = "STALE_SEQ"
R_OVERDUE_DEADLINE = "OVERDUE_DEADLINE"
R_STALE_SENSOR = "STALE_SENSOR"
R_SIM_DISCONNECTED = "SIM_DISCONNECTED"
R_SPEED_OVER_LIMIT = "SPEED_OVER_LIMIT"
R_ANGULAR_OVER_LIMIT = "ANGULAR_OVER_LIMIT"
R_BAD_TRANSITION = "BAD_TRANSITION"
R_MALFORMED = "MALFORMED"

# Allowed state requests carried by a command: NOMINAL or DEGRADED only.
# SAFE_STOP is entered by denial latching, exited only via supervisor reset.
_REQUESTABLE = (ST_NOMINAL, ST_DEGRADED)


@dataclass
class GuardContext:
    last_seq: int = 0
    state: int = ST_NOMINAL
    reset_armed: bool = False  # set only by the supervisor path


def decide(cmd: dict[str, Any], ctx: GuardContext, limits: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one command. Returns {decision, reason, state_out, applied}.

    cmd keys: magic, version, size_ok(bool), seq, now_ms, deadline_ms,
              linear_mps, angular_radps, req_state, sensor_age_ms,
              sim_connected. Missing/oddly-typed fields => DENY MALFORMED.
    """
    def deny(reason: str, latch: bool) -> dict[str, Any]:
        state_out = ST_SAFE_STOP if latch else ctx.state
        return {"decision": DENY, "reason": reason,
                "state_out": state_out, "applied": False}

    try:
        magic = int(cmd["magic"])
        version = int(cmd["version"])
        size_ok = bool(cmd["size_ok"])
        seq = int(cmd["seq"])
        now_ms = int(cmd["now_ms"])
        deadline_ms = int(cmd["deadline_ms"])
        linear = float(cmd["linear_mps"])
        angular = float(cmd["angular_radps"])
        req_state = int(cmd["req_state"])
        sensor_age_ms = int(cmd["sensor_age_ms"])
        sim_connected = bool(cmd["sim_connected"])
    except (KeyError, TypeError, ValueError):
        return deny(R_MALFORMED, latch=True)

    if not (linear == linear and angular == angular):  # NaN check
        return deny(R_MALFORMED, latch=True)
    if abs(linear) == float("inf") or abs(angular) == float("inf"):
        return deny(R_MALFORMED, latch=True)

    if magic != PROTOCOL_MAGIC:
        return deny(R_BAD_MAGIC, latch=True)
    if version != PROTOCOL_VERSION:
        return deny(R_BAD_VERSION, latch=True)
    if not size_ok:
        return deny(R_BAD_SIZE, latch=True)
    if seq <= ctx.last_seq:
        return deny(R_STALE_SEQ, latch=False)
    if now_ms > deadline_ms:
        return deny(R_OVERDUE_DEADLINE, latch=False)
    if sensor_age_ms > int(limits["freshness_limit_ms"]):
        return deny(R_STALE_SENSOR, latch=True)
    if not sim_connected:
        return deny(R_SIM_DISCONNECTED, latch=True)
    if abs(linear) > float(limits["max_linear_speed_mps"]):
        return deny(R_SPEED_OVER_LIMIT, latch=False)
    if abs(angular) > float(limits["max_angular_speed_radps"]):
        return deny(R_ANGULAR_OVER_LIMIT, latch=False)

    if ctx.state == ST_SAFE_STOP:
        if not ctx.reset_armed:
            return deny(R_BAD_TRANSITION, latch=True)
        if req_state not in _REQUESTABLE:
            return deny(R_BAD_TRANSITION, latch=True)
        ctx.last_seq = seq
        ctx.reset_armed = False
        return {"decision": ALLOW, "reason": R_OK,
                "state_out": req_state, "applied": True}

    if req_state not in _REQUESTABLE:
        return deny(R_BAD_TRANSITION, latch=False)
    ctx.last_seq = seq
    return {"decision": ALLOW, "reason": R_OK,
            "state_out": req_state, "applied": True}
