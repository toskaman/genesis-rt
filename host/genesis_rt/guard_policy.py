# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Guard policy mirror (host side).

This module is the exact behavioral mirror of
target/qnx8/common/guard_policy.c. Both are verified against the same
decision vectors (see tests + target/qnx8/host_tests/guard_vector).

Fail-closed: any unknown, malformed, stale or out-of-range input is
denied. Leaving SAFE_STOP requires an explicit supervisor reset, never
a normal command.

Parity contract (mirrors guard_policy.c exactly):
- decide() returns state_out but never mutates ctx.state; the CALLER
  applies it (faultlab loop, genesis_guard.c main loop). This matches
  the C side, which only mutates last_seq/reset_armed.
- Integer fields must fit their wire width (uint32/uint16); negative,
  boolean or out-of-range values are denied MALFORMED (fail-closed).
  The C struct cannot represent such values, so rejecting them cannot
  break parity on any input a real sender can produce.
- Check order is magic -> version -> size -> NaN/Inf -> seq ->
  deadline -> sensor -> sim -> estop -> speed -> angular -> transition.
  estop_engaged is strict 0/1 (wire uint8); any other value is
  MALFORMED, fail-closed.
- Sequence freshness uses serial-number arithmetic (RFC 1982): with
  uint32 seq, delta = (seq - last_seq) mod 2^32 is accepted iff
  1 <= delta < 2^31. Counter wraparound (2^32-1 -> 0) is accepted;
  duplicates, replays and huge forward jumps are denied STALE_SEQ.
- Deadline comparison uses the same serial arithmetic (§16): with
  uint32 clocks, overdue = 0 < (now_ms - deadline_ms) mod 2^32
  < 2^31. Commands stay correct across the 2^32ms wraparound
  (~49.7 days); now == deadline is not overdue. Pairs 2^31+ ms
  apart are ambiguous by construction (RFC 1982) and read as
  "deadline in the future" — unreachable for real near-term
  deadlines (period + 20ms margin).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

PROTOCOL_MAGIC = 0x47454E31  # "GEN1"
PROTOCOL_VERSION = 1

_SEQ_MOD = 1 << 32
_SEQ_HALF = 1 << 31

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
R_ESTOP = "ESTOP"

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
              sim_connected, estop_engaged (int 0/1).
              Missing/oddly-typed fields => DENY MALFORMED.
    """
    def deny(reason: str, latch: bool) -> dict[str, Any]:
        state_out = ST_SAFE_STOP if latch else ctx.state
        return {"decision": DENY, "reason": reason,
                "state_out": state_out, "applied": False}

    int_fields = ("magic", "version", "seq", "now_ms", "deadline_ms",
                  "req_state", "sensor_age_ms", "estop_engaged")
    try:
        for _key in int_fields + ("linear_mps", "angular_radps"):
            if isinstance(cmd[_key], bool):
                return deny(R_MALFORMED, latch=True)
        magic = int(cmd["magic"])
        version = int(cmd["version"])
        size_ok = bool(cmd["size_ok"])
        seq = int(cmd["seq"])
        now_ms = int(cmd["now_ms"])
        deadline_ms = int(cmd["deadline_ms"])
        # Wire fidelity (Wave 10 E3): the guard decides on float32
        # wire bytes (genesis_cmd_t), so the oracle quantizes speeds
        # the same way. Pack overflow (huge double -> inf) falls into
        # the MALFORMED handler below, matching the C isnan/isinf
        # rejection of the narrowed value.
        linear = struct.unpack("f", struct.pack("f", float(cmd["linear_mps"])))[0]
        angular = struct.unpack("f", struct.pack("f", float(cmd["angular_radps"])))[0]
        req_state = int(cmd["req_state"])
        sensor_age_ms = int(cmd["sensor_age_ms"])
        sim_connected = bool(cmd["sim_connected"])
        estop = int(cmd["estop_engaged"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return deny(R_MALFORMED, latch=True)

    wire_ok = (
        0 <= magic < (1 << 32) and 0 <= version < (1 << 16)
        and 0 <= seq < (1 << 32) and 0 <= now_ms < (1 << 32)
        and 0 <= deadline_ms < (1 << 32) and 0 <= req_state < (1 << 16)
        and 0 <= sensor_age_ms < (1 << 32) and estop in (0, 1)
    )
    if not wire_ok:
        return deny(R_MALFORMED, latch=True)

    try:
        freshness = int(limits["freshness_limit_ms"])
        max_linear = float(limits["max_linear_speed_mps"])
        max_angular = float(limits["max_angular_speed_radps"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return deny(R_MALFORMED, latch=True)

    if magic != PROTOCOL_MAGIC:
        return deny(R_BAD_MAGIC, latch=True)
    if version != PROTOCOL_VERSION:
        return deny(R_BAD_VERSION, latch=True)
    if not size_ok:
        return deny(R_BAD_SIZE, latch=True)
    if not (linear == linear and angular == angular):  # NaN check
        return deny(R_MALFORMED, latch=True)
    if abs(linear) == float("inf") or abs(angular) == float("inf"):
        return deny(R_MALFORMED, latch=True)
    delta = (seq - ctx.last_seq) % _SEQ_MOD
    if not 0 < delta < _SEQ_HALF:
        return deny(R_STALE_SEQ, latch=False)
    overdue = (now_ms - deadline_ms) % _SEQ_MOD
    if 0 < overdue < _SEQ_HALF:
        return deny(R_OVERDUE_DEADLINE, latch=False)
    if sensor_age_ms > freshness:
        return deny(R_STALE_SENSOR, latch=True)
    if not sim_connected:
        return deny(R_SIM_DISCONNECTED, latch=True)
    if estop:
        return deny(R_ESTOP, latch=True)
    if abs(linear) > max_linear:
        return deny(R_SPEED_OVER_LIMIT, latch=False)
    if abs(angular) > max_angular:
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
