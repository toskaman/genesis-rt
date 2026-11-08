#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Interactive pilot session timer (Titan W2, impact workstream).

Walks one operator through the six pilot tasks of
docs/business/pilot-study.md §2 in one lane, timestamps start/stop in
UTC, asks the §3/§4 template questions, and appends one JSON line per
task in exactly the format analyze_pilot.py validates. Nothing is
estimated: every number is either a clock reading or the operator's
own answer. Raw lines are appended, never rewritten.

Abandoned tasks are recorded WITH abandoned=true (never silently
dropped, never counted as completions). Participant (non-OWNER) rows
require explicit consent at record time; declining consent records
nothing for that task.

  python bench/productivity/pilot_timer.py --team OWNER --lane genesis \
      --out bench/productivity/data/owner-2026-11.jsonl
  python bench/productivity/analyze_pilot.py bench/productivity/data/owner-2026-11.jsonl

Label owner-operated data as such: it is NOT independent validation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_pilot import LANES, PROTOCOL, TASKS, load_rows  # noqa: E402

PROMPTS = {
    "validate": "Accept/reject 3 machine contracts (1 unknown key, 1 limit violation).",
    "generate": "Produce build files for the AMR IR; confirm the guard limit in the header.",
    "campaign": "Run the 8-scenario fault campaign; state the verdict per scenario.",
    "evidence": "Hand a reviewer a package proving the verdict; reviewer verifies alone.",
    "compare": "Given two runs (limit 0.5 -> 0.05), state what changed and if release is OK.",
    "regression": "Reproduce the stale-proximity failure, apply the fix, confirm green.",
}


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _ask(prompt: str, kind: type, read=input, lo=None, hi=None):
    while True:
        raw = read(prompt).strip()
        try:
            if kind is not bool:
                val = kind(raw)
                if (lo is not None and val < lo) or (hi is not None and val > hi):
                    raise ValueError
                return val
            if kind is bool:
                if raw.lower() in ("y", "yes", "true", "1"):
                    return True
                if raw.lower() in ("n", "no", "false", "0"):
                    return False
                raise ValueError
        except ValueError:
            print("  invalid answer, try again")


def run_task(team: str, lane: str, task: str, read=input, clock=time.monotonic,
             now=_utc) -> dict | None:
    print(f"\n== {task} ({lane}) — {PROMPTS[task]}")
    kind = "owner" if team.upper().startswith("OWNER") else "participant"
    read("Press Enter to START the clock... ")
    t0, started = clock(), now()
    read("Press Enter when the task is DONE (or abandoned)... ")
    t1, finished = clock(), now()
    abandoned = _ask("  abandoned before finishing? (y/n): ", bool, read)
    if kind == "participant":
        consent = _ask("  consent to anonymized use of this record? (y/n): ",
                       bool, read)
        if not consent:
            print("  consent declined: nothing recorded for this task")
            return None
    row = {
        "protocol": PROTOCOL,
        "team": team, "task": task, "lane": lane,
        "started_utc": started, "finished_utc": finished,
        "duration_min": round((t1 - t0) / 60.0, 2),
        "abandoned": abandoned,
        "interruptions_min": _ask("  interruptions (minutes): ", float, read, lo=0),
        "commands_run": _ask("  commands run (count from shell history): ", int, read, lo=0),
        "manual_steps": _ask("  manual steps (count): ", int, read, lo=0),
        "fault_found": _ask("  fault found? (y/n): ", bool, read),
        "fault_id": read("  fault id (blank if none): ").strip() or None,
        "evidence": _ask("  evidence package produced? (y/n): ", bool, read),
        "reviewer_min": _ask("  reviewer minutes (0 if none): ", float, read, lo=0),
        "reviewer_pass": _ask("  reviewer verified it? (y/n): ", bool, read),
        "confidence": _ask("  your confidence 1-5: ", float, read, lo=1, hi=5),
        "notes": read("  notes: ").strip(),
        "operator_kind": kind,
        "consent": True,
    }
    return row


def plan_session(team: str, seed: int | None = None) -> dict:
    """Randomize which lane the team runs first (counterbalancing).

    Pure function of (team, seed): the same seed replays the same
    order. The plan ships next to the JSONL rows; pairing validation
    is order-agnostic, but the recorded order proves the lanes were
    counterbalanced instead of always genesis-first.
    """
    rng = random.Random(seed)
    order = list(LANES)
    rng.shuffle(order)
    return {"protocol": PROTOCOL, "type": "session-plan", "team": team,
            "lane_order": order, "seed": seed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--team", required=True, help="anonymous id, e.g. OWNER or T1")
    ap.add_argument("--lane", choices=LANES,
                    help="lane to time (not needed with --plan)")
    ap.add_argument("--out", help="JSONL rows file (not needed with --plan)")
    ap.add_argument("--tasks", nargs="*", default=list(TASKS), choices=TASKS)
    ap.add_argument("--plan", action="store_true",
                    help="print the randomized lane order for --team and exit")
    ap.add_argument("--seed", type=int, default=None,
                    help="plan RNG seed (replays the same order)")
    ap.add_argument("--plan-out", default=None,
                    help="write the session plan JSON here (else stdout)")
    a = ap.parse_args(argv)
    if a.plan:
        plan = plan_session(a.team, a.seed)
        text = json.dumps(plan, indent=2, sort_keys=True)
        if a.plan_out:
            Path(a.plan_out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if not a.lane or not a.out:
        ap.error("--lane and --out are required (unless --plan)")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for task in a.tasks:
        row = run_task(a.team, a.lane, task)
        if row is None:  # consent declined: nothing recorded
            continue
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        load_rows(out)  # fail-closed: the file must stay analyzable
        print(f"  recorded {task}: {row['duration_min']} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
