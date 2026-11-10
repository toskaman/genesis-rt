# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""One-click BEFORE/AFTER change proof ("Prove my change").

Runs the existing pipeline twice (before IR, after IR), diffs the two
run directories with the existing ``compare`` machinery, re-verifies
both passport chains, and writes one ``verdict.json``. Pure composition
of green paths: no schema, validator, codegen, gate-semantics, or
target changes. When a leg cannot run, the error carries the equivalent
manual commands so the caller can always fall back to today's flow.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .compare import compare_runs
from .evidence import load_passport, verify_chain
from .orchestrator import run_pipeline, valid_run_id

#: Room for the "-before"/"-after" run suffixes inside the 64-char run id cap.
MAX_CHANGE_ID_LEN = 48


def valid_change_id(change_id: str) -> bool:
    """Same fail-closed rule as run ids (single segment, no traversal)."""
    return (valid_run_id(change_id) and len(change_id) <= MAX_CHANGE_ID_LEN)


def manual_commands(before_ir: str | Path, after_ir: str | Path,
                    before_id: str, after_id: str,
                    runs_dir: str | Path) -> list[str]:
    """Equivalent manual flow (today's 3-command Demo C recipe)."""
    runs = Path(runs_dir)
    return [
        f"genesis-rt demo --ir {before_ir}  # note run id, or re-run with an explicit id",
        f"genesis-rt demo --ir {after_ir}",
        f"genesis-rt compare {runs / before_id} {runs / after_id}",
    ]


class ChangeLegError(RuntimeError):
    """One leg of the BEFORE/AFTER pair could not run; no verdict written."""

    def __init__(self, leg: str, ir: str | Path, error: str,
                 fallback: list[str]):
        self.leg = leg
        self.ir = str(ir)
        self.leg_error = error
        self.fallback = list(fallback)
        super().__init__(f"{leg} leg failed for {ir}: {error} "
                         f"(manual fallback: {' ; '.join(fallback)})")


def _run_leg(leg: str, ir_path: str | Path, runs_dir: Path, run_id: str,
             scenarios: list[str] | None,
             fallback: list[str]) -> dict[str, Any]:
    try:
        return run_pipeline(ir_path, runs_dir, run_id=run_id,
                            scenarios=scenarios)
    except Exception as exc:
        raise ChangeLegError(leg, ir_path,
                             f"{type(exc).__name__}: {exc}",
                             fallback) from exc


def verify_change(before_ir: str | Path, after_ir: str | Path,
                  runs_dir: str | Path, changes_dir: str | Path,
                  change_id: str | None = None,
                  scenarios: list[str] | None = None) -> dict[str, Any]:
    """Run BEFORE+AFTER, compare, seal one verdict.json. Returns the verdict.

    ``verdict["verdict"]`` is the after-leg gate verdict (the banner
    answers "is the new revision green?"); the full BEFORE/AFTER gate
    pair, the knob table, and the fixed/broken lists travel in the same
    document. Raises ChangeLegError when a leg cannot run.
    """
    cid = change_id or f"chg-{uuid.uuid4().hex[:12]}"
    if not valid_change_id(cid):
        raise ValueError(f"invalid change_id: {cid!r} "
                         "(ASCII alnum, '-', '_' only, 1..48 chars)")
    runs = Path(runs_dir)
    before_id, after_id = f"{cid}-before", f"{cid}-after"
    fallback = manual_commands(before_ir, after_ir, before_id, after_id, runs)
    before = _run_leg("before", before_ir, runs, before_id, scenarios,
                      fallback)
    after = _run_leg("after", after_ir, runs, after_id, scenarios, fallback)
    comp = compare_runs(before["run_dir"], after["run_dir"])
    chains_valid = {}
    for leg, summary in (("before", before), ("after", after)):
        chains_valid[leg] = not verify_chain(
            load_passport(summary["passport"]))

    def _leg(summary: dict[str, Any]) -> dict[str, Any]:
        gate = summary.get("steps", {}).get("gate", {})
        return {"run_id": summary["run_id"], "run_dir": summary["run_dir"],
                "passport": summary["passport"], "verdict": summary["verdict"],
                "level": summary["level"],
                "release_eligible": summary["release_eligible"],
                "qnx_verified": summary["qnx_verified"],
                # OMEGA7 C banner: sealed gate reasons per leg so
                # the card can banner quarantines (additive key).
                "reasons": list(gate.get("reasons", []))
                if isinstance(gate, dict) else []}

    verdict: dict[str, Any] = {
        "change_id": cid,
        "verdict": after["verdict"],
        "before": _leg(before),
        "after": _leg(after),
        "chains_valid": chains_valid,
        "compare": comp,
        "manual_commands": fallback,
    }
    cdir = Path(changes_dir) / cid
    cdir.mkdir(parents=True, exist_ok=True)
    vpath = cdir / "verdict.json"
    vpath.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
    verdict["verdict_path"] = str(vpath)
    return verdict


def render_card_text(verdict: dict[str, Any]) -> str:
    """Compact one-screen card for the CLI (deterministic)."""
    before, after = verdict["before"], verdict["after"]
    comp = verdict["compare"]
    lines = [f"prove-change: {verdict['change_id']}  "
             f"before={before['run_id']} ({before['verdict']})  "
             f"after={after['run_id']} ({after['verdict']})", ""]
    lim = (comp.get("contract", {}).get("limits_changed", {})
           if comp.get("contract", {}).get("limits_known") else None)
    if lim is None:
        lines.append("contract limits changed: unknown (limits not recorded)")
    else:
        lines.append("contract limits changed: " + (
            ", ".join(f"{k}: {v[0]} -> {v[1]}"
                      for k, v in sorted(lim.items())) or "-"))
    lines.append(f"fixed: {comp['scenarios'].get('fixed') or '-'}")
    lines.append(f"broken: {comp['scenarios'].get('broken') or '-'}")
    gen = comp["generated"]
    lines.append(f"generated changed: {gen['changed'] or '-'}")
    chains = verdict.get("chains_valid", {})
    lines.append("chains: before=" + ("valid" if chains.get("before") else
                                      "INVALID") + " after=" +
                 ("valid" if chains.get("after") else "INVALID"))
    lines.append(f"verdict: {verdict['verdict']}")
    # OMEGA7 C banner: quarantine reasons surface as PHYSICS
    # WARNING lines per leg. The composition pin forbids
    # importing gate here, so this literal mirrors
    # gate.QUARANTINE_PREFIX (drift is caught by the arm-card
    # integration test). Native cards keep zero banner lines.
    for tag in ("before", "after"):
        for reason in verdict.get(tag, {}).get("reasons") or []:
            if isinstance(reason, str) and \
                    reason.startswith("quarantined physics: "):
                lines.append(
                    f"{tag}: PHYSICS WARNING: "
                    + reason[len("quarantined physics: "):])
    if verdict.get("verdict_path"):
        lines.append(f"verdict.json: {verdict['verdict_path']}")
    return "\n".join(lines) + "\n"
