# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §5: target op state machine + runner (stub steps, no QEMU)."""
import json
import os
import subprocess
import sys
import threading
import time

import pytest

from genesis_rt import target as tgt


@pytest.fixture()
def runner(tmp_path):
    r = tgt.TargetRunner(tmp_path / "ops", tmp_path / "target.lock")
    try:
        yield r
    finally:
        r.close()


def _poll_state(r, op_id, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = r.get(op_id)
        assert rec is not None
        if rec["state"] in tgt.TERMINAL_TARGET:
            return rec
        time.sleep(0.05)
    raise AssertionError(f"op {op_id} never settled: {r.get(op_id)}")


def _stub_ok(name):
    return lambda ctx: (True, f"{name} stub ok")


def _stub_all(monkeypatch):
    for name in ("validate", "env", "generate", "build", "seal", "replay"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))


def test_op_lifecycle_stub_steps(runner, monkeypatch):
    _stub_all(monkeypatch)
    rec = runner.start("build-only", params={"ir": {"machine": {"id": "t"}}})
    assert rec["state"] == "PENDING"
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED"
    assert [s["state"] for s in final["steps"]] == ["done"] * 6
    evts = runner.events(rec["op_id"])
    assert [e["seq"] for e in evts] == list(range(len(evts)))
    assert evts[0]["kind"] == "op_started"
    assert evts[-1]["kind"] == "op_completed"


def test_unknown_workflow_rejected_no_record(runner, tmp_path):
    with pytest.raises(tgt.TargetOpError):
        runner.start("nope", params={})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


def test_unknown_param_rejected_no_record(runner, tmp_path):
    with pytest.raises(tgt.TargetOpError):
        runner.start("build-only", params={"ir": {}, "rm_rf": "/"})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


