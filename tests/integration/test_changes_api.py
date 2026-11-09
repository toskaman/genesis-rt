# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: K1 change-proof API (POST /changes, GET /changes/{id})."""
import json

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


def _cell_pair(repo_root):
    cell = repo_root / "examples" / "cell-demo"
    return (json.loads((cell / "cell-ir-broken.json").read_text(encoding="utf-8")),
            json.loads((cell / "cell-ir.json").read_text(encoding="utf-8")))


def test_post_changes_round_trip(client, repo_root):
    before, after = _cell_pair(repo_root)
    r = client.post("/changes", json={"ir_before": before, "ir_after": after,
                                      "scenarios": ["cell_nominal_transfer"],
                                      "change_id": "chg-api-1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["change_id"] == "chg-api-1"
    assert body["before"]["verdict"] == "FAIL"
    assert body["after"]["verdict"] == "PASS"
    assert body["compare"]["contract"]["limits_changed"] == {
        "max_linear_speed_mps": [0.3, 1.2]}
    assert body["compare"]["scenarios"]["fixed"] == ["cell_nominal_transfer"]


def test_get_changes_by_id(client, repo_root):
    before, after = _cell_pair(repo_root)
    r = client.post("/changes", json={"ir_before": before, "ir_after": after,
                                      "scenarios": ["cell_nominal_transfer"]})
    assert r.status_code == 200, r.text
    change_id = r.json()["change_id"]
    fetched = client.get(f"/changes/{change_id}")
    assert fetched.status_code == 200
    assert fetched.json()["change_id"] == change_id
    assert fetched.json()["verdict"] == "PASS"


def test_get_changes_unknown_is_404(client):
    assert client.get("/changes/chg-nope").status_code == 404


def test_get_changes_bad_id_is_400(client):
    assert client.get("/changes/..%2Fescape").status_code in (400, 404)


def test_post_changes_invalid_ir_is_400(client, repo_root):
    _, after = _cell_pair(repo_root)
    r = client.post("/changes", json={"ir_before": {"schema_version": 1},
                                      "ir_after": after})
    assert r.status_code == 400


def test_post_changes_missing_payload_is_400(client, repo_root):
    _, after = _cell_pair(repo_root)
    assert client.post("/changes", json={"ir_after": after}).status_code == 400
    assert client.post("/changes", json={}).status_code == 400
