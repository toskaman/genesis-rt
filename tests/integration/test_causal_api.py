# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: causal dossiers API roundtrip."""

import json

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt.causal_run import verify_dossier  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def _payload(repo_root):
    incident = json.loads(
        (repo_root / "examples" / "causal-demo"
         / "estop-cell-transfer.json").read_text(encoding="utf-8"))
    machine_ir = json.loads(
        (repo_root / "examples" / "cell-demo"
         / "cell-ir.json").read_text(encoding="utf-8"))
    return {"incident": incident, "machine_ir": machine_ir,
            "only": ["H-estop"]}


def test_post_dossier_sealed_roundtrip(client, repo_root):
    resp = client.post("/causal/dossiers", json=_payload(repo_root))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["causality"]["winning_hypothesis"] == "H-estop"
    assert verify_dossier(body)["valid"] is True


def test_get_dossier_reverifies(client, repo_root):
    created = client.post("/causal/dossiers",
                          json=_payload(repo_root)).json()
    inc_id = created["incident"]["incident_id"]
    resp = client.get(f"/causal/dossiers/{inc_id}")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_get_unknown_dossier_404(client):
    assert client.get("/causal/dossiers/nope-1").status_code == 404


def test_flagship_pair_served(client):
    resp = client.get("/causal/flagship")
    assert resp.status_code == 200
    body = resp.json()
    assert body["incident"]["incident_id"] == "inc-estop-cell-01"
    assert body["machine_ir"]["machine"]["kind"] == "industrial_cell"


def test_post_invalid_incident_400(client, repo_root):
    payload = _payload(repo_root)
    payload["incident"].pop("observed")
    resp = client.post("/causal/dossiers", json=payload)
    assert resp.status_code == 400


def test_fix_appends_k1_proof(client, repo_root):
    created = client.post("/causal/dossiers",
                          json=_payload(repo_root)).json()
    inc_id = created["incident"]["incident_id"]
    machine_ir = json.loads(
        (repo_root / "examples" / "cell-demo"
         / "cell-ir.json").read_text(encoding="utf-8"))
    resp = client.post(f"/causal/dossiers/{inc_id}/fix",
                       json={"ir_after": machine_ir})
    assert resp.status_code == 200, resp.text
    assert resp.json()["fix"]["change_id"].startswith(inc_id + "-fix")
