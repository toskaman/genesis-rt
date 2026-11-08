#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Aggregate pilot measurement rows with paired-data validation (Titan W2).

Input: JSON-lines, one record per (team, task, lane) — the
machine-readable form of docs/business/pilot-study.md §§3-4::

    {"team": "T1", "task": "validate", "lane": "genesis",
     "started_utc": "2026-11-08T10:00:00+00:00",
     "finished_utc": "2026-11-08T10:18:30+00:00",
     "duration_min": 18.5, "interruptions_min": 0,
     "commands_run": 8, "manual_steps": 2,
     "fault_found": true, "fault_id": "unknown-key",
     "evidence": true, "reviewer_min": 6.0,
     "reviewer_pass": true, "confidence": 4,
     "abandoned": false, "operator_kind": "participant",
     "consent": true}

Output: aggregate JSON on stdout (also ``--out``). Medians only —
no means over tiny samples, no hour-dollar conversions. Rows that
fail validation abort the run with a line number (fail-closed):
pilot data must never silently shrink.

Honesty rules baked in:

- A comparison needs PAIRED tasks: the same team completing the same
  task in BOTH lanes. Two teams that each ran one lane are
  INCOMPLETE_PAIRED_DATA, never a supported comparison.
- Owner-operated rows are exploratory only (OWNER_ONLY_EXPLORATORY);
  they never count as independent validation.
- Abandoned tasks are counted separately and excluded from medians.
- Per-task lane deltas report both medians and both n's, never a
  single "X% faster" headline; within-subject paired deltas are the
  comparative statistic.
- ``generalization`` is always INSUFFICIENT_FOR_GENERALIZATION: a
  pilot is not powered for general claims. The paired n is reported
  so a future powered study can size itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

TASKS = ("validate", "generate", "campaign", "evidence", "compare",
         "regression")
LANES = ("genesis", "reference")
PROTOCOL = "pilot-study-v2"

# Sample-validity ladder, weakest to strongest. Order matters: the
# analyzer reports the strongest status the data actually earns.
NO_HUMAN_DATA = "NO_HUMAN_DATA"
OWNER_ONLY_EXPLORATORY = "OWNER_ONLY_EXPLORATORY"
INCOMPLETE_PAIRED_DATA = "INCOMPLETE_PAIRED_DATA"
PAIRED_PILOT_LIMITED = "PAIRED_PILOT_LIMITED"
QUICK_PAIRED_PILOT = "QUICK_PAIRED_PILOT"
INDEPENDENT_PILOT_COMPLETE = "INDEPENDENT_PILOT_COMPLETE"
# Omega3 §6.2: the low-friction tier runs exactly these three
# high-signal tasks in both lanes. QUICK is never equivalent to a
# completed six-task study; the full bar (COMPLETE_TEAMS x all six)
# is unchanged.
QUICK_TASKS = ("generate", "campaign", "evidence")
QUICK_TEAMS = 2
INSUFFICIENT_FOR_GENERALIZATION = "INSUFFICIENT_FOR_GENERALIZATION"

# A complete independent pilot: this many participant teams with every
# task paired. Below this, PAIRED_PILOT_LIMITED.
COMPLETE_TEAMS = 2


def _num(row: dict, key: str, line: int, lo: float = 0.0) -> float:
    val = row.get(key)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"line {line}: {key} must be a number")
    if val < lo:
        raise ValueError(f"line {line}: {key} must be >= {lo}")
    return float(val)


def _bool(row: dict, key: str, line: int) -> bool:
    val = row.get(key)
    if not isinstance(val, bool):
        raise ValueError(f"line {line}: {key} must be true/false")
    return val


def _stamp(row: dict, key: str, line: int) -> dt.datetime:
    raw = row.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"line {line}: {key} must be an ISO timestamp")
    try:
        stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"line {line}: {key} not ISO: {raw!r}") from exc
    if stamp.tzinfo is None:
        raise ValueError(f"line {line}: {key} must carry a timezone")
    return stamp


