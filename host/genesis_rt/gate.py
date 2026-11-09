# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Release gate: fail-closed verdict over an evidence passport.

PASS requires ALL of: valid hash chain, every required scenario
present with status "pass", a qnx_build record present (its own
qnx_verified flag is reported separately and never conflated with
the host verdict), no failed/crashed records among required
scenarios, no pipeline_error record, and no duplicate record kinds.
Anything else => FAIL with explicit reasons.

On top of the host verdict, the gate assigns the highest EARNED
verification level so a host PASS can never pose as target-qualified
release evidence:

    NONE < HOST_TESTED < QNX_COMPILED < QNX_EXECUTED
         < QNX_BEHAVIOR_VERIFIED < QNX_PERFORMANCE_MEASURED

Each tier requires the previous one plus strictly stronger evidence
(see _level()). ``release_eligible`` is True only at
QNX_BEHAVIOR_VERIFIED or above with FULL coverage of the IR-declared
scenarios: a release decision must fail when QNX behavior evidence is
absent (even if every host scenario passes) and when the required set
silently omits declared scenarios. The QNX_PERFORMANCE_MEASURED tier
needs a ``qnx_perf`` record with measurements, produced by
``scripts/qnx_target.py perf`` (target-side bench) and attached via
``run_pipeline(..., perf_record=...)`` / ``demo --perf-record``.

Imported QNX records are untrusted until bound (§6): above QNX_EXECUTED
every tier additionally requires the provenance bindings checked by
``genesis_rt.provenance`` (exact matrix, timestamps, target identity,
IR/machine digest match, staged-vs-built binaries, transcript digests,
recomputed perf distribution). Unbound evidence caps the tier with an
explicit reason instead of failing the host verdict.

