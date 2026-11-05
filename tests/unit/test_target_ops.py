# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §5: target op state machine + runner (stub steps, no QEMU)."""
import json
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
    for name in ("validate", "env", "generate", "build"):
        monkeypatch.setitem(tgt.STEP_IMPLS, name, _stub_ok(name))


def test_op_lifecycle_stub_steps(runner, monkeypatch):
    _stub_all(monkeypatch)
    rec = runner.start("build-only", params={"ir": {"machine": {"id": "t"}}})
    assert rec["state"] == "PENDING"
    final = _poll_state(runner, rec["op_id"])
    assert final["state"] == "COMPLETED"
    assert [s["state"] for s in final["steps"]] == ["done"] * 4
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
    for name in ("env", "generate", "build"):
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


def test_list_ops_newest_first(runner, monkeypatch):
    _stub_all(monkeypatch)
    a = runner.start("build-only", params={"ir": {}})
    _poll_state(runner, a["op_id"])
    b = runner.start("build-only", params={"ir": {}})
    _poll_state(runner, b["op_id"])
    rows = runner.list_ops()
    assert [r["op_id"] for r in rows] == [b["op_id"], a["op_id"]]
    assert rows[0]["state"] == "COMPLETED"
