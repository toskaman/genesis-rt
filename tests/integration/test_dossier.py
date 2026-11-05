# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 10 Sprint B (F6): one-click engineering dossier export.

Builder + endpoint tests over synthetic terminal ops: PASS/FAIL/NOT
VERIFIED display logic, tamper visibility, HTML escaping, secret
redaction, size caps, and HTTP error mapping.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt import dossier as dos_mod  # noqa: E402
from genesis_rt.evidence import attach_verdict, build_passport  # noqa: E402

OP = "op-aaaabbbbcccc"


def _ir(machine="TestCell"):
    return {"schema_version": 1, "machine": {"name": machine, "kind": "cell"},
            "verification": {"scenarios": ["nominal"]}}


def _passport(op_id, gate="PASS"):
    pp = build_passport(
        op_id, _ir(),
        {"ir_sha256": "abc123", "sources": ["gen.c"]},
        [{"scenario": "nominal", "seed": 1000, "status": "pass",
          "checks": [{"name": "c1", "passed": True}], "stats": {},
          "trace": []}],
        qnx_build={"status": "ok"},
        qnx_target={"checks": [{"name": "c1", "passed": True,
                                "detail": "ok"}]},
        qnx_perf={"raw_samples_us": [1.0, 2.0], "method": "target_clock"})
    return attach_verdict(pp, {"verdict": gate, "tier": "QNX_EXECUTED"})


def _write_op(ops_dir: Path, op_id: str = OP, state: str = "COMPLETED",
              gate: str = "PASS", machine: str = "TestCell",
              params: dict | None = None,
              tamper_passport: bool = False) -> Path:
    ops_dir.mkdir(parents=True, exist_ok=True)
    rec = {"op_id": op_id, "workflow": "full", "state": state,
           "params": params or {},
           "artifacts": {"qnx_verified": gate == "PASS" and state
                         == "COMPLETED", "ir_sha256": "abc123",
                         "replay": "MATCH"}}
    (ops_dir / f"{op_id}.json").write_text(json.dumps(rec), encoding="utf-8")
    (ops_dir / f"{op_id}.events.jsonl").write_text(
        '{"seq": 0, "kind": "op_started"}\n', encoding="utf-8")
    work = ops_dir / op_id
    (work / "target").mkdir(parents=True)
    (work / "perf").mkdir(parents=True)
    ir = _ir(machine)
    (work / "ir.json").write_text(json.dumps(ir), encoding="utf-8")
    pp = _passport(op_id, gate)
    if tamper_passport:
        pp["chain"][1]["body"]["ir_sha256"] = "EVIL"
    (work / "passport.json").write_text(json.dumps(pp), encoding="utf-8")
    (work / "target" / "qnx-target-record.json").write_text(json.dumps(
        {"checks": [{"name": "c1", "passed": True, "detail": "ok"},
                    {"name": "c2", "passed": gate == "PASS",
                     "detail": "ok" if gate == "PASS" else "boom"}],
         "ir": {"ir_sha256": "abc123"}}), encoding="utf-8")
    (work / "target" / "target-c1.log").write_text("target ran c1\n",
                                                  encoding="utf-8")
    (work / "perf" / "qnx-perf-record.json").write_text(json.dumps(
        {"raw_samples_us": [1.0, 2.0], "method": "target_clock"}),
        encoding="utf-8")
    (work / "qnx-build-record.json").write_text(json.dumps(
        {"environment": {"qcc_version": "qcc 12.2.0"}}), encoding="utf-8")
    (work / "qemu-console.log").write_text("boot ok\n", encoding="utf-8")
    return ops_dir


def _unzip(blob: bytes) -> dict[str, bytes]:
    out = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            assert ".." not in name and not name.startswith("/"), name
            out[name] = zf.read(name)
    return out


def test_dossier_pass_op(tmp_path):
    ops = _write_op(tmp_path / "ops")
    blob = dos_mod.build_dossier_zip(ops, OP)
    files = _unzip(blob)
    prefix = f"dossier-{OP}/"
    assert f"{prefix}report.html" in files
    assert f"{prefix}manifest.json" in files
    assert f"{prefix}VERIFY.md" in files
    manifest = json.loads(files[f"{prefix}manifest.json"].decode("utf-8"))
    assert manifest["op_id"] == OP
    for name, digest in manifest["files"].items():
        assert hashlib.sha256(files[prefix + name]).hexdigest() == digest
    report = files[f"{prefix}report.html"].decode("utf-8")
    assert 'badge pass">PASS' in report
    assert "2/2 checks passed" in report
    assert "TestCell" in report
    assert "chain replays clean" in report


def test_dossier_failed_op_shows_fail(tmp_path):
    ops = _write_op(tmp_path / "ops", state="FAILED", gate="FAIL")
    files, rec, redacted = dos_mod.collect_op_files(ops, OP)
    report, verdict = dos_mod.render_report(OP, rec, files, redacted)
    assert verdict == "FAIL"
    assert 'badge fail">FAIL' in report
    assert "badge pass" not in report
    assert "1/2 checks passed" in report


def test_dossier_tampered_passport_never_green(tmp_path):
    ops = _write_op(tmp_path / "ops", tamper_passport=True)
    blob = dos_mod.build_dossier_zip(ops, OP)
    report = _unzip(blob)[f"dossier-{OP}/report.html"].decode("utf-8")
    assert "NOT VERIFIED" in report
    assert "badge pass" not in report
    assert "replay" in report.lower() and "FAIL" in report


def test_dossier_non_terminal_409(tmp_path):
    ops = _write_op(tmp_path / "ops", state="EXECUTING")
    with pytest.raises(dos_mod.DossierError) as ei:
        dos_mod.build_dossier_zip(ops, OP)
    assert ei.value.status == 409


