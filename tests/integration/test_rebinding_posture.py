# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §8 remainder: DNS-rebinding / localhost-boundary posture pins.

Threat: a drive-by web page reaching the loopback API via DNS rebinding
(evil.test resolving to 127.0.0.1). Layers, each pinned here:
  1. serve binds 127.0.0.1, single worker (see test_serve_bind.py);
  2. no CORS middleware: preflighted cross-origin fetch earns no
     access-control-allow-origin, so the browser blocks it;
  3. Origin guard: simple cross-origin writes rejected 403
     (see test_jobs.py / test_projects_api.py / test_target_api.py);
  4. JSON-only writes: an Origin-less form POST dies at body
     validation (422) before any job/op exists;
  5. GET inventory below: every GET route was audited side-effect
     free (only idempotent store init). Adding a GET route fails
     this test until the audit list is extended deliberately.
Host-header validation was assessed and deliberately not added: with
1-5, no browser vector reaches a state change, and local processes are
trusted callers (docs/local-security-model.md).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    return api_mod.create_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as cli:
        yield cli


def test_preflight_earns_no_cors_allowance(client):
    r = client.options(
        "/jobs",
        headers={"Origin": "https://evil.test",
                 "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type"})
    assert "access-control-allow-origin" not in r.headers


def test_form_post_rejected_without_execution(client):
    r = client.post("/jobs", data={"example": "amr-demo",
                                   "run_id": "run-form-csrf"})
    assert r.status_code == 422
    assert client.get("/jobs").json() == {"jobs": []}


def test_unknown_export_creates_no_run_artifacts(client, tmp_path):
    assert client.get("/runs/does-not-exist/export").status_code == 404
    assert client.get("/projects/prj-000000000000/export").status_code == 404
    assert client.get("/runs").json() == {"runs": []}
    artifacts = tmp_path / "artifacts"
    run_dirs = [p for p in artifacts.iterdir() if p.name.startswith("run-")]
    assert run_dirs == []


# Audited 2026-11-05: each GET below performs no attacker-controlled
# side effect (reads + idempotent store init only). Extend deliberately.
# /docs, /redoc, /openapi.json, /docs/oauth2-redirect are FastAPI's
# default static API docs (read-only).
AUDITED_GET_ROUTES = [
    "/",
    "/dashboard.html",
    "/docs",
    "/docs/oauth2-redirect",
    "/env",
    "/examples",
    "/examples/{example}/{file}",
    "/genesis_verify.js",
    "/health",
    "/ipc-timeline",
    "/jobs",
    "/jobs/{job_id}",
    "/jobs/{job_id}/events",
    "/jobs/{job_id}/files",
    "/jobs/{job_id}/files/{name}",
    "/openapi.json",
    "/projects",
    "/projects/{pid}",
    "/projects/{pid}/diff",
    "/projects/{pid}/export",
    "/projects/{pid}/history",
    "/projects/{pid}/impact",
    "/projects/{pid}/revisions/{rev}",
    "/redoc",
    "/runs",
    "/runs/{run_id}",
    "/runs/{run_id}/export",
    "/runs/{run_id}/passport/raw",
    "/studio.html",
    "/target/ops",
    "/target/ops/compare",
    "/target/ops/compare/dossier",
    "/target/ops/{op_id}",
    "/target/ops/{op_id}/decision",
    "/target/ops/{op_id}/dossier",
    "/target/ops/{op_id}/events",
]


def test_get_route_inventory_matches_audit(app):
    paths = sorted({getattr(r, "path", "")
                    for r in app.routes
                    if "GET" in getattr(r, "methods", set())})
    assert paths == AUDITED_GET_ROUTES
