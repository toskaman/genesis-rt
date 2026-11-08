# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Titan W2: pilot paired-data validation (no human data is fabricated).

Covers analyze_pilot.py's sample-validity ladder and pilot_timer.py's
consent/abandoned record paths with synthetic rows only.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest


def _load(repo_root, name):
    spec = importlib.util.spec_from_file_location(
        f"pilot_{name}_under_test",
        repo_root / "bench" / "productivity" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def ap(repo_root):
    return _load(repo_root, "analyze_pilot")


@pytest.fixture()
def pt(repo_root):
    return _load(repo_root, "pilot_timer")


def _row(team, task, lane, **kw):
    base = {
        "team": team, "task": task, "lane": lane,
        "started_utc": "2026-11-08T10:00:00+00:00",
        "finished_utc": "2026-11-08T10:10:00+00:00",
        "duration_min": 10.0, "interruptions_min": 0,
        "commands_run": 5, "manual_steps": 1,
        "fault_found": True, "fault_id": "x",
        "evidence": True, "reviewer_min": 2.0,
        "reviewer_pass": True, "confidence": 4,
        "abandoned": False,
        "operator_kind": ("owner" if team.upper().startswith("OWNER")
                          else "participant"),
        "consent": True,
    }
    base.update(kw)
    return base


def _write(tmp_path, rows):
    p = tmp_path / "pilot.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                 encoding="utf-8")
    return p


# -- sample-validity ladder --------------------------------------------

def test_empty_is_no_human_data(ap, tmp_path):
    assert ap.analyze([])["sample_status"] == ap.NO_HUMAN_DATA
    p = tmp_path / "empty.jsonl"
    p.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="NO_HUMAN_DATA"):
        ap.load_rows(p)
    assert ap.main([str(p)]) == 1


def test_owner_only_never_comparative(ap, tmp_path):
    rows = [_row("OWNER", t, lane) for t in ap.TASKS for lane in ap.LANES]
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.OWNER_ONLY_EXPLORATORY
    assert out["n_paired_tasks"] == 0
    assert out["paired"] == []


def test_two_single_lane_teams_are_incomplete(ap, tmp_path):
    # THE flaw case: old code reported "supported-sample" here.
    rows = ([_row("T1", t, "genesis") for t in ap.TASKS]
            + [_row("T2", t, "reference") for t in ap.TASKS])
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.INCOMPLETE_PAIRED_DATA
    assert out["n_teams"] == 2
    assert out["paired_delta_min_median"] is None


def test_single_paired_task_is_limited(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis", duration_min=8.0),
            _row("T1", "validate", "reference", duration_min=20.0)]
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.PAIRED_PILOT_LIMITED
    assert out["n_paired_tasks"] == 1
    assert out["paired"] == [{"team": "T1", "task": "validate",
                              "genesis_min": 8.0, "reference_min": 20.0,
                              "delta_min": 12.0}]
    assert out["paired_delta_min_median"] == 12.0


def test_two_full_teams_are_complete(ap, tmp_path):
    rows = [_row(team, t, lane, duration_min=10.0 if lane == "genesis" else 15.0)
            for team in ("T1", "T2") for t in ap.TASKS
            for lane in ap.LANES]
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.INDEPENDENT_PILOT_COMPLETE
    assert out["n_paired_tasks"] == 12
    assert out["paired_delta_min_median"] == 5.0


# -- quick tier (Omega3 §6.2) --------------------------------------------

def _quick_rows(team, lanes=("genesis", "reference")):
    return [_row(team, t, lane)
            for t in ("generate", "campaign", "evidence")
            for lane in lanes]


def test_two_quick_teams_are_quick_paired(ap, tmp_path):
    rows = _quick_rows("T1") + _quick_rows("T2")
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.QUICK_PAIRED_PILOT
    assert out["n_paired_tasks"] == 6
    assert out["generalization"]["verdict"] == (
        ap.INSUFFICIENT_FOR_GENERALIZATION)


