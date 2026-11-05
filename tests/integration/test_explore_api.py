# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: explorer endpoints (/explore, /explore/replay)."""
import copy

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


def _explore_body(ir, **kw):
    body = {"ir": ir, "invariant": "no_over_limit_allow",
            "params": {"max_allow_linear": 0.9},
            "strategies": ["boundary"],
            "budgets": {"max_scripts": 200, "max_findings": 1},
            "seed": 7}
    body.update(kw)
    return body


def test_explore_finds_violation(client, amr_ir_dict):
    r = client.post("/explore", json=_explore_body(amr_ir_dict))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["findings"]) == 1
    rec = body["findings"][0]
    assert rec["tier"] == "host-discovered"
    assert rec["observed"]["passed"] is False
    assert rec["shrunk_script"]["commands"]
    assert body["budget_exhausted"] is False


def test_explore_honest_empty_and_invalid(client, amr_ir_dict):
    r = client.post("/explore", json=_explore_body(
        amr_ir_dict, params={}, budgets={"max_scripts": 20}))
    assert r.status_code == 200, r.text
    assert r.json()["findings"] == []
    r = client.post("/explore", json=_explore_body(
        amr_ir_dict, invariant="nope"))
    assert r.status_code == 400, r.text
    r = client.post("/explore", json=_explore_body({"schema_version": 1}))
    assert r.status_code == 400, r.text
    assert "invalid IR" in r.text


def test_explore_replay_and_fix(client, amr_ir_dict):
    r = client.post("/explore", json=_explore_body(amr_ir_dict))
    assert r.status_code == 200, r.text
    rec = r.json()["findings"][0]
    r = client.post("/explore/replay",
                    json={"record": rec, "ir": amr_ir_dict})
    assert r.status_code == 200, r.text
    assert r.json()["deterministic"] is True
    fixed = copy.deepcopy(amr_ir_dict)
    fixed["control"]["max_linear_speed_mps"] = 0.9
    r = client.post("/explore/replay", json={"record": rec, "ir": fixed})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["violated"] is False
    assert body["same_ir"] is False


def test_explore_replay_rejects_bad_record(client, amr_ir_dict):
    r = client.post("/explore/replay",
                    json={"record": {"nope": 1}, "ir": amr_ir_dict})
    assert r.status_code == 400, r.text
