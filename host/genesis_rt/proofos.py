# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""GENESIS ProofOS: continuous verification plans (Wave 12 §6).

A plan answers, for one base→source change: what changed, what is
affected, which checks must run, what can be verified locally, what
needs a QNX target, and what remains blocked. It is built from the
CI IR-check report (validation + change impact) and travels with it
as a machine-readable review artifact.

Hard rule, enforced by construction: a plan NEVER grants release
eligibility. ``release_status.eligible`` is always False at plan
time; only ``gate.evaluate`` over complete evidence can pass a
release. Targeted retest lists are advisory fast feedback.

Stage lifecycle (plan-level; execution states stay with the pipeline
and target ops, which this module does not duplicate):

    CHANGE_DETECTED -> IR_VALIDATED -> IMPACT_ANALYZED
        -> HOST_VERIFIED -> NATIVE_PENDING -> TARGET_VERIFIED
        -> EVIDENCE_SEALED -> REVIEW_READY

Exceptional (terminal unless noted): INVALID, FAILED, BLOCKED,
CANCELLED, STALE, INTERRUPTED. ``advance`` enforces legal moves.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .codegen import canonical_json
from .provenance import EXPECTED_TARGET_CHECKS, TARGET_PLATFORM

PLAN_VERSION = 1
GENERATOR = "proofos/1"

STAGES = ("CHANGE_DETECTED", "IR_VALIDATED", "IMPACT_ANALYZED",
          "HOST_VERIFIED", "NATIVE_PENDING", "TARGET_VERIFIED",
          "EVIDENCE_SEALED", "REVIEW_READY")
EXCEPTIONAL = ("INVALID", "FAILED", "BLOCKED", "CANCELLED", "STALE",
               "INTERRUPTED")
TERMINAL = ("INVALID", "FAILED", "CANCELLED", "REVIEW_READY")

_NEXT: dict[str, tuple[str, ...]] = {
    "CHANGE_DETECTED": ("IR_VALIDATED", "INVALID", "CANCELLED",
                        "INTERRUPTED"),
    "IR_VALIDATED": ("IMPACT_ANALYZED", "INVALID", "CANCELLED",
                     "INTERRUPTED"),
    "IMPACT_ANALYZED": ("HOST_VERIFIED", "FAILED", "BLOCKED",
                        "CANCELLED", "STALE", "INTERRUPTED"),
    "HOST_VERIFIED": ("NATIVE_PENDING", "FAILED", "BLOCKED",
                      "CANCELLED", "STALE", "INTERRUPTED"),
    "NATIVE_PENDING": ("TARGET_VERIFIED", "FAILED", "BLOCKED",
                       "CANCELLED", "STALE", "INTERRUPTED"),
    "TARGET_VERIFIED": ("EVIDENCE_SEALED", "FAILED", "BLOCKED",
                        "CANCELLED", "STALE", "INTERRUPTED"),
    "EVIDENCE_SEALED": ("REVIEW_READY", "FAILED", "BLOCKED",
                        "CANCELLED", "STALE", "INTERRUPTED"),
    "REVIEW_READY": ("STALE",),
    "BLOCKED": ("CANCELLED", "INTERRUPTED", "IMPACT_ANALYZED"),
    "STALE": ("CHANGE_DETECTED", "CANCELLED"),
    "FAILED": (),
    "INVALID": (),
    "CANCELLED": (),
    "INTERRUPTED": ("CHANGE_DETECTED", "CANCELLED"),
}

