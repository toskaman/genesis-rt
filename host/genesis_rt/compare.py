# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Build comparison: diff two pipeline run directories.

Answers "what changed between build A and build B": machine identity,
declared scenarios, generated sources (hash + unified diff), per-scenario
statuses, and gate verdict/level/release. Powers the broken-vs-fixed
revision story: same request, different evidence.

Inputs are run directories produced by ``run_pipeline`` (``passport.json``
+ ``generated/``). Pure stdlib, deterministic output.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any


def _load_run(run_dir: str | Path) -> tuple[dict[str, Any], Path]:
    d = Path(run_dir)
    passport_path = d / "passport.json"
    if not passport_path.is_file():
        raise ValueError(f"not a run directory (no passport.json): {d}")
    passport = json.loads(passport_path.read_text(encoding="utf-8"))
    return passport, d


def _chain_by_kind(passport: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_kind: dict[str, dict[str, Any]] = {}
    for rec in passport.get("chain", []):
        if isinstance(rec, dict) and "kind" in rec:
            by_kind.setdefault(rec["kind"], rec)
    return by_kind


def _scenario_statuses(by_kind: dict[str, dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kind, rec in sorted(by_kind.items()):
        if kind.startswith("scenario:"):
            body = rec.get("body", {})
            out[body.get("scenario", kind)] = body.get("status", "?")
    return out


def _generated_files(run_dir: Path) -> dict[str, str]:
    """Text outputs only (strict UTF-8): binaries are hash-compared."""
    gen = run_dir / "generated"
    if not gen.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(gen.iterdir()):
        if not p.is_file():
            continue
        try:
            out[p.name] = p.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary: see _generated_binary_hashes
    return out


def _generated_binary_hashes(run_dir: Path) -> dict[str, str]:
    """sha256 per non-UTF-8 file in generated/ (binaries differ silently)."""
    gen = run_dir / "generated"
    if not gen.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(gen.iterdir()):
        if not p.is_file():
            continue
        raw = p.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            out[p.name] = hashlib.sha256(raw).hexdigest()
    return out


_LIMIT_KEYS = ("period_ms", "max_linear_speed_mps",
               "max_angular_speed_radps", "freshness_limit_ms")


def _contract_diff(ira: dict[str, Any],
                   irb: dict[str, Any]) -> dict[str, Any]:
    """Field-level contract delta (which knob moved, not just sha≠sha)."""
    ma = ira.get("machine") or {}
    mb = irb.get("machine") or {}
    la = ira.get("limits") or {}
    lb = irb.get("limits") or {}
    known = bool(la) and bool(lb)
    changed = {k: [la.get(k), lb.get(k)] for k in _LIMIT_KEYS
               if known and la.get(k) != lb.get(k)}
    return {"machine_changed": ma.get("id") != mb.get("id")
            or ma.get("kind") != mb.get("kind"),
            "limits_known": known,
            "limits_changed": changed}


_PERF_STATS = ("count", "p50", "p95", "p99", "max")


def _measurements_diff(by_kind_a: dict[str, dict[str, Any]],
                       by_kind_b: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Bound-perf delta: per-metric percentile moves, or honest absence."""
    ma = ((by_kind_a.get("qnx_perf") or {}).get("body", {})
          .get("measurements", {}) or {})
    mb = ((by_kind_b.get("qnx_perf") or {}).get("body", {})
          .get("measurements", {}) or {})
    changed: dict[str, dict[str, list[Any]]] = {}
    for metric in sorted(set(ma) & set(mb)):
        da, db = ma[metric] or {}, mb[metric] or {}
        delta = {s: [da.get(s), db.get(s)] for s in _PERF_STATS
                 if da.get(s) != db.get(s)}
        if delta:
            changed[metric] = delta
    return {"only_a": sorted(set(ma) - set(mb)),
            "only_b": sorted(set(mb) - set(ma)),
            "changed": changed}


def _fixed_broken(sa: dict[str, str],
                  sb: dict[str, str]) -> tuple[list[str], list[str]]:
    fixed = sorted(n for n in set(sa) & set(sb)
                   if sa[n] != "pass" and sb[n] == "pass")
    broken = sorted(n for n in set(sa) & set(sb)
                    if sa[n] == "pass" and sb[n] != "pass")
    return fixed, broken


def compare_runs(run_a: str | Path, run_b: str | Path) -> dict[str, Any]:
    """Compare two run directories. Returns a structured, JSON-safe diff."""
    pa, da = _load_run(run_a)
    pb, db = _load_run(run_b)
    ka, kb = _chain_by_kind(pa), _chain_by_kind(pb)

    ira = (ka.get("ir") or {}).get("body", {})
    irb = (kb.get("ir") or {}).get("body", {})
    scen_a = list(ira.get("scenarios", []))
    scen_b = list(irb.get("scenarios", []))

    ga = da / "generated"
    gb = db / "generated"
    fa = _generated_files(da) if ga.is_dir() else {}
    fb = _generated_files(db) if gb.is_dir() else {}
    names_a, names_b = set(fa), set(fb)
    changed = sorted(n for n in names_a & names_b if fa[n] != fb[n])
    diffs = {}
    for name in changed:
        diffs[name] = "".join(difflib.unified_diff(
            fa[name].splitlines(keepends=True),
            fb[name].splitlines(keepends=True),
            fromfile=f"a/{name}", tofile=f"b/{name}"))
    ba = _generated_binary_hashes(da) if ga.is_dir() else {}
    bb = _generated_binary_hashes(db) if gb.is_dir() else {}
    binaries_changed = sorted(n for n in set(ba) & set(bb)
                              if ba[n] != bb[n])
    binaries_only_a = sorted(set(ba) - set(bb))
    binaries_only_b = sorted(set(bb) - set(ba))

    sa, sb = _scenario_statuses(ka), _scenario_statuses(kb)
    status_changes = {name: [sa.get(name, "-"), sb.get(name, "-")]
                      for name in sorted(set(sa) | set(sb))
                      if sa.get(name) != sb.get(name)}
    fixed, broken = _fixed_broken(sa, sb)

    va = pa.get("gate", "?")
    vb = pb.get("gate", "?")
    verdict_a = next((r.get("body", {}) for r in pa.get("chain", [])
                      if r.get("kind") == "gate_verdict"), {})
    verdict_b = next((r.get("body", {}) for r in pb.get("chain", [])
                      if r.get("kind") == "gate_verdict"), {})

    return {
        "run_a": pa.get("run_id", str(da)),
        "run_b": pb.get("run_id", str(db)),
        "ir": {
            "machine_a": (ira.get("machine") or {}).get("id"),
            "machine_b": (irb.get("machine") or {}).get("id"),
            "kind_a": (ira.get("machine") or {}).get("kind"),
            "kind_b": (irb.get("machine") or {}).get("kind"),
            "scenarios_only_a": sorted(set(scen_a) - set(scen_b)),
            "scenarios_only_b": sorted(set(scen_b) - set(scen_a)),
            "ir_sha256_equal": ira.get("ir_sha256") == irb.get("ir_sha256"),
        },
        "contract": _contract_diff(ira, irb),
        "measurements": _measurements_diff(ka, kb),
        "generated": {
            "only_a": sorted(names_a - names_b),
            "only_b": sorted(names_b - names_a),
            "changed": changed,
            "diffs": diffs,
            "binaries_changed": binaries_changed,
            "binaries_only_a": binaries_only_a,
            "binaries_only_b": binaries_only_b,
        },
        "scenarios": {
            "status_a": sa,
            "status_b": sb,
            "status_changes": status_changes,
            "fixed": fixed,
            "broken": broken,
        },
        "verdict": {
            "a": {"verdict": va,
                  "level": verdict_a.get("level"),
                  "release_eligible": verdict_a.get("release_eligible")},
            "b": {"verdict": vb,
                  "level": verdict_b.get("level"),
                  "release_eligible": verdict_b.get("release_eligible")},
            "changed": (va, verdict_a.get("level"),
                        verdict_a.get("release_eligible")) != (
                            vb, verdict_b.get("level"),
                            verdict_b.get("release_eligible")),
            "release_changed": (verdict_a.get("release_eligible") !=
                                verdict_b.get("release_eligible")),
        },
    }


def render_text(comp: dict[str, Any]) -> str:
    """One-screen human summary of a comparison (deterministic)."""
    lines = [f"compare: {comp['run_a']}  vs  {comp['run_b']}", ""]
    ir = comp["ir"]
    lines.append(f"machine: {ir['machine_a']} ({ir['kind_a']})  vs  "
                 f"{ir['machine_b']} ({ir['kind_b']})")
    lines.append(f"ir identical: {ir['ir_sha256_equal']}")
    if ir["scenarios_only_a"] or ir["scenarios_only_b"]:
        lines.append(f"scenarios only in a: {ir['scenarios_only_a'] or '-'}")
        lines.append(f"scenarios only in b: {ir['scenarios_only_b'] or '-'}")
    gen = comp["generated"]
    lines.append(f"generated changed: {gen['changed'] or '-'}")
    if gen["only_a"] or gen["only_b"]:
        lines.append(f"generated only in a: {gen['only_a'] or '-'}")
        lines.append(f"generated only in b: {gen['only_b'] or '-'}")
    bchg = gen.get("binaries_changed", [])
    if bchg or gen.get("binaries_only_a") or gen.get("binaries_only_b"):
        lines.append(f"binaries changed (sha256): {bchg or '-'}")
    contract = comp.get("contract", {})
    lim = contract.get("limits_changed", {})
    if contract.get("limits_known"):
        lines.append("contract limits changed: " + (
            ", ".join(f"{k}: {v[0]} -> {v[1]}"
                      for k, v in sorted(lim.items())) or "-"))
    else:
        lines.append("contract limits changed: unknown (limits not recorded)")
    ch = comp["scenarios"]["status_changes"]
    lines.append(f"scenario status changes: {ch or '-'}")
    lines.append(f"fixed: {comp['scenarios'].get('fixed') or '-'}")
    lines.append(f"broken: {comp['scenarios'].get('broken') or '-'}")
    meas = comp.get("measurements", {})
    mchg = meas.get("changed", {})
    if meas.get("only_a") or meas.get("only_b") or mchg:
        lines.append("measurements changed: " + (
            ", ".join(f"{m}.{s}: {v[0]} -> {v[1]}"
                      for m, stats in sorted(mchg.items())
                      for s, v in sorted(stats.items()))
            or f"only_a={meas.get('only_a')} only_b={meas.get('only_b')}"))
    else:
        lines.append("measurements changed: -")
    va, vb = comp["verdict"]["a"], comp["verdict"]["b"]
    lines.append(f"verdict: {va}  vs  {vb}")
    lines.append(f"verdict changed: {comp['verdict']['changed']}")
    lines.append(f"release eligibility changed: "
                 f"{comp['verdict'].get('release_changed')}")
    return "\n".join(lines) + "\n"
