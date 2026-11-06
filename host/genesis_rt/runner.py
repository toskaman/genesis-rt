# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Reference self-hosted QNX verification runner (Wave 12 §8).

Trusted-revision -> validated plan -> authorized job -> exclusive
target lease -> native execution -> evidence -> review artifact.

Trust boundaries (see docs/runner/SELF_HOSTED_RUNNER.md):

* The network boundary is HMAC-SHA256 (``GENESIS_RUNNER_TOKEN``,
  server-side env only). No token, no job.
* The code boundary is the pinned revision: the runner only
  executes jobs whose ``revision`` equals its own checked-out
  ``HEAD``. It never checks out untrusted revisions itself.
* The execution boundary is an allowlist: three operations mapped
  server-side to fixed target workflows. Clients choose timeouts
  (capped), never steps, shells, paths, or binaries.
* The target boundary is the existing exclusive ``TargetRunner``
  lease: one live op, safe cancellation, crash recovery.

Adapters: ``local`` drives the real ``TargetRunner`` (needs SDK +
QEMU image); ``fake`` returns a canned terminal record honestly
labeled ``adapter: fake`` with ``qnx_verified: False`` — for
tests, guides, and CI plumbing without a target. The fake
adapter can never produce a verified verdict.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ALLOWED_OPS = {
    "native_build": "build-only",
    "native_verify": "verify-only",
    "native_full": "full",
}
JOB_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
REV_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_JOB_BYTES = 512 * 1024
MAX_IR_BYTES = 256 * 1024
DEFAULT_TIMEOUT_S = 600
MAX_TIMEOUT_S = 1800
SIG_PREFIX = "sha256="

TERMINAL_JOB = ("COMPLETED", "FAILED", "CANCELLED", "REJECTED",
                "TIMEOUT", "BLOCKED")


class RunnerError(Exception):
    """Job rejected or runner misconfigured (fail-closed)."""


class RunnerAuthError(RunnerError):
    """Bad or missing job signature."""


class RunnerBusy(RunnerError):
    """Target leased by another job/op."""


def sign_body(body: bytes, token: str) -> str:
    return SIG_PREFIX + hmac.new(token.encode("utf-8"), body,
                                 hashlib.sha256).hexdigest()


def authorize(body: bytes, signature: str | None, token: str | None) -> None:
    if not token:
        raise RunnerAuthError("runner token not configured")
    if not signature or not signature.startswith(SIG_PREFIX):
        raise RunnerAuthError("missing or malformed job signature")
    want = sign_body(body, token)
    if not hmac.compare_digest(want, signature):
        raise RunnerAuthError("job signature does not verify")


@dataclass
class RunnerConfig:
    repo_root: Path
    jobs_dir: Path
    target_ops_dir: Path
    image_dir: str | None = None
    ssh_port: int = 2222
    default_timeout_s: int = DEFAULT_TIMEOUT_S
    max_timeout_s: int = MAX_TIMEOUT_S
    adapter: str = "local"
    fake_results: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root)
        self.jobs_dir = Path(self.jobs_dir)
        self.target_ops_dir = Path(self.target_ops_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        if self.adapter not in ("local", "fake"):
            raise RunnerError(f"unknown adapter: {self.adapter!r}")
        if not 1 <= self.default_timeout_s <= self.max_timeout_s <= 7200:
            raise RunnerError("bad timeout bounds")


class JobStore:
    def __init__(self, jobs_dir: Path) -> None:
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, job_id: str) -> Path:
        return self.jobs_dir / f"job-{job_id}.json"

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            try:
                return json.loads(self._path(job_id).read_text(
                    encoding="utf-8"))
            except (OSError, ValueError):
                return None

    def put(self, rec: dict[str, Any]) -> None:
        with self._lock:
            path = self._path(rec["job_id"])
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            tmp.replace(path)


def server_head(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30, check=True)
    except (subprocess.SubprocessError, OSError) as exc:
        raise RunnerError(f"cannot determine server HEAD: {exc}") from exc
    head = out.stdout.strip()
    if not REV_RE.fullmatch(head):
        raise RunnerError("server HEAD is not a full commit sha")
    return head


