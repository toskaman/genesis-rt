# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""GENESIS Evidence Graph: typed provenance over passports (+ optional IR).

``build_graph`` folds one hash-verified passport (and, when supplied, the
Machine IR it ran) into ``{nodes, edges}`` with explicit predicates. Every
node carries a stable id, a type, a label, chain source refs, a status and
the artifacts behind it. Links the source data cannot support are omitted
— and their absence is itself visible (``unverified``/``missing`` nodes).

Tampered or version-unknown passports raise ``InvalidPassport``: they are
never rendered as verified. Inputs are size/node capped for hostile docs.
"""
from __future__ import annotations

from typing import Any

from . import evidence as _evidence
from . import provenance as _provenance

MAX_PASSPORT_BYTES = 2 * 1024 * 1024
MAX_IR_BYTES = 256 * 1024
MAX_NODES = 2000
MAX_EDGES = 8000

NODE_TYPES = ("requirement", "ir", "limit", "file", "build", "binary",
              "target", "process", "target_check", "scenario", "check",
              "observation", "verdict")

PREDICATES = ("verified_by", "derives_from", "defines", "compiled_into",
              "built_by", "executed_as", "observed_in", "failed_by")


class InvalidPassport(Exception):
    """Passport unusable for graphing (chain broken / bad shape)."""


class GraphTooLarge(Exception):
    """Input exceeds the safety caps."""


def _short(value: Any, limit: int = 16) -> str:
    text = str(value or "")
    return text[:limit] + ("…" if len(text) > limit else "")


def build_graph(passport: dict[str, Any],
                ir: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the evidence graph. Raises InvalidPassport / GraphTooLarge."""
    import json as _json

    if len(_json.dumps(passport)) > MAX_PASSPORT_BYTES:
        raise GraphTooLarge("passport exceeds 2 MiB")
    if ir is not None and len(_json.dumps(ir)) > MAX_IR_BYTES:
        raise GraphTooLarge("IR exceeds 256 KiB")
    errors = _evidence.verify_chain(passport)
    if errors:
        raise InvalidPassport("; ".join(errors[:5]))
    chain = passport.get("chain", [])
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for record in chain:
        by_kind.setdefault(str(record.get("kind")), []).append(record)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    def add_node(node_id: str, ntype: str, label: str, status: str,
                 source: list[dict[str, Any]] | None = None,
                 artifacts: dict[str, Any] | None = None,
                 data: dict[str, Any] | None = None) -> None:
        if len(nodes) >= MAX_NODES:
            raise GraphTooLarge(f"node cap {MAX_NODES} reached")
        nodes.append({"id": node_id, "type": ntype, "label": label,
                      "status": status, "source": source or [],
                      "artifacts": artifacts or {}, "data": data or {}})

    def add_edge(src: str, predicate: str, dst: str) -> None:
        if len(edges) >= MAX_EDGES:
            raise GraphTooLarge(f"edge cap {MAX_EDGES} reached")
        edges.append({"from": src, "predicate": predicate, "to": dst})

    def src_of(record: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"seq": record.get("seq"), "kind": record.get("kind")}]

    run_id = passport.get("run_id")
    ir_rec = (by_kind.get("ir") or [{}])[0]
    ir_body = ir_rec.get("body", {}) if isinstance(ir_rec, dict) else {}
    machine = ir_body.get("machine", {}) if isinstance(ir_body, dict) else {}
    codegen_rec = (by_kind.get("codegen") or [{}])[0]
    codegen_body = codegen_rec.get("body", {}) if isinstance(codegen_rec, dict) else {}
    build_rec = (by_kind.get("qnx_build") or [{}])[0]
    build_body = build_rec.get("body", {}) if isinstance(build_rec, dict) else {}
    target_rec = (by_kind.get("qnx_target") or [{}])[0]
    target_body = target_rec.get("body", {}) if isinstance(target_rec, dict) else {}
    verdict_rec = (by_kind.get("gate_verdict") or [{}])[0]
    verdict_body = verdict_rec.get("body", {}) if isinstance(verdict_rec, dict) else {}

    scenario_recs = sorted(
        (r for kind, rs in by_kind.items() if kind.startswith("scenario:")
         for r in rs),
        key=lambda r: str(r.get("kind")))
    scen_status = {str(r.get("kind", "")).split(":", 1)[1]:
                   (r.get("body", {}) or {}).get("status", "?")
                   for r in scenario_recs
                   if ":" in str(r.get("kind", ""))}

    # -- requirement (needs the IR doc; v2 carries verification.requirements)
    requirements: list[dict[str, Any]] = []
    if isinstance(ir, dict):
        ver = ir.get("verification", {})
        if isinstance(ver, dict) and isinstance(ver.get("requirements"), list):
            requirements = [r for r in ver["requirements"]
                            if isinstance(r, dict)]
    for req in requirements[:200]:
        rid = str(req.get("id", "?"))
        scen = str(req.get("scenario", ""))
        status = scen_status.get(scen)
        node_status = ("verified" if status == "pass" else
                       "failed" if status not in (None, "?") else
                       "unverified")
        add_node(f"req:{rid}", "requirement",
                 str(req.get("claim", rid))[:160] or rid, node_status,
                 artifacts={"scenario": scen},
                 data={"id": rid, "scenario": scen,
                       "scenario_status": status or "not_run"})
        # Red-team round 2, A4: verified_by only when the scenario
        # actually passed — never to an unrun/failed scenario.
        if status == "pass":
            add_edge(f"req:{rid}", "verified_by", f"scenario:{scen}")

    # -- IR + limits
    mid = machine.get("id", "?") if isinstance(machine, dict) else "?"
    add_node("ir", "ir",
             f"{mid} (schema v{ir_body.get('schema_version', '?')})",
             "verified", source=src_of(ir_rec) if ir_rec else [],
             artifacts={"ir_sha256": ir_body.get("ir_sha256")},
             data={"machine": machine,
                   "scenarios": ir_body.get("scenarios", [])})
    limits = ir_body.get("limits", {}) or {}
    if isinstance(limits, dict):
        for key in sorted(limits)[:64]:
            add_node(f"limit:{key}", "limit", f"{key} = {limits[key]}",
                     "info", source=src_of(ir_rec) if ir_rec else [],
                     data={"key": key, "value": limits[key]})
            add_edge("ir", "defines", f"limit:{key}")

    # -- generated files -> build -> binaries
    files = codegen_body.get("files", {}) or {}
    if isinstance(files, dict):
        for name in sorted(files)[:256]:
            add_node(f"file:{name}", "file",
                     f"{name} ({_short(files[name])})", "verified",
                     source=src_of(codegen_rec) if codegen_rec else [],
                     artifacts={"sha256": files[name]},
                     data={"name": name, "sha256": files[name],
                           "generator": codegen_body.get("generator_version"),
                           "template_version":
                               codegen_body.get("template_version")})
            add_edge(f"file:{name}", "derives_from", "ir")
            add_edge(f"file:{name}", "compiled_into", "build")
    build_status = str(build_body.get("status", "missing"))
    binaries = build_body.get("binaries", {}) or {}
    add_node("build", "build",
             f"qnx build ({build_status})",
             "verified" if build_status == "ok" else
             "missing" if build_status == "missing" else "unverified",
             source=src_of(build_rec) if build_rec else [],
             data={"status": build_status,
                   "toolchain": build_body.get("qcc_version") or
                   build_body.get("environment"),
                   "reason": build_body.get("reason"),
                   "verified_on_target":
                       build_body.get("verified_on_target")})
    if isinstance(binaries, dict):
        for name in sorted(binaries)[:256]:
            meta = binaries[name] if isinstance(binaries[name], dict) else {}
            add_node(f"binary:{name}", "binary",
                     f"{name} ({_short(meta.get('sha256'))})", "verified",
                     source=src_of(build_rec) if build_rec else [],
                     artifacts={"sha256": meta.get("sha256")},
                     data={"name": name, "sha256": meta.get("sha256"),
                           "size": meta.get("size"),
                           "cksum": meta.get("cksum")})
            add_edge(f"binary:{name}", "built_by", "build")

    # -- target binding: processes + matrix checks (only what is recorded)
    bound_reasons = _provenance.validate_target_binding(
        ir_body=ir_body if isinstance(ir_body, dict) else {},
        build_body=build_body if isinstance(build_body, dict) else {},
        target_body=target_body if isinstance(target_body, dict) else {})
    bound = not bound_reasons
    tgt = target_body.get("target", {}) if isinstance(target_body, dict) else {}
    tstatus = str(target_body.get("status", "missing"))
    add_node("target", "target",
             f"target ({tstatus}{', bound' if bound else ''})",
             "verified" if bound else
             "missing" if tstatus == "missing" else "unverified",
             source=src_of(target_rec) if target_rec else [],
             data={"status": tstatus, "bound": bound,
                   "reasons": bound_reasons[:8],
                   "platform": tgt.get("platform") if isinstance(tgt, dict) else None,
                   "window": [target_body.get("started_utc"),
                              target_body.get("finished_utc")]})
    if bound:
        add_edge("build", "verified_by", "target")
    staged = target_body.get("staged", {}) or {}
    if isinstance(staged, dict):
        build_bins = binaries if isinstance(binaries, dict) else {}
        for name in sorted(staged)[:256]:
            meta = staged[name] if isinstance(staged[name], dict) else {}
            bmeta = build_bins.get(name, {}) if isinstance(build_bins, dict) else {}
            matched = bool(bmeta) and bmeta.get("cksum") == meta.get("cksum") \
                and bmeta.get("size") == meta.get("size")
            add_node(f"process:{name}", "process",
                     f"{name} ({'matched' if matched else 'unstaged-source'})",
                     "verified" if matched else "unverified",
                     source=src_of(target_rec) if target_rec else [],
                     data={"name": name, "cksum": meta.get("cksum"),
                           "size": meta.get("size"), "matched": matched})
            add_edge(f"process:{name}", "observed_in", "target")
            if matched:
                add_edge(f"process:{name}", "executed_as", f"binary:{name}")
    for check in (target_body.get("checks", []) or [])[:64]:
        if not isinstance(check, dict):
            continue
        name = str(check.get("name", "?"))
        transcripts = target_body.get("transcripts", {}) or {}
        digest = transcripts.get(name) if isinstance(transcripts, dict) else None
        add_node(f"tcheck:{name}", "target_check", name,
                 "verified" if check.get("passed") else "failed",
                 source=src_of(target_rec) if target_rec else [],
                 artifacts={"transcript_sha256": digest},
                 data={"name": name, "passed": bool(check.get("passed")),
                       "detail": str(check.get("detail", ""))[:300],
                       "transcript_sha256": digest})
        add_edge(f"tcheck:{name}", "observed_in", "target")
        add_edge("target", "verified_by", f"tcheck:{name}")

    # -- scenarios + checks + trace observations
    for record in scenario_recs:
        kind = str(record.get("kind", ""))
        name = kind.split(":", 1)[1] if ":" in kind else kind
        body = record.get("body", {}) or {}
        status = body.get("status", "?")
        checks = body.get("checks", []) or []
        trace = body.get("trace", {}) or {}
        digest = trace.get("digest", "?") if isinstance(trace, dict) else "?"
        add_node(f"scenario:{name}", "scenario",
                 f"{name} ({status})",
                 "verified" if status == "pass" else
                 "failed" if status not in ("?", "skip", "missing") else
                 "unverified",
                 source=src_of(record),
                 artifacts={"seed": body.get("seed")},
                 data={"name": name, "status": status,
                       "seed": body.get("seed"),
                       "stats": body.get("stats", {}),
                       "trace_digest": digest})
        add_edge(f"scenario:{name}", "derives_from", "ir")
        add_edge("verdict", "derives_from", f"scenario:{name}")
        obs_id = f"trace:{name}"
        add_node(obs_id, "observation",
                 f"trace {_short(digest, 12)}"
                 f" ({trace.get('event_count', len(trace.get('events', [])))} events"
                 f"{', truncated' if trace.get('truncated') else ''})"
                 if isinstance(trace, dict) else "trace (?)",
                 "verified" if isinstance(trace, dict) and digest != "?" else "missing",
                 source=src_of(record),
                 data={"digest": digest,
                       "events": trace.get("event_count",
                                           len(trace.get("events", [])))
                       if isinstance(trace, dict) else 0,
                       "truncated": bool(trace.get("truncated"))
                       if isinstance(trace, dict) else False})
        add_edge(obs_id, "observed_in", f"scenario:{name}")
        if isinstance(checks, list):
            for check in checks[:128]:
                if not isinstance(check, dict):
                    continue
                cname = str(check.get("name", "?"))
                passed = bool(check.get("passed"))
                cid = f"check:{name}:{cname}"
                add_node(cid, "check",
                         f"{cname} ({'pass' if passed else 'FAIL'})",
                         "verified" if passed else "failed",
                         source=src_of(record),
                         data={"name": cname, "passed": passed,
                               "detail": str(check.get("Detail",
                                                       check.get("detail", "")))[:300]})
                add_edge(f"scenario:{name}", "verified_by", cid)
                add_edge(cid, "verified_by" if passed else "failed_by", obs_id)

    # -- verdict (declared after scenarios so edges dangle nowhere)
    verdict = str(verdict_body.get("verdict", "UNKNOWN"))
    nodes.append({"id": "verdict", "type": "verdict",
                  "label": f"gate {verdict} ({verdict_body.get('level', '?')})",
                  "status": "verified" if verdict == "PASS" else
                  "failed" if verdict == "FAIL" else "unverified",
                  "source": src_of(verdict_rec) if verdict_rec else [],
                  "artifacts": {},
                  "data": {"verdict": verdict,
                           "level": verdict_body.get("level"),
                           "reasons": verdict_body.get("reasons", []),
                           "qnx_verified": verdict_body.get("qnx_verified"),
                           "release_eligible":
                               verdict_body.get("release_eligible"),
                           "failed": verdict_body.get("failed", []),
                           "coverage": verdict_body.get("coverage", {})}})
    if bound:
        add_edge("verdict", "derives_from", "target")

    # verdict-first ordering helps readers; edges already reference it.
    nodes.sort(key=lambda n: ({"verdict": 0, "requirement": 1, "ir": 2,
                               "limit": 3, "file": 4, "build": 5,
                               "binary": 6, "target": 7, "process": 8,
                               "target_check": 9, "scenario": 10,
                               "check": 11, "observation": 12}
                              .get(n["type"], 99), n["id"]))
    by_type: dict[str, int] = {}
    for node in nodes:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
    return {"run_id": run_id, "chain_valid": True, "bound": bound,
            "ir_attached": ir is not None,
            "requirements": len(requirements),
            "nodes": nodes, "edges": edges,
            "counts": {"nodes": len(nodes), "edges": len(edges),
                       "by_type": by_type},
            "truncated": False}