def test_duplicate_live_op_rejected(runner, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def _slow(ctx):
        started.set()
        release.wait(timeout=30)
        return (True, "slow ok")

    monkeypatch.setitem(tgt.STEP_IMPLS, "validate", _slow)
    for name in ("env", "generate", "build", "seal", "replay"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    rec = runner.start("build-only", params={"ir": {}})
    assert started.wait(timeout=10)
    try:
        with pytest.raises(tgt.TargetBusy):
            runner.start("build-only", params={"ir": {}})
    finally:
        release.set()
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED"


def test_cancel_flips_and_stops_between_steps(runner, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def _slow(ctx):
        started.set()
        release.wait(timeout=30)
        return (True, "slow ok")

    monkeypatch.setitem(tgt.STEP_IMPLS, "validate", _slow)
    for name in ("env", "generate", "build"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    rec = runner.start("build-only", params={"ir": {}})
    assert started.wait(timeout=10)
    out = runner.cancel(rec["op_id"])
    assert out["state"] not in tgt.TERMINAL_TARGET  # async: step still runs
    release.set()
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "CANCELLED"
    assert final["steps"][0]["state"] == "done"  # step 1 finished
    assert final["steps"][1]["state"] == "pending"  # step 2 never ran


def test_failed_step_fails_op_terminal_sticky(runner, monkeypatch):
    monkeypatch.setitem(tgt.STEP_IMPLS, "validate",
                        lambda ctx: (False, "boom"))
    for name in ("env", "generate", "build"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    rec = runner.start("build-only", params={"ir": {}})
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "FAILED"
    assert "boom" in final["reason"]
    assert runner.cancel(rec["op_id"])["state"] == "FAILED"  # sticky


def test_blocked_step_skips_rest(runner, monkeypatch):
    def _no_sdk(ctx):
        raise tgt.TargetBlocked("QNX SDK not installed")

    monkeypatch.setitem(tgt.STEP_IMPLS, "env", _no_sdk)
    for name in ("validate", "generate", "build"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    rec = runner.start("build-only", params={"ir": {}})
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "BLOCKED"
    assert "SDK" in final["reason"]
    assert [s["state"] for s in final["steps"]] == ["done", "blocked",
                                                   "pending", "pending",
                                                   "pending", "pending"]


def test_interrupted_recovery_marks_stale_live(tmp_path):
    ops = tmp_path / "ops"
    ops.mkdir()
    (ops / "op-abc123def456.json").write_text(json.dumps({
        "op_id": "op-abc123def456", "workflow": "full", "state": "VERIFYING",
        "reason": "", "steps": [], "created": 1.0, "updated": 1.0,
        "artifacts": {}}), encoding="utf-8")
    r = tgt.TargetRunner(ops, tmp_path / "target.lock")
    try:
        rec = r.get("op-abc123def456")
        assert rec["state"] == "INTERRUPTED"
    finally:
        r.close()


def _dead_pid():
    """A pid naming no live process (barring instant pid reuse)."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def _write_op(ops_dir, op_id, state, owner_pid, updated):
    ops_dir.mkdir(exist_ok=True)
    (ops_dir / f"{op_id}.json").write_text(json.dumps({
        "op_id": op_id, "workflow": "full", "state": state,
        "reason": "", "steps": [], "created": updated, "updated": updated,
        "owner_pid": owner_pid, "artifacts": {}}), encoding="utf-8")


def test_recover_spares_live_owner_op(tmp_path):
    """A second runner must not reap an op whose owner is alive (this
    killed a live campaign op on 2026-11-05)."""
    now = time.time()
    _write_op(tmp_path / "ops", "op-liveowner01", "VERIFYING",
              os.getpid(), now)
    r = tgt.TargetRunner(tmp_path / "ops", tmp_path / "target.lock")
    try:
        assert r.get("op-liveowner01")["state"] == "VERIFYING"
    finally:
        r.close()


def test_recover_reaps_dead_owner_op(tmp_path):
    now = time.time()
    _write_op(tmp_path / "ops", "op-deadowner01", "VERIFYING",
              _dead_pid(), now)
    r = tgt.TargetRunner(tmp_path / "ops", tmp_path / "target.lock")
    try:
        rec = r.get("op-deadowner01")
        assert rec["state"] == "INTERRUPTED"
        assert rec["reason"] == "previous process ended before completion"
    finally:
        r.close()


def test_recover_reaps_ancient_op_despite_live_pid(tmp_path):
    """Pid-reuse backstop: untouched for >24h is reaped even when the
    recorded pid happens to be alive."""
    now = time.time()
    _write_op(tmp_path / "ops", "op-ancient0001", "VERIFYING",
              os.getpid(), now - 25 * 3600)
    r = tgt.TargetRunner(tmp_path / "ops", tmp_path / "target.lock")
    try:
        rec = r.get("op-ancient0001")
        assert rec["state"] == "INTERRUPTED"
        assert "pid reuse" in rec["reason"]
    finally:
        r.close()


def test_list_ops_newest_first(runner, monkeypatch):
    _stub_all(monkeypatch)
    a = runner.start("build-only", params={"ir": {}})
    _poll_state(runner, a["op_id"])
    b = runner.start("build-only", params={"ir": {}})
    _poll_state(runner, b["op_id"])
    rows = runner.list_ops()
    assert [r["op_id"] for r in rows] == [b["op_id"], a["op_id"]]
    assert rows[0]["state"] == "COMPLETED"


def test_two_runners_share_file_lock(tmp_path, monkeypatch):
    _stub_all(monkeypatch)
    lock = tmp_path / "target.lock"
    r1 = tgt.TargetRunner(tmp_path / "ops1", lock)
    r2 = tgt.TargetRunner(tmp_path / "ops2", lock)
    started = threading.Event()
    release = threading.Event()

    def _slow(ctx):
        started.set()
        release.wait(timeout=30)
        return (True, "slow ok")

    monkeypatch.setitem(tgt.STEP_IMPLS, "validate", _slow)
    try:
        rec = r1.start("build-only", params={"ir": {}})
        assert started.wait(timeout=10)
        try:
            with pytest.raises(tgt.TargetBusy):
                r2.start("build-only", params={"ir": {}})
        finally:
            release.set()
        assert _poll_state(r1, rec["op_id"])["state"] == "COMPLETED"
    finally:
        r1.close()
        r2.close()


def test_failure_after_boot_runs_bounded_cleanup(runner, monkeypatch):
    called = []

    def _boot(ctx):
        ctx["artifacts"]["qemu_pid"] = 424242
        return (True, "boot stub ok")

    def _stop(ctx):
        called.append("stop")
        return (True, "stop stub ok")

    for name in ("validate", "env", "generate", "build", "probe_image"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    monkeypatch.setitem(tgt.STEP_IMPLS, "qemu_boot", _boot)
    monkeypatch.setitem(tgt.STEP_IMPLS, "wait_ssh", lambda ctx: (False, "no ssh"))
    monkeypatch.setitem(tgt.STEP_IMPLS, "qemu_stop", _stop)
    rec = runner.start("full", params={"ir": {}, "image_dir": str(runner.ops_dir)})
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "FAILED"
    assert called == ["stop"]
    states = {s["name"]: s["state"] for s in final["steps"]}
    assert states["wait_ssh"] == "failed"
    assert states["qemu_stop"] == "done"
    assert states["qemu_verify"] == "pending"


def test_built_binaries_excludes_sources(tmp_path):
    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "genesis_guard").write_text("elf", encoding="utf-8")
    for name in ("genesis_build_gen.mk", "genesis_config_gen.h",
                 "genesis_machine_gen.c", "other.txt", "README.md"):
        (gen / name).write_text("x", encoding="utf-8")
    assert tgt._built_binaries(gen) == [str(gen / "genesis_guard")]


def test_wait_ssh_banner_true_and_silent_false():
    import socket
    import threading as _th

    def _serve(banner, box, stop):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        box["port"] = srv.getsockname()[1]
        box["ready"].set()
        srv.settimeout(15)
        try:
            conn, _ = srv.accept()
            with conn:
                if banner:
                    conn.sendall(banner)
                stop.wait(15)
        except OSError:
            pass
        finally:
            srv.close()

    box, stop = {"ready": _th.Event()}, _th.Event()
    t = _th.Thread(target=_serve, args=(b"SSH-2.0-test\r\n", box, stop),
                   daemon=True)
    t.start()
    assert box["ready"].wait(timeout=10)
    try:
        assert tgt._wait_ssh_banner(box["port"], 10) is True
    finally:
        stop.set()
        t.join(timeout=10)

    box2, stop2 = {"ready": _th.Event()}, _th.Event()
    t2 = _th.Thread(target=_serve, args=(None, box2, stop2), daemon=True)
    t2.start()
    assert box2["ready"].wait(timeout=10)
    try:
        t0 = time.monotonic()
        assert tgt._wait_ssh_banner(box2["port"], 3) is False
        assert time.monotonic() - t0 < 10
    finally:
        stop2.set()
        t2.join(timeout=10)


def test_unlocked_strips_wraps_decorator():
    import functools

    @functools.wraps(lambda args: 0)
    def _decorated(args):
        return -1  # pragma: no cover

    assert tgt._unlocked(_decorated)(None) == 0
    plain = lambda args: 7
    assert tgt._unlocked(plain) is plain


def test_step_stdout_captured_on_failure(runner, monkeypatch):
    def _loud_fail(ctx):
        print("X-DIAG-789 unique-failure-marker")
        return (False, "boom")

    monkeypatch.setitem(tgt.STEP_IMPLS, "validate", _loud_fail)
    for name in ("env", "generate", "build"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    rec = runner.start("build-only", params={"ir": {}})
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "FAILED"
    assert "boom" in final["reason"]
    assert "X-DIAG-789 unique-failure-marker" in final["reason"]


def _seal_ctx(tmp_path, amr_ir, artifacts=None, params=None):
    work = tmp_path / "w"
    work.mkdir(exist_ok=True)
    return {"op_id": "op-seal-test",
            "params": {"ir": amr_ir, **(params or {})},
            "work_dir": str(work),
            "artifacts": dict(artifacts or {})}


def test_seal_refuses_without_gen_manifest(tmp_path, amr_ir):
    ok, detail = tgt._step_seal(_seal_ctx(tmp_path, amr_ir))
    assert ok is False
    assert "no gen manifest" in detail


def test_seal_refuses_without_build_record(tmp_path, amr_ir):
    man = tmp_path / "w" / "manifest.json"
    man.parent.mkdir(exist_ok=True)
    man.write_text(json.dumps({"ir_sha256": "abc"}), encoding="utf-8")
    ctx = _seal_ctx(tmp_path, amr_ir, {"gen_manifest": str(man)})
    ok, detail = tgt._step_seal(ctx)
    assert ok is False
    assert "no qnx build record" in detail


def _sealed_passport(tmp_path, amr_ir, run_id="op-seal-test"):
    from genesis_rt import evidence as ev
    from genesis_rt import gate
    from genesis_rt.projects import validate_any
    _, valid = validate_any(amr_ir)
    manifest = {"ir_sha256": "0" * 64, "files": []}
    passport = ev.build_passport(run_id, valid, manifest, [],
                                 None, None, None, None)
    verdict = gate.evaluate(passport, [])
    ev.attach_verdict(passport, verdict)
    ppath = tmp_path / "passport.json"
    ev.save_passport(passport, ppath)
    return ppath, verdict


def test_replay_accepts_sealed_passport(tmp_path, amr_ir):
    ppath, verdict = _sealed_passport(tmp_path, amr_ir)
    ctx = _seal_ctx(tmp_path, amr_ir,
                    {"passport": str(ppath), "wanted": [],
                     "verdict": verdict["verdict"],
                     "ir_sha256": "0" * 64})
    ok, detail = tgt._step_replay(ctx)
    assert ok is True, detail
    assert ctx["artifacts"]["replay"]["verdict"] == verdict["verdict"]


def test_replay_rejects_foreign_op_passport(tmp_path, amr_ir):
    # Red-team: a VALID passport sealed for another op (same verdict)
    # swapped onto this op's path must not replay as ours.
    ppath, verdict = _sealed_passport(tmp_path, amr_ir,
                                      run_id="op-aaaaaaaaaaaa")
    ctx = _seal_ctx(tmp_path, amr_ir,
                    {"passport": str(ppath), "wanted": [],
                     "verdict": verdict["verdict"],
                     "ir_sha256": "0" * 64})
    ok, detail = tgt._step_replay(ctx)
    assert ok is False, detail
    assert "op-aaaaaaaaaaaa" in detail or "run_id" in detail


def test_replay_rejects_ir_mismatch(tmp_path, amr_ir):
    ppath, verdict = _sealed_passport(tmp_path, amr_ir)
    ctx = _seal_ctx(tmp_path, amr_ir,
                    {"passport": str(ppath), "wanted": [],
                     "verdict": verdict["verdict"],
                     "ir_sha256": "f" * 64})
    ok, detail = tgt._step_replay(ctx)
    assert ok is False, detail
    assert "ir_sha256" in detail


def test_replay_rejects_tampered_passport(tmp_path, amr_ir):
    ppath, verdict = _sealed_passport(tmp_path, amr_ir)
    doc = json.loads(ppath.read_text(encoding="utf-8"))
    doc["chain"][2]["body"]["status"] = "ok"  # flip build body, keep JSON valid
    ppath.write_text(json.dumps(doc), encoding="utf-8")
    ctx = _seal_ctx(tmp_path, amr_ir,
                    {"passport": str(ppath), "wanted": [],
                     "verdict": verdict["verdict"]})
    ok, detail = tgt._step_replay(ctx)
    assert ok is False, detail


def test_extra_src_missing_file_rejected(runner, tmp_path):
    with pytest.raises(tgt.TargetOpError):
        runner.start("build-only", params={"ir": {}, "extra_src": ["nope"]})
    assert list((tmp_path / "ops").glob("op-*.json")) == []


def test_put_cleans_staging_and_appends_extra_src(tmp_path, monkeypatch):
    calls = {}

    class _FakeQt:
        def cmd_run(self, args):
            calls["clean"] = list(args.command)
            return 0

        def cmd_put(self, args):
            calls["put"] = list(args.src)
            return 0

    monkeypatch.setattr(tgt, "_qt", lambda: _FakeQt())
    extra = tmp_path / "genesis_guard_conv"
    extra.write_text("x", encoding="utf-8")
    ctx = {"params": {"extra_src": [str(extra)]},
           "work_dir": str(tmp_path), "artifacts": {"binaries": ["a", "b"]}}
    ok, detail = tgt._step_qemu_put(ctx)
    assert ok is True, detail
    assert calls["clean"] == ["rm -f /tmp/genesis/genesis_*"]
    assert calls["put"] == ["a", "b", str(extra)]


def test_put_cleanup_failure_aborts_before_put(tmp_path, monkeypatch):
    calls = []

    class _FakeQt:
        def cmd_run(self, args):
            return 2

        def cmd_put(self, args):
            calls.append(list(args.src))
            return 0

    monkeypatch.setattr(tgt, "_qt", lambda: _FakeQt())
    ctx = {"params": {}, "work_dir": str(tmp_path),
           "artifacts": {"binaries": ["a"]}}
    ok, detail = tgt._step_qemu_put(ctx)
    assert ok is False
    assert "staging cleanup rc=2" in detail
    assert calls == []


def test_perf_passes_build_set(tmp_path, monkeypatch):
    calls = {}

    class _FakeQt:
        def cmd_perf(self, args):
            calls["build_set"] = args.build_set
            return 0

    monkeypatch.setattr(tgt, "_qt", lambda: _FakeQt())
    ctx = {"params": {"build_set": "bs.json"}, "work_dir": str(tmp_path),
           "artifacts": {}}
    ok, detail = tgt._step_qemu_perf(ctx)
    assert ok is True, detail
    assert calls["build_set"] == "bs.json"


def test_validate_normalizes_ir_in_record(runner, monkeypatch, amr_ir_dict):
    from genesis_rt.projects import validate_any
    for name in ("env", "generate", "build", "seal", "replay"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))
    raw_scenarios = list(amr_ir_dict["verification"]["scenarios"])
    _, want = validate_any(amr_ir_dict)
    assert want["verification"]["scenarios"] != raw_scenarios  # raw file order
    rec = runner.start("build-only", params={"ir": amr_ir_dict})
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED"
    got = final["params"]["ir"]["verification"]["scenarios"]
    assert got == want["verification"]["scenarios"]


class _FakeUUID:
    def __init__(self, hexv):
        self.hex = hexv


def test_start_retries_on_op_id_collision(runner, monkeypatch):
    """Red-team round 2, A3: a colliding/reused op id must never make
    start() overwrite an existing operation record."""
    _stub_all(monkeypatch)
    hexes = iter(["deadbeef1234" + "0" * 20,
                  "deadbeef1234" + "0" * 20,
                  "abcdef123456" + "0" * 20])
    monkeypatch.setattr(tgt.uuid, "uuid4", lambda: _FakeUUID(next(hexes)))
    first = runner.start("build-only",
                         params={"ir": {"machine": {"id": "t"}}})
    assert first["op_id"] == "op-deadbeef1234"
    _poll_state(runner, first["op_id"])
    second = runner.start("build-only",
                          params={"ir": {"machine": {"id": "t"}}})
    assert second["op_id"] == "op-abcdef123456"  # retried, not reused
    assert runner.get(first["op_id"])["state"] == "COMPLETED"  # intact
    _poll_state(runner, second["op_id"])


def test_write_record_retries_transient_replace_denied(runner, monkeypatch):
    """Windows: replace() denied by a concurrent reader is retried.

    Observed as WinError 5 flaking _run threads; the contention window is
    microseconds, so a bounded retry succeeds instead of killing the op.
    """
    from pathlib import Path
    real_replace = Path.replace
    calls = []

    def _flaky_replace(self, target):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError(13, "denied")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _flaky_replace)
    runner._write_record({"op_id": "op-retry", "state": "EXECUTING",
                          "reason": "", "steps": []})
    assert len(calls) == 3
    assert runner.get("op-retry")["state"] == "EXECUTING"


def test_write_record_gives_up_after_bounded_retries(runner, monkeypatch):
    """Persistent replace denial still fails loud (never silent loss)."""
    from pathlib import Path

    def _always_denied(self, target):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(Path, "replace", _always_denied)
    with pytest.raises(PermissionError):
        runner._write_record({"op_id": "op-denied", "state": "EXECUTING",
                              "reason": "", "steps": []})


def test_validate_params_caps_ir_and_scenarios():
    """Titan F3: /target/ops params are capped like /runs (ir size,
    scenario count/charset, src list length)."""
    steps = ["validate", "generate"]
    with pytest.raises(tgt.TargetOpError, match="256 KiB"):
        tgt._validate_params(steps, {"ir": {"pad": "x" * (300 * 1024)}})
    with pytest.raises(tgt.TargetOpError, match="32 entries"):
        tgt._validate_params(steps, {"ir": {}, "scenarios": ["s"] * 33})
    with pytest.raises(tgt.TargetOpError, match="must be \\[A-Za-z"):
        tgt._validate_params(steps, {"ir": {}, "scenarios": ["ok", "a/b"]})
    with pytest.raises(tgt.TargetOpError, match="64 files"):
        tgt._validate_params(
            steps, {"ir": {}, "src": ["f"] * 65, "scenarios": ["s"]})
    ok = tgt._validate_params(
        steps, {"ir": {"a": 1}, "scenarios": ["nominal_navigation"]})
    assert ok["scenarios"] == ["nominal_navigation"]
