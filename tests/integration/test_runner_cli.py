# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: runner-submit / runner-status / runner-cancel CLI.

Fake adapter only (no QEMU): proves the CLI plumbing, auth wiring,
and exit codes. The local adapter's execution path is covered by
tests/unit/test_runner.py with stubbed target steps, plus a live
build-only demonstration recorded in docs/runner/SELF_HOSTED_RUNNER.md.
"""
import json
import subprocess
from pathlib import Path

from genesis_rt.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOKEN = "test-token-0123456789abcdef"


def _head():
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
        timeout=30).stdout.strip()


def _job_file(tmp_path, job_id="cli-1", **over):
    ir = json.loads((REPO_ROOT / "examples" / "amr-demo"
                     / "machine-ir.json").read_text(encoding="utf-8"))
    job = {"job_id": job_id, "operation": "native_build",
           "revision": _head(), "ir": ir}
    job.update(over)
    path = tmp_path / f"{job_id}.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    return path


def _dirs(tmp_path):
    return ["--jobs-dir", str(tmp_path / "jobs"),
            "--ops-dir", str(tmp_path / "ops")]


def test_submit_fake_completes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GENESIS_RUNNER_TOKEN", TOKEN)
    job = _job_file(tmp_path)
    rc = main(["runner-submit", "--job", str(job),
               "--adapter", "fake"] + _dirs(tmp_path))
    out = capsys.readouterr().out
    assert rc == 0, out
    body = json.loads(out)
    assert body["status"] == "COMPLETED"
    assert body["adapter"] == "fake"
    assert body["qnx_verified"] is False


def test_submit_rejects_revision_mismatch(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GENESIS_RUNNER_TOKEN", TOKEN)
    job = _job_file(tmp_path, revision="1" * 40)
    rc = main(["runner-submit", "--job", str(job),
               "--adapter", "fake"] + _dirs(tmp_path))
    err = capsys.readouterr().err
    assert rc == 1, err
    assert "revision mismatch" in err


def test_submit_needs_token_env(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GENESIS_RUNNER_TOKEN", raising=False)
    job = _job_file(tmp_path)
    rc = main(["runner-submit", "--job", str(job),
               "--adapter", "fake"] + _dirs(tmp_path))
    assert rc == 2
    assert "GENESIS_RUNNER_TOKEN" in capsys.readouterr().err


def test_status_and_cancel_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GENESIS_RUNNER_TOKEN", TOKEN)
    job = _job_file(tmp_path)
    assert main(["runner-submit", "--job", str(job),
                 "--adapter", "fake"] + _dirs(tmp_path)) == 0
    capsys.readouterr()
    assert main(["runner-status", "--job-id", "cli-1"]
                + _dirs(tmp_path)) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["job_id"] == "cli-1"
    assert main(["runner-status", "--job-id", "ghost"]
                + _dirs(tmp_path)) == 2
    capsys.readouterr()
    # Terminal job: cancel is sticky, still COMPLETED.
    assert main(["runner-cancel", "--job-id", "cli-1"]
                + _dirs(tmp_path)) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETED"
    assert main(["runner-cancel", "--job-id", "ghost"]
                + _dirs(tmp_path)) == 1
