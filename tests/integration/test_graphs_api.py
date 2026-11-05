# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: Evidence Graph endpoints (/graphs, /graphs/compare)."""
import copy
import json

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt import evidence, faultlab, gate  # noqa: E402
from genesis_rt.ir import validate_ir  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def _passport(amr_ir, bound_evidence, tag, scenarios=None):
    scenarios = scenarios if scenarios is not None else list(
        amr_ir["verification"]["scenarios"])
    results = faultlab.run_all(amr_ir, scenarios)
    p = evidence.build_passport(f"run-{tag}", amr_ir,
                                bound_evidence["manifest"], results,
                                bound_evidence["build"])
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios))


def test_graph_valid_passport_with_requirements(client, amr_ir,
                                                bound_evidence, repo_root):
    v2 = json.loads((repo_root / "examples" / "amr-demo" /
                     "machine-ir-v2.json").read_text(encoding="utf-8"))
    p = _passport(amr_ir, bound_evidence, "api-ok")
    r = client.post("/graphs", json={"passport": p, "ir": v2})
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["run_id"] == "run-api-ok" and g["chain_valid"] is True
    assert g["ir_attached"] is True and g["requirements"] == 2
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["req:REQ-AMR-01"]["status"] == "verified"
    assert by_id["verdict"]["data"]["verdict"] == "PASS"
    for e in g["edges"]:
        assert e["from"] in by_id and e["to"] in by_id


def test_graph_without_ir_marks_requirements_gap(client, amr_ir,
                                                 bound_evidence):
    r = client.post("/graphs", json={
        "passport": _passport(amr_ir, bound_evidence, "api-bare")})
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["ir_attached"] is False and g["requirements"] == 0
    assert not [n for n in g["nodes"] if n["type"] == "requirement"]


def test_graph_tampered_rejected_with_409(client, amr_ir, bound_evidence):
    p = _passport(amr_ir, bound_evidence, "api-tamper")
    p["chain"][2]["body"]["status"] = "ok-but-forged"
    r = client.post("/graphs", json={"passport": p})
    assert r.status_code == 409, r.text
    assert "passport unusable" in r.text


def test_graph_compare_limit_change(client, amr_ir, amr_ir_dict,
                                    bound_evidence):
    before = _passport(amr_ir, bound_evidence, "api-cmp-a")
    changed = copy.deepcopy(amr_ir_dict)
    changed["control"]["max_linear_speed_mps"] = 0.9
    after_ir = validate_ir(changed)
    scenarios = list(after_ir["verification"]["scenarios"])
    results = faultlab.run_all(after_ir, scenarios)
    pb = evidence.build_passport("run-api-cmp-b", after_ir,
                                 bound_evidence["manifest"], results,
                                 bound_evidence["build"])
    after = evidence.attach_verdict(pb, gate.evaluate(pb, scenarios))
    r = client.post("/graphs/compare",
                    json={"passport_a": before, "passport_b": after})
    assert r.status_code == 200, r.text
    diff = r.json()
    assert diff["from_run"] == "run-api-cmp-a"
    assert {c["id"] for c in diff["changed"]} >= {
        "limit:max_linear_speed_mps"}


def test_graph_accepts_raw_passport_text(client, amr_ir, bound_evidence):
    # Browsers MUST post raw text: JS number semantics destroy 1.0 -> 1.
    p = _passport(amr_ir, bound_evidence, "api-raw")
    text = json.dumps(p, indent=2, sort_keys=True) + "\n"
    r = client.post("/graphs", json={"passport": text})
    assert r.status_code == 200, r.text
    assert r.json()["run_id"] == "run-api-raw"
    assert r.json()["counts"]["nodes"] > 50
    r = client.post("/graphs/compare",
                    json={"passport_a": text, "passport_b": text})
    assert r.status_code == 200, r.text
    assert r.json()["changed"] == []


def _js_damage(value):
    """Simulate a browser parse/reserialize: integral floats lose '.0'."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _js_damage(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_js_damage(v) for v in value]
    return value


def test_graph_js_reserialized_dict_rejected(client, amr_ir, bound_evidence):
    from genesis_rt.ir import canonical_json

    p = _passport(amr_ir, bound_evidence, "api-js")
    damaged = _js_damage(p)
    # NB: plain == is blind here (1 == 1.0 in Python); the chain hashes
    # bytes, so compare canonical serializations.
    assert canonical_json(damaged) != canonical_json(p)
    r = client.post("/graphs", json={"passport": damaged})
    assert r.status_code == 409, r.text
    assert "hash mismatch" in r.text


def test_graph_malformed_text_rejected(client):
    r = client.post("/graphs", json={"passport": "{nope"})
    assert r.status_code == 400, r.text
    r = client.post("/graphs", json={"passport": "[1, 2]"})
    assert r.status_code == 400, r.text


def test_graph_compare_identical_is_empty_and_tamper_409(
        client, amr_ir, bound_evidence):
    p = _passport(amr_ir, bound_evidence, "api-cmp-same")
    r = client.post("/graphs/compare",
                    json={"passport_a": p, "passport_b": p})
    assert r.status_code == 200, r.text
    diff = r.json()
    assert diff["changed"] == [] and diff["added"] == []
    assert diff["removed"] == [] and diff["edges_added"] == []
    bad = copy.deepcopy(p)
    bad["chain"][0]["body"]["ir_sha256"] = "f" * 64
    r = client.post("/graphs/compare",
                    json={"passport_a": p, "passport_b": bad})
    assert r.status_code == 409, r.text
