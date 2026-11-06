#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Aggregate anonymized pilot measurement templates (Wave 12 §12).

Input: JSON-lines, one record per (team, task, lane) — the
machine-readable form of docs/business/pilot-study.md §§3-4::

    {"team": "T1", "task": "validate", "lane": "genesis",
     "duration_min": 18.5, "interruptions_min": 0,
     "commands_run": 8, "manual_steps": 2,
     "fault_found": true, "fault_id": "unknown-key",
     "evidence": true, "reviewer_min": 6.0,
     "reviewer_pass": true, "confidence": 4}

Output: aggregate JSON on stdout (also ``--out``). Medians only —
no means over tiny samples, no hour-dollar conversions. Rows that
fail validation abort the run with a line number (fail-closed):
pilot data must never silently shrink.

Honesty rules baked in: ``n_teams < 2`` sets
``comparative_claims: "insufficient"``; per-task lane deltas are
reported with both medians and both n's, never as a single
"X% faster" headline.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

TASKS = ("validate", "generate", "campaign", "evidence", "compare",
         "regression")
LANES = ("genesis", "reference")


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
        rows.append({
            "team": team, "task": task, "lane": lane,
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
        })
        if rows[-1]["confidence"] > 5.0:
            raise ValueError(f"line {line}: confidence must be 1..5")
    if not rows:
        raise ValueError("no data rows")
    return rows


def _med(vals: list[float]) -> float | None:
    return statistics.median(vals) if vals else None


def analyze(rows: list[dict]) -> dict:
    teams = sorted({r["team"] for r in rows})
    tasks: dict[str, dict] = {}
    for task in TASKS:
        per_lane = {}
        for lane in LANES:
            sub = [r for r in rows if r["task"] == task
                   and r["lane"] == lane]
            per_lane[lane] = {
                "n": len(sub),
                "duration_min_median": _med([r["duration_min"]
                                             for r in sub]),
                "reviewer_min_median": _med([r["reviewer_min"]
                                             for r in sub]),
                "commands_median": _med([r["commands_run"] for r in sub]),
                "manual_steps_median": _med([r["manual_steps"]
                                             for r in sub]),
                "fault_found_rate": (sum(r["fault_found"] for r in sub)
                                     / len(sub)) if sub else None,
                "evidence_rate": (sum(r["evidence"] for r in sub)
                                  / len(sub)) if sub else None,
                "reviewer_pass_rate": (sum(r["reviewer_pass"] for r in sub)
                                       / len(sub)) if sub else None,
                "confidence_median": _med([r["confidence"] for r in sub]),
            }
        tasks[task] = per_lane
    return {
        "n_teams": len(teams),
        "teams": teams,
        "n_rows": len(rows),
        "comparative_claims": ("supported-sample"
                               if len(teams) >= 2 else "insufficient"),
        "tasks": tasks,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate pilot JSONL rows.")
    ap.add_argument("input", help="anonymized rows (.jsonl)")
    ap.add_argument("--out", default=None, help="write aggregate JSON here")
    args = ap.parse_args(argv)
    try:
        result = analyze(load_rows(Path(args.input)))
    except (OSError, ValueError) as exc:
        print(f"pilot analysis refused: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
