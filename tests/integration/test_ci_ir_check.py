# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §11: CI IR check (validate changed IRs + report retest impact).

Wave 12 §7 hardening: renames, deletions, nested layouts, unsafe
paths, unusable bases and summary sanitization (tmp git repos).
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ci_ir_check as ci  # noqa: E402

needs_git = pytest.mark.skipif(shutil.which("git") is None,
                               reason="git not installed")

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


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 0, f"git {args}: {proc.stderr[-500:]}"
    return proc.stdout.strip()


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "examples" / "demo").mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "ci@test")
    _git(root, "config", "user.name", "CI Test")
    _git(root, "config", "commit.gpgsign", "false")
    monkeypatch.setattr(ci, "REPO_ROOT", root)
    return root


def _commit_ir(root: Path, rel: str, doc: dict, message: str) -> str:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    _git(root, "add", rel)
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@needs_git
def test_deleted_ir_with_valid_base_is_neutral(git_repo):
    rel = "examples/demo/machine-ir.json"
    base = _commit_ir(git_repo, rel, _load_amr(), "add IR")
    (git_repo / rel).unlink()
    entry = ci.check_file(rel, base=base)
    assert entry["valid"] is True
    assert entry["status"] == "deleted"


@needs_git
def test_changed_ir_files_reports_deletion(git_repo):
    rel = "examples/demo/machine-ir.json"
    base = _commit_ir(git_repo, rel, _load_amr(), "add IR")
    _git(git_repo, "rm", "-q", rel)
    _git(git_repo, "commit", "-q", "-m", "delete IR")
    found, reason = ci.changed_ir_files(base)
    assert reason == ""
    assert (rel, None, "deleted") in found


@needs_git
def test_renamed_ir_diffs_against_old_path(git_repo):
    old = "examples/demo/old-name.json"
    new = "examples/demo/new-name.json"
    base = _commit_ir(git_repo, old, _load_amr(), "add IR")
    _git(git_repo, "mv", old, new)
    _git(git_repo, "commit", "-q", "-m", "rename IR")
    found, _ = ci.changed_ir_files(base)
    assert (new, old, "renamed") in found
    entry = ci.check_file(new, base=base, old_rel=old)
    assert entry["valid"] is True
    assert entry["status"] == f"renamed from {old} (unchanged)"
    assert entry["renamed_from"] == old


@needs_git
def test_multi_commit_change_detected_with_retest(git_repo):
    rel = "examples/demo/machine-ir.json"
    base = _commit_ir(git_repo, rel, _load_amr(), "add IR")
    doc = _load_amr()
    doc["control"]["max_linear_speed_mps"] = 1.6
    _commit_ir(git_repo, rel, doc, "raise limit")
    doc["control"]["max_linear_speed_mps"] = 1.7
    _commit_ir(git_repo, rel, doc, "raise limit again")
    found, _ = ci.changed_ir_files(base)
    assert [(p, o) for p, o, _ in found] == [(rel, None)]
    entry = ci.check_file(rel, base=base)
    assert entry["status"] == "changed"
    assert entry["retest"] != []
    assert entry["limits_changed"] is True
    assert entry["ir_sha256_before"] != entry["ir_sha256_after"]


@needs_git
def test_unrelated_change_yields_empty_list(git_repo):
    _commit_ir(git_repo, "examples/demo/machine-ir.json", _load_amr(),
               "add IR")
    note = git_repo / "notes.txt"
    note.write_text("hello", encoding="utf-8")
    _git(git_repo, "add", "notes.txt")
    base = _git(git_repo, "rev-parse", "HEAD")
    _git(git_repo, "commit", "-q", "-m", "unrelated")
    found, reason = ci.changed_ir_files(base)
    assert reason == ""
    assert found == []


def test_unsafe_paths_rejected_without_disk_touch(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    for rel in ("../escape.json", "examples/../../x.json",
                "/abs/path.json", "C:/abs/path.json", ""):
        entry = ci.check_file(rel, base=None)
        assert entry["valid"] is False
        assert "unsafe path" in entry["error"]


def test_not_an_ir_skipped_when_never_an_ir(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    data = tmp_path / "data.json"
    data.write_text(json.dumps({"foo": 1}), encoding="utf-8")
    entry = ci.check_file("data.json", base=None)
    assert entry["valid"] is True
    assert entry["status"] == "not an IR (skipped)"


@needs_git
def test_markers_lost_after_valid_base_is_invalid(git_repo):
    rel = "examples/demo/machine-ir.json"
    base = _commit_ir(git_repo, rel, _load_amr(), "add IR")
    (git_repo / rel).write_text(json.dumps({"foo": 1}), encoding="utf-8")
    entry = ci.check_file(rel, base=base)
    assert entry["valid"] is False
    assert "markers lost" in entry["error"]


def test_zero_sha_base_falls_back():
    found, reason = ci.changed_ir_files("0" * 40)
    assert found is None
    assert "does not resolve" in reason


def test_summary_strips_control_characters():
    report = {"verdict": "FAIL",
              "files": [{"path": "a.json", "status": "bad",
                         "error": "line1\n| injected | row |",
                         "retest": ["x\ny"]}]}
    text = ci.render_summary(report)
    assert "\n| injected |" not in text
    assert text.count("\n| `") == 1  # still exactly one table row


def test_nested_ir_layout_found(tmp_path, monkeypatch):
    nested = tmp_path / "examples" / "a" / "b" / "deep.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ci, "REPO_ROOT", tmp_path)
    assert "examples/a/b/deep.json" in ci.all_ir_files()


def test_main_plan_out_writes_valid_plan(tmp_path):
    from genesis_rt.proofos import validate_plan

    out = tmp_path / "report.json"
    plan_out = tmp_path / "plan.json"
    rc = ci.main(["--base", "HEAD", "--out", str(out),
                  "--plan-out", str(plan_out), AMR_IR])
    assert rc == 0
    plan = json.loads(plan_out.read_text(encoding="utf-8"))
    assert validate_plan(plan) == []
    assert plan["release_status"]["eligible"] is False
    assert plan["source_commit"]


@needs_git
def test_main_first_push_base_scans_all(git_repo, tmp_path, monkeypatch):
    _commit_ir(git_repo, "examples/demo/machine-ir.json", _load_amr(),
               "add IR")
    monkeypatch.setenv("GENESIS_CI_BASE", "0" * 40)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    out = tmp_path / "report.json"
    rc = ci.main(["--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["fallback_note"] != ""
    assert report["files"][0]["status"] == "valid (no base diff)"
