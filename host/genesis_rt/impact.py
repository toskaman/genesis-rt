# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Requirements-to-release engine (§11): change-impact analysis.

``analyze_impact`` compares two validated Machine IR revisions and
reports a *conservative* impact set: changed requirements, guard
limits, states, transitions, contracts, sensors/actuators, the
generated files whose bytes really moved (both revisions are run
through the deterministic code generator), and the scenarios that
must be re-run. ``release_status`` folds a new passport into that
report: what changed, what was retested, what remains unverified,
whether the binary changed, host vs QNX, and whether the evidence is
current.

Conservative means: the engine may ask for more retesting than
strictly needed, but it never claims a change is impact-free unless
nothing material moved — and it never claims formal completeness.
Targeted re-runs are rapid feedback only: release eligibility stays
with the full gate (``gate.evaluate`` refuses reduced coverage).
"""
from __future__ import annotations

import json
import tempfile
from typing import Any

from . import evidence as _evidence
from .codegen import generate as _generate
from .codegen import ir_sha256 as _ir_sha256
from .ir import IRValidationError, guard_limits
from .projects import ir_diff, validate_any


def _machine_of(ir: dict[str, Any]) -> dict[str, Any]:
    m = ir.get("machine", {}) if isinstance(ir, dict) else {}
    return {"id": m.get("id"), "kind": m.get("kind")} if isinstance(m, dict) \
        else {"id": None, "kind": None}


def _scenarios_of(ir: dict[str, Any]) -> list[str]:
    ver = ir.get("verification", {}) if isinstance(ir, dict) else {}
    scens = ver.get("scenarios", []) if isinstance(ver, dict) else []
    return [s for s in scens if isinstance(s, str)]


def _requirements_of(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ver = ir.get("verification", {}) if isinstance(ir, dict) else {}
    reqs = ver.get("requirements", []) if isinstance(ver, dict) else []
    return {str(r.get("id")): r for r in reqs
            if isinstance(r, dict) and r.get("id")}


def _by_key(rows: Any, key: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        return {}
    return {str(r.get(key)): r for r in rows
            if isinstance(r, dict) and r.get(key) is not None}


def _transitions_of(ir: dict[str, Any]) -> dict[str, Any]:
    rows = ir.get("transitions", []) or []
    if not isinstance(rows, list):
        return {}
    out: dict[str, Any] = {}
    seen: dict[str, int] = {}
    for t in rows:
        if not isinstance(t, dict):
            continue
        base = f"{t.get('from')}->{t.get('to')}:{t.get('event')}"
        seen[base] = seen.get(base, 0) + 1
        key = base if seen[base] == 1 else f"{base}#{seen[base]}"
        out[key] = t
    return out


def _keyed_diff(before: dict[str, Any], after: dict[str, Any],
                cap: int = 200) -> dict[str, Any]:
    added = sorted(set(after) - set(before))[:cap]
    removed = sorted(set(before) - set(after))[:cap]
    changed = sorted(k for k in set(before) & set(after)
                     if before[k] != after[k])[:cap]
    return {"added": added, "removed": removed, "changed": changed}


def _file_diff(before_ir: dict[str, Any],
               after_ir: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Regenerate both revisions; diff the real output digests."""
    try:
        with tempfile.TemporaryDirectory(prefix="genesis-impact-a-") as tmp_a, \
                tempfile.TemporaryDirectory(prefix="genesis-impact-b-") as tmp_b:
            fa = _generate(before_ir, tmp_a)["files"]
            fb = _generate(after_ir, tmp_b)["files"]
    except Exception as exc:  # valid IR should always render; fail loudly
        return {"added": [], "removed": [], "changed": []}, \
            f"codegen failed during impact analysis: {exc}"
    out: dict[str, Any] = {"added": sorted(set(fb) - set(fa)),
                           "removed": sorted(set(fa) - set(fb)),
                           "changed": []}
    for name in sorted(set(fa) & set(fb)):
        if fa[name] != fb[name]:
            out["changed"].append({"name": name, "before_sha256": fa[name],
                                  "after_sha256": fb[name]})
    return out, None