def load_rows(path: Path) -> list[dict]:
    rows = []
    seen = set()
    for line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(),
                               start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"line {line}: not JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"line {line}: record must be an object")
        team, task, lane = (row.get("team"), row.get("task"),
                            row.get("lane"))
        if not isinstance(team, str) or not team.strip():
            raise ValueError(f"line {line}: team must be a non-empty string")
        if task not in TASKS:
            raise ValueError(f"line {line}: task must be one of {TASKS}")
        if lane not in LANES:
            raise ValueError(f"line {line}: lane must be genesis/reference")
        key = (team, task, lane)
        if key in seen:
            raise ValueError(f"line {line}: duplicate {key}")
        seen.add(key)
        started = _stamp(row, "started_utc", line)
        finished = _stamp(row, "finished_utc", line)
        if finished < started:
            raise ValueError(f"line {line}: finished_utc before started_utc")
        kind = row.get("operator_kind")
        if kind not in ("owner", "participant"):
            raise ValueError(
                f"line {line}: operator_kind must be owner/participant")
        is_owner_team = team.upper().startswith("OWNER")
        if is_owner_team and kind != "owner":
            raise ValueError(
                f"line {line}: OWNER* team must be operator_kind owner")
        if not is_owner_team and kind != "participant":
            raise ValueError(
                f"line {line}: non-OWNER team must be operator_kind "
                "participant")
        consent = _bool(row, "consent", line)
        if kind == "participant" and not consent:
            raise ValueError(
                f"line {line}: participant rows require consent=true; "
                "unconsented data must not be recorded")
        abandoned = _bool(row, "abandoned", line)
        notes = row.get("notes", "")
        if not isinstance(notes, str):
            raise ValueError(f"line {line}: notes must be a string")
        protocol = row.get("protocol")
        if protocol is not None and protocol != PROTOCOL:
            raise ValueError(
                f"line {line}: protocol {protocol!r} is not {PROTOCOL}")
        rows.append({
            "team": team, "task": task, "lane": lane,
            "protocol": protocol,
            "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(),
            "duration_min": _num(row, "duration_min", line),
            "interruptions_min": _num(row, "interruptions_min", line),
            "commands_run": _num(row, "commands_run", line),
            "manual_steps": _num(row, "manual_steps", line),
            "fault_found": _bool(row, "fault_found", line),
            "fault_id": row.get("fault_id"),
            "evidence": _bool(row, "evidence", line),
            "reviewer_min": _num(row, "reviewer_min", line),
            "reviewer_pass": _bool(row, "reviewer_pass", line),
            "confidence": _num(row, "confidence", line, lo=1.0),
            "abandoned": abandoned,
            "operator_kind": kind,
            "consent": consent,
            "notes": notes,
        })
        if rows[-1]["confidence"] > 5.0:
            raise ValueError(f"line {line}: confidence must be 1..5")
    if not rows:
        raise ValueError(f"no data rows ({NO_HUMAN_DATA})")
    return rows


def _med(vals: list[float]) -> float | None:
    return statistics.median(vals) if vals else None


def _rate(vals: list[bool]) -> float | None:
    return (sum(vals) / len(vals)) if vals else None


