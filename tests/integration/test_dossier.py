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


OP2 = "op-ddddeeeeffff"
ALT_IR = "def456"


def _write_op(ops_dir: Path, op_id: str = OP, state: str = "COMPLETED",
              gate: str = "PASS", machine: str = "TestCell",
              params: dict | None = None,
              tamper_passport: bool = False,
              ir_digest: str = "abc123") -> Path:
    ops_dir.mkdir(parents=True, exist_ok=True)
    rec = {"op_id": op_id, "workflow": "full", "state": state,
           "params": params or {},
           "artifacts": {"qnx_verified": gate == "PASS" and state
                         == "COMPLETED", "ir_sha256": ir_digest,
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
         "ir": {"ir_sha256": ir_digest}}), encoding="utf-8")
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


def test_dossier_redacts_secret_values_and_runner_job(tmp_path):
    """Titan F4: secrets inside string values and runner-job.json."""
    ops = _write_op(tmp_path / "ops", params={
        "note": "token=tokval-9z9 see ?api_key=SEKKEY-8y8", "cmd": "plain"})
    blob = dos_mod.build_dossier_zip(
        ops, OP, job_record={"job_id": "job-1", "status": "COMPLETED",
                             "note": "password=hunter3"})
    files = _unzip(blob)
    bundled = files[f"dossier-{OP}/target-op.json"].decode("utf-8")
    assert "tokval-9z9" not in bundled and "SEKKEY-8y8" not in bundled
    assert "token=***REDACTED***" in bundled
    assert "plain" in bundled
    runjob = files[f"dossier-{OP}/runner-job.json"].decode("utf-8")
    assert "hunter3" not in runjob
    assert "password=***REDACTED***" in runjob


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
    _write_op(tmp_path / "artifacts" / "target-ops", op_id=OP2,
              state="FAILED", gate="FAIL", ir_digest=ALT_IR)
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
    assert a["gate_sealed"] is True
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


def test_assess_unsealed_op_not_sealed(tmp_path):
    # AFTER-style op: failed before SEALING, so no passport.json at all.
    ops = _write_op(tmp_path / "ops", state="FAILED", gate="FAIL")
    (ops / OP / "passport.json").unlink()
    files, rec, _red = dos_mod.collect_op_files(ops, OP)
    a = dos_mod.assess_op(OP, rec, files)
    assert a["verdict"] == "FAIL"
    assert a["gate"] == "UNKNOWN"
    assert a["gate_level"] == "not sealed"
    assert a["gate_sealed"] is False
    assert "passport.json" in a["missing_evidence"]


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


def test_compare_ops_diff(tmp_path):
    ops = _write_op(tmp_path / "ops")
    _write_op(ops, op_id=OP2, state="FAILED", gate="FAIL", ir_digest=ALT_IR)
    c = dos_mod.compare_ops(ops, None, OP, OP2)
    assert c["before"]["verdict"] == "PASS"
    assert c["after"]["verdict"] == "FAIL"
    d = c["diff"]
    assert d["ir_changed"] is True
    assert d["verdict_changed"] is True
    assert d["gate_changed"] is True
    assert d["release_changed"] is True
    assert d["toolchain_changed"] is False
    assert d["newly_failed"] == ["c2"]
    assert d["newly_passed"] == []
    assert (d["matrix_before"], d["matrix_after"]) == ("2/2", "1/2")


def test_compare_same_op_no_changes(tmp_path):
    ops = _write_op(tmp_path / "ops")
    d = dos_mod.compare_ops(ops, None, OP, OP)["diff"]
    assert d["ir_changed"] is d["verdict_changed"] is False
    assert d["newly_failed"] == d["newly_passed"] == []


def test_compare_toolchain_change_detected(tmp_path):
    ops = _write_op(tmp_path / "ops")
    _write_op(ops, op_id=OP2)
    (ops / OP2 / "qnx-build-record.json").write_text(json.dumps(
        {"environment": {"qcc_version": "qcc 12.3.0"}}), encoding="utf-8")
    d = dos_mod.compare_ops(ops, None, OP, OP2)["diff"]
    assert d["toolchain_changed"] is True
    assert d["verdict_changed"] is False