def analyze_impact(before_doc: Any, after_doc: Any) -> dict[str, Any]:
    """Compare two IR revisions. Raises IRValidationError on bad input."""
    v_before, before = validate_any(before_doc)
    v_after, after = validate_any(after_doc)
    ma, mb = _machine_of(before), _machine_of(after)
    same_machine = ma == mb and ma["id"] is not None
    machine_changed = json.dumps(before.get("machine", {}), sort_keys=True,
                                 default=str) != json.dumps(
                                     after.get("machine", {}), sort_keys=True,
                                     default=str)
    extras_changed = sorted(
        key for key in ("fault_responses", "simulation", "commands",
                        "telemetry")
        if before.get(key) != after.get(key))

    reqs_a, reqs_b = _requirements_of(before), _requirements_of(after)
    requirements = _keyed_diff(
        {k: json.dumps(v, sort_keys=True) for k, v in reqs_a.items()},
        {k: json.dumps(v, sort_keys=True) for k, v in reqs_b.items()})

    try:
        lim_a, lim_b = guard_limits(before), guard_limits(after)
    except (KeyError, TypeError, ValueError):
        lim_a = lim_b = None
    if lim_a is None or lim_b is None:
        limits = {"changed": [], "note": "limits not comparable across "
                  "these revisions (treated as changed)"}
        limits_changed = True
    else:
        limits = {"changed": [
            {"key": k, "before": lim_a[k], "after": lim_b[k]}
            for k in sorted(set(lim_a) | set(lim_b))
            if lim_a.get(k) != lim_b.get(k)]}
        limits_changed = bool(limits["changed"])

    states = _keyed_diff(_by_key(before.get("states"), "id"),
                         _by_key(after.get("states"), "id"))
    transitions = _keyed_diff(_transitions_of(before),
                              _transitions_of(after))
    contracts = _keyed_diff(_by_key(before.get("safety_contracts"), "name"),
                            _by_key(after.get("safety_contracts"), "name"))
    sensors = _keyed_diff(_by_key(before.get("sensors"), "id"),
                          _by_key(after.get("sensors"), "id"))
    actuators = _keyed_diff(_by_key(before.get("actuators"), "id"),
                            _by_key(after.get("actuators"), "id"))
    control_changed = before.get("control") != after.get("control")

    scens_a, scens_b = _scenarios_of(before), _scenarios_of(after)
    scenarios = {"added": sorted(set(scens_b) - set(scens_a)),
                 "removed": sorted(set(scens_a) - set(scens_b)),
                 "kept": sorted(set(scens_a) & set(scens_b))}

    files, codegen_error = _file_diff(before, after)

    # -- conservative impacted set: every entry carries its reason.
    impacted: dict[str, list[str]] = {}
    if not same_machine:
        for s in scens_b:
            impacted.setdefault(s, []).append("different machine id/kind")
    else:
        for s in scenarios["added"]:
            impacted.setdefault(s, []).append("scenario added")
        for rid in (requirements["added"] + requirements["removed"] +
                    requirements["changed"]):
            for side in (reqs_a.get(rid, {}), reqs_b.get(rid, {})):
                scen = side.get("scenario") if isinstance(side, dict) else None
                if isinstance(scen, str) and scen in scens_b:
                    impacted.setdefault(scen, []).append(
                        f"requirement {rid} changed")
        global_kinds = []
        if limits_changed or control_changed:
            global_kinds.append("guard limits/control")
        if machine_changed:
            global_kinds.append("machine block")
        if extras_changed:
            global_kinds.append("/".join(extras_changed))
        for name, bucket in (("safety contracts", contracts),
                             ("states", states),
                             ("transitions", transitions),
                             ("sensors", sensors),
                             ("actuators", actuators)):
            if bucket["added"] or bucket["removed"] or bucket["changed"]:
                global_kinds.append(name)
        classified = bool(global_kinds) or bool(
            requirements["added"] or requirements["removed"] or
            requirements["changed"]) or bool(
                scenarios["added"] or scenarios["removed"])
        if _ir_sha256(before) != _ir_sha256(after) and not classified:
            # Every IR byte is hashed: a digest move no class explains is
            # still a change. Stay conservative rather than silent.
            global_kinds.append("unclassified IR difference (fail-closed)")
        # NOTE: generated files are *reported* factually, but they never
        # trigger the global set alone: provenance headers embed the IR
        # digest, so every IR edit moves bytes. Retest scope follows the
        # semantic classes (requirements map precisely; any guard
        # contract change stays conservative).
        if codegen_error:
            global_kinds.append("codegen failure (fail-closed)")
        if global_kinds:
            reason = ("conservative: " + ", ".join(sorted(global_kinds)) +
                      " changed; limits/contracts/states are global to "
                      "every scenario")
            for s in scens_b:
                impacted.setdefault(s, []).append(reason)
    retest = sorted(impacted)
    raw = ir_diff(before_doc, after_doc)
    return {
        "before": {"ir_sha256": _ir_sha256(before),
                   "schema_version": v_before, "machine": ma},
        "after": {"ir_sha256": _ir_sha256(after),
                  "schema_version": v_after, "machine": mb},
        "same_machine": same_machine,
        "requirements": requirements,
        "limits": limits,
        "states": states,
        "transitions": transitions,
        "contracts": contracts,
        "sensors": sensors,
        "actuators": actuators,
        "control_changed": control_changed,
        "machine_changed": machine_changed,
        "extras_changed": extras_changed,
        "scenarios": scenarios,
        "files": files,
        "codegen_error": codegen_error,
        "impacted": [{"scenario": s, "reasons": sorted(set(r))}
                     for s, r in sorted(impacted.items())],
        "retest": retest,
        "evidence_invalidated": bool(retest),
        "raw_diff": raw,
        "conservative": True,
        "completeness": "heuristic impact set, not a formal proof: "
                        "retest is necessary, release still needs the "
                        "full gate over every declared scenario",
    }


