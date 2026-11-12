# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Causal run: experiment plans, host repro, native grounding, dossier.

Pure composition over green paths: incident intake, deterministic
hypothesis ranking, ``run_pipeline`` host legs, archived Omega2
transcripts (or a live TargetRunner op), K1 ``verify_change`` for the
fix leg, and a sealed dossier document. The dossier spans multiple
runs, so it is a separate hash-sealed file referencing passports
rather than new passport records.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from . import causal
from .causal import rank_hypotheses, scenario_for, verdict_for
from .change import verify_change
from .evidence import load_passport, verify_chain
from .incident import incident_digest, load_incident
from .orchestrator import run_pipeline

DOSSIER_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ARCHIVED_PACK = "evidence/qnx8-x86_64-omega2-before"

TERMINAL_LIVE = ("COMPLETED", "FAILED", "CANCELLED", "BLOCKED",
                 "TIMED_OUT")


class DossierError(ValueError):
    """Dossier invalid, or a causal step cannot run as specified."""


def plan_experiments(ranked: list[dict[str, Any]],
                     machine_kind: str) -> list[dict[str, Any]]:
    """Order ranked hypotheses into experiment plans (rank order)."""
    plans = []
    for order, hyp in enumerate(ranked, start=1):
        hyp_id = hyp["id"]
        table = causal.get_hypothesis(hyp_id) or {}
        scenario = scenario_for(hyp_id, machine_kind)
        kind = ("manifest" if not table.get("scenarios")
                else "faultlab")
        plans.append({"order": order, "hypothesis_id": hyp_id,
                      "scenario": scenario, "experiment_kind": kind,
                      "native_check": table.get("native_check")})
    return plans


