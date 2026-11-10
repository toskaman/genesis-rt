# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: W1 break-it API (POST /demo/break)."""
import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def test_post_demo_break_refuses_mutated_binary(client):
    r = client.post("/demo/break", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fresh"]["verdict"] == "CONSISTENT"
    assert body["stale"]["verdict"] == "STALE"
    assert body["stale"]["stale_binaries"] == ["genesis_guard"]
    assert body["elapsed_s"] < 30.0


def test_post_demo_break_no_input_needed(client):
    r = client.post("/demo/break")
    assert r.status_code == 200, r.text
    assert r.json()["stale"]["verdict"] == "STALE"
