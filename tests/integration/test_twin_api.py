# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: twin endpoint (POST /twin/frames)."""
import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt import evidence, faultlab, gate  # noqa: E402
from genesis_rt.twin import verify_track  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def _passport(amr_ir, bound_evidence):
    results = faultlab.run_all(amr_ir, ["corrupted_message"])
    p = evidence.build_passport("run-twinapi", amr_ir,
                                bound_evidence["manifest"], results,
                                bound_evidence["build"], None)
    return evidence.attach_verdict(p, gate.evaluate(p, ["corrupted_message"]))


def test_twin_frames_dict_and_raw_text(client, amr_ir, bound_evidence):
    passport = _passport(amr_ir, bound_evidence)
    for payload in (passport, __import__("json").dumps(passport)):
        r = client.post("/twin/frames",
                        json={"passport": payload,
                              "scenario": "corrupted_message"})
        assert r.status_code == 200, r.text
        track = r.json()
        assert track["kind"] == "diff"
        assert track["scenario"] == "corrupted_message"
        assert track["interp"] == "stepwise-hold"
        assert track["frames"] and track["markers"]
        assert verify_track(track) == []


def test_twin_frames_unknown_scenario_is_400(client, amr_ir, bound_evidence):
    passport = _passport(amr_ir, bound_evidence)
    r = client.post("/twin/frames",
                    json={"passport": passport, "scenario": "missing"})
    assert r.status_code == 400
    assert "corrupted_message" in r.text


def test_twin_frames_tampered_chain_is_409(client, amr_ir, bound_evidence):
    passport = _passport(amr_ir, bound_evidence)
    passport["chain"][0]["body"]["ir_sha256"] = "00" * 32
    r = client.post("/twin/frames",
                    json={"passport": passport,
                          "scenario": "corrupted_message"})
    assert r.status_code == 409