def outcome_status(scenario_status: str | None) -> str:
    """Map a faultlab scenario status to an experiment outcome.

    ``crash`` (kind mismatch, harness failure) is ``unsupported``:
    a tooling failure must never read as a reproduced mechanism.
    Unknown statuses fail closed to ``missing``.
    """
    if scenario_status == "pass":
        return "pass"
    if scenario_status == "fail":
        return "fail"
    if scenario_status == "crash":
        return "unsupported"
    return "missing"


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def _canonical(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


#: Location metadata: attached after sealing, never covered by it
#: (same pattern as change.py verdict_path).
_UNSEALED_KEYS = frozenset({"seal", "dossier_path"})


def seal_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    """Hash-seal a dossier in place. Refuses double sealing."""
    if "seal" in dossier:
        raise ValueError("dossier already sealed")
    body = {k: v for k, v in dossier.items()
            if k not in _UNSEALED_KEYS}
    dossier["seal"] = hashlib.sha256(
        _canonical(body).encode("utf-8")).hexdigest()
    return dossier


def _load_dossier_doc(dossier: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(dossier, dict):
        return dossier
    try:
        raw = json.loads(Path(dossier).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DossierError(f"cannot load dossier {dossier}: {exc}")
    if not isinstance(raw, dict):
        raise DossierError(f"dossier {dossier} is not an object")
    return raw


def verify_dossier(dossier: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Fail-closed dossier verification. Never raises for findings."""
    try:
        doc = _load_dossier_doc(dossier)
    except DossierError as exc:
        return {"valid": False, "errors": [str(exc)]}
    errors: list[str] = []
    if doc.get("dossier_version") != DOSSIER_VERSION:
        errors.append("unsupported dossier_version")
    seal = doc.get("seal")
    body = {k: v for k, v in doc.items()
            if k not in _UNSEALED_KEYS}
    expect = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    if not isinstance(seal, str) or seal != expect:
        errors.append("seal mismatch: dossier was modified")
    incident = doc.get("incident", {})
    if isinstance(incident, dict) and "observed" in incident:
        digest = incident.get("digest")
        probe = {k: v for k, v in incident.items() if k != "digest"}
        if incident_digest(probe) != digest:
            errors.append("incident digest mismatch")
    machine = doc.get("machine", {})
    if isinstance(machine, dict) and machine.get("ir_sha256"):
        ipath = machine.get("ir", "")
        try:
            actual = hashlib.sha256(
                Path(ipath).read_bytes()).hexdigest()
        except OSError:
            errors.append("before-IR file missing")
        else:
            if actual != machine["ir_sha256"]:
                errors.append("before-IR hash mismatch")
    for exp in doc.get("experiments", []) or []:
        ground = exp.get("native_grounding")
        if isinstance(ground, dict) and ground.get("transcript_sha256"):
            try:
                tsha = _canon_sha256(Path(ground.get("transcript", "")))
            except OSError:
                errors.append(f"experiment {exp.get('id')}: "
                              "native transcript missing")
            else:
                if tsha != ground["transcript_sha256"]:
                    errors.append(f"experiment {exp.get('id')}: "
                                  "native transcript hash mismatch")
        ppath = exp.get("passport")
        if not ppath:
            continue
        try:
            chain_errors = verify_chain(load_passport(ppath))
        except (OSError, ValueError) as exc:
            errors.append(f"experiment {exp.get('id')}: "
                          f"passport unreadable: {exc}")
            continue
        if chain_errors:
            errors.append(f"experiment {exp.get('id')}: "
                          f"passport chain invalid: {chain_errors[0]}")
    fix = doc.get("fix")
    if isinstance(fix, dict) and fix.get("verdict_path"):
        if not Path(fix["verdict_path"]).exists():
            errors.append("fix verdict.json missing")
    return {"valid": not errors, "errors": errors}


def _resolve(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _fresh_run_id(runs_dir: Path, base: str) -> str:
    candidate = base[:64]
    suffix = 2
    while (runs_dir / candidate / "passport.json").exists():
        tail = f"-r{suffix}"
        candidate = base[:64 - len(tail)] + tail
        suffix += 1
    return candidate


def _passport_scenario(passport_path: str,
                       scenario: str) -> dict[str, Any] | None:
    try:
        passport = load_passport(passport_path)
    except (OSError, ValueError):
        return None
    for record in passport.get("chain", []) or []:
        body = record.get("body", {}) if isinstance(record, dict) else {}
        if (isinstance(body, dict)
                and body.get("scenario") == scenario):
            return body
    return None


def _canon_sha256(path: Path) -> str:
    """sha256 of a transcript with CRLF canonicalized to LF.

    Evidence packs ship LF transcripts (scripts/build_evidence_pack.py);
    hashing the canonical form keeps a live dossier verifiable against
    its published pack on every platform."""
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _ground_archived(native_check: str | None,
                     pack_dir: Path) -> dict[str, Any]:
    if not native_check:
        return {"mode": "archived", "status": "no-native-check",
                "note": "mechanism has no native injector; host only"}
    transcript = (pack_dir / "transcripts"
                  / f"target-{native_check}.log")
    if not transcript.exists():
        return {"mode": "archived", "status": "absent",
                "transcript": str(transcript)}
    digest = _canon_sha256(transcript)
    return {"mode": "archived", "status": "present",
            "transcript": str(transcript),
            "transcript_sha256": digest}


LIVE_WORKFLOW = "full"


def _run_live_op(ir_obj: dict[str, Any], ops_dir: Path,
                 runner_factory: Callable[[], Any] | None,
                 live_params: dict[str, Any],
                 timeout_s: float) -> dict[str, Any]:
    """Run ONE hermetic native op for the whole incident.

    The ``full`` workflow generates, builds and stages this incident's
    own machine binaries before the 16-check matrix runs, so grounding
    never depends on leftovers from an earlier campaign. One QEMU boot
    serves every hypothesis (each reads its own check from the record).
    """
    if runner_factory is None:
        from .target import TargetRunner

        def _default() -> Any:
            return TargetRunner(ops_dir)

        runner_factory = _default
    runner = runner_factory()
    params = dict(live_params)
    params["ir"] = ir_obj
    t0 = time.monotonic()
    try:
        rec = runner.start(LIVE_WORKFLOW, params)
    except Exception as exc:
        return {"mode": "live", "status": "start-failed",
                "workflow": LIVE_WORKFLOW,
                "error": f"{type(exc).__name__}: {exc}"}
    op_id = rec.get("op_id", "")
    deadline = t0 + timeout_s
    state: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        state = runner.get(op_id)
        if state is None or state.get("state") in TERMINAL_LIVE:
            break
        time.sleep(2)
    elapsed = round(time.monotonic() - t0, 1)
    base = {"mode": "live", "workflow": LIVE_WORKFLOW, "op_id": op_id,
            "op_seconds": elapsed}
    if state is None:
        return {**base, "status": "unknown"}
    if state.get("state") not in TERMINAL_LIVE:
        cancel = getattr(runner, "cancel", None)
        if callable(cancel):
            try:
                cancel(op_id)
            except Exception:
                pass
        return {**base, "status": "timeout", "state": state.get("state")}
    artifacts = state.get("artifacts", {}) or {}
    if state.get("state") != "COMPLETED":
        return {**base, "status": "op-failed", "state": state.get("state"),
                "reason": state.get("reason", "")}
    out = {**base, "status": "completed", "state": "COMPLETED",
           "passport": artifacts.get("passport", ""),
           "verdict": artifacts.get("verdict"),
           "qnx_verified": artifacts.get("qnx_verified"),
           "target_dir": artifacts.get("target_dir", "")}
    record: dict[str, Any] | None = None
    tdir = artifacts.get("target_dir")
    if tdir:
        rpath = Path(tdir) / "qnx-target-record.json"
        try:
            record = json.loads(rpath.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record = None
    out["_record"] = record
    return out


def _ground_from_live(native_check: str | None,
                      live: dict[str, Any] | None) -> dict[str, Any]:
    """Per-hypothesis grounding read from the single live op.

    ``present`` only when the op COMPLETED, the target record lists the
    hypothesis's native check as passed on QNX, and its transcript file
    exists (sha256 recorded). Anything else is reported as it is.
    """
    if not native_check:
        return {"mode": "live", "status": "no-native-check",
                "note": "mechanism has no native injector; host only"}
    if live is None:
        return {"mode": "live", "status": "not-run",
                "native_check": native_check}
    public = {k: v for k, v in live.items() if not k.startswith("_")}
    if live.get("status") != "completed":
        return {**public, "native_check": native_check}
    record = live.get("_record")
    if not isinstance(record, dict):
        return {**public, "status": "no-record",
                "native_check": native_check}
    check = next((c for c in record.get("checks", []) or []
                  if isinstance(c, dict)
                  and c.get("name") == native_check), None)
    if check is None:
        return {**public, "status": "absent", "native_check": native_check}
    transcript = Path(live.get("target_dir", "")) / \
        f"target-{native_check}.log"
    grounding = {**public, "native_check": native_check,
                 "check_passed": bool(check.get("passed")),
                 "verified_on_target": record.get("verified_on_target"),
                 "transcript": str(transcript)}
    if transcript.is_file():
        grounding["transcript_sha256"] = _canon_sha256(transcript)
    if not check.get("passed"):
        grounding["status"] = "check-failed"
    elif "transcript_sha256" not in grounding:
        grounding["status"] = "absent"
    else:
        grounding["status"] = "present"
    return grounding


def _machine_kind(ir_path: Path) -> str:
    try:
        raw = json.loads(ir_path.read_text(encoding="utf-8"))
        return str(raw["machine"]["kind"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DossierError(f"cannot read machine kind from {ir_path}: "
                           f"{exc}") from exc


def reproduce(incident_path: str | Path, runs_dir: str | Path,
              dossiers_dir: str | Path, target: str = "archived",
              machine_ir: str | Path | None = None,
              only: list[str] | None = None,
              pack_dir: str | Path | None = None,
              runner_factory: Callable[[], Any] | None = None,
              live_params: dict[str, Any] | None = None,
              live_timeout_s: float = 900) -> dict[str, Any]:
    """Run steps 1-6: intake, rank, host repro, native grounding, seal."""
    if target not in ("archived", "live"):
        raise DossierError(f"unknown target mode: {target!r}")
    incident = load_incident(incident_path)
    ir_path = _resolve(machine_ir or incident["machine_ir"])
    kind = _machine_kind(ir_path)
    try:
        ir_bytes = ir_path.read_bytes()
    except OSError as exc:
        raise DossierError(f"cannot read IR {ir_path}: {exc}") from exc
    ranked = rank_hypotheses(incident)
    if only is not None:
        wanted = set(only)
        ranked = [h for h in ranked if h["id"] in wanted]
        unknown = wanted - {h["id"] for h in ranked}
        if unknown:
            raise DossierError(f"unknown hypotheses: {sorted(unknown)}")
    plans = plan_experiments(ranked, kind)
    runs = Path(runs_dir)
    pack = Path(pack_dir) if pack_dir else REPO_ROOT / ARCHIVED_PACK
    inc_id = incident["incident_id"]
    hypotheses: list[dict[str, Any]] = []
    experiments: list[dict[str, Any]] = []
    live: dict[str, Any] | None = None
    for plan in plans:
        hyp_id = plan["hypothesis_id"]
        scenario = plan["scenario"]
        exp_id = f"exp-{plan['order']:02d}-{hyp_id}"
        outcome = "missing"
        note = ""
        run_id = ""
        passport = ""
        seed: Any = None
        checks_failed: list[str] = []
        if scenario is None:
            if plan["experiment_kind"] == "manifest":
                note = ("staged-vs-manifest check not wired in this "
                        "slice; native grounding only")
            else:
                note = "no host scenario for this machine kind"
        else:
            run_id = _fresh_run_id(runs, f"{inc_id}-e{plan['order']:02d}")
            try:
                summary = run_pipeline(ir_path, runs, run_id=run_id,
                                       scenarios=[scenario])
            except Exception as exc:
                outcome = "missing"
                note = f"pipeline error: {type(exc).__name__}: {exc}"
            else:
                scen = (summary.get("steps", {}).get("verification", {})
                        .get("scenarios", {}).get(scenario))
                outcome = outcome_status(scen)
                passport = summary.get("passport", "")
                record = (_passport_scenario(passport, scenario)
                          if passport else None)
                if record is not None:
                    seed = record.get("seed")
                    checks_failed = [c.get("name", "?")
                                     for c in record.get("checks", []) or []
                                     if isinstance(c, dict)
                                     and not c.get("passed", True)]
        if target == "live":
            if live is None and plan["native_check"]:
                live = _run_live_op(
                    json.loads(ir_bytes.decode("utf-8")),
                    dossiers_dir_run(runs), runner_factory,
                    dict(live_params or {}), live_timeout_s)
            grounding = _ground_from_live(plan["native_check"], live)
        else:
            grounding = _ground_archived(plan["native_check"], pack)
        verdict = verdict_for(hyp_id, {"status": outcome}, incident)
        ranked_entry = next(h for h in ranked if h["id"] == hyp_id)
        hypotheses.append(
            {"id": hyp_id, "cause": ranked_entry["cause"],
             "mechanism": ranked_entry["mechanism"],
             "rank": ranked_entry["rank"],
             "matched_signals": ranked_entry["matched_signals"],
             "verdict": verdict, "experiment_id": exp_id})
        experiments.append(
            {"id": exp_id, "hypothesis_id": hyp_id,
             "scenario": scenario, "seed": seed, "run_id": run_id,
             "passport": passport, "outcome": outcome, "note": note,
             "checks_failed": checks_failed,
             "native_grounding": grounding})
    winner = next((h["id"] for h in hypotheses
                   if h["verdict"] == "SUPPORTED"), None)
    counts: dict[str, int] = {}
    for h in hypotheses:
        counts[h["verdict"]] = counts.get(h["verdict"], 0) + 1
    ddir = Path(dossiers_dir) / inc_id
    ddir.mkdir(parents=True, exist_ok=True)
    before_ir = ddir / "before-ir.json"
    before_ir.write_bytes(ir_bytes)
    dossier: dict[str, Any] = {
        "dossier_version": DOSSIER_VERSION,
        "incident": {**incident,
                     "digest": incident_digest(incident)},
        "machine": {"ir": str(before_ir), "kind": kind,
                    "ir_sha256": hashlib.sha256(ir_bytes).hexdigest()},
        "hypotheses": hypotheses,
        "experiments": experiments,
        "causality": {"winning_hypothesis": winner,
                      "conclusive": winner is not None,
                      "verdict_counts": counts},
        "target_mode": target,
        "created_utc": _utc_now(),
    }
    if target == "live":
        dossier["native_op"] = (
            {k: v for k, v in live.items() if not k.startswith("_")}
            if live is not None else {"status": "not-run",
                                      "note": "no hypothesis has a "
                                              "native check"})
    seal_dossier(dossier)
    (ddir / "dossier.json").write_text(
        json.dumps(dossier, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    dossier["dossier_path"] = str(ddir)
    return dossier


def dossiers_dir_run(runs_dir: str | Path) -> Path:
    """Sibling ops dir for live target runs (kept out of runs/)."""
    ops = Path(runs_dir).parent / "target-ops"
    ops.mkdir(parents=True, exist_ok=True)
    return ops


def verify_fix(dossier_dir: str | Path, after_ir: str | Path,
               runs_dir: str | Path, changes_dir: str | Path,
               scenarios: list[str] | None = None) -> dict[str, Any]:
    """Append a K1 BEFORE/AFTER fix proof to a sealed dossier + reseal."""
    ddir = Path(dossier_dir)
    doc = _load_dossier_doc(ddir / "dossier.json")
    checked = verify_dossier(doc)
    if not checked["valid"]:
        raise DossierError(f"dossier invalid: {checked['errors'][0]}")
    before_ir = _resolve(doc["machine"]["ir"])
    if scenarios is None:
        winner = (doc.get("causality", {}) or {}).get(
            "winning_hypothesis")
        scenarios = [e["scenario"] for e in doc.get("experiments", [])
                     if e.get("hypothesis_id") == winner
                     and e.get("scenario")]
    inc_id = doc["incident"]["incident_id"]
    change_id = f"{inc_id}-fix-{uuid.uuid4().hex[:6]}"
    verdict = verify_change(before_ir, after_ir, runs_dir, changes_dir,
                            change_id=change_id,
                            scenarios=scenarios or None)
    old_seal = doc["seal"]
    updated = copy.deepcopy(doc)
    updated.pop("seal", None)
    updated["fix"] = {"change_id": change_id,
                      "verdict": verdict["verdict"],
                      "before_verdict": verdict["before"]["verdict"],
                      "after_verdict": verdict["after"]["verdict"],
                      "verdict_path": verdict["verdict_path"]}
    updated["supersedes"] = old_seal
    seal_dossier(updated)
    (ddir / "dossier.json").write_text(
        json.dumps(updated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    updated["dossier_path"] = str(ddir)
    return updated
