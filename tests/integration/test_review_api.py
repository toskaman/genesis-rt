# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: Wave 12 review endpoints (GET /ipc-timeline,
POST /review/plan). Payloads come from the committed capture and the
real proofos validator — no invented spans, no invented verdicts."""

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt.proofos import build_plan  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    app = api_mod.create_app()
    with TestClient(app) as cli:
        yield cli


def _change(**over):
    base = {"path": "examples/amr-demo/machine-ir.json", "status": "changed",
            "valid": True, "renamed_from": None,
            "ir_sha256_before": "a" * 64, "ir_sha256_after": "b" * 64,
            "limits_changed": True, "requirements_changed": 2,
            "retest": ["nominal_navigation"]}
    base.update(over)
    return base


def _plan(**over):
    kw = {"source_commit": "s" * 40, "base_commit": "b" * 40,
          "changes": [_change()]}
    kw.update(over)
    return build_plan(**kw)


def test_ipc_timeline_serves_committed_capture(client):
    r = client.get("/ipc-timeline")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["available"] is True
    assert body["instrumentation"] == "GENESIS_IPC_TRACE=1"
    assert "CLOCK_MONOTONIC" in body["clock"]
    assert len(body["trips"]) == 5
    first = body["trips"][0]
    assert first["seq"] == 1
    assert first["round_trip_us"] > 0
    assert first["guard_span_us"] > 0
    assert first["guard_span_us"] < first["round_trip_us"]
    assert first["device_span_us"] is None  # unmeasured: stays unknown
    assert first["decision"] in ("ALLOW", "DENY")
    assert any("QEMU" in w for w in body["warnings"])
    assert body["run_meta"]["port"] == 2222
    assert "qemu-system" in body["run_meta"]["qemu"]
    assert len(body["run_meta"]["binaries"]["genesis_guard"]) == 64


def test_ipc_timeline_spans_match_raw_nanoseconds(client):
    # Guard against render-layer drift: the served microsecond spans must
    # equal the raw ns deltas, not a recomputed fantasy.
    body = client.get("/ipc-timeline").json()
    for trip in body["trips"]:
        ns = trip["done_ns"] - trip["send_ns"]
        assert trip["round_trip_us"] == pytest.approx(ns / 1000.0, abs=0.001)
        gs = trip["reply_ns"] - trip["recv_ns"]
        assert trip["guard_span_us"] == pytest.approx(gs / 1000.0, abs=0.001)


def test_review_plan_valid_brief(client):
    r = client.post("/review/plan", json={"plan": _plan()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    assert sorted(body["summary"]) == [
        "can_accept", "residual_risks", "trust", "what_changed",
        "what_happened", "what_tested", "why_matters"]
    changed = body["summary"]["what_changed"]
    assert len(changed) == 1
    assert changed[0]["path"] == "examples/amr-demo/machine-ir.json"
    assert changed[0]["before"] == "a" * 12
    assert changed[0]["after"] == "b" * 12
    verdict = body["summary"]["can_accept"]
    assert verdict["eligible"] is False  # plan-time: never auto-release
    assert any("plan-time verdict" in r for r in verdict["reasons"])
    assert body["summary"]["what_tested"]["native_needed"] is True


def test_review_plan_invalid_fails_closed(client):
    r = client.post("/review/plan", json={"plan": {"bogus": True}})
    assert r.status_code == 400, r.text
    assert r.json()["valid"] is False
    assert r.json()["errors"]
    assert "summary" not in r.json()  # no verdict wording on failure


def test_review_plan_rejects_oversize_payload(client):
    big = {"plan_version": 1, "pad": "x" * (300 * 1024)}
    r = client.post("/review/plan", json={"plan": big})
    assert r.status_code == 400, r.text
    assert "too large" in r.text


def test_review_plan_rejects_non_object(client):
    r = client.post("/review/plan", json={"plan": [1, 2, 3]})
    assert r.status_code in (400, 422), r.text
