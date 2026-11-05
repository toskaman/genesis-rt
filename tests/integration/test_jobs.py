# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M1 (§7): async job lifecycle — submit, poll, SSE, cancel,
recovery, crashes. A cancelled/crashed/interrupted job never carries
a success verdict."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt.jobs import JobManager  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    return api_mod.create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as cli:
        yield cli


def _poll_state(cli, job_id, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = cli.get(f"/jobs/{job_id}")
        assert r.status_code == 200, r.text
        if r.json()["state"] in ("succeeded", "failed", "cancelled",
                                  "interrupted"):
            return r.json()
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} never settled")


def test_job_submit_poll_succeeds(client):
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "scenarios": ["nominal_navigation"]})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    rec = _poll_state(client, job_id)
    assert rec["state"] == "succeeded"
    assert rec["verdict"] == "PASS"
    # job_id == run_id: the sync history endpoints serve async jobs too
    p = client.get(f"/runs/{job_id}")
    assert p.status_code == 200
    assert p.json()["run_id"] == job_id


def _frames(text):
    out = []
    for chunk in text.split("\n\n"):
        seq = kind = data = None
        for line in chunk.splitlines():
            if line.startswith("id: "):
                seq = int(line[4:])
            elif line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if seq is not None:
            out.append((seq, kind, data))
    return out


def test_job_events_stream_ordered(client):
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "scenarios": ["nominal_navigation"]})
    job_id = r.json()["job_id"]
    ev = client.get(f"/jobs/{job_id}/events")
    assert ev.status_code == 200, ev.text
    assert "text/event-stream" in ev.headers["content-type"]
    frames = _frames(ev.text)
    assert [s for s, _, _ in frames] == sorted(s for s, _, _ in frames)
    assert frames[0][0] == 0
    assert all(d["job_id"] == job_id for _, _, d in frames)
    kinds = [k for _, k, _ in frames]
    assert kinds[0] == "queued" and kinds[-1] == "done"


def test_job_events_resume_after(client):
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "scenarios": ["nominal_navigation"]})
    job_id = r.json()["job_id"]
    _poll_state(client, job_id)
    full = _frames(client.get(f"/jobs/{job_id}/events").text)
    assert len(full) >= 3
    tail = _frames(client.get(f"/jobs/{job_id}/events?after=1").text)
    assert tail and all(s > 1 for s, _, _ in tail)
    hdr = _frames(client.get(f"/jobs/{job_id}/events",
                             headers={"Last-Event-ID": "1"}).text)
    assert [(s, k) for s, k, _ in hdr] == [(s, k) for s, k, _ in tail]


def test_unknown_job_is_404(client):
    assert client.get("/jobs/run-nope-404").status_code == 404
    assert client.delete("/jobs/run-nope-404").status_code == 404
    assert client.get("/jobs/run-nope-404/events").status_code == 404


def test_invalid_job_id_is_400(client):
    assert client.get("/jobs/no!!").status_code == 400
    # encoded traversal never reaches a job: router 404s it safely
    assert client.get("/jobs/..%2F..").status_code in (400, 404)


def test_jobs_validation_parity(client):
    assert client.post("/jobs", json={"run_id": "no!!"}).status_code == 400
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "scenarios": ["nope_scenario"]})
    assert r.status_code == 400
    assert client.post("/jobs", json={}).status_code == 400


def test_duplicate_active_job_is_409(app, tmp_path, monkeypatch):
    from genesis_rt import orchestrator
    entered, release = threading.Event(), threading.Event()
    real_generate = orchestrator.codegen.generate

    def slow_generate(*a, **k):
        entered.set()
        assert release.wait(timeout=60)
        return real_generate(*a, **k)

    monkeypatch.setattr(orchestrator.codegen, "generate", slow_generate)
    with TestClient(app) as cli:
        r1 = cli.post("/jobs", json={"example": "amr-demo", "run_id": "run-dup-1"})
        assert r1.status_code == 202
        try:
            assert entered.wait(timeout=60)
            r2 = cli.post("/jobs", json={"example": "amr-demo",
                                          "run_id": "run-dup-1"})
            assert r2.status_code == 409, r2.text
        finally:
            release.set()
        rec = _poll_state(cli, "run-dup-1")
        assert rec["state"] == "succeeded"


