# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M4 (§15): job-manager lifecycle and boundedness.

Direct JobManager tests (no HTTP): the completion-Event track cap,
DB fallback for evicted jobs, submit-after-close rejection, event cap,
crash recovery, and job-correlated structured logs.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import sys
import time

import pytest

from genesis_rt import jobs as jobs_mod
from genesis_rt.jobs import JobManager


@pytest.fixture()
def mgr(tmp_path):
    m = JobManager(tmp_path / "runs.db", tmp_path / "artifacts")
    yield m
    m.close()


def _bogus_ir(tmp_path, name="no-such.json"):
    return tmp_path / name  # missing file: worker fails fast, never success


def test_done_track_cap_evicts_terminal(mgr, tmp_path, monkeypatch):
    monkeypatch.setattr(jobs_mod, "MAX_TRACKED_JOBS", 5)
    ids = []
    for i in range(8):
        # sequential submit+wait: earlier jobs are terminal at each submit,
        # so eviction has something to trim
        jid = mgr.submit(_bogus_ir(tmp_path), run_id=f"evict-{i:02d}")
        ids.append(jid)
        rec = mgr.wait(jid, timeout=120)
        assert rec["state"] == "failed"  # bogus IR: failed, never success
    assert len(mgr._done) <= 5
    # evicted jobs still resolve through the DB fallback
    rec = mgr.wait(ids[0], timeout=10)
    assert rec["state"] == "failed"


def test_submit_after_close_rejected(mgr, tmp_path):
    mgr.close()
    with pytest.raises(RuntimeError, match="closed"):
        mgr.submit(_bogus_ir(tmp_path))
    with pytest.raises(RuntimeError, match="closed"):
        mgr.submit(_bogus_ir(tmp_path), run_id="late-01")


def test_event_cap_never_exceeded(mgr, tmp_path):
    jid = mgr.submit(_bogus_ir(tmp_path), run_id="flood-01")
    for i in range(jobs_mod.MAX_EVENTS_PER_JOB + 50):
        mgr._emit(jid, "note", f"msg-{i}")
    mgr.wait(jid, timeout=120)
    assert len(mgr.events(jid, limit=500)) <= 500
    conn = sqlite3.connect(str(mgr.db_path))
    try:
        count = conn.execute("SELECT COUNT(*) FROM events WHERE job_id=?",
                             (jid,)).fetchone()[0]
    finally:
        conn.close()
    assert count <= jobs_mod.MAX_EVENTS_PER_JOB


def test_recovery_marks_abandoned_interrupted(tmp_path, caplog):
    db = tmp_path / "runs.db"
    first = JobManager(db, tmp_path / "artifacts")
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                     ("orphan-01", "running", None, None, None, None,
                      1.0, 1.0, None))  # NULL owner: pre-ownership record
        conn.commit()
    finally:
        conn.close()
    first.close()
    with caplog.at_level(logging.WARNING, logger="genesis.jobs"):
        second = JobManager(db, tmp_path / "artifacts")
    try:
        rec = second.get("orphan-01")
        assert rec is not None
        assert rec["state"] == "interrupted"
        assert rec["verdict"] != "PASS"
        assert "job=orphan-01" in caplog.text
    finally:
        second.close()


def _dead_pid():
    """A pid naming no live process (barring instant pid reuse)."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def _plant_job(db_path, job_id, state, owner_pid, updated):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                     (job_id, state, None, None, None, None,
                      updated, updated, owner_pid))
        conn.commit()
    finally:
        conn.close()


def test_recovery_spares_live_owner_job(tmp_path):
    """A second manager must not reap a job whose owner is alive."""
    db = tmp_path / "runs.db"
    first = JobManager(db, tmp_path / "artifacts")
    now = time.time()
    _plant_job(db, "live-01", "running", os.getpid(), now)
    first.close()
    second = JobManager(db, tmp_path / "artifacts")
    try:
        assert second.get("live-01")["state"] == "running"
    finally:
        second.close()


def test_recovery_reaps_dead_owner_job(tmp_path):
    db = tmp_path / "runs.db"
    first = JobManager(db, tmp_path / "artifacts")
    now = time.time()
    _plant_job(db, "dead-01", "running", _dead_pid(), now)
    first.close()
    second = JobManager(db, tmp_path / "artifacts")
    try:
        rec = second.get("dead-01")
        assert rec is not None and rec["state"] == "interrupted"
        kinds = [e["kind"] for e in second.events("dead-01")]
        assert "interrupted" in kinds
    finally:
        second.close()


def test_logs_carry_job_id(mgr, tmp_path, caplog):
    with caplog.at_level(logging.INFO, logger="genesis.jobs"):
        jid = mgr.submit(_bogus_ir(tmp_path), run_id="logged-01")
        mgr.wait(jid, timeout=120)
    assert f"job={jid} submit queued" in caplog.text
    assert f"job={jid} running" in caplog.text
    assert f"job={jid} terminal failed" in caplog.text


def test_close_is_idempotent_and_reusable_guard(mgr):
    mgr.close()
    mgr.close()  # second close must not raise or hang
    assert mgr.closed is True
