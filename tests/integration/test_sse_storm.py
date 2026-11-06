# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §14: SSE reconnect storms deliver full replays without residue.

Clients reconnect aggressively (browser refresh, tab return, flaky
networks). Every reconnect on a terminal job must replay the full
ordered history and then close; 50 sequential + 5 concurrent streams
must leave no stray worker threads behind.
"""
from __future__ import annotations

import json
import threading
import time

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402

STORM_SEQUENTIAL = 50
STORM_CONCURRENT = 5


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    return api_mod.create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as cli:
        yield cli


def _terminal_job(cli) -> str:
    r = cli.post("/jobs", json={"example": "amr-demo",
                                "scenarios": ["nominal_navigation"]})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        rec = cli.get(f"/jobs/{job_id}").json()
        if rec["state"] in ("succeeded", "failed", "cancelled",
                            "interrupted"):
            assert rec["state"] == "succeeded", rec
            return job_id
        time.sleep(0.1)
    raise AssertionError("job never settled")


def _frames(text: str):
    out = []
    for chunk in text.split("\n\n"):
        seq = kind = None
        for line in chunk.splitlines():
            if line.startswith("id: "):
                seq = int(line[4:])
            elif line.startswith("event: "):
                kind = line[7:]
        if seq is not None:
            out.append((seq, kind))
    return out


def _full_replay(cli, job_id: str):
    r = cli.get(f"/jobs/{job_id}/events")
    assert r.status_code == 200, r.text[:200]
    frames = _frames(r.text)
    assert frames, "empty replay"
    seqs = [s for s, _ in frames]
    assert seqs == sorted(seqs), "replay must be ordered"
    assert seqs[0] == 0, "replay must start at seq 0"
    assert frames[-1][1] in ("done", "failed", "cancelled",
                             "interrupted"), frames[-1]
    return frames


def _job_threads():
    return [t for t in threading.enumerate()
            if (t.name or "").startswith("genesis-job")]


def test_sse_reconnect_storm_sequential(client):
    job_id = _terminal_job(client)
    want = _full_replay(client, job_id)
    before = len(_job_threads())
    for _ in range(STORM_SEQUENTIAL):
        assert _full_replay(client, job_id) == want
    assert len(_job_threads()) == before  # streams close; pool intact


def test_sse_reconnect_storm_concurrent(client):
    job_id = _terminal_job(client)
    want = _full_replay(client, job_id)
    before = len(_job_threads())
    errors: list = []

    def _hit():
        try:
            got = _full_replay(client, job_id)
            assert got == want
        except Exception as exc:  # noqa: BLE001 - collected, re-raised
            errors.append(exc)

    workers = [threading.Thread(target=_hit)
               for _ in range(STORM_CONCURRENT)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=120)
        assert not w.is_alive(), "stream worker stuck"
    assert errors == []
    assert len(_job_threads()) == before


def test_sse_storm_total_threads_bounded(client):
    job_id = _terminal_job(client)
    for _ in range(3):  # warmup: portals/pools settle
        _full_replay(client, job_id)
    before = threading.active_count()
    for _ in range(STORM_SEQUENTIAL):
        _full_replay(client, job_id)
    assert threading.active_count() <= before + 2