def render_graph_text(graph: dict[str, Any]) -> str:
    """One-screen textual summary: verdict, requirements, gaps."""
    nodes = graph.get("nodes", [])
    by_id = {n["id"]: n for n in nodes}
    verdict = by_id.get("verdict", {})
    data = verdict.get("data", {})
    lines = [
        f"graph: run {graph.get('run_id')} "
        f"({graph['counts']['nodes']} nodes, "
        f"{graph['counts']['edges']} edges, "
        f"target {'bound' if graph.get('bound') else 'unbound'})",
        f"verdict: {verdict.get('label', '?')} "
        f"qnx_verified={data.get('qnx_verified')} "
        f"release_eligible={data.get('release_eligible')}",
    ]
    reqs = [n for n in nodes if n["type"] == "requirement"]
    if reqs:
        lines.append("requirements:")
        for n in reqs:
            lines.append(f"  [{n['status']}] {n['data'].get('id')}: "
                         f"{n['label'][:100]} -> "
                         f"{n['data'].get('scenario')}")
    elif not graph.get("ir_attached"):
        lines.append("requirements: (attach --ir to resolve them)")
    failed = [n for n in nodes if n["status"] == "failed"]
    if failed:
        lines.append("failed:")
        for n in failed[:20]:
            lines.append(f"  {n['type']}:{n['id']} :: {n['label'][:100]}")
    gaps = [n for n in nodes if n["status"] in ("missing", "unverified")]
    if gaps:
        lines.append("gaps:")
        for n in gaps[:20]:
            lines.append(f"  [{n['status']}] {n['type']}:{n['id']} :: "
                         f"{n['label'][:100]}")
    return "\n".join(lines) + "\n"