def analyze(rows: list[dict]) -> dict:
    """Aggregate validated rows; see module docstring for the rules."""
    if not rows:
        return {
            "sample_status": NO_HUMAN_DATA,
            "n_rows": 0,
            "note": "no pilot rows: no human comparison exists",
        }
    teams = sorted({r["team"] for r in rows})
    owners = sorted({r["team"] for r in rows
                     if r["operator_kind"] == "owner"})
    participants = sorted({r["team"] for r in rows
                           if r["operator_kind"] == "participant"})

    def _cell(team: str, task: str, lane: str) -> dict | None:
        for r in rows:
            if (r["team"] == team and r["task"] == task
                    and r["lane"] == lane and not r["abandoned"]):
                return r
        return None

    # Paired cells: same participant team, same task, both lanes done.
    paired: list[dict] = []
    for team in participants:
        for task in TASKS:
            gen, ref = _cell(team, task, "genesis"), _cell(team, task,
                                                           "reference")
            if gen is not None and ref is not None:
                paired.append({
                    "team": team, "task": task,
                    "genesis_min": gen["duration_min"],
                    "reference_min": ref["duration_min"],
                    "delta_min": ref["duration_min"] - gen["duration_min"],
                })
    paired_teams = sorted({p["team"] for p in paired})
    full_teams = [t for t in paired_teams
                  if sum(1 for p in paired if p["team"] == t) == len(TASKS)]
    quick_teams = [t for t in paired_teams
                   if all(any(p["team"] == t and p["task"] == q
                             for p in paired)
                          for q in QUICK_TASKS)]

    if not participants:
        status = OWNER_ONLY_EXPLORATORY
    elif not paired:
        status = INCOMPLETE_PAIRED_DATA
    elif len(full_teams) >= COMPLETE_TEAMS:
        status = INDEPENDENT_PILOT_COMPLETE
    elif len(quick_teams) >= QUICK_TEAMS:
        status = QUICK_PAIRED_PILOT
    else:
        status = PAIRED_PILOT_LIMITED

    tasks: dict[str, dict] = {}
    for task in TASKS:
        per_lane = {}
        for lane in LANES:
            done = [r for r in rows if r["task"] == task
                    and r["lane"] == lane and not r["abandoned"]]
            dropped = sum(1 for r in rows if r["task"] == task
                          and r["lane"] == lane and r["abandoned"])
            per_lane[lane] = {
                "n_completed": len(done),
                "n_abandoned": dropped,
                "duration_min_median": _med([r["duration_min"]
                                             for r in done]),
                "reviewer_min_median": _med([r["reviewer_min"]
                                             for r in done]),
                "commands_median": _med([r["commands_run"] for r in done]),
                "manual_steps_median": _med([r["manual_steps"]
                                             for r in done]),
                "fault_found_rate": _rate([r["fault_found"] for r in done]),
                "evidence_rate": _rate([r["evidence"] for r in done]),
                "reviewer_pass_rate": _rate([r["reviewer_pass"]
                                             for r in done]),
                "confidence_median": _med([r["confidence"] for r in done]),
            }
        tasks[task] = per_lane
    return {
        "protocol": PROTOCOL,
        "sample_status": status,
        "n_rows": len(rows),
        "n_teams": len(teams),
        "teams": teams,
        "owner_teams": owners,
        "participant_teams": participants,
        "n_paired_tasks": len(paired),
        "paired_teams": paired_teams,
        "paired_delta_min_median": _med([p["delta_min"] for p in paired]),
        "paired": paired,
        "generalization": {
            "verdict": INSUFFICIENT_FOR_GENERALIZATION,
            "paired_participant_teams": len(paired_teams),
            "note": "pilot-scale sample by design; powered-study sizing "
                    "needs this n, not a general claim",
        },
        "tasks": tasks,
    }


CSV_COLUMNS = ("protocol", "team", "task", "lane", "started_utc",
               "finished_utc", "duration_min", "abandoned",
               "interruptions_min", "commands_run", "manual_steps",
               "fault_found", "fault_id", "evidence", "reviewer_min",
               "reviewer_pass", "confidence", "operator_kind", "consent",
               "notes")


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if any(c in text for c in (",", '"', "\n", "\r")):
        text = '"' + text.replace('"', '""') + '"'
    return text


def rows_to_csv(rows: list[dict]) -> str:
    """Validated rows as CSV (same data as the JSONL, spreadsheet-safe).

    Only call with rows that passed load_rows: export never cleans or
    imputes, it only re-serializes.
    """
    lines = [",".join(CSV_COLUMNS)]
    for row in rows:
        lines.append(",".join(_csv_cell(row.get(col)) for col in CSV_COLUMNS))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate pilot JSONL rows.")
    ap.add_argument("input", help="anonymized rows (.jsonl)")
    ap.add_argument("--out", default=None, help="write aggregate JSON here")
    ap.add_argument("--to-csv", default=None,
                    help="also write the validated rows as CSV here")
    args = ap.parse_args(argv)
    try:
        rows = load_rows(Path(args.input))
        result = analyze(rows)
    except (OSError, ValueError) as exc:
        print(f"pilot analysis refused: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.to_csv:
        Path(args.to_csv).write_text(rows_to_csv(rows), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