OMEGA7 arm quarantine (B2): ``robotic_arm_virtual`` has no arm
kinematics on host or target; the host faultlab runs it on the
differential-drive corridor. The gate fails any campaign whose
``ir`` record names the arm kind, or any of whose required
scenario bodies carries a ``physics_note``, with an explicit
``quarantined physics`` reason pointing at the disclosure.
Native-kind verdicts are byte-identical (neither signal fires
for them).
"""

from __future__ import annotations

import datetime
from typing import Any

from . import provenance
from .evidence import verify_chain

LEVELS = ("NONE", "HOST_TESTED", "QNX_COMPILED", "QNX_EXECUTED",
          "QNX_BEHAVIOR_VERIFIED", "QNX_PERFORMANCE_MEASURED")

# Release policy: behavior on target is the minimum for eligibility.
# Performance evidence is recorded (informational tier) but not required
# until a product policy declares perf budgets.
RELEASE_MIN_LEVEL = "QNX_BEHAVIOR_VERIFIED"


def _level(base_ok: bool, by_kind: dict[str, Any]) -> tuple[str, list[str]]:
    """Highest earned tier + explicit cap reasons (informational)."""
    if not base_ok:
        return "NONE", ["host base not satisfied (see verdict reasons)"]
    reasons: list[str] = []
    build = (by_kind.get("qnx_build") or {}).get("body", {})
    if build.get("status") != "ok":
        return "HOST_TESTED", [
            f"qnx_build.status={build.get('status')!r} (need 'ok' for QNX_COMPILED)"]
    target = (by_kind.get("qnx_target") or {}).get("body", {})
    checks = target.get("checks", [])
    if target.get("status") != "ok" or not isinstance(checks, list) or not checks:
        return "QNX_COMPILED", [
            f"qnx_target.status={target.get('status')!r} with "
            f"{len(checks) if isinstance(checks, list) else 0} checks "
            f"(need 'ok' + >=1 check for QNX_EXECUTED)"]
    if target.get("verified_on_target") is not True or not all(
            isinstance(c, dict) and c.get("passed") is True for c in checks):
        n_pass = sum(1 for c in checks
                     if isinstance(c, dict) and c.get("passed") is True)
        capped = [
            f"target ran ({n_pass}/{len(checks)} checks passed, "
            f"verified_on_target={target.get('verified_on_target')!r}); "
            f"need all-pass for QNX_BEHAVIOR_VERIFIED"]
        if target.get("provenance_error"):
            capped.append(f"target provenance error: "
                          f"{target['provenance_error']}")
        return "QNX_EXECUTED", capped
    ir_body = (by_kind.get("ir") or {}).get("body", {})
    unbound = provenance.validate_target_binding(
        ir_body=ir_body if isinstance(ir_body, dict) else {},
        build_body=build if isinstance(build, dict) else {},
        target_body=target if isinstance(target, dict) else {})
    if unbound:
        return "QNX_EXECUTED", [
            "target evidence not bound to this run "
            "(need provenance for QNX_BEHAVIOR_VERIFIED):"] + unbound
    perf = (by_kind.get("qnx_perf") or {}).get("body", {})
    if perf.get("status") != "ok" or not perf.get("measurements"):
        return "QNX_BEHAVIOR_VERIFIED", [
            "no qnx_perf record with measurements "
            "(benchmark harness not run; capped below QNX_PERFORMANCE_MEASURED)"]
    unbound_perf = provenance.validate_perf_binding(
        build_body=build if isinstance(build, dict) else {},
        target_body=target if isinstance(target, dict) else {},
        perf_body=perf if isinstance(perf, dict) else {},
        ir_body=ir_body if isinstance(ir_body, dict) else {})
    if unbound_perf:
        return "QNX_BEHAVIOR_VERIFIED", [
            "perf evidence not bound "
            "(need provenance for QNX_PERFORMANCE_MEASURED):"] + unbound_perf
    return "QNX_PERFORMANCE_MEASURED", reasons


def evaluate(passport: dict[str, Any], required_scenarios: list[str]) -> dict[str, Any]:
    reasons: list[str] = []
    chain = passport.get("chain", [])

    chain_errors = verify_chain(passport)
    if chain_errors:
        reasons.extend(f"chain: {e}" for e in chain_errors)

    by_kind: dict[str, Any] = {}
    for r in chain:
        if not isinstance(r, dict):
            continue
        kind = r.get("kind")
        if kind in by_kind:
            reasons.append(f"duplicate record kind: {kind} (refusing ambiguous evidence)")
        by_kind[kind] = r
    pipe_err = by_kind.get("pipeline_error")
    if pipe_err is not None:
        body = pipe_err.get("body", {}) if isinstance(pipe_err, dict) else {}
        reasons.append(f"pipeline error in step {body.get('step', '?')}: "
                       f"{body.get('error', 'unknown error')}")
    qnx_rec = by_kind.get("qnx_build")
    if qnx_rec is None:
        reasons.append("missing qnx_build record")

    missing: list[str] = []
    failed: list[str] = []
    for name in required_scenarios:
        rec = by_kind.get(f"scenario:{name}")
        if rec is None:
            missing.append(name)
            continue
        status = rec.get("body", {}).get("status")
        if status != "pass":
            failed.append(f"{name}={status}")
    if missing:
        reasons.append(f"missing scenario records: {sorted(missing)}")
    if failed:
        reasons.append(f"non-pass scenarios: {sorted(failed)}")
    if not required_scenarios:
        reasons.append("no required scenarios declared (refusing vacuous pass)")

    # OMEGA7 B2 quarantine: the arm kind runs on aliased corridor
    # physics (the ir body carries the kind; faultlab stamps
    # physics_note on its results). Either signal fails the
    # verdict loudly — an arm campaign can never pass silently.
    ir_rec = by_kind.get("ir")
    ir_qbody = (ir_rec.get("body", {}) if isinstance(ir_rec, dict)
                else {})
    machine = (ir_qbody.get("machine", {})
               if isinstance(ir_qbody, dict) else {})
    if isinstance(machine, dict) and \
            machine.get("kind") == "robotic_arm_virtual":
        reasons.append(
            "quarantined physics: robotic_arm_virtual ran on "
            "diffdrive-corridor (see "
            "docs/limitations-and-safety.md #10)")
    noted: list[str] = []
    for name in required_scenarios:
        rec = by_kind.get(f"scenario:{name}")
        body = rec.get("body") if isinstance(rec, dict) else None
        if isinstance(body, dict) and body.get("physics_note"):
            noted.append(name)
    if noted:
        reasons.append(
            f"quarantined physics: {len(noted)} scenario(s) ran on "
            f"aliased physics ({', '.join(sorted(noted))}); see "
            "docs/limitations-and-safety.md #10")

    verdict = "FAIL" if reasons else "PASS"
    # Host base for leveling ignores qnx_build *presence* (a hand-deleted
    # record already breaks the hash chain, so base_ok is False anyway);
    # every tier above HOST_TESTED re-checks build evidence strictly.
    base_ok = not [r for r in reasons if r != "missing qnx_build record"]
    level, level_reasons = _level(base_ok, by_kind)
    qnx_verified = LEVELS.index(level) >= LEVELS.index("QNX_BEHAVIOR_VERIFIED")
    release_eligible = LEVELS.index(level) >= LEVELS.index(RELEASE_MIN_LEVEL)
    # Coverage integrity (§10): the required set must cover every scenario
    # the IR declares, else release is refused loudly (never silently).
    ir_body = (by_kind.get("ir") or {}).get("body", {})
    declared = ir_body.get("scenarios") if isinstance(ir_body, dict) else None
    if isinstance(declared, list) and all(isinstance(s, str) for s in declared):
        omitted = sorted(s for s in declared if s not in required_scenarios)
        coverage: dict[str, Any] = {
            "declared": len(declared),
            "required": len(required_scenarios),
            "omitted": omitted,
        }
    else:
        omitted = []
        coverage = {"declared": None, "required": len(required_scenarios),
                    "omitted": []}
    if omitted:
        release_eligible = False
        level_reasons = level_reasons + [
            f"reduced coverage: {len(omitted)}/{len(declared)} declared "
            f"scenario(s) omitted from required: {omitted} (release refused)"
        ]
    return {
        "verdict": verdict,
        "reasons": reasons,
        "coverage": coverage,
        "required": sorted(required_scenarios),
        "missing": sorted(missing),
        "failed": sorted(failed),
        "qnx_verified": qnx_verified,
        "level": level,
        "level_reasons": level_reasons,
        "release_eligible": release_eligible,
        "evaluated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