def test_endpoint_compare_roundtrip(client):
    r = client.get(f"/target/ops/compare?before={OP}&after={OP2}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["before"]["op_id"] == OP
    assert body["after"]["op_id"] == OP2
    assert body["diff"]["newly_failed"] == ["c2"]


def test_endpoint_compare_errors(client):
    assert client.get("/target/ops/compare?before=x&after=y").status_code \
        == 400
    assert client.get(f"/target/ops/compare?before={OP}"
                      "&after=op-000000000000").status_code == 404
    assert client.get(f"/target/ops/compare?before={OP}"
                      "&after=op-111111111111").status_code == 409


def _write_change_proof(ops, op_id, limit, decision, reason, sha, define):
    work = ops / op_id
    (work / "target" / "target-limits_differ.log").write_text(
        "$ echo ---PROBE-AMR---; probe 1.5; echo ---PROBE-CONV---\n"
        "---PROBE-AMR---\n"
        f"PROBE linear=1.500 estop=0 decision={decision} reason={reason} "
        "state=1\n---PROBE-CONV---\n"
        "PROBE linear=1.500 estop=0 decision=ALLOW reason=OK state=1\n"
        "[exit=0]\n",
        encoding="utf-8")
    (work / "gen").mkdir(exist_ok=True)
    (work / "gen" / "genesis_config_gen.h").write_text(
        f"#define GENESIS_MAX_LINEAR_MPS {define}\n", encoding="utf-8")
    (work / "qnx-build-record.json").write_text(json.dumps(
        {"environment": {"qcc_version": "qcc 12.2.0"},
         "binaries": {"genesis_guard": {"sha256": sha, "size": 1}}}),
        encoding="utf-8")
    rec_p = ops / f"{op_id}.json"
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    rec["params"] = {"ir": {"control": {"max_linear_speed_mps": limit}}}
    rec_p.write_text(json.dumps(rec), encoding="utf-8")


def test_compare_change_proof_rows(tmp_path):
    ops = _write_op(tmp_path / "ops")
    _write_op(ops, op_id=OP2)
    _write_change_proof(ops, OP, 1.2, "DENY", "SPEED_OVER_LIMIT",
                        "aa" * 32, "1.2")
    _write_change_proof(ops, OP2, 1.6, "ALLOW", "OK", "bb" * 32, "1.6")
    c = dos_mod.compare_ops(ops, None, OP, OP2)
    d = c["diff"]
    assert (d["limit_before"], d["limit_after"],
            d["limit_changed"]) == (1.2, 1.6, True)
    assert d["probe15_before"] == {"decision": "DENY",
                                   "reason": "SPEED_OVER_LIMIT"}
    assert d["probe15_after"] == {"decision": "ALLOW", "reason": "OK"}
    assert d["probe15_flipped"] is True
    assert (d["guard_sha_before"], d["guard_sha_after"],
            d["guard_sha_changed"]) == ("aa" * 32, "bb" * 32, True)
    assert (d["config_before"], d["config_after"],
            d["config_changed"]) == ("1.2", "1.6", True)
    assert c["before"]["change_proof"]["limit"] == 1.2


def test_compare_missing_proof_shows_unknown(tmp_path):
    ops = _write_op(tmp_path / "ops")
    d = dos_mod.compare_ops(ops, None, OP, OP)["diff"]
    assert d["probe15_before"] is None
    assert d["probe15_flipped"] is False
    assert d["limit_changed"] is False


def test_compare_zip_roundtrip(tmp_path):
    ops = _write_op(tmp_path / "ops")
    _write_op(ops, op_id=OP2)
    _write_change_proof(ops, OP, 1.2, "DENY", "SPEED_OVER_LIMIT",
                        "aa" * 32, "1.2")
    _write_change_proof(ops, OP2, 1.6, "ALLOW", "OK", "bb" * 32, "1.6")
    blob = dos_mod.build_compare_zip(ops, None, OP, OP2)
    got = _unzip(blob)
    names = sorted(n.split("/", 1)[1] for n in got)
    assert names == ["VERIFY.md", "after.json", "before.json",
                     "compare-report.html", "manifest.json"]
    html = got[f"compare-{OP}-vs-{OP2}/compare-report.html"].decode()
    assert "DENY" in html and "ALLOW" in html and "1.6" in html
    manifest = json.loads(
        got[f"compare-{OP}-vs-{OP2}/manifest.json"].decode())
    assert manifest["kind"] == "compare"
    for name, digest in manifest["files"].items():
        data = got[f"compare-{OP}-vs-{OP2}/{name}"]
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_endpoint_compare_dossier(client):
    r = client.get(f"/target/ops/compare/dossier?before={OP}&after={OP2}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert client.get("/target/ops/compare/dossier?before=x&after=y"
                      ).status_code == 400
    assert client.get("/target/ops/compare/dossier?before=op-000000000000"
                      f"&after={OP}").status_code == 404


def _report_for(ops_dir: Path, op_id: str = OP) -> str:
    blob = dos_mod.build_dossier_zip(ops_dir, op_id)
    files = _unzip(blob)
    return files[f"dossier-{op_id}/report.html"].decode("utf-8")


def test_dossier_report_has_toc_anchors_and_print_css(tmp_path):
    ops = _write_op(tmp_path / "ops")
    report = _report_for(ops)
    assert '<nav class="toc"' in report
    for anchor in ("summary", "why", "matrix", "replay", "impact",
                   "limitations"):
        assert f'href="#{anchor}"' in report, anchor
        assert f'<h2 id="{anchor}">' in report, anchor
    assert "@media print" in report


def test_dossier_coverage_unknown_for_old_passport(tmp_path):
    ops = _write_op(tmp_path / "ops")  # gate body without coverage
    report = _report_for(ops)
    assert "<td>Coverage</td>" in report
    assert "old passport without a coverage record" in report


def _write_targeted_op(ops_dir: Path) -> Path:
    ops_dir.mkdir(parents=True, exist_ok=True)
    rec = {"op_id": OP, "workflow": "full", "state": "COMPLETED",
           "params": {},
           "artifacts": {"qnx_verified": True, "ir_sha256": "abc123",
                         "replay": "MATCH"}}
    (ops_dir / f"{OP}.json").write_text(json.dumps(rec), encoding="utf-8")
    (ops_dir / f"{OP}.events.jsonl").write_text(
        '{"seq": 0, "kind": "op_started"}\n', encoding="utf-8")
    work = ops_dir / OP
    (work / "target").mkdir(parents=True)
    (work / "perf").mkdir(parents=True)
    (work / "ir.json").write_text(json.dumps(_ir()), encoding="utf-8")
    pp = build_passport(
        OP, _ir(), {"ir_sha256": "abc123", "sources": ["gen.c"]},
        [{"scenario": "nominal", "seed": 1000, "status": "pass",
          "checks": [{"name": "c1", "passed": True}], "stats": {},
          "trace": []}],
        qnx_build={"status": "ok"},
        qnx_target={"checks": [{"name": "c1", "passed": True,
                                "detail": "ok"}]},
        qnx_perf={"raw_samples_us": [1.0], "method": "target_clock"})
    attach_verdict(pp, {"verdict": "PASS", "tier": "QNX_EXECUTED",
                        "coverage": {"declared": 8, "required": 3,
                                     "omitted": ["s4", "s5", "s6", "s7",
                                                 "s8"]}})
    (work / "passport.json").write_text(json.dumps(pp), encoding="utf-8")
    (work / "target" / "qnx-target-record.json").write_text(json.dumps(
        {"checks": [{"name": "c1", "passed": True, "detail": "ok"}],
         "ir": {"ir_sha256": "abc123"}}), encoding="utf-8")
    (work / "perf" / "qnx-perf-record.json").write_text(json.dumps(
        {"raw_samples_us": [1.0], "method": "target_clock"}),
        encoding="utf-8")
    (work / "qnx-build-record.json").write_text(json.dumps(
        {"environment": {"qcc_version": "qcc 12.2.0"}}), encoding="utf-8")
    return ops_dir


def test_dossier_targeted_coverage_rendered(tmp_path):
    ops = _write_targeted_op(tmp_path / "ops")
    report = _report_for(ops)
    assert "TARGETED" in report
    assert "full verification PENDING" in report
    assert "3 of 8" in report
    assert "s4" in report  # omitted scenarios named


def test_coverage_of_tolerates_shapes():
    full = dos_mod._coverage_of(
        {"coverage": {"declared": 8, "required": 8, "omitted": []}})
    assert full == {"declared": 8, "required": 8, "omitted": [],
                    "targeted": False}
    listed = dos_mod._coverage_of(
        {"coverage": {"declared": ["a", "b"], "required": ["a"],
                      "omitted": ["b"]}})
    assert listed["declared"] == 2 and listed["required"] == 1
    assert listed["targeted"] is True
    weird = dos_mod._coverage_of({"coverage": {"declared": None,
                                               "required": True,
                                               "omitted": "x"}})
    assert weird["declared"] == "?" and weird["required"] == "?"
    assert weird["omitted"] == [] and weird["targeted"] is False
    missing = dos_mod._coverage_of({})
    assert missing["targeted"] is None


def _job(op_id=OP):
    return {"job_id": "ci-42", "status": "COMPLETED",
            "operation": "native_full", "revision": "f" * 40,
            "ir_sha256": "abc123", "plan_id": "plan-1",
            "adapter": "local", "op_id": op_id,
            "qnx_verified": True}


def test_dossier_embeds_runner_job(tmp_path):
    ops = _write_op(tmp_path / "ops")
    blob = dos_mod.build_dossier_zip(ops, OP, job_record=_job())
    files = _unzip(blob)
    body = files[f"dossier-{OP}/runner-job.json"].decode("utf-8")
    assert json.loads(body)["job_id"] == "ci-42"
    report = files[f"dossier-{OP}/report.html"].decode("utf-8")
    assert "ci-42" in report and "ffffffffffff" in report
    assert "runner-job.json" in report
    manifest = json.loads(files[f"dossier-{OP}/manifest.json"])
    assert f"runner-job.json" in manifest["files"]


def test_dossier_without_job_says_local(tmp_path):
    ops = _write_op(tmp_path / "ops")
    blob = dos_mod.build_dossier_zip(ops, OP)
    files = _unzip(blob)
    assert f"dossier-{OP}/runner-job.json" not in files
    report = files[f"dossier-{OP}/report.html"].decode("utf-8")
    assert "no runner job linked" in report


def test_dossier_escapes_job_fields(tmp_path):
    ops = _write_op(tmp_path / "ops")
    job = _job()
    job["job_id"] = "<img src=x>"
    blob = dos_mod.build_dossier_zip(ops, OP, job_record=job)
    report = _unzip(blob)[f"dossier-{OP}/report.html"].decode("utf-8")
    assert "<img" not in report and "&lt;img" in report


def test_find_job_by_op(tmp_path):
    from genesis_rt.runner import find_job_by_op

    jobs = tmp_path / "jobs"
    jobs.mkdir()
    (jobs / "job-ci-42.json").write_text(json.dumps(_job()),
                                          encoding="utf-8")
    (jobs / "job-other.json").write_text(json.dumps(_job(OP2)),
                                          encoding="utf-8")
    (jobs / "job-broken.json").write_text("{oops", encoding="utf-8")
    found = find_job_by_op(jobs, OP)
    assert found and found["job_id"] == "ci-42"
    assert find_job_by_op(jobs, "op-000000000000") is None
    assert find_job_by_op(jobs, "not-an-op") is None
    assert find_job_by_op(tmp_path / "missing", OP) is None
