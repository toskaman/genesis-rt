# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: change-impact endpoints (/impact, project impact)."""
import copy
import json

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt import codegen, evidence, faultlab, gate  # noqa: E402
from genesis_rt.ir import validate_ir  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def _passport(ir, manifest, tag, build):
    scenarios = list(ir["verification"]["scenarios"])
    results = faultlab.run_all(ir, scenarios)
    p = evidence.build_passport(f"run-{tag}", ir, manifest, results, build)
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios))


def test_impact_limit_change(client, amr_ir_dict):
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    r = client.post("/impact",
                    json={"ir_before": amr_ir_dict, "ir_after": after})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["limits"]["changed"][0]["key"] == "max_linear_speed_mps"
    assert len(body["retest"]) == 8
    assert body["evidence_invalidated"] is True
    assert body["conservative"] is True


def test_impact_no_change_and_invalid(client, amr_ir_dict):
    r = client.post("/impact", json={"ir_before": amr_ir_dict,
                                     "ir_after": copy.deepcopy(amr_ir_dict)})
    assert r.status_code == 200, r.text
    assert r.json()["retest"] == []
    r = client.post("/impact", json={"ir_before": {"schema_version": 1},
                                     "ir_after": amr_ir_dict})
    assert r.status_code == 400, r.text
    assert "invalid IR" in r.text


def test_impact_release_current_passport(client, amr_ir_dict, tmp_path):
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    after_ir = validate_ir(after)
    manifest = codegen.generate(after_ir, tmp_path / "gen-rel-api")
    p = _passport(after_ir, manifest, "rel-api", {"status": "missing"})
    text = json.dumps(p, indent=2, sort_keys=True)
    r = client.post("/impact/release",
                    json={"ir_before": amr_ir_dict, "ir_after": after,
                          "passport": text})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chain_ok"] is True and body["evidence_current"] is True
    assert body["targeted_complete"] is True
    assert body["verdict"] == "PASS" and body["level"] == "HOST_TESTED"
    assert body["release_eligible"] is False
    assert body["binary_changed"]["known"] is False


def test_impact_release_tamper_is_a_finding(client, amr_ir_dict, tmp_path):
    after = copy.deepcopy(amr_ir_dict)
    after["control"]["max_linear_speed_mps"] = 0.9
    after_ir = validate_ir(after)
    manifest = codegen.generate(after_ir, tmp_path / "gen-rel-t")
    p = _passport(after_ir, manifest, "rel-t", {"status": "missing"})
    p["chain"][0]["body"]["ir_sha256"] = "0" * 64
    r = client.post("/impact/release",
                    json={"ir_before": amr_ir_dict, "ir_after": after,
                          "passport": p})
    # A broken chain is the answer (200 + chain_ok false), not a rejection.
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chain_ok"] is False
    assert body["evidence_current"] is False


def test_project_impact_between_revisions(client, amr_ir_dict):
    r = client.post("/projects", json={"from_example": "amr-demo",
                                       "from_file": "machine-ir.json"})
    assert r.status_code == 201, r.text
    pid = r.json()["pid"]
    changed = copy.deepcopy(amr_ir_dict)
    changed["control"]["max_linear_speed_mps"] = 0.9
    r = client.put(f"/projects/{pid}", json={"ir": changed})
    assert r.status_code == 200, r.text
    r = client.get(f"/projects/{pid}/impact?rev_from=1&rev_to=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["from"], body["to"]) == (1, 2)
    assert len(body["retest"]) == 8
    r = client.get(f"/projects/{pid}/impact?rev_from=2&rev_to=2")
    assert r.json()["retest"] == []
    assert client.get(f"/projects/{pid}/impact?rev_from=1&rev_to=9"
                      ).status_code == 404
    assert client.get("/projects/prj-000000000000/impact").status_code == 404
    assert client.get("/projects/nope/impact").status_code == 400