def test_cancel_running_job_no_success_verdict(app, tmp_path, monkeypatch):
    from genesis_rt import orchestrator
    entered, release = threading.Event(), threading.Event()
    real_generate = orchestrator.codegen.generate

    def slow_generate(*a, **k):
        entered.set()
        assert release.wait(timeout=60)
        return real_generate(*a, **k)

    monkeypatch.setattr(orchestrator.codegen, "generate", slow_generate)
    with TestClient(app) as cli:
        r = cli.post("/jobs", json={"example": "amr-demo",
                                     "run_id": "run-cancel-2"})
        assert r.status_code == 202
        try:
            assert entered.wait(timeout=60)
            c = cli.delete("/jobs/run-cancel-2")
            assert c.status_code == 202, c.text
        finally:
            release.set()
        rec = _poll_state(cli, "run-cancel-2")
        assert rec["state"] == "cancelled"
        assert rec["verdict"] is None
        # cancelled runs leave cancel evidence, never a success passport
        failure = json.loads((tmp_path / "artifacts" / "run-cancel-2"
                              / "failure.json").read_text(encoding="utf-8"))
        assert failure["failure"]["step"] == "cancelled"
        assert client_get(cli, "/runs/run-cancel-2") == 404


def client_get(cli, path):
    return cli.get(path).status_code


def test_repeated_cancel_idempotent(app, monkeypatch):
    from genesis_rt import orchestrator
    entered, release = threading.Event(), threading.Event()
    real_generate = orchestrator.codegen.generate

    def slow_generate(*a, **k):
        entered.set()
        assert release.wait(timeout=60)
        return real_generate(*a, **k)

    monkeypatch.setattr(orchestrator.codegen, "generate", slow_generate)
    with TestClient(app) as cli:
        cli.post("/jobs", json={"example": "amr-demo", "run_id": "run-rc-1"})
        try:
            assert entered.wait(timeout=60)
            assert cli.delete("/jobs/run-rc-1").status_code == 202
            assert cli.delete("/jobs/run-rc-1").status_code in (200, 202)
        finally:
            release.set()
        rec = _poll_state(cli, "run-rc-1")
        assert rec["state"] == "cancelled"
        # cancelling a settled job reports its state, never 404
        assert cli.delete("/jobs/run-rc-1").status_code == 200


def test_two_simultaneous_jobs_overlap(app, monkeypatch):
    from genesis_rt import orchestrator
    real_generate = orchestrator.codegen.generate
    live = 0
    peak = 0
    guard = threading.Lock()

    def slow_generate(*a, **k):
        nonlocal live, peak
        with guard:
            live += 1
            peak = max(peak, live)
        try:
            time.sleep(3)
            return real_generate(*a, **k)
        finally:
            with guard:
                live -= 1

    monkeypatch.setattr(orchestrator.codegen, "generate", slow_generate)
    with TestClient(app) as cli:
        ids = []
        for i in (1, 2):
            r = cli.post("/jobs", json={"example": "amr-demo",
                                         "run_id": f"run-para-{i}"})
            assert r.status_code == 202
            ids.append(r.json()["job_id"])
        for jid in ids:
            assert _poll_state(cli, jid)["state"] == "succeeded"
    assert peak >= 2, "pool serialized the two jobs"


def test_worker_crash_failed_no_verdict(app, monkeypatch):
    import genesis_rt.jobs as jobs_mod

    def boom(*a, **k):
        raise RuntimeError("simulated worker crash")

    monkeypatch.setattr(jobs_mod, "run_pipeline", boom)
    with TestClient(app) as cli:
        r = cli.post("/jobs", json={"example": "amr-demo",
                                     "run_id": "run-crash-1"})
        assert r.status_code == 202
        rec = _poll_state(cli, "run-crash-1")
        assert rec["state"] == "failed"
        assert "RuntimeError" in (rec["error"] or "")
        assert rec["verdict"] is None
        assert cli.get("/runs/run-crash-1").status_code == 404