def validate_job(job: Any, *, head: str,
                 max_timeout_s: int) -> dict[str, Any]:
    """Validate an untrusted job dict against the pinned HEAD.

    Returns the normalized job (validated IR, capped timeout).
    Raises RunnerError for every rejection.
    """
    from .codegen import ir_sha256
    from .ir import canonical_json, validate_ir
    from .proofos import validate_plan

    if not isinstance(job, dict):
        raise RunnerError("job must be a JSON object")
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID_RE.fullmatch(job_id):
        raise RunnerError("job_id must match [A-Za-z0-9_-]{1,64}")
    op = job.get("operation")
    if op not in ALLOWED_OPS:
        raise RunnerError(f"operation {op!r} is not allowlisted; "
                          f"allowed: {sorted(ALLOWED_OPS)}")
    if job.get("revision") != head:
        raise RunnerError("revision mismatch: runner is pinned to "
                          f"{head}, job asks for {job.get('revision')!r}")
    raw_ir = job.get("ir")
    if not isinstance(raw_ir, dict):
        raise RunnerError("job ir must be an object")
    if len(canonical_json(raw_ir).encode("utf-8")) > MAX_IR_BYTES:
        raise RunnerError("job ir too large")
    try:
        ir = validate_ir(copy.deepcopy(raw_ir))
    except (ValueError, TypeError) as exc:
        raise RunnerError(f"job ir invalid: {exc}") from exc
    digest = ir_sha256(ir)
    plan = job.get("plan")
    if plan is not None:
        errors = validate_plan(plan)
        if errors:
            raise RunnerError(f"job plan invalid: {errors[0]}")
        if plan.get("source_commit") != head:
            raise RunnerError("plan source_commit does not match "
                              "the pinned revision")
        if plan.get("stage") == "INVALID":
            raise RunnerError("plan stage is INVALID")
        afters = [c.get("ir_sha256_after") for c in plan.get("changes", [])]
        if digest not in afters:
            raise RunnerError("submitted IR matches no plan change entry "
                              "(plan/IR binding failed)")
    timeout = job.get("timeout_s", DEFAULT_TIMEOUT_S)
    if (not isinstance(timeout, int) or isinstance(timeout, bool)
            or not 1 <= timeout <= max_timeout_s):
        raise RunnerError(f"timeout_s must be 1..{max_timeout_s}")
    return {"job_id": job_id, "operation": op, "revision": head,
            "ir": ir, "ir_sha256": digest,
            "plan_id": plan.get("plan_id") if plan else None,
            "timeout_s": timeout}


def _job_record(job_id: str, status: str, **kw: Any) -> dict[str, Any]:
    rec = {"job_id": job_id, "status": status,
           "updated": time.time()}
    rec.update(kw)
    return rec


def submit(body: bytes, signature: str | None, *,
           config: RunnerConfig, token: str | None,
           target: Any = None) -> dict[str, Any]:
    """Authorize, validate, and start (or replay) a job.

    Idempotent: a duplicate delivery of a known job_id returns the
    stored record instead of re-running. ``target`` is the shared
    TargetRunner (local adapter only).
    """
    if len(body) > MAX_JOB_BYTES:
        raise RunnerError("job body too large")
    authorize(body, signature, token)
    try:
        job = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RunnerError(f"job body is not JSON: {exc}") from exc
    store = JobStore(config.jobs_dir)
    known = store.get(str(job.get("job_id", "")))
    if known is not None:
        # Duplicate delivery: never re-run, report stored state.
        # A live job reports RUNNING; a terminal job replays.
        if known.get("status") not in TERMINAL_JOB:
            return {**known, "duplicate": True}
        return {**known, "duplicate": True}
    head = server_head(config.repo_root)
    try:
        valid = validate_job(job, head=head,
                             max_timeout_s=config.max_timeout_s)
    except RunnerError as exc:
        rec = _job_record(str(job.get("job_id", "unknown")), "REJECTED",
                          reason=str(exc), revision=str(job.get("revision")))
        if JOB_ID_RE.fullmatch(rec["job_id"]):
            store.put(rec)
        raise
    rec = _job_record(valid["job_id"], "RUNNING",
                      operation=valid["operation"],
                      revision=valid["revision"],
                      ir_sha256=valid["ir_sha256"],
                      plan_id=valid["plan_id"],
                      adapter=config.adapter,
                      timeout_s=valid["timeout_s"],
                      started=time.time())
    store.put(rec)
    if config.adapter == "fake":
        return _finish_fake(config, store, rec, valid)
    return _start_local(config, store, rec, valid, target)


