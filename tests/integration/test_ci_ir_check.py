# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §11: CI IR check (validate changed IRs + report retest impact)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ci_ir_check as ci  # noqa: E402

AMR_IR = "examples/amr-demo/machine-ir.json"


def _load_amr() -> dict:
    return json.loads((REPO_ROOT / AMR_IR).read_text(encoding="utf-8"))


def _entry() -> dict:
    return {"path": AMR_IR, "valid": True, "error": "", "status": "",
            "retest": [], "limits_changed": False,
            "requirements_changed": 0}


def test_diff_entry_unchanged_reports_no_retest():
    doc = _load_amr()
    entry = _entry()
    ci.diff_entry(entry, copy.deepcopy(doc), doc)
    assert entry["status"] == "unchanged"
    assert entry["retest"] == []
    assert entry["limits_changed"] is False


def test_diff_entry_limit_change_reports_retest():
    before = _load_amr()
    after = copy.deepcopy(before)
    after["control"]["max_linear_speed_mps"] = 1.6  # W11 BEFORE/AFTER pair
    entry = _entry()
    ci.diff_entry(entry, before, after)
    assert entry["status"] == "changed"
    assert entry["retest"] != []  # conservative: every scenario re-runs
    assert entry["limits_changed"] is True


def test_diff_entry_garbage_before_stays_fail_closed():
    entry = _entry()
    ci.diff_entry(entry, {"schema_version": 1}, _load_amr())
    assert entry["status"].startswith("valid (base uncomparable")


def test_check_file_missing_reports_unreadable():
    entry = ci.check_file("examples/amr-demo/no-such.json", base="HEAD")
    assert entry["valid"] is False
    assert "not found" in entry["error"]


def test_check_file_bad_json_reports_invalid(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    entry = ci.check_file("bad.json", base=None)
    assert entry["valid"] is False
    assert "not valid JSON" in entry["error"]


def test_check_file_bad_ir_reports_invalid(tmp_path, monkeypatch):
    bad = tmp_path / "bad-ir.json"
    bad.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    entry = ci.check_file("bad-ir.json", base=None)
    assert entry["valid"] is False
    assert "IR validation failed" in entry["error"]


def test_check_file_known_good_is_valid_unchanged():
    entry = ci.check_file(AMR_IR, base="HEAD")
    assert entry["valid"] is True
    assert entry["status"] == "unchanged"
    assert entry["retest"] == []


def test_changed_ir_files_bad_base_falls_back():
    found, reason = ci.changed_ir_files("no-such-ref-zzz-genesis")
    assert found is None
    assert "does not resolve" in reason


def test_all_ir_files_finds_examples():
    found = ci.all_ir_files()
    assert AMR_IR in found
    assert len(found) >= 6


def test_main_exit_codes(tmp_path, monkeypatch, capsys):
    out = tmp_path / "report.json"
    rc = ci.main(["--base", "HEAD", "--out", str(out), AMR_IR])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "PASS"
    assert report["files"][0]["status"] == "unchanged"
    capsys.readouterr()

    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    rc = ci.main(["--out", str(out), "bad.json"])
    assert rc == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"


def test_main_writes_step_summary(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    out = tmp_path / "report.json"
    rc = ci.main(["--base", "HEAD", "--out", str(out), AMR_IR])
    assert rc == 0
    text = summary.read_text(encoding="utf-8")
    assert "GENESIS IR check" in text
    assert AMR_IR in text
    assert "release eligibility" in text  # honest scope disclaimer
