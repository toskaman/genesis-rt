# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Contract-aware native oracle (Wave 11 §5).

Predicts the verdict a correct native guard MUST return for a
``genesis_faultinject probe`` command, derived from the validated IR
(limit + machine kind) and the wire policy semantics — never from the
observed transcript. The target-matrix parser compares observed vs
predicted; a valid contract change (1.2 -> 1.6) flips predictions
instead of failing the campaign, while a genuinely wrong guard still
fails.

Wire fidelity: the probe carries linear_mps as float32
(genesis_cmd_t) against a float64 limit with strict ``>`` denial —
the same rule as host/genesis_rt/guard_policy.py, pinned by the
C/Python conformance vectors.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

EXPECTED_ALLOW = "EXPECTED_ALLOW"
EXPECTED_DENY = "EXPECTED_DENY"
EXPECTED_SAFE_STOP = "EXPECTED_SAFE_STOP"
EXPECTED_ERROR = "EXPECTED_ERROR"
INCONCLUSIVE = "INCONCLUSIVE"
UNSUPPORTED = "UNSUPPORTED"

SUPPORTED_MACHINE_KINDS = ("differential_drive_robot", "conveyor")

# IR schema bound for max_linear_speed_mps (examples/amr-demo schema).
MIN_LIMIT_MPS = 0.0
MAX_LIMIT_MPS = 10.0
# Probe CLI bound (genesis_faultinject.c run_probe: |v| <= 1e6).
MAX_PROBE_MPS = 1e6
# 3-decimal probe plans need daylight between 0 and the limit.
MIN_PLANNED_LIMIT_MPS = 0.002


@dataclass(frozen=True)
class OracleVerdict:
    verdict: str  # one of the EXPECTED_*/INCONCLUSIVE/UNSUPPORTED constants
    decision: str | None  # ALLOW / DENY / None when unpredicted
    reason: str | None  # OK / SPEED_OVER_LIMIT / ESTOP / None
    state_out: int | None  # 1 nominal / 3 safe-stop / None
    detail: str


def _f32(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if number != number or abs(number) == float("inf"):
        return None
    return number


def expect_linear_probe(*, machine_kind: str, limit_mps: Any,
                        probe_mps: Any, estop: bool = False) -> OracleVerdict:
    """Predict a nominal probe verdict from the contract.

    The probe is well-formed by construction (fresh seq, sane
    deadline, zero angular, fresh sensor, sim up); only the speed
    comparison and estop can fire.
    """
    if machine_kind not in SUPPORTED_MACHINE_KINDS:
        return OracleVerdict(UNSUPPORTED, None, None, None,
                             f"machine kind {machine_kind!r} has no probe "
                             f"semantics (supported: "
                             f"{', '.join(SUPPORTED_MACHINE_KINDS)})")
    limit = _finite_number(limit_mps)
    probe = _finite_number(probe_mps)
    if limit is None or not (MIN_LIMIT_MPS < limit <= MAX_LIMIT_MPS):
        return OracleVerdict(INCONCLUSIVE, None, None, None,
                             f"limit {limit_mps!r} outside schema "
                             f"({MIN_LIMIT_MPS}, {MAX_LIMIT_MPS}]")
    if probe is None or abs(probe) > MAX_PROBE_MPS:
        return OracleVerdict(INCONCLUSIVE, None, None, None,
                             f"probe {probe_mps!r} unusable "
                             f"(|v| <= {MAX_PROBE_MPS:g})")
    if estop:
        # Estop dominates speed (guard check order), latches safe-stop.
        return OracleVerdict(EXPECTED_SAFE_STOP, "DENY", "ESTOP", 3,
                             "estop dominates the speed comparison")
    wire = _f32(probe)
    if abs(wire) > limit:
        return OracleVerdict(EXPECTED_DENY, "DENY", "SPEED_OVER_LIMIT", 1,
                             f"wire {wire!r} exceeds limit {limit!r}")
    return OracleVerdict(EXPECTED_ALLOW, "ALLOW", "OK", 1,
                         f"wire {wire!r} within limit {limit!r}")


#: Fixed reference probe added to every plan: the iconic 1.5 m/s
#: comparison is preserved across contract changes (BEFORE DENY vs
#: AFTER ALLOW), with boundary probes around it.
REFERENCE_PROBE_MPS = 1.5


def plan_probes(limit_mps: float) -> list[float] | None:
    """Below/at/above/reference probe plan for a bound limit (sorted,
    3 decimals), or None when the limit admits no discriminating plan
    (the check then fails closed with an explicit reason)."""
    limit = _finite_number(limit_mps)
    if limit is None or limit < MIN_PLANNED_LIMIT_MPS:
        return None
    below = round(0.5 * limit, 3)
    above = round(limit + 0.5, 3)
    if not (0.0 < below < limit < above):
        return None
    return sorted({below, limit, above, REFERENCE_PROBE_MPS})