def _finish_fake(config: RunnerConfig, store: JobStore,
                 rec: dict[str, Any],
                 valid: dict[str, Any]) -> dict[str, Any]:
    canned = config.fake_results.get(valid["operation"], {})
    rec = {**rec, "status": "COMPLETED", "finished": time.time(),
           "adapter": "fake", "op_id": None,
           "qnx_verified": False,
           "note": ("fake adapter: plumbing only, never a native "
                    "verification verdict"),
           "result": canned or {"echo": valid["operation"]}}
    store.put(rec)
    return rec


def _start_local(config: RunnerConfig, store: JobStore,
                 rec: dict[str, Any], valid: dict[str, Any],
                 target: Any) -> dict[str, Any]:
    if target is None:
        rec = {**rec, "status": "BLOCKED",
               "reason": "local adapter needs a TargetRunner",
               "finished": time.time()}
        store.put(rec)
        return rec
    params: dict[str, Any] = {"ir": valid["ir"]}
    if config.image_dir:
        params["image_dir"] = config.image_dir
        params["ssh_port"] = config.ssh_port
    workflow = ALLOWED_OPS[valid["operation"]]
    try:
        op = target.start(workflow, params=params)
    except Exception as exc:
        name = type(exc).__name__
        if name == "TargetBusy":
            rec = {**rec, "status": "BLOCKED",
                   "reason": f"target leased: {exc}",
                   "finished": time.time()}
            store.put(rec)
            raise RunnerBusy(str(exc)) from exc
        rec = {**rec, "status": "FAILED",
               "reason": f"target start failed: {exc}",
               "finished": time.time()}
        store.put(rec)
        raise RunnerError(f"target start failed: {exc}") from exc
    rec = {**rec, "op_id": op["op_id"]}
    store.put(rec)
    waiter = threading.Thread(target=_join_op,
                              args=(config, valid, rec["op_id"],
                                    time.time()),
                              daemon=True,
                              name=f"genesis-runner-{valid['job_id']}")
    waiter.start()
    return rec


def _join_op(config: RunnerConfig, valid: dict[str, Any],
             op_id: str, started: float) -> None:
    from .target import TERMINAL_TARGET, TargetRunner

    store = JobStore(config.jobs_dir)
    target = TargetRunner(config.target_ops_dir)
    deadline = started + valid["timeout_s"]
    try:
        while time.time() < deadline:
            op = target.get(op_id)
            if op is None:
                break
            if op.get("state") in TERMINAL_TARGET:
                break
            time.sleep(1.0)
        op = target.get(op_id)
        timed_out = (op is None
                     or op.get("state") not in TERMINAL_TARGET)
        if timed_out:
            try:
                target.cancel(op_id)
            except Exception:
                pass
        op = target.get(op_id) or {}
        state = op.get("state", "UNKNOWN")
        if timed_out:
            status, reason = "TIMEOUT", (
                f"op {op_id} exceeded {valid['timeout_s']}s; "
                "cancel requested")
        elif state == "COMPLETED":
            status, reason = "COMPLETED", ""
        elif state == "CANCELLED":
            status, reason = "CANCELLED", op.get("reason", "")
        else:
            status, reason = "FAILED", op.get("reason", state)
        rec = store.get(valid["job_id"]) or {}
        rec.update({"status": status, "reason": reason,
                    "finished": time.time(), "updated": time.time(),
                    "op_state": state,
                    "artifacts": op.get("artifacts", {}),
                    "qnx_verified": bool(
                        (op.get("artifacts") or {}).get("qnx_verified",
                                                       False))})
        store.put(rec)
    finally:
        target.close()


def status(config: RunnerConfig, job_id: str) -> dict[str, Any] | None:
    if not JOB_ID_RE.fullmatch(job_id or ""):
        return None
    return JobStore(config.jobs_dir).get(job_id)


def cancel(config: RunnerConfig, job_id: str,
           target: Any = None) -> dict[str, Any]:
    store = JobStore(config.jobs_dir)
    rec = store.get(job_id)
    if rec is None:
        raise RunnerError(f"unknown job: {job_id}")
    if rec.get("status") in TERMINAL_JOB:
        return rec  # sticky terminal
    if rec.get("op_id") and target is not None:
        try:
            target.cancel(rec["op_id"])
        except Exception:
            pass  # op already settled or owned elsewhere; settle the job
    rec.update({"status": "CANCELLED", "reason": "cancelled by operator",
                "finished": time.time(), "updated": time.time()})
    store.put(rec)
    return rec