def test_quick_plus_extras_is_still_not_full(ap, tmp_path):
    # Two teams pair the quick three plus two extra tasks each, but
    # neither pairs all six: QUICK, never COMPLETE.
    rows = (_quick_rows("T1") + _quick_rows("T2")
            + [_row("T1", t, lane) for t in ("validate", "compare")
               for lane in ("genesis", "reference")]
            + [_row("T2", t, lane) for t in ("validate", "regression")
               for lane in ("genesis", "reference")])
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["sample_status"] == ap.QUICK_PAIRED_PILOT


def test_single_quick_team_is_limited(ap, tmp_path):
    out = ap.analyze(ap.load_rows(_write(tmp_path, _quick_rows("T1"))))
    assert out["sample_status"] == ap.PAIRED_PILOT_LIMITED


def test_quick_subset_is_exactly_three_tasks(ap):
    assert tuple(ap.QUICK_TASKS) == ("generate", "campaign", "evidence")
    assert set(ap.QUICK_TASKS) < set(ap.TASKS)


def test_timer_quick_flag_selects_quick_tasks(pt):
    ns = pt.build_parser().parse_args(["--team", "T1", "--quick"])
    assert ns.tasks == ["generate", "campaign", "evidence"]


def test_generalization_always_insufficient(ap, tmp_path):
    rows = [_row(team, t, lane)
            for team in ("T1", "T2") for t in ap.TASKS
            for lane in ap.LANES]
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    assert out["generalization"]["verdict"] == (
        ap.INSUFFICIENT_FOR_GENERALIZATION)
    assert out["generalization"]["paired_participant_teams"] == 2


# -- abandoned / validation ---------------------------------------------

def test_abandoned_excluded_from_medians_but_counted(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis", duration_min=8.0),
            _row("T1", "validate", "reference", duration_min=999.0,
                 abandoned=True),
            _row("T2", "validate", "reference", duration_min=20.0)]
    out = ap.analyze(ap.load_rows(_write(tmp_path, rows)))
    ref = out["tasks"]["validate"]["reference"]
    assert ref["n_completed"] == 1
    assert ref["n_abandoned"] == 1
    assert ref["duration_min_median"] == 20.0
    # T1's pair is broken by the abandonment: nothing paired
    assert out["sample_status"] == ap.INCOMPLETE_PAIRED_DATA


def test_participant_without_consent_refused(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis", consent=False)]
    with pytest.raises(ValueError, match="consent"):
        ap.load_rows(_write(tmp_path, rows))


def test_owner_team_must_be_owner_kind(ap, tmp_path):
    rows = [_row("OWNER", "validate", "genesis",
                 operator_kind="participant")]
    with pytest.raises(ValueError, match="OWNER"):
        ap.load_rows(_write(tmp_path, rows))
    rows = [_row("T1", "validate", "genesis", operator_kind="owner")]
    with pytest.raises(ValueError, match="participant"):
        ap.load_rows(_write(tmp_path, rows))


def test_bad_timestamps_refused(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis",
                 finished_utc="2026-11-08T09:00:00+00:00")]
    with pytest.raises(ValueError, match="before started"):
        ap.load_rows(_write(tmp_path, rows))
    rows = [_row("T1", "validate", "genesis", started_utc="not-a-time")]
    with pytest.raises(ValueError, match="not ISO"):
        ap.load_rows(_write(tmp_path, rows))
    rows = [_row("T1", "validate", "genesis",
                 started_utc="2026-11-08T10:00:00")]
    with pytest.raises(ValueError, match="timezone"):
        ap.load_rows(_write(tmp_path, rows))


def test_duplicate_still_refused(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis"),
            _row("T1", "validate", "genesis")]
    with pytest.raises(ValueError, match="duplicate"):
        ap.load_rows(_write(tmp_path, rows))


