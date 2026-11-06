# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: self-hosted runner reference (auth, allowlist,
provenance pinning, idempotency, bounded execution).

The fake adapter proves the plumbing; stubbed TargetRunner steps
prove the local adapter's join/cancel/timeout logic without QEMU.
"""
import json
import time
from pathlib import Path

import pytest

from genesis_rt import runner
from genesis_rt.codegen import ir_sha256
from genesis_rt.ir import validate_ir
from genesis_rt.proofos import build_plan
from genesis_rt.runner import (RunnerAuthError, RunnerBusy, RunnerConfig,
                               RunnerError, authorize, cancel, sign_body,
                               status, submit)
from genesis_rt.target import WORKFLOWS, TargetRunner

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOKEN = "test-token-0123456789abcdef"

with open(REPO_ROOT / "examples" / "amr-demo" / "machine-ir.json",
          encoding="utf-8") as fh:
    AMR_IR = json.load(fh)


@pytest.fixture()
def head():
    return runner.server_head(REPO_ROOT)


@pytest.fixture()
def cfg(tmp_path):
    return RunnerConfig(
        repo_root=REPO_ROOT,
        jobs_dir=tmp_path / "jobs",
        target_ops_dir=tmp_path / "ops",
        adapter="fake")


def _job(head, job_id="job-1", **over):
    body = {"job_id": job_id, "operation": "native_build",
            "revision": head, "ir": AMR_IR}
    body.update(over)
    return body


def _submit(cfg, body, token=TOKEN):
    raw = json.dumps(body).encode("utf-8")
    return submit(raw, sign_body(raw, token), config=cfg, token=token)


def _plan(head, digest):
    return build_plan(
        source_commit=head, base_commit="0" * 40,
        changes=[{"path": "examples/amr-demo/machine-ir.json",
                  "status": "changed", "valid": True,
                  "renamed_from": None,
                  "ir_sha256_before": "0" * 64,
                  "ir_sha256_after": digest,
                  "limits_changed": True,
                  "requirements_changed": 1,
                  "retest": ["nominal_navigation"]}])


def test_auth_missing_bad_or_unconfigured(cfg, head):
    raw = json.dumps(_job(head)).encode("utf-8")
    with pytest.raises(RunnerAuthError, match="missing or malformed"):
        submit(raw, None, config=cfg, token=TOKEN)
    with pytest.raises(RunnerAuthError, match="does not verify"):
        submit(raw, sign_body(raw, "wrong-token"), config=cfg, token=TOKEN)
    with pytest.raises(RunnerAuthError, match="not configured"):
        submit(raw, sign_body(raw, TOKEN), config=cfg, token=None)
    authorize(raw, sign_body(raw, TOKEN), TOKEN)  # sanity: valid passes


def test_rejects_bad_shapes(cfg, head):
    with pytest.raises(RunnerError, match="too large"):
        submit(b"x" * (runner.MAX_JOB_BYTES + 1),
               sign_body(b"x", TOKEN), config=cfg, token=TOKEN)
    raw = b"not json"
    with pytest.raises(RunnerError, match="not JSON"):
        submit(raw, sign_body(raw, TOKEN), config=cfg, token=TOKEN)
    with pytest.raises(RunnerError, match="job_id"):
        _submit(cfg, _job(head, job_id="../evil"))
    rec = None
    with pytest.raises(RunnerError, match="not allowlisted"):
        _submit(cfg, _job(head, operation="rm -rf /"))
    rec = status(cfg, "job-1")
    assert rec["status"] == "REJECTED" and "allowlisted" in rec["reason"]


def test_revision_pin_and_ir_validation(cfg, head):
    # Distinct job_ids: REJECTED records are stored, and a replayed
    # id would return the stored REJECTED record instead of
    # re-validating (idempotency, tested separately).
    with pytest.raises(RunnerError, match="revision mismatch"):
        _submit(cfg, _job(head, job_id="r1", revision="1" * 40))
    bad = dict(AMR_IR)
    bad["control"] = {"max_linear_speed_mps": -5}
    with pytest.raises(RunnerError, match="job ir invalid"):
        _submit(cfg, _job(head, job_id="r2", ir=bad))
    with pytest.raises(RunnerError, match="timeout_s"):
        _submit(cfg, _job(head, job_id="r3", timeout_s=99999))


def test_plan_binding(cfg, head, amr_ir_dict):
    # The pipeline digests the validated IR (impact.validate_any),
    # so the test plan must bind the validated digest too.
    import copy

    digest = ir_sha256(validate_ir(copy.deepcopy(amr_ir_dict)))
    rec = _submit(cfg, _job(head, plan=_plan(head, digest)))
    assert rec["status"] == "COMPLETED"
    assert rec["plan_id"] == _plan(head, digest)["plan_id"]
    with pytest.raises(RunnerError, match="source_commit"):
        _submit(cfg, _job(head, job_id="j2",
                           plan=_plan("2" * 40, digest)))
    with pytest.raises(RunnerError, match="no plan change entry"):
        _submit(cfg, _job(head, job_id="j3",
                           plan=_plan(head, "3" * 64)))
    bad = _plan(head, digest)
    bad["stage"] = "INVALID"
    with pytest.raises(RunnerError, match="stage is INVALID"):
        _submit(cfg, _job(head, job_id="j4", plan=bad))
    with pytest.raises(RunnerError, match="plan invalid"):
        _submit(cfg, _job(head, job_id="j5", plan={"nope": True}))


def test_fake_completion_never_verifies(cfg, head):
    rec = _submit(cfg, _job(head))
    assert rec["status"] == "COMPLETED"
    assert rec["adapter"] == "fake"
    assert rec["qnx_verified"] is False
    assert rec["op_id"] is None
    import copy

    assert rec["ir_sha256"] == ir_sha256(
        validate_ir(copy.deepcopy(AMR_IR)))


def test_duplicate_delivery_replays_without_rerun(cfg, head):
    first = _submit(cfg, _job(head))
    second = _submit(cfg, _job(head))
    assert second["duplicate"] is True
    assert second["finished"] == first["finished"]
    assert second["status"] == first["status"]


def test_cancel_unknown_and_terminal(cfg, head):
    with pytest.raises(RunnerError, match="unknown job"):
        cancel(cfg, "nope")
    rec = _submit(cfg, _job(head))
    assert cancel(cfg, "job-1")["status"] == rec["status"]
    assert status(cfg, "bad id!") is None


def test_server_head_requires_git_repo(tmp_path):
    with pytest.raises(RunnerError, match="cannot determine server HEAD"):
        runner.server_head(tmp_path)


def test_local_adapter_needs_target_runner(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    raw = json.dumps(_job(head)).encode("utf-8")
    rec = submit(raw, sign_body(raw, TOKEN), config=cfg, token=TOKEN,
                 target=None)
    assert rec["status"] == "BLOCKED"


class StubTarget(TargetRunner):
    """Real TargetRunner machinery, stubbed step bodies."""

    def __init__(self, *args, sleep=0.0, fail_on=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._sleep = sleep
        self._fail_on = set(fail_on)

    def start(self, workflow, params=None, step_impls=None):
        def _mk(name):
            def _fn(ctx):
                if self._sleep:
                    time.sleep(self._sleep)
                if name in self._fail_on:
                    return (False, f"stub failure at {name}")
                return (True, "stub")
            return _fn
        impls = {s: _mk(s) for s in WORKFLOWS[workflow]}
        if step_impls:
            impls.update(step_impls)
        return super().start(workflow, params=params, step_impls=impls)


def _wait_status(cfg, job_id, want, budget=15.0):
    deadline = time.time() + budget
    while time.time() < deadline:
        rec = status(cfg, job_id)
        if rec and rec["status"] in want:
            return rec
        time.sleep(0.2)
    return status(cfg, job_id)


def test_local_adapter_completes_stub_op(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    target = StubTarget(cfg.target_ops_dir)
    try:
        raw = json.dumps(_job(head)).encode("utf-8")
        rec = submit(raw, sign_body(raw, TOKEN), config=cfg,
                     token=TOKEN, target=target)
        assert rec["status"] == "RUNNING"
        assert rec["op_id"]
        # Duplicate while live: reported, not re-run.
        dup = submit(raw, sign_body(raw, TOKEN), config=cfg,
                     token=TOKEN, target=target)
        assert dup["duplicate"] is True
        assert dup["status"] == "RUNNING"
        done = _wait_status(cfg, "job-1", ("COMPLETED",))
        assert done["status"] == "COMPLETED"
        assert done["op_state"] == "COMPLETED"
        assert done["qnx_verified"] is False  # stubs prove no native claim
    finally:
        target.close()


def test_local_adapter_reports_step_failure(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    target = StubTarget(cfg.target_ops_dir, fail_on=("build",))
    try:
        raw = json.dumps(_job(head)).encode("utf-8")
        submit(raw, sign_body(raw, TOKEN), config=cfg, token=TOKEN,
               target=target)
        done = _wait_status(cfg, "job-1", ("FAILED",))
        assert done["status"] == "FAILED"
        assert "build" in done["reason"]
    finally:
        target.close()


def test_local_adapter_cancel_live_job(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    target = StubTarget(cfg.target_ops_dir, sleep=5.0)
    try:
        raw = json.dumps(_job(head, timeout_s=120)).encode("utf-8")
        submit(raw, sign_body(raw, TOKEN), config=cfg, token=TOKEN,
               target=target)
        rec = cancel(cfg, "job-1", target)
        assert rec["status"] == "CANCELLED"
        done = _wait_status(cfg, "job-1", ("CANCELLED",))
        assert done["status"] == "CANCELLED"
    finally:
        target.close()


def test_local_adapter_timeout_cancels_op(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    target = StubTarget(cfg.target_ops_dir, sleep=5.0)
    try:
        raw = json.dumps(_job(head, timeout_s=2)).encode("utf-8")
        submit(raw, sign_body(raw, TOKEN), config=cfg, token=TOKEN,
               target=target)
        done = _wait_status(cfg, "job-1", ("TIMEOUT",), budget=20.0)
        assert done["status"] == "TIMEOUT"
        assert "exceeded 2s" in done["reason"]
    finally:
        target.close()


def test_second_job_blocked_while_target_leased(head, tmp_path):
    cfg = RunnerConfig(repo_root=REPO_ROOT, jobs_dir=tmp_path / "jobs",
                       target_ops_dir=tmp_path / "ops", adapter="local")
    target = StubTarget(cfg.target_ops_dir, sleep=5.0)
    try:
        raw1 = json.dumps(_job(head, job_id="j1")).encode("utf-8")
        submit(raw1, sign_body(raw1, TOKEN), config=cfg, token=TOKEN,
               target=target)
        raw2 = json.dumps(_job(head, job_id="j2")).encode("utf-8")
        with pytest.raises(RunnerBusy):
            submit(raw2, sign_body(raw2, TOKEN), config=cfg,
                   token=TOKEN, target=target)
        assert status(cfg, "j2")["status"] == "BLOCKED"
    finally:
        target.close()