def test_restart_marks_abandoned_interrupted(tmp_path):
    db = tmp_path / "runs.db"
    m1 = JobManager(db, tmp_path / "artifacts")
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                 ("run-ghost-1", "running", None, None, None, None, 1.0, 1.0))
    conn.commit()
    conn.close()
    m1.close()
    m2 = JobManager(db, tmp_path / "artifacts")
    try:
        rec = m2.get("run-ghost-1")
        assert rec is not None and rec["state"] == "interrupted"
        assert rec["verdict"] is None
        kinds = [e["kind"] for e in m2.events("run-ghost-1")]
        assert "interrupted" in kinds
    finally:
        m2.close()


def test_lifespan_closes_manager(app):
    mgr = app.state.jobs
    assert mgr.closed is False
    with TestClient(app):
        pass
    assert mgr.closed is True
    with pytest.raises(RuntimeError, match="closed"):
        mgr.submit("nope.json")


def test_repeated_sessions_share_history(app):
    with TestClient(app) as cli:
        r = cli.post("/jobs", json={"example": "amr-demo",
                                     "run_id": "run-sess-1",
                                     "scenarios": ["nominal_navigation"]})
        assert r.status_code == 202
        assert _poll_state(cli, "run-sess-1")["state"] == "succeeded"
    app2 = api_mod.create_app()
    with TestClient(app2) as cli:
        r = cli.post("/jobs", json={"example": "amr-demo",
                                     "run_id": "run-sess-2",
                                     "scenarios": ["nominal_navigation"]})
        assert r.status_code == 202
        assert _poll_state(cli, "run-sess-2")["state"] == "succeeded"
        names = [j["job_id"] for j in cli.get("/jobs").json()["jobs"]]
        assert "run-sess-1" in names and "run-sess-2" in names


def test_db_consistency_after_job(client, tmp_path):
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "run_id": "run-dbc-1",
                                    "scenarios": ["nominal_navigation"]})
    assert r.status_code == 202
    _poll_state(client, "run-dbc-1")
    conn = sqlite3.connect(str(tmp_path / "artifacts" / "runs.db"))
    try:
        job = conn.execute("SELECT state, verdict FROM jobs WHERE job_id=?",
                           ("run-dbc-1",)).fetchone()
        assert job == ("succeeded", "PASS")
        seqs = [row[0] for row in conn.execute(
            "SELECT seq FROM events WHERE job_id=? ORDER BY seq",
            ("run-dbc-1",)).fetchall()]
        assert seqs == list(range(len(seqs))) and len(seqs) >= 3
        run = conn.execute("SELECT verdict FROM runs WHERE run_id=?",
                           ("run-dbc-1",)).fetchone()
        assert run == ("PASS",)
    finally:
        conn.close()


def test_origin_guard_rejects_foreign_writes(client):
    evil = {"Origin": "https://evil.test"}
    r = client.post("/jobs", json={"example": "amr-demo"}, headers=evil)
    assert r.status_code == 403
    r = client.delete("/jobs/run-x", headers=evil)
    assert r.status_code == 403
    ok = {"Origin": "http://127.0.0.1:8077"}
    r = client.post("/jobs", json={"example": "amr-demo",
                                    "scenarios": ["nominal_navigation"]},
                    headers=ok)
    assert r.status_code == 202, r.text
    _poll_state(client, r.json()["job_id"])


def test_jobs_overload_returns_429_without_orphan_upload(client, app, tmp_path,
                                                         monkeypatch, amr_ir):
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(app.state.jobs, "_max_live", 0)
    before = set((tmp_path / "artifacts").glob("upload-*.ir.json"))
    r = client.post("/jobs", json={"ir": amr_ir})
    assert r.status_code == 429, r.text
    assert r.headers.get("retry-after") == "5"
    after = set((tmp_path / "artifacts").glob("upload-*.ir.json"))
    assert after == before