def test_cli_writes_out_file(ap, tmp_path):
    rows = [_row("OWNER", "validate", "genesis")]
    src = _write(tmp_path, rows)
    dst = tmp_path / "agg.json"
    assert ap.main([str(src), "--out", str(dst)]) == 0
    assert json.loads(dst.read_text(encoding="utf-8"))["sample_status"] == (
        ap.OWNER_ONLY_EXPLORATORY)


def test_cli_subprocess_end_to_end(repo_root, tmp_path):
    script = (repo_root / "bench" / "productivity" / "analyze_pilot.py")
    rows = [_row("T1", "validate", "genesis", duration_min=10.0),
            _row("T1", "validate", "reference", duration_min=30.0)]
    src = _write(tmp_path, rows)
    proc = subprocess.run([sys.executable, str(script), str(src)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["sample_status"] == "PAIRED_PILOT_LIMITED"
    lanes = body["tasks"]["validate"]
    assert lanes["genesis"]["duration_min_median"] == 10.0
    assert lanes["reference"]["duration_min_median"] == 30.0
    bad = _write(tmp_path, [{**_row("T1", "validate", "genesis"),
                             "duration_min": -1}])
    proc = subprocess.run([sys.executable, str(script), str(bad)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 1
    assert "line 1" in proc.stderr


# -- timer ---------------------------------------------------------------

def _scripted(answers):
    it = iter(answers)
    return lambda prompt="": next(it)


def test_timer_consent_decline_records_nothing(pt):
    read = _scripted(["", "", "n", "n"])  # start, done, kept?, no consent
    assert pt.run_task("T1", "genesis", "validate", read=read,
                       clock=lambda: 0.0,
                       now=lambda: "2026-11-08T10:00:00+00:00") is None


def test_timer_abandoned_flag_recorded(pt):
    read = _scripted(["", "", "y", "0", "3", "1", "y", "fid",
                      "y", "1", "y", "4", "gave up"])
    row = pt.run_task("OWNER", "reference", "validate", read=read,
                      clock=lambda: 0.0,
                      now=lambda: "2026-11-08T10:00:00+00:00")
    assert row is not None
    assert row["abandoned"] is True
    assert row["operator_kind"] == "owner"
    assert row["consent"] is True
    assert row["protocol"] == "pilot-study-v2"


def test_timer_row_passes_analyzer(pt, ap, tmp_path):
    read = _scripted(["", "", "n", "y", "0", "3", "1", "y", "fid",
                      "y", "1", "y", "4", "ok"])
    ticks = iter([100.0, 700.0])
    row = pt.run_task("T9", "genesis", "generate", read=read,
                      clock=lambda: next(ticks),
                      now=lambda: "2026-11-08T10:00:00+00:00")
    assert row["duration_min"] == 10.0
    loaded = ap.load_rows(_write(tmp_path, [row]))
    assert loaded[0]["team"] == "T9"
    assert ap.analyze(loaded)["sample_status"] == ap.INCOMPLETE_PAIRED_DATA


def test_session_plan_covers_both_lanes_and_replays(pt):
    plan = pt.plan_session("T1", seed=7)
    assert sorted(plan["lane_order"]) == ["genesis", "reference"]
    assert plan["team"] == "T1" and plan["seed"] == 7
    assert pt.plan_session("T1", seed=7) == plan
    orders = {tuple(pt.plan_session("T%d" % i, seed=i)["lane_order"])
              for i in range(20)}
    assert len(orders) == 2  # both orders occur: real counterbalancing


def test_csv_export_reserializes_validated_rows(ap, tmp_path):
    rows = [_row("T1", "validate", "genesis", notes='a, "quoted" note'),
            _row("T1", "validate", "reference", fault_id=None)]
    text = ap.rows_to_csv(ap.load_rows(_write(tmp_path, rows)))
    lines = text.splitlines()
    assert lines[0].split(",")[:4] == ["protocol", "team", "task", "lane"]
    assert len(lines) == 3
    assert '"a, ""quoted"" note"' in lines[1]
    import csv
    parsed = list(csv.reader(lines))
    assert parsed[2][parsed[0].index("fault_id")] == ""
