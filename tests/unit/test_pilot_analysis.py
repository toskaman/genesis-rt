# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the pilot analysis script.

All rows below are SYNTHETIC fixtures for code coverage — not
pilot results. No pilot has been conducted (see
docs/business/pilot-study.md).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "bench" / "productivity" / "analyze_pilot.py"


def _row(team="T1", task="validate", lane="genesis", **over):
    base = {"team": team, "task": task, "lane": lane,
            "duration_min": 10.0, "interruptions_min": 0,
            "commands_run": 5, "manual_steps": 1,
            "fault_found": True, "fault_id": "f1",
            "evidence": True, "reviewer_min": 4.0,
            "reviewer_pass": True, "confidence": 4}
    base.update(over)
    return base


def _write(tmp_path, rows):
    path = tmp_path / "rows.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def _run(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, text=True, timeout=60)


def test_aggregates_two_team_sample(tmp_path):
    rows = [_row("T1", "validate", "genesis", duration_min=10.0),
            _row("T1", "validate", "reference", duration_min=30.0),
            _row("T2", "validate", "genesis", duration_min=14.0,
                 fault_found=False),
            _row("T2", "validate", "reference", duration_min=34.0)]
    proc = _run(_write(tmp_path, rows))
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["n_teams"] == 2
    assert body["comparative_claims"] == "supported-sample"
    lanes = body["tasks"]["validate"]
    assert lanes["genesis"]["duration_min_median"] == 12.0
    assert lanes["reference"]["duration_min_median"] == 32.0
    assert lanes["genesis"]["fault_found_rate"] == 0.5
    assert lanes["reference"]["evidence_rate"] == 1.0


def test_single_team_flagged_insufficient(tmp_path):
    proc = _run(_write(tmp_path, [_row()]))
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["comparative_claims"] == "insufficient"


def test_bad_rows_fail_closed_with_line_numbers(tmp_path):
    good = _row()
    cases = [
        [{**good, "task": "nap"}],
        [{**good, "lane": "chaos"}],
        [{**good, "duration_min": -1}],
        [{**good, "confidence": 9}],
        [{**good, "fault_found": "yes"}],
        [{**good, "team": ""}],
        [good, dict(good)],
    ]
    for rows in cases:
        proc = _run(_write(tmp_path, rows))
        assert proc.returncode == 1, rows
        assert "line" in proc.stderr
    proc = _run(_write(tmp_path, []))
    assert proc.returncode == 1
    assert "no data rows" in proc.stderr
