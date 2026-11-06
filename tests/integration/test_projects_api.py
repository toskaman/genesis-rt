# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: Studio Live endpoints (examples/validate/projects/env/static)."""
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


def _mk(client, **kw):
    kw.setdefault("from_example", "amr-demo")
    r = client.post("/projects", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def test_examples_lists_committed_files(client):
    r = client.get("/examples")
    assert r.status_code == 200
    by_name = {e["example"]: e for e in r.json()["examples"]}
    assert set(by_name) == {"amr-demo", "conveyor-demo", "cell-demo"}
    amr = {f["file"]: f for f in by_name["amr-demo"]["files"]}
    assert amr["machine-ir.json"]["ok"] is True
    assert amr["machine-ir.json"]["summary"]["machine"]["id"] == "amr-demo-01"
    assert amr["machine-ir-v2.json"]["summary"]["schema_version"] == 2
    cell = {f["file"]: f for f in by_name["cell-demo"]["files"]}
    assert set(cell) == {"cell-ir.json"}  # broken fixture not listed
    assert cell["cell-ir.json"]["ok"] is True


def test_read_example_raw(client):
    r = client.get("/examples/amr-demo/machine-ir.json")
    assert r.status_code == 200
    assert r.json()["ir"]["machine"]["id"] == "amr-demo-01"
    assert client.get("/examples/amr-demo/cell-ir-broken.json").status_code == 400
    assert client.get("/examples/nope/machine-ir.json").status_code == 400


def test_validate_ok_and_invalid(client, amr_ir_dict):
    r = client.post("/validate", json={"ir": amr_ir_dict})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["summary"]["machine"]["id"] == "amr-demo-01"
    r = client.post("/validate", json={"ir": {"schema_version": 1}})
    assert r.status_code == 400
    assert "invalid IR" in r.text


def test_validate_returns_stable_ir_sha256(client, amr_ir_dict):
    """ir_sha256 is the digest of the VALIDATED doc (Source pin source).

    Regression: the Studio pin check hashed reserialized text, and
    JSON.stringify spells 1.0 as 1, so genuine generated files showed
    MISMATCH. The backend digest survives int/float respelling.
    """
    import copy

    from genesis_rt.codegen import ir_sha256
    from genesis_rt.projects import validate_any

    r = client.post("/validate", json={"ir": amr_ir_dict})
    assert r.status_code == 200
    _, valid = validate_any(amr_ir_dict)
    assert r.json()["ir_sha256"] == ir_sha256(valid)
    damaged = copy.deepcopy(amr_ir_dict)
    damaged["control"]["max_angular_speed_radps"] = 1  # JS spells 1.0 so
    r2 = client.post("/validate", json={"ir": damaged})
    assert r2.status_code == 200
    assert r2.json()["ir_sha256"] == r.json()["ir_sha256"]


def test_create_from_example_defaults_name(client):
    body = _mk(client)
    assert body["name"] == "amr-demo-01"
    assert body["head"] == 1
    assert body["summary"]["counts"]["scenarios"] == 8


def test_create_from_v2_file_and_ir_payload(client, amr_ir_dict, repo_root):
    body = _mk(client, from_example="amr-demo", from_file="machine-ir-v2.json",
               name="v2-bot")
    assert body["name"] == "v2-bot"
    assert body["summary"]["schema_version"] == 2
    assert body["summary"]["counts"]["states"] == 3
    body = _mk(client, from_example=None, ir=amr_ir_dict, name="upload-bot")
    assert body["name"] == "upload-bot"
    assert body["summary"]["machine"]["id"] == "amr-demo-01"


def test_create_rejects_bad_sources(client):
    assert client.post("/projects", json={}).status_code == 400  # neither
    assert client.post("/projects", json={"from_example": "amr-demo",
                                          "ir": {}}).status_code == 400  # both
    assert client.post("/projects", json={"from_file": "x"}).status_code == 400
    r = client.post("/projects", json={"from_example": "nope"})
    assert r.status_code == 404
    r = client.post("/projects", json={"from_example": "amr-demo",
                                       "from_file": "../../secrets"})
    assert r.status_code == 400
    r = client.post("/projects", json={"ir": {"schema_version": 1}})
    assert r.status_code == 400 and "invalid IR" in r.text
    r = client.post("/projects", json={"from_example": "amr-demo",
                                       "name": "../escape"})
    assert r.status_code == 400


def test_create_rejects_oversize(client):
    r = client.post("/projects", json={"ir": {"schema_version": 1,
                                              "pad": "x" * 300_000}})
    assert r.status_code == 400 and "too large" in r.text


def test_get_list_and_bad_ids(client):
    body = _mk(client, name="listed")
    r = client.get(f"/projects/{body['pid']}")
    assert r.status_code == 200
    assert r.json()["ir"]["machine"]["id"] == "amr-demo-01"
    r = client.get("/projects")
    assert [p["pid"] for p in r.json()["projects"]] == [body["pid"]]
    assert client.get("/projects/nope").status_code == 400
    assert client.get("/projects/prj-000000000000").status_code == 404


def test_save_revision_history_and_diff(client, amr_ir_dict):
    pid = _mk(client)["pid"]
    changed = dict(amr_ir_dict)
    changed["control"] = dict(amr_ir_dict["control"],
                              max_linear_speed_mps=0.9)
    r = client.put(f"/projects/{pid}", json={"ir": changed})
    assert r.status_code == 200
    assert r.json()["head"] == 2
    r = client.get(f"/projects/{pid}/history")
    assert [h["rev"] for h in r.json()["revisions"]] == [1, 2]
    r = client.get(f"/projects/{pid}/revisions/1")
    assert r.json()["ir"]["control"]["max_linear_speed_mps"] != 0.9
    assert client.get(f"/projects/{pid}/revisions/9").status_code == 404
    r = client.get(f"/projects/{pid}/diff?rev_from=1&rev_to=2")
    paths = {c["path"] for c in r.json()["changed"]}
    assert "control.max_linear_speed_mps" in paths
    r = client.get(f"/projects/{pid}/diff")  # defaults: 1..head
    assert (r.json()["from"], r.json()["to"]) == (1, 2)
    # identical save is a no-op, invalid save keeps head
    r = client.put(f"/projects/{pid}", json={"ir": changed})
    assert r.json()["unchanged"] is True and r.json()["head"] == 2
    r = client.put(f"/projects/{pid}", json={"ir": {"schema_version": 1}})
    assert r.status_code == 400
    assert client.get(f"/projects/{pid}").json()["head"] == 2


def test_duplicate_and_export(client):
    pid = _mk(client, name="orig")["pid"]
    r = client.post(f"/projects/{pid}/duplicate", json={"name": "copy"})
    assert r.status_code == 201
    dup = r.json()
    assert dup["pid"] != pid and dup["head"] == 1
    assert client.get(f"/projects/{dup['pid']}").json()["ir"] == \
        client.get(f"/projects/{pid}").json()["ir"]
    r = client.get(f"/projects/{pid}/export")
    assert r.status_code == 200
    assert r.json()["project"]["name"] == "orig"
    assert "attachment" in r.headers["content-disposition"]
    assert client.get("/projects/prj-000000000000/export").status_code == 404


def test_env_reports_toolchain(client):
    r = client.get("/env")
    assert r.status_code == 200
    body = r.json()
    assert body["api"] == "0.2.0"
    assert isinstance(body["environment"]["sdk_present"], bool)
    assert isinstance(body["environment"]["qemu"]["present"], bool)


def test_static_serves_studio_same_origin(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "GENESIS RT" in r.text and "genesis_verify.js" in r.text
    r = client.get("/genesis_verify.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert client.get("/dashboard.html").status_code == 200
    assert client.get("/nope.html").status_code == 404


def test_cross_origin_project_write_rejected(client):
    r = client.post("/projects", json={"from_example": "amr-demo"},
                    headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_cross_origin_project_put_rejected(client):
    pid = _mk(client, name="victim")["pid"]
    ir = client.get(f"/projects/{pid}").json()["ir"]
    r = client.put(f"/projects/{pid}", json={"ir": ir},
                   headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    ok = client.get(f"/projects/{pid}").json()
    assert ok["head"] == 1  # nothing was written