_NATIVE_TRIGGER = ("changed", "added", "deleted", "renamed")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hex64(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _native_needed(changes: list[dict[str, Any]]) -> bool:
    for entry in changes:
        status = str(entry.get("status", ""))
        if entry.get("renamed_from") or any(
                status == t or status.startswith(f"{t} ")
                or status.startswith(f"renamed from ")
                for t in ("changed", "added", "deleted")):
            return True
    return False


def build_plan(*, source_commit: str | None, base_commit: str | None,
               changes: list[dict[str, Any]],
               report_sha256: str | None = None) -> dict[str, Any]:
    """Build a plan from validated CI IR-check entries (pure)."""
    invalid = [e["path"] for e in changes if not e.get("valid")]
    native = _native_needed(changes)
    targeted: list[str] = []
    for entry in changes:
        for scen in entry.get("retest") or []:
            item = f"{entry['path']}:{scen}"
            if item not in targeted:
                targeted.append(item)
    stage = "INVALID" if invalid else "IMPACT_ANALYZED"
    reasons = [f"invalid IR: {p}" for p in invalid] or [
        "plan-time verdict only: run the full host suite, the "
        "native matrix (when required), then gate.evaluate"]
    plan: dict[str, Any] = {
        "plan_version": PLAN_VERSION,
        "generator": GENERATOR,
        "plan_id": "",
        "source_commit": source_commit,
        "base_commit": base_commit,
        "generated_utc": _utcnow(),
        "stage": stage,
        "changes": [
            {"path": e.get("path"), "status": e.get("status"),
             "valid": bool(e.get("valid")),
             "renamed_from": e.get("renamed_from"),
             "ir_sha256_before": e.get("ir_sha256_before"),
             "ir_sha256_after": e.get("ir_sha256_after"),
             "limits_changed": bool(e.get("limits_changed")),
             "requirements_changed": int(
                 e.get("requirements_changed") or 0),
             "retest": list(e.get("retest") or [])}
            for e in changes
        ],
        "required_host_tests": (["tests/ (full host suite)"] +
                                [f"targeted (advisory): {t}"
                                 for t in targeted]),
        "required_native_checks": ([{"name": c} for c in
                                    EXPECTED_TARGET_CHECKS]
                                   if native else []),
        "target_requirements": {"needed": native,
                                "platform": TARGET_PLATFORM
                                if native else None},
        "evidence": {"ir_report_sha256": report_sha256},
        "release_status": {"eligible": False, "reasons": reasons},
        "stage_history": [{"stage": stage, "at": _utcnow(),
                           "note": "plan built"}],
    }
    core = {"source": source_commit, "base": base_commit,
            "changes": [(c["path"], c["status"], c["ir_sha256_before"],
                         c["ir_sha256_after"]) for c in plan["changes"]],
            "generator": GENERATOR, "version": PLAN_VERSION}
    plan["plan_id"] = hashlib.sha256(
        canonical_json(core).encode("utf-8")).hexdigest()
    return plan


def validate_plan(plan: Any) -> list[str]:
    """Structural fail-closed check for plan consumers ([] = ok)."""
    if not isinstance(plan, dict):
        return ["plan is not an object"]
    errors: list[str] = []
    if plan.get("plan_version") != PLAN_VERSION:
        errors.append(f"unsupported plan_version: "
                      f"{plan.get('plan_version')!r}")
    if not _hex64(plan.get("plan_id")):
        errors.append("plan_id is not a sha256 hex digest")
    if plan.get("stage") not in STAGES + EXCEPTIONAL:
        errors.append(f"unknown stage: {plan.get('stage')!r}")
    for key in ("source_commit", "base_commit"):
        val = plan.get(key)
        if val is not None and not (isinstance(val, str) and val):
            errors.append(f"{key} must be a string or null")
    changes = plan.get("changes")
    if not isinstance(changes, list):
        errors.append("changes must be a list")
    else:
        for i, entry in enumerate(changes):
            if not isinstance(entry, dict):
                errors.append(f"changes[{i}] is not an object")
                continue
            for digest_key in ("ir_sha256_before", "ir_sha256_after"):
                digest = entry.get(digest_key)
                if digest is not None and not _hex64(digest):
                    errors.append(f"changes[{i}].{digest_key} is not "
                                  f"a sha256 hex digest")
    release = plan.get("release_status")
    if not isinstance(release, dict) or release.get("eligible") is not False:
        errors.append("release_status.eligible must be false at plan time")
    native = plan.get("required_native_checks")
    if not isinstance(native, list):
        errors.append("required_native_checks must be a list")
    return errors


def advance(plan: dict[str, Any], to: str,
            note: str = "") -> dict[str, Any]:
    """Move a plan to a new stage (returns a new dict; raises ValueError
    on illegal transitions or terminal plans)."""
    current = plan.get("stage")
    if current in TERMINAL:
        raise ValueError(f"plan is terminal ({current}); no transitions")
    if to not in _NEXT.get(str(current), ()):
        raise ValueError(f"illegal transition {current} -> {to}")
    if to == "REVIEW_READY":
        raise ValueError("REVIEW_READY requires sealed evidence "
                         "via the release pipeline, not advance()")
    import copy
    nxt = copy.deepcopy(plan)
    nxt["stage"] = to
    nxt.setdefault("stage_history", []).append(
        {"stage": to, "at": _utcnow(), "note": note})
    return nxt