def compare_graphs(a: dict[str, Any],
                   b: dict[str, Any]) -> dict[str, Any]:
    """Diff two graphs by node id: added/removed/changed (status+data).

    ``changed`` entries carry a bounded field diff (via the shared
    structural diff) so the UI can show *what* moved, not just that
    something did. Edges are compared as a set of triples.
    """
    from .projects import ir_diff

    na = {n["id"]: n for n in a.get("nodes", [])}
    nb = {n["id"]: n for n in b.get("nodes", [])}
    added = sorted(set(nb) - set(na))
    removed = sorted(set(na) - set(nb))
    changed = []
    for nid in sorted(set(na) & set(nb)):
        x, y = na[nid], nb[nid]
        if x.get("status") != y.get("status") or x.get("data") != y.get("data"):
            diff = ir_diff(x.get("data", {}), y.get("data", {}))
            changed.append({"id": nid, "type": y.get("type"),
                            "before_status": x.get("status"),
                            "after_status": y.get("status"),
                            "fields": diff["changed"][:25],
                            "truncated": diff["truncated"] or
                            len(diff["changed"]) > 25})
    ea = {(e["from"], e["predicate"], e["to"]) for e in a.get("edges", [])}
    eb = {(e["from"], e["predicate"], e["to"]) for e in b.get("edges", [])}
    return {"from_run": a.get("run_id"), "to_run": b.get("run_id"),
            "added": added, "removed": removed, "changed": changed,
            "edges_added": sorted(eb - ea), "edges_removed": sorted(ea - eb)}
