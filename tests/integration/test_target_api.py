# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §5: target ops API — guard, admission, cancel, honest BLOCKED."""
from __future__ import annotations

import json
import threading
import time

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt import target as tgt_mod  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    return api_mod.create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as cli:
        yield cli


def _poll_op(cli, op_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = cli.get(f"/target/ops/{op_id}")
        assert r.status_code == 200, r.text
        if r.json()["state"] in tgt_mod.TERMINAL_TARGET:
            return r.json()
        time.sleep(0.05)
    raise AssertionError(f"op {op_id} never settled")


def _stub_all(monkeypatch):
    for name in ("validate", "env", "generate", "build"):
        monkeypatch.setitem(tgt_mod.STEP_IMPLS, name,
                            lambda ctx, n=name: (True, f"{n} stub ok"))


def test_target_foreign_origin_post_rejected(client):
    r = client.post("/target/ops", json={"workflow": "build-only"},
                    headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_target_unknown_workflow_400(client):
    r = client.post("/target/ops", json={"workflow": "nope"})
    assert r.status_code == 400


def test_target_bad_and_unknown_op_id(client):
    assert client.get("/target/ops/not-an-id").status_code == 400
    assert client.get("/target/ops/op-000000000000").status_code == 404
    assert client.delete("/target/ops/op-000000000000").status_code == 404


def test_target_get_and_list_completed(client, monkeypatch):
    _stub_all(monkeypatch)
    r = client.post("/target/ops", json={"workflow": "build-only",
                                         "params": {"ir": {}}})
    assert r.status_code == 202, r.text
    op_id = r.json()["op_id"]
    rec = _poll_op(client, op_id)
    assert rec["state"] == "COMPLETED"
    assert client.get(f"/target/ops/{op_id}").json()["state"] == "COMPLETED"
    rows = client.get("/target/ops").json()["ops"]
    assert [o["op_id"] for o in rows] == [op_id]


def test_target_duplicate_live_409(client, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def _slow(ctx):
        started.set()
        release.wait(timeout=30)
        return (True, "slow ok")

    monkeypatch.setitem(tgt_mod.STEP_IMPLS, "validate", _slow)
    for name in ("env", "generate", "build"):
        monkeypatch.setitem(tgt_mod.STEP_IMPLS, name,
                            lambda ctx: (True, "stub ok"))
    try:
        r = client.post("/target/ops", json={"workflow": "build-only",
                                             "params": {"ir": {}}})
        assert r.status_code == 202, r.text
        assert started.wait(timeout=10)
        r2 = client.post("/target/ops", json={"workflow": "build-only",
                                              "params": {"ir": {}}})
        assert r2.status_code == 409
    finally:
        release.set()
    assert _poll_op(client, r.json()["op_id"])["state"] == "COMPLETED"


def test_target_cancel_flows(client, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def _slow(ctx):
        started.set()
        release.wait(timeout=30)
        return (True, "slow ok")

    monkeypatch.setitem(tgt_mod.STEP_IMPLS, "validate", _slow)
    for name in ("env", "generate", "build"):
        monkeypatch.setitem(tgt_mod.STEP_IMPLS, name,
                            lambda ctx: (True, "stub ok"))
    r = client.post("/target/ops", json={"workflow": "build-only",
                                         "params": {"ir": {}}})
    op_id = r.json()["op_id"]
    assert started.wait(timeout=10)
    d = client.delete(f"/target/ops/{op_id}")
    assert d.status_code == 200
    release.set()
    assert _poll_op(client, op_id)["state"] == "CANCELLED"


def test_target_blocked_never_pass(client, monkeypatch):
    def _no_sdk(ctx):
        raise tgt_mod.TargetBlocked("QNX SDK not installed")

    monkeypatch.setitem(tgt_mod.STEP_IMPLS, "env", _no_sdk)
    for name in ("validate", "generate", "build"):
        monkeypatch.setitem(tgt_mod.STEP_IMPLS, name,
                            lambda ctx: (True, "stub ok"))
    r = client.post("/target/ops", json={"workflow": "build-only",
                                         "params": {"ir": {}}})
    rec = _poll_op(client, r.json()["op_id"])
    assert rec["state"] == "BLOCKED"
    assert "SDK" in rec["reason"]
    assert "PASS" not in json.dumps(rec)


def test_build_only_op_real_build(client, amr_ir):
    from genesis_rt.build_adapter import probe
    if not probe()["sdk_present"]:
        pytest.skip("QNX SDK not installed (honest skip, not a pass)")
    r = client.post("/target/ops", json={"workflow": "build-only",
                                         "params": {"ir": amr_ir}})
    assert r.status_code == 202, r.text
    rec = _poll_op(client, r.json()["op_id"], timeout=300)
    assert rec["state"] == "COMPLETED", rec
    assert rec["artifacts"].get("binaries"), rec["artifacts"]