def test_dossier_unknown_op_404(tmp_path):
    (tmp_path / "ops").mkdir()
    with pytest.raises(dos_mod.DossierError) as ei:
        dos_mod.build_dossier_zip(tmp_path / "ops", OP)
    assert ei.value.status == 404


def test_dossier_escapes_html(tmp_path):
    evil = "<script>alert(1)</script>"
    ops = _write_op(tmp_path / "ops", machine=evil)
    blob = dos_mod.build_dossier_zip(ops, OP)
    report = _unzip(blob)[f"dossier-{OP}/report.html"].decode("utf-8")
    assert "<script>" not in report
    assert "&lt;script&gt;" in report


def test_dossier_redacts_secrets(tmp_path):
    ops = _write_op(tmp_path / "ops", params={
        "api_token": "hunter2", "nested": {"password": "s3cret"}})
    blob = dos_mod.build_dossier_zip(ops, OP)
    files = _unzip(blob)
    bundled = files[f"dossier-{OP}/target-op.json"].decode("utf-8")
    assert "hunter2" not in bundled and "s3cret" not in bundled
    assert "***REDACTED***" in bundled
    manifest = json.loads(files[f"dossier-{OP}/manifest.json"]
                          .decode("utf-8"))
    assert "params.api_token" in manifest["redacted_keys"]


def test_dossier_size_cap_413(tmp_path):
    ops = _write_op(tmp_path / "ops")
    (ops / OP / "target" / "big.log").write_bytes(b"x" * (26 * 1024 * 1024))
    with pytest.raises(dos_mod.DossierError) as ei:
        dos_mod.build_dossier_zip(ops, OP)
    assert ei.value.status == 413


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "ARTIFACTS", tmp_path / "artifacts")
    _write_op(tmp_path / "artifacts" / "target-ops")
    ops = _write_op(tmp_path / "artifacts" / "target-ops",
                    op_id="op-111111111111", state="EXECUTING")
    # Live owner + fresh heartbeat: crash recovery must spare this op so
    # the endpoint exercises its 409 (non-terminal) path.
    live_p = ops / "op-111111111111.json"
    live = json.loads(live_p.read_text(encoding="utf-8"))
    live["owner_pid"] = os.getpid()
    live["updated"] = time.time()
    live_p.write_text(json.dumps(live), encoding="utf-8")
    with TestClient(api_mod.create_app()) as cli:
        yield cli


def test_endpoint_dossier_roundtrip(client):
    r = client.get(f"/target/ops/{OP}/dossier")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert f"dossier-{OP}.zip" in r.headers["content-disposition"]
    files = _unzip(r.content)
    assert f"dossier-{OP}/report.html" in files


def test_endpoint_dossier_errors(client):
    assert client.get("/target/ops/not-an-id/dossier").status_code == 400
    assert client.get("/target/ops/op-000000000000/dossier").status_code \
        == 404
    assert client.get("/target/ops/op-111111111111/dossier").status_code \
        == 409


def test_assess_pass_op(tmp_path):
    ops = _write_op(tmp_path / "ops")
    files, rec, _red = dos_mod.collect_op_files(ops, OP)
    a = dos_mod.assess_op(OP, rec, files)
    assert a["verdict"] == "PASS"
    assert a["release_eligible"] is True
    assert a["gate_level"] == "QNX_EXECUTED"  # legacy tier fallback
    assert a["matrix"] == {"passed": 2, "total": 2, "failed": []}
    assert a["perf_samples"] == 2
    assert a["missing_evidence"] == [] and a["chain_errors"] == []
    assert a["why"] == ["all gates green: COMPLETED + gate PASS + "
                        "QNX-verified + clean replay"]


def test_assess_failed_op_explains_why(tmp_path):
    ops = _write_op(tmp_path / "ops", state="FAILED", gate="FAIL")
    files, rec, _red = dos_mod.collect_op_files(ops, OP)
    a = dos_mod.assess_op(OP, rec, files)
    assert a["verdict"] == "FAIL"
    assert a["release_eligible"] is False
    assert "op did not complete (state FAILED)" in a["why"]
    assert "gate verdict is FAIL, not PASS" in a["why"]
    assert "not QNX-verified (host-only or unverified target run)" \
        in a["why"]
    assert "native check failed: c2" in a["why"]
    # Report and endpoint share the same assessment.
    report, verdict = dos_mod.render_report(OP, rec, files, _red)
    assert verdict == "FAIL"
    assert "Why this verdict" in report
    assert "native check failed: c2" in report


def test_assess_tampered_op_not_verified(tmp_path):
    ops = _write_op(tmp_path / "ops", tamper_passport=True)
    files, rec, _red = dos_mod.collect_op_files(ops, OP)
    a = dos_mod.assess_op(OP, rec, files)
    assert a["verdict"] == "NOT VERIFIED"
    assert a["release_eligible"] is False
    assert any(w.startswith("evidence replay failed:") for w in a["why"])


def test_endpoint_decision_roundtrip(client):
    r = client.get(f"/target/ops/{OP}/decision")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["op_id"] == OP and body["verdict"] == "PASS"
    assert body["release_eligible"] is True
    assert body["matrix"] == {"passed": 2, "total": 2, "failed": []}
    assert isinstance(body["why"], list) and body["why"]
    assert body["chain_errors"] == []


def test_endpoint_decision_errors(client):
    assert client.get("/target/ops/not-an-id/decision").status_code == 400
    assert client.get("/target/ops/op-000000000000/decision").status_code \
        == 404
