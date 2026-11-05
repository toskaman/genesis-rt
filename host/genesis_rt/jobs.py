# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Local job manager: bounded async execution of the orchestrator pipeline.

One JobManager owns a small worker pool (default 2 host workers), a SQLite
job/event store (same runs.db as the API history) and per-job completion
events. States: queued -> running -> succeeded | failed | cancelled, plus
'interrupted' for rows left behind by a previous process (recovery on init).

A cancelled, failed, crashed or interrupted job never carries a success
verdict. Event rows carry (job_id, seq, kind, message, ts) for SSE replay.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from .orchestrator import (
    CancelledRun,
    request_cancel,
    run_pipeline,
    valid_run_id,
)

TERMINAL = ("succeeded", "failed", "cancelled", "interrupted")
MAX_EVENTS_PER_JOB = 1000
MAX_EVENT_CHARS = 2000
MAX_WORKERS = 2
CANCEL_POLL_S = 5.0
# §15: completion Events are per-job memory; evict terminal jobs' events
# past this cap (wait() falls back to a DB read for evicted jobs).
MAX_TRACKED_JOBS = 200

log = logging.getLogger("genesis.jobs")


class JobConflict(Exception):
    """A live job already owns the requested id (maps to HTTP 409)."""


class JobNotFound(Exception):
    """No such job id (maps to HTTP 404)."""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS runs "
                 "(run_id TEXT PRIMARY KEY, verdict TEXT, passport TEXT, run_dir TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS jobs "
                 "(job_id TEXT PRIMARY KEY, state TEXT, verdict TEXT, run_dir TEXT,"
                 " error TEXT, summary TEXT, created REAL, updated REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS events "
                 "(job_id TEXT, seq INTEGER, kind TEXT, message TEXT, ts REAL,"
                 " PRIMARY KEY(job_id, seq))")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "summary" not in cols:  # additive migration for the sync facade
        conn.execute("ALTER TABLE jobs ADD COLUMN summary TEXT")
        conn.commit()
    return conn


