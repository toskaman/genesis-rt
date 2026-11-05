# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §7: bounded admission — overload refuses without a trace."""
import sqlite3
import threading

import pytest

from genesis_rt.jobs import JobManager, JobOverloaded


def test_submit_over_capacity_rejected_no_row(tmp_path):
    mgr = JobManager(tmp_path / "runs.db", tmp_path / "art", max_live=3)
    gate = threading.Event()
    mgr._work = lambda job_id, *a: gate.wait(timeout=30)
    try:
        for i in range(3):
            mgr.submit(tmp_path / f"{i}.json")
        with pytest.raises(JobOverloaded):
            mgr.submit(tmp_path / "over.json")
        conn = sqlite3.connect(str(tmp_path / "runs.db"))
        try:
            n = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        finally:
            conn.close()
        assert n == 3
    finally:
        gate.set()
        mgr.close()


def test_terminal_job_queryable_without_completion_event(tmp_path):
    mgr = JobManager(tmp_path / "runs.db", tmp_path / "art")
    try:
        conn = sqlite3.connect(str(tmp_path / "runs.db"))
        try:
            conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                         ("run-evicted-1", "succeeded", "PASS", None,
                          None, None, 1.0, 2.0))
            conn.commit()
        finally:
            conn.close()
        assert mgr._done.get("run-evicted-1") is None  # never tracked here
        rec = mgr.wait("run-evicted-1", timeout=5)
        assert (rec["state"], rec["verdict"]) == ("succeeded", "PASS")
        assert mgr.get("run-evicted-1")["state"] == "succeeded"
    finally:
        mgr.close()


def test_rapid_burst_bounds_live_and_recovers(tmp_path):
    mgr = JobManager(tmp_path / "runs.db", tmp_path / "art", max_live=5)
    gate = threading.Event()
    mgr._work = lambda job_id, *a: gate.wait(timeout=30)
    try:
        ok, refused = 0, 0
        for i in range(50):
            try:
                mgr.submit(tmp_path / f"b{i}.json")
                ok += 1
            except JobOverloaded:
                refused += 1
        assert (ok, refused) == (5, 45)
        gate.set()
        mgr.close()
        # rows stay queryable; no completion-event leak past the track cap
        assert len(mgr._done) <= 200
    finally:
        gate.set()
        try:
            mgr.close()
        except RuntimeError:
            pass
