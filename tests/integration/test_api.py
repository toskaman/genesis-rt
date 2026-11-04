# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: API isolation, error mapping, concurrency."""
import json
import threading

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


def _conveyor_ir(repo_root):
    path = repo_root / "examples" / "conveyor-demo" / "machine-ir.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_unknown_scenario_is_400_not_500(client, amr_ir_dict):
    r = client.post("/runs", json={"ir": amr_ir_dict, "scenarios": ["nope"]})
    assert r.status_code == 400
    assert "unknown scenarios" in r.text


def test_invalid_ir_is_400(client):
    r = client.post("/runs", json={"ir": {"schema_version": 1}})
    assert r.status_code == 400


def test_too_many_scenarios_rejected(client, amr_ir_dict):
    r = client.post("/runs", json={"ir": amr_ir_dict,
                                   "scenarios": ["nominal_navigation"] * 33})
    assert r.status_code == 400


def test_missing_payload_is_400(client):
    assert client.post("/runs", json={}).status_code == 400


def test_v2_ir_upload_runs_pipeline(client, repo_root):
    """A schema v2 upload validates, runs, and records schema_version 2."""
    from pathlib import Path as _Path

    path = repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
    v2 = json.loads(path.read_text(encoding="utf-8"))
    r = client.post("/runs", json={"ir": v2,
                                   "scenarios": ["nominal_navigation"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] == "PASS"
    passport = json.loads(_Path(body["passport"]).read_text(encoding="utf-8"))
    ir_record = next(e for e in passport["chain"] if e["kind"] == "ir")
    assert ir_record["body"]["schema_version"] == 2


def test_concurrent_uploads_stay_isolated(repo_root, amr_ir_dict, tmp_path, monkeypatch):
    """Two parallel POST /runs => distinct correct passports, no cross-talk."""
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    payloads = [
        {"ir": amr_ir_dict, "scenarios": ["nominal_navigation"]},
        {"ir": _conveyor_ir(repo_root), "scenarios": ["nominal_navigation"]},
    ]
    results: dict[int, dict] = {}
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        try:
            with TestClient(app) as cli:
                resp = cli.post("/runs", json=payloads[i])
                results[i] = {"status": resp.status_code, "body": resp.json()}
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=600)
    assert not errors
    assert all(v["status"] == 200 for v in results.values()), results
    run_ids = {v["body"]["run_id"] for v in results.values()}
    assert len(run_ids) == 2
    machines = set()
    for v in results.values():
        passport = json.loads(
            (tmp_path / "artifacts" / v["body"]["run_id"] / "passport.json")
            .read_text(encoding="utf-8"))
        ir_rec = next(r for r in passport["chain"] if r["kind"] == "ir")
        machines.add(ir_rec["body"]["machine"]["id"])
    assert machines == {"amr-demo-01", "conveyor-demo-01"}
    leftovers = list((tmp_path / "artifacts").glob("upload-*.ir.json"))
    assert leftovers == []


def test_cancel_unknown_run_is_404(client):
    assert client.delete("/runs/run-no-such-run/cancel").status_code == 404


def test_invalid_run_id_is_400(client, amr_ir_dict):
    r = client.post("/runs", json={"ir": amr_ir_dict, "run_id": "../evil"})
    assert r.status_code == 400


def test_duplicate_run_id_is_409(client, amr_ir_dict):
    first = client.post("/runs", json={"ir": amr_ir_dict, "run_id": "run-dup-1",
                                       "scenarios": ["nominal_navigation"]})
    assert first.status_code == 200
    second = client.post("/runs", json={"ir": amr_ir_dict, "run_id": "run-dup-1",
                                        "scenarios": ["nominal_navigation"]})
    assert second.status_code == 409


def test_cancel_active_run_aborts_with_409(repo_root, amr_ir_dict, tmp_path,
                                           monkeypatch):
    """POST with a client run_id runs in a thread; DELETE cancels it; the
    POST surfaces 409 and partial cancel evidence stays on disk."""
    from genesis_rt import orchestrator
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    entered, release = threading.Event(), threading.Event()
    real_generate = orchestrator.codegen.generate

    def slow_generate(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=60), "cancel test stalled"
        return real_generate(*args, **kwargs)

    monkeypatch.setattr(orchestrator.codegen, "generate", slow_generate)
    app = api_mod.create_app()
    outcome: dict = {}

    def post():
        with TestClient(app) as cli:
            resp = cli.post("/runs", json={
                "ir": amr_ir_dict, "run_id": "run-cancel-1",
                "scenarios": ["nominal_navigation"]})
            outcome["status"] = resp.status_code
            outcome["body"] = resp.json()

    t = threading.Thread(target=post)
    t.start()
    try:
        assert entered.wait(timeout=60), "pipeline never started"
        with TestClient(app) as cli:
            cancel = cli.delete("/runs/run-cancel-1/cancel")
            assert cancel.status_code == 202
        release.set()
        t.join(timeout=120)
    finally:
        release.set()
        t.join(timeout=120)
    assert outcome["status"] == 409, outcome
    assert outcome["body"]["run_id"] == "run-cancel-1"
    failure = json.loads(
        (tmp_path / "artifacts" / "run-cancel-1" / "failure.json")
        .read_text(encoding="utf-8"))
    assert failure["failure"]["step"] == "cancelled"


def test_get_run_roundtrip_and_errors(client, amr_ir_dict):
    r = client.post("/runs", json={"ir": amr_ir_dict,
                                   "scenarios": ["nominal_navigation"]})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    got = client.get(f"/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["run_id"] == run_id
    assert client.get("/runs/does-not-exist").status_code == 404
    assert client.get("/runs/../evil").status_code in (400, 404, 405)