def _chain_bodies(passport: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for r in passport.get("chain", []) or []:
        if isinstance(r, dict) and r.get("kind") not in out:
            out[r.get("kind")] = r.get("body", {})
    return out


def release_status(before_doc: Any, after_doc: Any, passport: Any,
                   base_passport: Any | None = None) -> dict[str, Any]:
    """Release comparison: impact + what a new passport actually retested.

    A broken passport chain is a *finding* (``chain_ok: false``), not a
    rejection: the caller asked whether this evidence releases the new
    revision, and the answer is no, with reasons.
    """
    impact = analyze_impact(before_doc, after_doc)
    if not isinstance(passport, dict):
        return {"impact": impact, "chain_ok": False,
                "chain_errors": ["passport is not an object"],
                "evidence_current": False}
    errors = _evidence.verify_chain(passport)
    if errors:
        return {"impact": impact, "chain_ok": False,
                "chain_errors": errors[:5], "evidence_current": False}
    bodies = _chain_bodies(passport)
    ir_body = bodies.get("ir", {}) if isinstance(bodies.get("ir"), dict) \
        else {}
    evidence_current = ir_body.get("ir_sha256") == \
        impact["after"]["ir_sha256"]
    passed = sorted(
        kind.split(":", 1)[1] for kind, body in bodies.items()
        if isinstance(kind, str) and kind.startswith("scenario:") and
        isinstance(body, dict) and body.get("status") == "pass")
    gate = bodies.get("gate_verdict", {}) \
        if isinstance(bodies.get("gate_verdict"), dict) else {}
    retest = impact["retest"]
    # Only passes recorded against the AFTER digest count as retested:
    # same scenario names on stale evidence prove nothing new.
    current_passes = set(passed) if evidence_current else set()
    retested = sorted(set(retest) & current_passes)
    build = bodies.get("qnx_build", {}) \
        if isinstance(bodies.get("qnx_build"), dict) else {}
    binary_changed: dict[str, Any]
    if base_passport is None:
        binary_changed = {"known": False,
                          "reason": "needs the before-run passport"}
    else:
        base_bodies = _chain_bodies(base_passport) \
            if isinstance(base_passport, dict) else {}
        base_build = base_bodies.get("qnx_build", {}) \
            if isinstance(base_bodies.get("qnx_build"), dict) else {}
        bins_a = base_build.get("binaries") \
            if isinstance(base_build.get("binaries"), dict) else None
        bins_b = build.get("binaries") \
            if isinstance(build.get("binaries"), dict) else None
        if bins_a is None or bins_b is None:
            binary_changed = {
                "known": False,
                "reason": "qnx_build binaries missing on at least one side "
                          "(host-only evidence has no binaries)"}
        else:
            digests = {n: (m.get("sha256") if isinstance(m, dict) else None)
                       for n, m in {**bins_a, **bins_b}.items()}
            changed = sorted(
                n for n in set(bins_a) | set(bins_b)
                if (bins_a.get(n, {}) if isinstance(bins_a.get(n), dict)
                    else {}).get("sha256") !=
                (bins_b.get(n, {}) if isinstance(bins_b.get(n), dict)
                 else {}).get("sha256"))
            binary_changed = {"known": True, "changed": bool(changed),
                              "binaries": sorted(changed), "digests": digests}
    host_or_qnx = gate.get("level", "?") if gate else \
        ("HOST_TESTED" if passed else "NONE")
    return {
        "impact": impact,
        "chain_ok": True,
        "chain_errors": [],
        "run_id": passport.get("run_id"),
        "evidence_current": evidence_current,
        "after_sha256": impact["after"]["ir_sha256"],
        "passport_sha256": ir_body.get("ir_sha256"),
        "retested": retested,
        "retest_pending": sorted(set(retest) - current_passes),
        "targeted_complete": set(retest) <= current_passes,
        "verdict": gate.get("verdict") if gate else None,
        "level": gate.get("level") if gate else None,
        "qnx_verified": gate.get("qnx_verified") if gate else False,
        "release_eligible": gate.get("release_eligible", False) if gate
        else False,
        "coverage": gate.get("coverage") if gate else None,
        "omitted": (gate.get("coverage", {}) or {}).get("omitted", [])
        if gate else [],
        "host_or_qnx": host_or_qnx,
        "qnx_build_status": build.get("status", "missing"),
        "source_changed": bool(impact["files"]["added"] or
                               impact["files"]["removed"] or
                               impact["files"]["changed"]),
        "binary_changed": binary_changed,
    }


def render_impact_text(report: dict[str, Any]) -> str:
    """One-screen textual summary of an impact report."""
    before, after = report["before"], report["after"]
    lines = [
        f"impact: {before['machine'].get('id')} "
        f"{before['ir_sha256'][:12]} -> {after['ir_sha256'][:12]} "
        f"(schema v{before['schema_version']} -> v{after['schema_version']})",
    ]
    if not report["same_machine"]:
        lines.append("different machines: full retest, no fine-grained "
                     "mapping attempted")
    for rid in report["requirements"]["changed"]:
        lines.append(f"  requirement changed: {rid}")
    for rid in report["requirements"]["added"]:
        lines.append(f"  requirement added: {rid}")
    for rid in report["requirements"]["removed"]:
        lines.append(f"  requirement removed: {rid}")
    for lim in report["limits"].get("changed", []):
        lines.append(f"  limit {lim['key']}: {lim['before']} -> "
                     f"{lim['after']}")
    if report["limits"].get("note"):
        lines.append(f"  limits: {report['limits']['note']}")
    if report.get("machine_changed"):
        lines.append("  machine block changed")
    for key in report.get("extras_changed", []):
        lines.append(f"  {key} changed")
    for kind in ("states", "transitions", "contracts", "sensors",
                 "actuators"):
        bucket = report[kind]
        for key in bucket["changed"]:
            lines.append(f"  {kind[:-1]} changed: {key}")
        for key in bucket["added"]:
            lines.append(f"  {kind[:-1]} added: {key}")
        for key in bucket["removed"]:
            lines.append(f"  {kind[:-1]} removed: {key}")
    for name in report["scenarios"]["added"]:
        lines.append(f"  scenario added: {name}")
    for name in report["scenarios"]["removed"]:
        lines.append(f"  scenario removed: {name}")
    files = report["files"]
    for entry in files["changed"]:
        lines.append(f"  file changed: {entry['name']}")
    for name in files["added"]:
        lines.append(f"  file added: {name}")
    for name in files["removed"]:
        lines.append(f"  file removed: {name}")
    if report["codegen_error"]:
        lines.append(f"  codegen: {report['codegen_error']}")
    if report["retest"]:
        lines.append(f"retest ({len(report['retest'])}): "
                     f"{', '.join(report['retest'])}")
    else:
        lines.append("retest: none (no material change)")
    lines.append("note: targeted retest is rapid feedback only; release "
                 "needs the full gate over every declared scenario")
    return "\n".join(lines) + "\n"


def render_release_text(status: dict[str, Any]) -> str:
    """One-screen textual summary of a release comparison."""
    lines = [render_impact_text(status["impact"]).rstrip(),
             f"run: {status.get('run_id')} "
             f"chain_ok={status.get('chain_ok')}"]
    if not status.get("chain_ok"):
        for err in status.get("chain_errors", []):
            lines.append(f"  chain: {err}")
        return "\n".join(lines) + "\n"
    lines.append(f"evidence_current={status['evidence_current']} "
                 f"(run {str(status['passport_sha256'])[:12]} vs "
                 f"after {status['after_sha256'][:12]})")
    lines.append(f"retested: "
                 f"{', '.join(status['retested']) or '(none)'}")
    lines.append(f"retest_pending: "
                 f"{', '.join(status['retest_pending']) or '(none)'}")
    lines.append(f"verdict={status['verdict']} level={status['level']} "
                 f"qnx_verified={status['qnx_verified']} "
                 f"release_eligible={status['release_eligible']}")
    if status["omitted"]:
        lines.append(f"omitted from required: "
                     f"{', '.join(status['omitted'])}")
    lines.append(f"source_changed={status['source_changed']} "
                 f"binary_changed={status['binary_changed']}")
    return "\n".join(lines) + "\n"
