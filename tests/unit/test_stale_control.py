# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""OMEGA7 B-13: stale-control workflow (sealed negative control).

Host-only tests: fake the SSH/QEMU boundary (cmd_verify), run the real
verify/seal/replay steps, build a control pack from a fixture op, and
verify it offline. No QNX SDK, no QEMU, no credentials needed.
"""
import json
import sys
import time
from pathlib import Path

import pytest

from genesis_rt import target as tgt
from genesis_rt.codegen import ir_sha256
from genesis_rt.provenance import EXPECTED_TARGET_CHECKS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_evidence_pack as packer  # noqa: E402
import verify_evidence_pack as verifier  # noqa: E402

REFUSAL = ["estop_target", "v2_transitions"]


@pytest.fixture()
def runner(tmp_path):
    r = tgt.TargetRunner(tmp_path / "ops", tmp_path / "target.lock")
    try:
        yield r
    finally:
        r.close()


def _record(failing, ir_sha="0" * 64):
    bad = set(failing)
    return {
        "status": "fail" if bad else "pass",
        "verified_on_target": False,
        "provenance_version": 2,
        "provenance_error": None,
        "ir": {"ir_sha256": ir_sha},
        "matrix": list(EXPECTED_TARGET_CHECKS),
        "checks": [{"name": n, "passed": n not in bad, "detail": ""}
                   for n in EXPECTED_TARGET_CHECKS],
        "transcripts": {n: "ab" * 32 for n in EXPECTED_TARGET_CHECKS},
    }


def _write_record(work: Path, failing, ir_sha="0" * 64):
    target = work / "target"
    target.mkdir(parents=True, exist_ok=True)
    rec = _record(failing, ir_sha)
    (target / "qnx-target-record.json").write_text(json.dumps(rec),
                                                   encoding="utf-8")
    (target / "target-estop_target.log").write_text("refused as designed\n",
                                                    encoding="utf-8")
    return rec


def _write_manifest(work: Path):
    man = {"created_utc": "2026-11-10T00:00:00+00:00", "dest": "/tmp/genesis",
           "files": {"genesis_guard": {"sha256": "aa" * 32, "size": 8,
                                       "cksum": 1}}}
    (work / "stage-manifest.json").write_text(json.dumps(man), encoding="utf-8")


def _ctx(tmp_path, amr_ir, failing, ir_sha="0" * 64, refusal=None):
    work = tmp_path / "w"
    work.mkdir(exist_ok=True)
    _write_record(work, failing, ir_sha)
    _write_manifest(work)
    return {"op_id": "op-seal-test",
            "params": {"ir": amr_ir,
                       "expect_refusal": (REFUSAL if refusal is None
                                          else refusal)},
            "work_dir": str(work), "artifacts": {}}


class _FakeQt:
    """Fake qnx_target boundary: configurable rc + fixture record."""

    def __init__(self, rc, failing):
        self.rc = rc
        self.failing = failing
        self.seen = {}

    def cmd_verify(self, args):
        self.seen["ir"] = args.ir
        self.seen["build_set"] = args.build_set
        self.seen["require_manifest"] = args.require_manifest
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        try:
            bound = json.loads(Path(args.ir).read_text(encoding="utf-8"))
            sha = ir_sha256(bound)
        except (OSError, ValueError):
            sha = "0" * 64
        (out / "qnx-target-record.json").write_text(
            json.dumps(_record(self.failing, sha)), encoding="utf-8")
        (out / "target-estop_target.log").write_text("refused as designed\n",
                                                     encoding="utf-8")
        return self.rc


def _poll_state(r, op_id, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = r.get(op_id)
        assert rec is not None
        if rec["state"] in tgt.TERMINAL_TARGET:
            return rec
        time.sleep(0.05)
    raise AssertionError(f"op {op_id} never settled: {r.get(op_id)}")


# -- workflow registration + params ------------------------------------

def test_stale_control_workflow_registered_with_impls():
    assert tgt.STALE_CONTROL_WORKFLOW == "stale-control"
    steps = tgt.WORKFLOWS["stale-control"]
    assert "qemu_verify_stale" in steps
    assert "seal_stale" in steps
    assert "generate" not in steps and "build" not in steps
    missing = [s for s in steps if s not in tgt.STEP_IMPLS]
    assert missing == []


def test_other_workflows_unchanged():
    assert tgt.WORKFLOWS["full"].count("seal") == 1
    assert "qemu_verify_stale" not in tgt.WORKFLOWS["full"]
    assert "seal_stale" not in tgt.WORKFLOWS["build-only"]
    assert "expect_refusal" not in tgt.WORKFLOWS["verify-only"]


@pytest.mark.parametrize("bad", [[], "estop_target", ["nope"], ["estop_target",
                                                                "estop_target"],
                                 [""], [1], ["ESTOP_TARGET"]])
def test_expect_refusal_rejects_bad_values(runner, tmp_path, amr_ir, bad):
    img = tmp_path / "img"
    img.mkdir()
    with pytest.raises(tgt.TargetOpError):
        runner.start("stale-control",
                     params={"ir": amr_ir, "image_dir": str(img),
                             "expect_refusal": bad})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


def test_stale_control_requires_expect_refusal(runner, tmp_path, amr_ir):
    img = tmp_path / "img"
    img.mkdir()
    with pytest.raises(tgt.TargetOpError, match="expect_refusal"):
        runner.start("stale-control",
                     params={"ir": amr_ir, "image_dir": str(img)})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


def test_unknown_param_still_rejected(runner, tmp_path, amr_ir):
    img = tmp_path / "img"
    img.mkdir()
    with pytest.raises(tgt.TargetOpError):
        runner.start("stale-control",
                     params={"ir": amr_ir, "image_dir": str(img),
                             "expect_refusal": REFUSAL, "rm_rf": "/"})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


# -- qemu_verify_stale ---------------------------------------------------

def test_verify_stale_exact_shape_ok(tmp_path, amr_ir, monkeypatch):
    fake = _FakeQt(rc=1, failing=REFUSAL)
    monkeypatch.setattr(tgt, "_qt", lambda: fake)
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test", "params": {"ir": amr_ir},
           "work_dir": str(work), "artifacts": {}}
    ctx["params"]["expect_refusal"] = REFUSAL
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is True, detail
    assert "estop_target" in detail and "v2_transitions" in detail
    assert (work / "ir.json").is_file()
    assert ctx["artifacts"]["stale_refusal"] == {
        "expected": REFUSAL, "failed": REFUSAL,
        "passed": 14, "total": 16}


def test_verify_stale_green_matrix_invalid(tmp_path, amr_ir, monkeypatch):
    fake = _FakeQt(rc=0, failing=[])
    monkeypatch.setattr(tgt, "_qt", lambda: fake)
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is False
    assert "INVALID" in detail


def test_verify_stale_transport_rc_refused(tmp_path, amr_ir, monkeypatch):
    fake = _FakeQt(rc=2, failing=REFUSAL)
    monkeypatch.setattr(tgt, "_qt", lambda: fake)
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is False
    assert "rc=2" in detail


@pytest.mark.parametrize("failing", [["estop_target"],
                                     ["estop_target", "v2_transitions",
                                      "target_info"],
                                     ["target_info", "faultinject"], []])
def test_verify_stale_wrong_shape_refused(tmp_path, amr_ir, monkeypatch,
                                          failing):
    fake = _FakeQt(rc=1, failing=failing)
    monkeypatch.setattr(tgt, "_qt", lambda: fake)
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is False
    assert "refusing to seal" in detail


def test_verify_stale_partial_matrix_refused(tmp_path, amr_ir, monkeypatch):
    class _Partial(_FakeQt):
        def cmd_verify(self, args):
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            rec = _record(REFUSAL)
            rec["checks"] = rec["checks"][:15]
            (out / "qnx-target-record.json").write_text(json.dumps(rec),
                                                        encoding="utf-8")
            return 1

    monkeypatch.setattr(tgt, "_qt", lambda: _Partial(1, REFUSAL))
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is False
    assert "16-check" in detail


def test_verify_stale_missing_record_refused(tmp_path, amr_ir, monkeypatch):
    class _Silent:
        def cmd_verify(self, args):
            Path(args.out).mkdir(parents=True, exist_ok=True)
            return 1

    monkeypatch.setattr(tgt, "_qt", lambda: _Silent())
    work = tmp_path / "w"
    work.mkdir()
    ctx = {"op_id": "op-verify-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_qemu_verify_stale(ctx)
    assert ok is False
    assert "without a target record" in detail


# -- seal_stale ----------------------------------------------------------

def test_seal_stale_ok_and_replay_matches(tmp_path, amr_ir):
    from genesis_rt.projects import validate_any
    _, valid = validate_any(amr_ir)
    ctx = _ctx(tmp_path, amr_ir, REFUSAL, ir_sha256(valid))
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is True, detail
    assert ctx["artifacts"]["verdict"] == "FAIL"
    assert ctx["artifacts"]["qnx_verified"] is False
    assert ctx["artifacts"]["wanted"] == []
    assert ctx["artifacts"]["stale_refusal"]["failed"] == REFUSAL
    passport = json.loads(Path(ctx["artifacts"]["passport"])
                          .read_text(encoding="utf-8"))
    assert passport["gate"] == "FAIL"
    ctl = next(r["body"] for r in passport["chain"]
               if r["kind"] == "stale_control")
    assert ctl["expected_refusal"] == REFUSAL
    assert ctl["failed_checks"] == REFUSAL
    assert ctl["matrix"] == "14/16"
    ok, detail = tgt._step_replay(ctx)
    assert ok is True, detail
    assert ctx["artifacts"]["replay"]["verdict"] == "FAIL"


def test_seal_stale_v2_ir_ok(tmp_path, repo_root):
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json")
                    .read_text(encoding="utf-8"))
    from genesis_rt.projects import validate_any
    _, valid = validate_any(v2)
    ctx = _ctx(tmp_path, v2, REFUSAL, ir_sha256(valid))
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is True, detail
    ok, detail = tgt._step_replay(ctx)
    assert ok is True, detail


def test_seal_stale_wrong_shape_refused(tmp_path, amr_ir):
    ctx = _ctx(tmp_path, amr_ir, ["estop_target"])
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is False
    assert "refusing to seal" in detail


def test_seal_stale_missing_record_refused(tmp_path, amr_ir):
    work = tmp_path / "w"
    work.mkdir()
    _write_manifest(work)
    ctx = {"op_id": "op-seal-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is False
    assert "no target record" in detail


def test_seal_stale_missing_manifest_refused(tmp_path, amr_ir):
    work = tmp_path / "w"
    work.mkdir()
    _write_record(work, REFUSAL)
    ctx = {"op_id": "op-seal-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is False
    assert "no stage manifest" in detail


def test_seal_stale_empty_manifest_refused(tmp_path, amr_ir):
    work = tmp_path / "w"
    work.mkdir()
    _write_record(work, REFUSAL)
    (work / "stage-manifest.json").write_text(json.dumps({"files": {}}),
                                              encoding="utf-8")
    ctx = {"op_id": "op-seal-test",
           "params": {"ir": amr_ir, "expect_refusal": REFUSAL},
           "work_dir": str(work), "artifacts": {}}
    ok, detail = tgt._step_seal_stale(ctx)
    assert ok is False
    assert "no files" in detail


# -- evidence.append_record guards ----------------------------------------

def test_append_record_guards():
    from genesis_rt import evidence as ev
    from genesis_rt import gate
    passport = {"passport_version": ev.PASSPORT_VERSION, "run_id": "op-x",
                "chain": []}
    ev.append_record(passport, "ir", {"a": 1})
    with pytest.raises(ValueError, match="duplicate"):
        ev.append_record(passport, "ir", {"a": 2})
    with pytest.raises(ValueError, match="must be an object"):
        ev.append_record(passport, "nope", [])  # type: ignore[arg-type]
    verdict = gate.evaluate(passport, [])
    ev.attach_verdict(passport, verdict)
    with pytest.raises(ValueError, match="already sealed"):
        ev.append_record(passport, "late", {})
    assert ev.verify_chain(passport) == []


# -- full op loop: runner -> pack -> offline verify ------------------------

def _stale_impls(monkeypatch, failing):
    real = tgt._qt()
    fake = _FakeQt(rc=1, failing=failing)
    fake.TargetLock = real.TargetLock
    monkeypatch.setattr(tgt, "_qt", lambda: fake)

    def _put(ctx):
        _write_manifest(Path(ctx["work_dir"]))
        return (True, "staged fixture manifest")

    def _boot(ctx):
        (Path(ctx["work_dir"]) / "qemu-console.log").write_text(
            "QEMU fixture boot\nlogin:\n", encoding="utf-8")
        return (True, "fixture boot")

    return {"env": lambda ctx: (True, "fixture env"),
            "probe_image": lambda ctx: (True, "fixture probe"),
            "qemu_boot": _boot,
            "wait_ssh": lambda ctx: (True, "fixture ssh"),
            "qemu_put": _put,
            "qemu_stop": lambda ctx: (True, "fixture stop")}


def test_runner_completes_exact_refusal(runner, tmp_path, amr_ir, monkeypatch):
    img = tmp_path / "img"
    img.mkdir()
    rec = runner.start("stale-control",
                       params={"ir": amr_ir, "image_dir": str(img),
                               "expect_refusal": REFUSAL},
                       step_impls=_stale_impls(monkeypatch, REFUSAL))
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED", final
    assert final["artifacts"]["verdict"] == "FAIL"
    assert final["artifacts"]["stale_refusal"]["failed"] == REFUSAL
    assert final["artifacts"]["replay"]["verdict"] == "FAIL"


def test_runner_fails_wrong_shape(runner, tmp_path, amr_ir, monkeypatch):
    img = tmp_path / "img"
    img.mkdir()
    rec = runner.start("stale-control",
                       params={"ir": amr_ir, "image_dir": str(img),
                               "expect_refusal": REFUSAL},
                       step_impls=_stale_impls(monkeypatch, ["target_info"]))
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "FAILED", final
    assert "refusing to seal" in final["reason"]


def test_pack_and_verify_roundtrip(runner, tmp_path, amr_ir, monkeypatch,
                                   capsys):
    img = tmp_path / "img"
    img.mkdir()
    rec = runner.start("stale-control",
                       params={"ir": amr_ir, "image_dir": str(img),
                               "expect_refusal": REFUSAL},
                       step_impls=_stale_impls(monkeypatch, REFUSAL))
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED", final
    ops_dir = tmp_path / "ops"
    pack = tmp_path / "pack"
    rc = packer.main(["--op", rec["op_id"], "--ops-dir", str(ops_dir),
                      "--out", str(pack), "--commit", "test123"])
    assert rc == 0, capsys.readouterr()
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["control"] == "stale"
    assert not [f for f in manifest["files"] if f.startswith("performance/")]
    expected = (pack / "EXPECTED_RESULTS.md").read_text(encoding="utf-8")
    assert "observed refusal: ['estop_target', 'v2_transitions']" in expected
    assert "FAIL is expected" in expected
    assert "14/16" in expected
    capsys.readouterr()
    assert verifier.main(["verify.py", str(pack)]) == 0
    out = capsys.readouterr().out
    assert "VERIFY OK" in out
    assert "refusal=['estop_target', 'v2_transitions']" in out


def test_verify_rejects_tampered_stale_pack(runner, tmp_path, amr_ir,
                                            monkeypatch, capsys):
    img = tmp_path / "img"
    img.mkdir()
    rec = runner.start("stale-control",
                       params={"ir": amr_ir, "image_dir": str(img),
                               "expect_refusal": REFUSAL},
                       step_impls=_stale_impls(monkeypatch, REFUSAL))
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED", final
    pack = tmp_path / "pack"
    rc = packer.main(["--op", rec["op_id"], "--ops-dir", str(tmp_path / "ops"),
                      "--out", str(pack), "--commit", "test123"])
    assert rc == 0, capsys.readouterr()
    log = pack / "transcripts" / "target-estop_target.log"
    log.write_text(log.read_text(encoding="utf-8") + "tampered\n",
                   encoding="utf-8")
    capsys.readouterr()
    assert verifier.main(["verify.py", str(pack)]) == 2
    assert "digest mismatch" in capsys.readouterr().out


def test_verify_rejects_claim_mismatch_stale_pack(runner, tmp_path, amr_ir,
                                                  monkeypatch, capsys):
    import hashlib
    img = tmp_path / "img"
    img.mkdir()
    rec = runner.start("stale-control",
                       params={"ir": amr_ir, "image_dir": str(img),
                               "expect_refusal": REFUSAL},
                       step_impls=_stale_impls(monkeypatch, REFUSAL))
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED", final
    pack = tmp_path / "pack"
    rc = packer.main(["--op", rec["op_id"], "--ops-dir", str(tmp_path / "ops"),
                      "--out", str(pack), "--commit", "test123"])
    assert rc == 0, capsys.readouterr()
    # Rewrite the op record's refusal (valid JSON, fresh digest) so the
    # file-integrity layer passes but the stale binding must still fail.
    op_p = pack / "target-op.json"
    doc = json.loads(op_p.read_text(encoding="utf-8"))
    doc["artifacts"]["stale_refusal"]["failed"] = ["target_info"]
    op_p.write_text(json.dumps(doc), encoding="utf-8")
    man_p = pack / "manifest.json"
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    manifest["files"]["target-op.json"] = hashlib.sha256(
        op_p.read_bytes()).hexdigest()
    man_p.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    capsys.readouterr()
    assert verifier.main(["verify.py", str(pack)]) == 2
    assert "stale:" in capsys.readouterr().out


def test_packer_refuses_mismatched_stale_op(tmp_path, amr_ir, capsys):
    ops_dir = tmp_path / "ops"
    op_id = "op-cccccccccccc"
    op_dir = ops_dir / op_id
    op_dir.mkdir(parents=True)
    _write_record(op_dir, ["target_info"])
    _write_manifest(op_dir)
    (op_dir / "ir.json").write_text(json.dumps(amr_ir), encoding="utf-8")
    (op_dir / "qemu-console.log").write_text("boot\n", encoding="utf-8")
    (op_dir / "passport.json").write_text(
        json.dumps({"passport_version": 1, "run_id": op_id, "gate": "FAIL",
                    "chain": [{"seq": 0, "kind": "stale_control",
                               "body": {"expected_refusal": REFUSAL,
                                        "failed_checks": REFUSAL},
                               "prev_hash": "GENESIS" + "0" * 57,
                               "hash": "00" * 32}]}),
        encoding="utf-8")
    (ops_dir / f"{op_id}.json").write_text(json.dumps({
        "op_id": op_id, "workflow": "stale-control", "state": "COMPLETED",
        "params": {"expect_refusal": REFUSAL},
        "artifacts": {"ir_sha256": "0" * 64,
                      "stale_refusal": {"expected": REFUSAL,
                                        "failed": REFUSAL}}}),
        encoding="utf-8")
    # The fixture record binds ir 0*64 but fails at target_info while the
    # sealed claim says REFUSAL: the builder must refuse before publishing.
    rc = packer.main(["--op", op_id, "--ops-dir", str(ops_dir),
                      "--out", str(tmp_path / "pack"), "--commit", "test123"])
    assert rc == 2
    assert "stale_control claim != target matrix" in capsys.readouterr().err


# -- frozen-pack backward compatibility ------------------------------------

@pytest.mark.parametrize("pack", ["qnx8-x86_64-omega2-before",
                                  "qnx8-x86_64-omega2-after"])
def test_frozen_omega2_packs_still_verify(repo_root, pack, capsys):
    capsys.readouterr()
    assert verifier.main(["verify.py", str(repo_root / "evidence" / pack)]) == 0
    assert "VERIFY OK" in capsys.readouterr().out