class JobManager:
    def __init__(self, db_path: str | Path, artifacts_dir: str | Path,
                 max_workers: int = MAX_WORKERS) -> None:
        self.db_path = Path(db_path)
        self.artifacts = Path(artifacts_dir)
        self._pool = ThreadPoolExecutor(max_workers=max_workers,
                                        thread_name_prefix="genesis-job")
        # RLock: _emit/_set_state re-enter from cancel()/worker paths that
        # already hold the lock; a plain Lock self-deadlocks those paths.
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._done: dict[str, threading.Event] = {}
        self._closed = False
        self._recover()

    # -- lifecycle ------------------------------------------------------
    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._pool.shutdown(wait=True, cancel_futures=True)

    def _recover(self) -> None:
        """Mark rows a dead process left behind as honestly interrupted."""
        conn = _connect(self.db_path)
        try:
            rows = conn.execute("SELECT job_id FROM jobs WHERE state IN "
                                "('queued','running')").fetchall()
            for (job_id,) in rows:
                now_wall = time.time()
                conn.execute("UPDATE jobs SET state='interrupted', "
                             "error='process ended before completion', "
                             "updated=? WHERE job_id=?", (now_wall, job_id))
                nxt = conn.execute("SELECT COALESCE(MAX(seq),-1)+1 FROM events "
                                   "WHERE job_id=?", (job_id,)).fetchone()[0]
                conn.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)",
                             (job_id, nxt, "interrupted",
                              "previous process ended before completion", now_wall))
                log.warning("job=%s recovered as interrupted", job_id)
            conn.commit()
        finally:
            conn.close()

    # -- submission -----------------------------------------------------
    def submit(self, ir_path: str | Path, scenarios: list[str] | None = None,
               run_id: str | None = None,
               cleanup: str | Path | None = None) -> str:
        with self._lock:
            if self._closed:
                raise RuntimeError("job manager is closed")
            job_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
            if not valid_run_id(job_id):
                raise ValueError(f"invalid run_id: {job_id!r}")
            conn = _connect(self.db_path)
            try:
                row = conn.execute("SELECT state FROM jobs WHERE job_id=?",
                                   (job_id,)).fetchone()
                if row is not None and row[0] not in TERMINAL:
                    raise JobConflict(f"job {job_id} already {row[0]}")
                if run_id is not None and (self.artifacts / job_id /
                                           "passport.json").exists():
                    raise JobConflict(f"run_id collision: {job_id} exists")
                now_wall = time.time()
                conn.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                             (job_id, "queued", None, None, None, None,
                              now_wall, now_wall))
                conn.execute("DELETE FROM events WHERE job_id=?", (job_id,))
                conn.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                             (job_id, 0, "queued", "job accepted", now_wall))
                conn.commit()
            finally:
                conn.close()
            self._done[job_id] = threading.Event()
            self._evict_done_locked()
            self._cond.notify_all()
        log.info("job=%s submit queued", job_id)
        self._pool.submit(self._work, job_id, Path(ir_path),
                          list(scenarios) if scenarios else None,
                          Path(cleanup) if cleanup else None)
        return job_id

    def _evict_done_locked(self) -> None:
        """Drop completion Events of terminal jobs past the track cap."""
        overflow = len(self._done) - MAX_TRACKED_JOBS
        if overflow <= 0:
            return
        conn = _connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT job_id FROM jobs WHERE state IN "
                "('succeeded','failed','cancelled','interrupted')"
                " ORDER BY updated ASC").fetchall()
        finally:
            conn.close()
        # oldest terminal first; skip ids already evicted (pop miss)
        popped = 0
        for (old_id,) in rows:
            if popped >= overflow:
                break
            if self._done.pop(old_id, None) is not None:
                popped += 1

    # -- queries --------------------------------------------------------
    def get(self, job_id: str) -> dict[str, Any] | None:
        conn = _connect(self.db_path)
        try:
            row = conn.execute("SELECT job_id, state, verdict, run_dir, error,"
                               " summary, created, updated FROM jobs WHERE job_id=?",
                               (job_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        keys = ("job_id", "state", "verdict", "run_dir", "error",
                "summary", "created", "updated")
        return dict(zip(keys, row))

    def wait(self, job_id: str, timeout: float | None = None) -> dict[str, Any]:
        with self._lock:
            evt = self._done.get(job_id)
        if evt is None:  # unknown, evicted (§15 cap), or restart
            rec = self.get(job_id)
            if rec is None:
                raise JobNotFound(job_id)
            return rec
        if not evt.wait(timeout):
            raise TimeoutError(job_id)
        rec = self.get(job_id)
        assert rec is not None
        return rec

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self.get(job_id)
            if rec is None:
                raise JobNotFound(job_id)
            if rec["state"] in TERMINAL:
                return rec  # idempotent: repeated cancel reports state
            if rec["state"] == "queued":
                self._set_state(job_id, "cancelled", error="cancelled before start")
                self._emit(job_id, "cancelled", "cancelled before start")
                self._done[job_id].set()
                self._cond.notify_all()
                return self.get(job_id)  # type: ignore[return-value]
        # running: flag the orchestrator checkpoint; bounded retry closes the
        # claim-vs-_ACTIVE.add race (run_pipeline checks first thing).
        deadline = time.monotonic() + CANCEL_POLL_S
        while time.monotonic() < deadline:
            if request_cancel(job_id):
                break
            cur = self.get(job_id)
            if cur is None or cur["state"] in TERMINAL:
                break
            time.sleep(0.05)
        with self._lock:
            self._cond.notify_all()
            return self.get(job_id)  # type: ignore[return-value]

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(200, limit))
        conn = _connect(self.db_path)
        try:
            rows = conn.execute("SELECT job_id, state, verdict, run_dir, error,"
                                " created, updated FROM jobs ORDER BY created DESC,"
                                " job_id LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
        keys = ("job_id", "state", "verdict", "run_dir", "error",
                "created", "updated")
        return [dict(zip(keys, r)) for r in rows]

    def events(self, job_id: str, after: int = -1,
               limit: int = 200) -> list[dict[str, Any]]:
        """Events with seq strictly greater than ``after`` (-1 = all)."""
        conn = _connect(self.db_path)
        try:
            rows = conn.execute("SELECT seq, kind, message, ts FROM events WHERE"
                                " job_id=? AND seq>? ORDER BY seq LIMIT ?",
                                (job_id, max(-1, after), max(1, min(500, limit)))).fetchall()
        finally:
            conn.close()
        return [{"job_id": job_id, "seq": s, "kind": k, "message": m, "ts": t}
                for s, k, m, t in rows]

    # -- worker ---------------------------------------------------------
    def _claim(self, job_id: str) -> bool:
        with self._lock:
            rec = self.get(job_id)
            if rec is None or rec["state"] != "queued":
                return False
            self._set_state(job_id, "running")
            self._emit(job_id, "started", "worker picked up job")
            self._cond.notify_all()
            return True

    def _work(self, job_id: str, ir_path: Path, scenarios: list[str] | None,
              cleanup: Path | None) -> None:
        try:
            if not self._claim(job_id):
                return  # cancelled while queued
            log.info("job=%s running", job_id)
            try:
                summary = run_pipeline(
                    ir_path, self.artifacts, run_id=job_id, scenarios=scenarios,
                    listener=lambda kind, msg: self._emit(job_id, kind, msg))
            except CancelledRun:
                with self._lock:
                    self._set_state(job_id, "cancelled",
                                    run_dir=str(self.artifacts / job_id),
                                    error="cancelled by request")
                    self._emit(job_id, "cancelled", "cancelled by request")
                log.info("job=%s terminal cancelled", job_id)
            except Exception as exc:  # worker crash path: failed, never success
                with self._lock:
                    self._set_state(job_id, "failed",
                                    error=f"{type(exc).__name__}: {exc}")
                    self._emit(job_id, "failed", f"{type(exc).__name__}: {exc}")
                log.warning("job=%s terminal failed err=%s: %s", job_id,
                            type(exc).__name__, exc)
            else:
                import json as _json
                passport_text = Path(summary["passport"]).read_text(encoding="utf-8")
                conn = _connect(self.db_path)
                try:
                    conn.execute("INSERT OR REPLACE INTO runs (run_id, verdict,"
                                 " passport, run_dir) VALUES (?,?,?,?)",
                                 (job_id, summary["verdict"], passport_text,
                                  str(summary["run_dir"])))
                    conn.commit()
                finally:
                    conn.close()
                with self._lock:
                    self._set_state(job_id, "succeeded", verdict=summary["verdict"],
                                    run_dir=str(summary["run_dir"]),
                                    summary=_json.dumps(summary))
                    self._emit(job_id, "done", f"verdict={summary['verdict']}")
                log.info("job=%s terminal succeeded verdict=%s", job_id,
                         summary["verdict"])
        finally:
            if cleanup is not None:
                try:
                    cleanup.unlink(missing_ok=True)
                except OSError:
                    pass
            with self._lock:
                evt = self._done.get(job_id)
                if evt is not None:
                    evt.set()
                self._cond.notify_all()

    # -- internals (call with self._lock held unless noted) --------------
    def _set_state(self, job_id: str, state: str, verdict: str | None = None,
                   run_dir: str | None = None, error: str | None = None,
                   summary: str | None = None) -> None:
        conn = _connect(self.db_path)
        try:
            conn.execute("UPDATE jobs SET state=?, verdict=COALESCE(?,verdict),"
                         " run_dir=COALESCE(?,run_dir), error=COALESCE(?,error),"
                         " summary=COALESCE(?,summary), updated=? WHERE job_id=?",
                         (state, verdict, run_dir, error, summary,
                          time.time(), job_id))
            conn.commit()
        finally:
            conn.close()

    def _emit(self, job_id: str, kind: str, message: str) -> None:
        message = str(message)[:MAX_EVENT_CHARS]
        with self._lock:
            conn = _connect(self.db_path)
            try:
                count = conn.execute("SELECT COUNT(*) FROM events WHERE job_id=?",
                                     (job_id,)).fetchone()[0]
                if count >= MAX_EVENTS_PER_JOB:
                    return
                nxt = conn.execute("SELECT COALESCE(MAX(seq),-1)+1 FROM events "
                                   "WHERE job_id=?", (job_id,)).fetchone()[0]
                conn.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)",
                             (job_id, nxt, kind, message, time.time()))
                conn.commit()
            finally:
                conn.close()
            self._cond.notify_all()


Listener = Callable[[str, str], None]
