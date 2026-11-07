# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""The pilot timer records clock readings and answers, in the format
analyze_pilot.py accepts — no estimation, no invented values."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench" / "productivity"))

from analyze_pilot import analyze, load_rows  # noqa: E402
from pilot_timer import run_task  # noqa: E402


def test_row_is_measured_and_analyzable(tmp_path):
    answers = iter(["", "", "0", "7", "2", "y", "unknown-key", "y", "3.5", "y", "4", "ok"])
    ticks = iter([100.0, 100.0 + 9 * 60])
    stamps = iter(["2026-11-07T17:00:00+00:00", "2026-11-07T17:09:00+00:00"])
    row = run_task("OWNER", "genesis", "validate", read=lambda _p: next(answers),
                   clock=lambda: next(ticks), now=lambda: next(stamps))
    assert row["duration_min"] == 9.0
    assert row["operator_kind"] == "owner"
    assert row["fault_id"] == "unknown-key"
    f = tmp_path / "d.jsonl"
    f.write_text(json.dumps(row) + "\n", encoding="utf-8")
    rep = analyze(load_rows(f))
    assert rep["comparative_claims"] == "insufficient"


def test_invalid_answers_are_reasked():
    answers = iter(["", "", "x", "0", "seven", "7", "2", "maybe", "n", "", "n", "0", "n", "9", "3", ""])
    ticks = iter([0.0, 60.0])
    row = run_task("T1", "reference", "generate", read=lambda _p: next(answers),
                   clock=lambda: next(ticks), now=lambda: "t")
    assert (row["commands_run"], row["fault_found"], row["confidence"]) == (7, False, 3.0)
