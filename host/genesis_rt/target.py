# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §5: native QNX target operations (state machine + runner).

One live op per host (campaign TargetLock). Steps run sequentially in a
worker thread; cancel is honored between steps. Transitions are
append-only and terminal states sticky: a failed step never reads as
success. Records live as JSON under ops_dir (no DB migration).

QEMU steps call the allowlisted cmd_* functions of scripts/qnx_target.py
in-process (lazy import, no shell), except qemu_boot which spawns QEMU
detached via the pinned build_qemu_argv. Free-form guest execution
(cmd_run) is deliberately NOT exposed. Never os.kill() a pid that may
be self: qemu_stop only signals pids verified as live QEMU processes.

v1 scope: validate/env/generate/build/probe_image/qemu_boot/wait_ssh/
qemu_put/qemu_verify/qemu_perf/qemu_stop. seal/replay/identity/sched
land in Task 3b (SEALING/REPLAYING states already reserved).
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .jobs import OWNER_STALE_AFTER_S, pid_alive

log = logging.getLogger("genesis.target")

STATES = ("PENDING", "VALIDATING", "BUILDING", "STAGING", "VERIFYING",
          "MEASURING", "SEALING", "REPLAYING", "COMPLETED")
TERMINAL_TARGET = ("COMPLETED", "FAILED", "CANCELLED", "BLOCKED",
                   "INTERRUPTED")

STEP_STATE: dict[str, str | None] = {
    "validate": "VALIDATING", "env": "VALIDATING",
    "generate": "BUILDING", "build": "BUILDING",
    "probe_image": "STAGING", "qemu_boot": "STAGING",
    "wait_ssh": "STAGING", "qemu_put": "STAGING",
    "qemu_verify": "VERIFYING",
    "qemu_perf": "MEASURING",
    "qemu_stop": None,  # teardown: tracked step, no state transition
    "seal": "SEALING",
    "replay": "REPLAYING",
}

WORKFLOWS: dict[str, list[str]] = {
    "full": ["validate", "env", "generate", "build", "probe_image",
             "qemu_boot", "wait_ssh", "qemu_put", "qemu_verify",
             "qemu_perf", "qemu_stop", "seal", "replay"],
    "build-only": ["validate", "env", "generate", "build", "seal", "replay"],
    "verify-only": ["env", "probe_image", "qemu_boot", "wait_ssh",
                    "qemu_verify", "qemu_stop"],
}

GUEST_STAGING_DIR = "/tmp/genesis"
DEFAULT_TARGET_USER = "qnxuser"

_OP_ID_RE = re.compile(r"op-[0-9a-f]{12}")
_USER_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
_MEM_RE = re.compile(r"\d+[GM]")
_CPU_RE = re.compile(r"[A-Za-z0-9_+,.\-]+")
_SCEN_RE = re.compile(r"[A-Za-z0-9_.\-]{1,128}")
_ACCELS = ("auto", "whpx", "tcg", "kvm")


class TargetOpError(Exception):
    """Unknown workflow/op, bad params, or step failure (HTTP 400)."""


class TargetBusy(Exception):
    """Another target op holds the campaign lock (HTTP 409)."""


class TargetBlocked(Exception):
    """Environment cannot run this op (honest BLOCKED, never PASS)."""


def valid_op_id(op_id: str) -> bool:
    return bool(_OP_ID_RE.fullmatch(op_id or ""))


_QT: Any | None = None


def _qt() -> Any:
    """Lazy scripts/qnx_target.py import (no shell, in-process calls)."""
    global _QT
    if _QT is None:
        scripts = Path(__file__).resolve().parent.parent.parent / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import qnx_target as mod
        _QT = mod
    return _QT


# -- params -----------------------------------------------------------
def _validate_params(steps: list[str], params: dict[str, Any]) -> dict[str, Any]:
    allowed = {"ir", "scenarios", "build_timeout", "image_dir", "memory",
               "accel", "cpu", "ssh_port", "user", "wait", "src", "samples",
               "build_set", "extra_src"}
    unknown = sorted(set(params) - allowed)
    if unknown:
        raise TargetOpError(f"unknown op params: {unknown}")
    out = dict(params)
    if "ir" in out and not isinstance(out["ir"], dict):
        raise TargetOpError("param 'ir' must be an object")
    if "ir" in out:
        # Titan F3: bound the persisted op record like /runs does.
        try:
            blob = json.dumps(out["ir"]).encode("utf-8")
        except (TypeError, ValueError):
            raise TargetOpError("param 'ir' must be JSON-serializable")
        if len(blob) > 256 * 1024:
            raise TargetOpError("param 'ir' exceeds 256 KiB")
    if "build_timeout" in out and not _is_int(out["build_timeout"], 60, 1800):
        raise TargetOpError("param 'build_timeout' must be 60..1800")
    if "image_dir" in out:
        p = Path(out["image_dir"])
        if not p.is_dir():
            raise TargetOpError(f"param 'image_dir' is not a directory: {p}")
        out["image_dir"] = str(p)
    if "memory" in out and not (isinstance(out["memory"], str)
                                and _MEM_RE.fullmatch(out["memory"])):
        raise TargetOpError("param 'memory' must look like '4G'")
    if "accel" in out and out["accel"] not in _ACCELS:
        raise TargetOpError(f"param 'accel' must be one of {_ACCELS}")
    if "cpu" in out and not (isinstance(out["cpu"], str)
                             and _CPU_RE.fullmatch(out["cpu"])):
        raise TargetOpError("param 'cpu' has invalid characters")
    if "ssh_port" in out and not _is_int(out["ssh_port"], 1, 65535):
        raise TargetOpError("param 'ssh_port' must be 1..65535")
    if "user" in out and not (isinstance(out["user"], str)
                              and _USER_RE.fullmatch(out["user"])):
        raise TargetOpError("param 'user' has invalid characters")
    if "wait" in out and not _is_int(out["wait"], 5, 900):
        raise TargetOpError("param 'wait' must be 5..900")
    for _list_param in ("src", "extra_src"):
        if _list_param in out and isinstance(out[_list_param], list) \
                and len(out[_list_param]) > 64:
            raise TargetOpError(f"param '{_list_param}' exceeds 64 files")
    if "src" in out:
        if not isinstance(out["src"], list) or not out["src"]:
            raise TargetOpError("param 'src' must be a non-empty file list")
        for s in out["src"]:
            if not isinstance(s, str) or not Path(s).is_file():
                raise TargetOpError(f"param 'src' missing file: {s!r}")
    if "extra_src" in out:
        if not isinstance(out["extra_src"], list) or not out["extra_src"]:
            raise TargetOpError("param 'extra_src' must be a non-empty file list")
        for s in out["extra_src"]:
            if not isinstance(s, str) or not Path(s).is_file():
                raise TargetOpError(f"param 'extra_src' missing file: {s!r}")
    if "samples" in out and not _is_int(out["samples"], 10, 100000):
        raise TargetOpError("param 'samples' must be 10..100000")
    if "build_set" in out and not Path(out["build_set"]).is_file():
        raise TargetOpError(f"param 'build_set' missing file: {out['build_set']!r}")
    if "scenarios" in out:
        sc = out["scenarios"]
        if (not isinstance(sc, list) or not sc
                or any(not isinstance(s, str) or not s for s in sc)):
            raise TargetOpError("param 'scenarios' must be a non-empty string list")
        if len(sc) > 32:
            raise TargetOpError("param 'scenarios' exceeds 32 entries")
        if any(len(s) > 128 or not _SCEN_RE.fullmatch(s) for s in sc):
            raise TargetOpError("param 'scenarios' entries must be "
                                "[A-Za-z0-9_.-]{1,128}")
    need_ir = {"validate", "generate"} & set(steps)
    if need_ir and "ir" not in out:
        raise TargetOpError(f"steps {sorted(need_ir)} require param 'ir'")
    need_image = {"probe_image", "qemu_boot", "qemu_stop"} & set(steps)
    if "qemu_boot" in steps and "image_dir" not in out:
        raise TargetOpError("step 'qemu_boot' requires param 'image_dir'")
    if "probe_image" in steps and "image_dir" not in out:
        raise TargetOpError("step 'probe_image' requires param 'image_dir'")
    _ = need_image
    return out


def _is_int(v: Any, lo: int, hi: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def _unlocked(fn: Callable[..., int]) -> Callable[..., int]:
    """cmd_* without the campaign-lock decorator.

    The op already holds the campaign lock for its whole lifetime;
    re-acquiring per step would deadlock against ourselves.
    """
    return getattr(fn, "__wrapped__", fn)


def _with_tail(detail: str, buf: io.StringIO, limit: int = 400) -> str:
    tail = buf.getvalue()[-limit:].strip()
    if tail:
        return f"{detail}\n--- step output tail ---\n{tail}"
    return detail


# -- runner -----------------------------------------------------------
StepFn = Callable[[dict[str, Any]], tuple[bool, str]]


class TargetRunner:
    def __init__(self, ops_dir: str | Path,
                 lock_path: str | Path | None = None) -> None:
        self.ops_dir = Path(ops_dir)
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = (Path(lock_path) if lock_path
                          else self.ops_dir / "target.lock")
        self._lock = threading.RLock()
        self._threads: dict[str, threading.Thread] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._procs: dict[str, Any] = {}
        self._closed = False
        self._recover()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            evts = list(self._cancel.values())
            threads = list(self._threads.values())
        for e in evts:
            e.set()
        for t in threads:
            t.join(timeout=10)

    # -- store ------------------------------------------------------
    def _record_path(self, op_id: str) -> Path:
        return self.ops_dir / f"{op_id}.json"

    def _events_path(self, op_id: str) -> Path:
        return self.ops_dir / f"{op_id}.events.jsonl"

    def get(self, op_id: str) -> dict[str, Any] | None:
        # RLock (re-entrant: callers already holding it are fine) +
        # atomic replace in _write_record: readers never see torn JSON.
        with self._lock:
            try:
                return json.loads(self._record_path(op_id).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None

    def _write_record(self, rec: dict[str, Any]) -> None:
        rec["updated"] = time.time()
        path = self._record_path(rec["op_id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        # Windows: a concurrent reader (open without FILE_SHARE_DELETE)
        # makes replace fail with WinError 5. The contention window is
        # microseconds; retry bounded before failing loud (2026-11-06).
        for attempt in range(10):
            try:
                tmp.replace(path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.02)

    def _emit(self, op_id: str, kind: str, message: str) -> None:
        with self._lock:
            path = self._events_path(op_id)
            try:
                seq = sum(1 for _ in path.read_text(encoding="utf-8").splitlines()
                          if _.strip())
            except OSError:
                seq = 0
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"seq": seq, "kind": kind,
                                     "message": message,
                                     "ts": time.time()}) + "\n")

    def list_ops(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(100, limit))
        recs = []
        for path in self.ops_dir.glob("op-*.json"):
            try:
                recs.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        recs.sort(key=lambda r: (r.get("updated", 0), r.get("op_id", "")),
                  reverse=True)
        return [{"op_id": r.get("op_id"), "workflow": r.get("workflow"),
                 "state": r.get("state"), "updated": r.get("updated")}
                for r in recs[:limit]]

    def events(self, op_id: str, after: int = -1,
               limit: int = 200) -> list[dict[str, Any]]:
        """Events with seq strictly greater than ``after`` (-1 = all).

        One poll returns at most ``limit`` rows (same page bound as
        the job store): a slow SSE consumer pages through a giant op
        log instead of receiving it in one burst (OMEGA6 D2).
        """
        try:
            lines = self._events_path(op_id).read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            if len(out) >= max(1, limit):
                break
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("seq", -1) > after:
                out.append(row)
        return out

    def _recover(self) -> None:
        # Ownership-guarded: only reap ops whose owner process is gone
        # (or records untouched for OWNER_STALE_AFTER_S). A blind reap
        # here killed a live campaign op on 2026-11-05 when a test
        # constructed a second runner against the same store.
        now = time.time()
        for path in sorted(self.ops_dir.glob("op-*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if rec.get("state") not in TERMINAL_TARGET:
                owner = rec.get("owner_pid")
                if (isinstance(owner, int) and pid_alive(owner)
                        and (now - (rec.get("updated") or 0))
                        <= OWNER_STALE_AFTER_S):
                    continue
                stale = (now - (rec.get("updated") or 0)) > OWNER_STALE_AFTER_S
                rec["state"] = "INTERRUPTED"
                rec["reason"] = ("stale: no update for 24h (possible pid reuse)"
                                 if stale and isinstance(owner, int)
                                 and pid_alive(owner)
                                 else "previous process ended before completion")
                self._write_record(rec)
                self._emit(rec["op_id"], "interrupted", rec["reason"])
                log.warning("op=%s recovered as interrupted", rec.get("op_id"))

    # -- control ----------------------------------------------------
    def start(self, workflow: str, params: dict[str, Any] | None = None,
              step_impls: dict[str, StepFn] | None = None) -> dict[str, Any]:
        if workflow not in WORKFLOWS:
            raise TargetOpError(f"unknown workflow: {workflow}")
        steps = WORKFLOWS[workflow]
        validated = _validate_params(steps, dict(params or {}))
        impls = dict(STEP_IMPLS)
        if step_impls:
            impls.update(step_impls)
        missing = [s for s in steps if s not in impls]
        if missing:
            raise TargetOpError(f"no implementation for steps: {missing}")
        op_id = None
        for _ in range(8):  # red-team round 2, A3: never reuse an op id
            candidate = f"op-{uuid.uuid4().hex[:12]}"
            if not self._record_path(candidate).exists():
                op_id = candidate
                break
        if op_id is None:
            raise TargetOpError("could not allocate a fresh operation id")
        with self._lock:
            if self._closed:
                raise TargetOpError("runner is closed")
            if self._threads:
                raise TargetBusy("another target op is live")
        qt = _qt()
        lock = qt.TargetLock(self.lock_path, owner=f"op:{op_id}")
        try:
            lock.acquire()
        except Exception as exc:
            if type(exc).__name__ == "TargetBusy":
                raise TargetBusy(str(exc)) from exc
            raise
        now = time.time()
        rec = {"op_id": op_id, "workflow": workflow, "state": "PENDING",
               "reason": "",
               "steps": [{"name": n, "state": "pending", "detail": ""}
                         for n in steps],
               "params": validated, "artifacts": {},
               "created": now, "updated": now, "owner_pid": os.getpid()}
        self._write_record(rec)
        self._emit(op_id, "op_started", f"workflow={workflow}")
        cancel_evt = threading.Event()
        thread = threading.Thread(target=self._run,
                                  args=(op_id, steps, validated, impls,
                                        lock, cancel_evt),
                                  daemon=True, name=f"genesis-target-{op_id}")
        with self._lock:
            self._threads[op_id] = thread
            self._cancel[op_id] = cancel_evt
        thread.start()
        log.info("op=%s start workflow=%s", op_id, workflow)
        # Return the as-accepted record, not a re-read: the worker may
        # already have advanced the on-disk state (PENDING->... race).
        return copy.deepcopy(rec)

    def cancel(self, op_id: str) -> dict[str, Any]:
        rec = self.get(op_id)
        if rec is None:
            raise TargetOpError(f"unknown op: {op_id}")
        if rec["state"] in TERMINAL_TARGET:
            return rec  # sticky terminal: repeated cancel reports state
        with self._lock:
            evt = self._cancel.get(op_id)
        if evt is None:
            rec["state"] = "CANCELLED"  # live nowhere here: settle directly
            rec["reason"] = "cancelled while not running"
            self._write_record(rec)
            self._emit(op_id, "op_cancelled", rec["reason"])
            return self.get(op_id)  # type: ignore[return-value]
        evt.set()
        return self.get(op_id)  # type: ignore[return-value]

    # -- worker -----------------------------------------------------
    def _set_state(self, op_id: str, state: str) -> None:
        with self._lock:
            rec = self.get(op_id)
            if rec is None or rec["state"] in TERMINAL_TARGET:
                return
            rec["state"] = state
            self._write_record(rec)
            self._emit(op_id, "state", state)

    def _set_step(self, op_id: str, name: str, state: str, detail: str) -> None:
        with self._lock:
            rec = self.get(op_id)
            if rec is None:
                return
            for s in rec["steps"]:
                if s["name"] == name:
                    s["state"] = state
                    s["detail"] = detail[:500]
            self._write_record(rec)
            self._emit(op_id, f"step_{state}", f"{name}: {detail[:200]}")

    def _finish(self, op_id: str, state: str, reason: str) -> None:
        with self._lock:
            rec = self.get(op_id)
            if rec is None or rec["state"] in TERMINAL_TARGET:
                return
            rec["state"] = state
            rec["reason"] = reason[:500]
            self._write_record(rec)
            self._emit(op_id, f"op_{state.lower()}", reason[:200])
            log.info("op=%s finish state=%s", op_id, state)

    def _run(self, op_id: str, steps: list[str], params: dict[str, Any],
             impls: dict[str, StepFn], lock: Any,
             cancel_evt: threading.Event) -> None:
        work_dir = self.ops_dir / op_id
        work_dir.mkdir(parents=True, exist_ok=True)
        ctx: dict[str, Any] = {"op_id": op_id, "runner": self,
                               "ops_dir": str(self.ops_dir),
                               "work_dir": str(work_dir),
                               "params": params, "artifacts": {},
                               "cancel": cancel_evt}
        try:
            for name in steps:
                if cancel_evt.is_set():
                    self._finish(op_id, "CANCELLED", "cancelled by operator")
                    return
                target_state = STEP_STATE.get(name)
                if target_state is not None:
                    self._set_state(op_id, target_state)
                self._set_step(op_id, name, "running", "")
                # Capture the step's stdout: cmd_* diagnostics land in the
                # record on failure instead of only the server log. Safe in
                # practice: one live op, and pipeline logging uses stderr.
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf):
                        ok, detail = impls[name](ctx)
                except TargetBlocked as exc:
                    self._set_step(op_id, name, "blocked", str(exc))
                    self._finish(op_id, "BLOCKED", str(exc))
                    return
                except TargetOpError as exc:
                    self._set_step(op_id, name, "failed", str(exc))
                    self._finish(op_id, "FAILED", str(exc))
                    return
                except Exception as exc:  # noqa: BLE001 — step fault → FAILED
                    detail = f"{type(exc).__name__}: {exc}"
                    detail = _with_tail(detail, buf)
                    self._set_step(op_id, name, "failed", detail)
                    self._finish(op_id, "FAILED", detail)
                    return
                if not ok:
                    detail = _with_tail(detail, buf)
                    self._set_step(op_id, name, "failed", detail)
                    self._finish(op_id, "FAILED", detail)
                    return
                self._set_step(op_id, name, "done", detail)
                self._save_artifacts(op_id, ctx["artifacts"])
            if cancel_evt.is_set():
                self._finish(op_id, "CANCELLED", "cancelled by operator")
            else:
                self._finish(op_id, "COMPLETED", "all steps done")
        finally:
            try:
                self._cleanup_qemu(op_id, ctx)
            except Exception:
                pass  # cleanup never masks the op outcome
            with self._lock:
                self._threads.pop(op_id, None)
                self._cancel.pop(op_id, None)
            try:
                lock.release()
            except OSError:
                pass

    def _cleanup_qemu(self, op_id: str, ctx: dict[str, Any]) -> None:
        """Bounded cleanup (§5): stop a booted QEMU unless already stopped."""
        if not ctx["artifacts"].get("qemu_pid"):
            return
        rec = self.get(op_id)
        if rec is not None:
            for step in rec.get("steps", []):
                if step["name"] == "qemu_stop" and step["state"] == "done":
                    return
        self._set_step(op_id, "qemu_stop", "running", "failure cleanup")
        try:
            ok, detail = STEP_IMPLS["qemu_stop"](ctx)
        except Exception as exc:  # noqa: BLE001 — best effort
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        self._set_step(op_id, "qemu_stop", "done" if ok else "failed",
                       f"cleanup: {detail}")
        self._emit(op_id, "cleanup", detail[:200])

    def _save_artifacts(self, op_id: str, artifacts: dict[str, Any]) -> None:
        with self._lock:
            rec = self.get(op_id)
            if rec is None:
                return
            safe = {}
            for key, val in artifacts.items():
                try:
                    safe[key] = json.loads(json.dumps(val))
                except (TypeError, ValueError):
                    safe[key] = str(val)[:200]
            rec["artifacts"] = safe
            self._write_record(rec)

    def _save_params(self, op_id: str, params: dict[str, Any]) -> None:
        """Persist post-start param updates (validate step normalization)."""
        with self._lock:
            rec = self.get(op_id)
            if rec is None:
                return
            try:
                rec["params"] = json.loads(json.dumps(params))
            except (TypeError, ValueError):
                return  # keep the start-time params rather than corrupt
            self._write_record(rec)


# -- real steps ---------------------------------------------------------
def _step_validate(ctx: dict[str, Any]) -> tuple[bool, str]:
    from .projects import validate_any
    try:
        _, valid = validate_any(ctx["params"]["ir"])
    except Exception as exc:
        return False, f"invalid IR: {exc}"
    # Normalize once, up front: validation sorts IR lists, so the raw
    # posted doc and the normalized form digest differently. Every later
    # step (generate manifest, verify --ir binding, seal) must use the
    # normalized form or provenance binding fails loudly at the gate.
    ctx["params"]["ir"] = valid
    ctx["runner"]._save_params(ctx["op_id"], ctx["params"])
    mid = valid.get("machine", {}).get("id", "?") if isinstance(valid, dict) else "?"
    ctx["artifacts"]["machine_id"] = mid
    return True, f"IR valid (machine={mid}, normalized)"


def _step_env(ctx: dict[str, Any]) -> tuple[bool, str]:
    from .build_adapter import probe, probe_qemu
    sdk = probe()
    try:
        qemu = probe_qemu()
    except Exception:
        qemu = {"present": False}
    ctx["artifacts"]["sdk_present"] = bool(sdk.get("sdk_present"))
    ctx["artifacts"]["qemu_present"] = bool(qemu.get("present"))
    if not sdk.get("sdk_present"):
        raise TargetBlocked("QNX SDK not installed (check-env for setup)")
    qcc = sdk.get("qcc_version", "?")
    return True, f"SDK present (qcc={qcc}, qemu={qemu.get('present')})"


def _step_generate(ctx: dict[str, Any]) -> tuple[bool, str]:
    from .codegen import generate
    from .codegen_v2 import generate_v2
    from .projects import validate_any
    out = Path(ctx["work_dir"]) / "gen"
    genesis_src = Path(__file__).resolve().parent.parent.parent / "target" / "qnx8"
    try:
        version, valid = validate_any(ctx["params"]["ir"])
    except Exception as exc:
        return False, f"invalid IR at generate: {exc}"
    # Mirror the CLI dispatch: v2 IRs need the machine module + V2
    # define, which v1 codegen silently drops (native 8-Nov finding).
    generate_fn = generate_v2 if version == 2 else generate
    try:
        manifest = generate_fn(valid, out, genesis_src=str(genesis_src))
    except Exception as exc:
        return False, f"codegen failed: {exc}"
    files = manifest.get("files", [])
    sha = str(manifest.get("ir_sha256", "?"))
    manifest_path = Path(ctx["work_dir"]) / "gen-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                             encoding="utf-8")
    ctx["artifacts"]["gen_dir"] = str(out)
    ctx["artifacts"]["gen_manifest"] = str(manifest_path)
    ctx["artifacts"]["ir_sha256"] = sha
    return True, f"{len(files)} files, ir {sha[:12]}"


_GEN_SRC_SUFFIXES = {".mk", ".h", ".c"}


def _built_binaries(gen_dir: Path) -> list[str]:
    """QNX target binaries: genesis_* files that are not build sources."""
    return sorted(str(p) for p in gen_dir.glob("genesis_*")
                  if p.is_file() and p.suffix not in _GEN_SRC_SUFFIXES)


def _step_build(ctx: dict[str, Any]) -> tuple[bool, str]:
    from .build_adapter import build_qnx
    gen_dir = ctx["artifacts"].get("gen_dir")
    if not gen_dir:
        return False, "no gen_dir (generate step did not run?)"
    rec = build_qnx(gen_dir, timeout=int(ctx["params"].get("build_timeout", 600)))
    if rec.get("status") == "blocked":
        raise TargetBlocked("QNX SDK missing at build time")
    build_rec_path = Path(ctx["work_dir"]) / "qnx-build-record.json"
    build_rec_path.write_text(json.dumps(rec, indent=2, sort_keys=True, default=str),
                              encoding="utf-8")
    ctx["artifacts"]["qnx_build_record"] = str(build_rec_path)
    bins = _built_binaries(Path(gen_dir))
    ctx["artifacts"]["binaries"] = bins
    if rec.get("status") != "ok":
        slim = {k: v for k, v in rec.items() if isinstance(v, (str, int, bool))}
        return False, f"build failed: {json.dumps(slim)[:300]}"
    return True, f"build ok, {len(bins)} binaries"


def _step_probe_image(ctx: dict[str, Any]) -> tuple[bool, str]:
    qt = _qt()
    rc = qt.cmd_probe_image(argparse.Namespace(image_dir=ctx["params"]["image_dir"]))
    if rc != 0:
        return False, f"probe_image rc={rc}"
    return True, "image probed"


def _step_qemu_boot(ctx: dict[str, Any]) -> tuple[bool, str]:
    qt = _qt()
    params = ctx["params"]
    qemu = qt.probe_qemu()
    if not qemu.get("present"):
        raise TargetBlocked("QEMU not found (set GENESIS_QEMU or install QEMU)")
    try:
        argv = qt.build_qemu_argv(
            qemu["path"], Path(params["image_dir"]),
            memory=params.get("memory", "4G"), accel=params.get("accel", "auto"),
            cpu=params.get("cpu", "auto"), ssh_port=int(params.get("ssh_port", 2222)))
    except FileNotFoundError as exc:
        return False, f"boot refused: {exc}"
    transcript = Path(ctx["work_dir"]) / "qemu-console.log"
    with open(transcript, "wb") as fh:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=fh,
                                stderr=subprocess.STDOUT)
    pidfile = Path(ctx["work_dir"]) / "qemu.pid"
    pidfile.write_text(str(proc.pid), encoding="utf-8")
    runner: TargetRunner = ctx["runner"]
    with runner._lock:
        runner._procs[ctx["op_id"]] = proc
    ctx["artifacts"]["qemu_pid"] = proc.pid
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = transcript.read_bytes()[-2000:].decode("utf-8", "replace")
            return False, f"QEMU exited at boot (rc={proc.returncode}): {tail[-300:]}"
        time.sleep(1)
    if not qt._pid_is_qemu(proc.pid):
        return False, f"QEMU pid {proc.pid} not a live QEMU process"
    return True, f"QEMU pid {proc.pid} alive"


def _wait_ssh_banner(port: int, budget_s: float) -> bool:
    """True when an SSH banner arrives before the budget expires.

    A bare TCP connect is not readiness (QEMU user-net accepts while the
    guest is still booting). Sequential single-connection probes only.
    """
    import socket
    deadline = time.monotonic() + budget_s
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        except OSError:
            time.sleep(2)
            continue
        try:
            remaining = max(0.5, min(5.0, deadline - time.monotonic()))
            sock.settimeout(remaining)
            banner = sock.recv(64)
        except OSError:
            banner = b""
        finally:
            try:
                sock.close()
            except OSError:
                pass
        if banner.startswith(b"SSH-"):
            return True
        time.sleep(5)
    return False


def _step_wait_ssh(ctx: dict[str, Any]) -> tuple[bool, str]:
    params = ctx["params"]
    port = int(params.get("ssh_port", 2222))
    wait = int(params.get("wait", 300))
    if _wait_ssh_banner(port, wait):
        return True, f"ssh banner on port {port}"
    return False, f"no ssh banner after {wait}s (guest sshd not up?)"


def _step_qemu_put(ctx: dict[str, Any]) -> tuple[bool, str]:
    qt = _qt()
    params = ctx["params"]
    src = params.get("src") or ctx["artifacts"].get("binaries") or []
    extra = params.get("extra_src") or []
    src = list(src) + [s for s in extra if s not in src]
    if not src:
        return False, "nothing to stage (no binaries built, no src given)"
    # Hermetic staging: the QEMU disk persists across boots, so leftovers
    # from previous campaigns would run unattributed. Drop them before
    # staging so verify observes exactly this op's files. Fixed command
    # (runner constant, no user input) confined to the staging dir.
    rc_clean = _unlocked(qt.cmd_run)(argparse.Namespace(
        command=[f"rm -f {GUEST_STAGING_DIR}/genesis_*"], timeout=60,
        ssh_port=int(params.get("ssh_port", 2222)),
        user=params.get("user", DEFAULT_TARGET_USER), password=None,
        out=None))
    if rc_clean != 0:
        return False, f"staging cleanup rc={rc_clean}"
    manifest_out = str(Path(ctx["work_dir"]) / "stage-manifest.json")
    rc = _unlocked(qt.cmd_put)(argparse.Namespace(
        src=list(src), dest=GUEST_STAGING_DIR,
        ssh_port=int(params.get("ssh_port", 2222)),
        user=params.get("user", DEFAULT_TARGET_USER), password=None,
        manifest_out=manifest_out))
    if rc != 0:
        return False, f"put rc={rc}"
    ctx["artifacts"]["stage_manifest"] = manifest_out
    return True, f"{len(src)} files staged + manifest (staging cleaned)"


def _step_qemu_verify(ctx: dict[str, Any]) -> tuple[bool, str]:
    qt = _qt()
    params = ctx["params"]
    work = Path(ctx["work_dir"])
    ir_path = work / "ir.json"
    ir_path.write_text(json.dumps(params.get("ir", {})), encoding="utf-8")
    manifest = work / "stage-manifest.json"
    out = work / "target"
    rc = _unlocked(qt.cmd_verify)(argparse.Namespace(
        ir=str(ir_path), build_set=params.get("build_set"),
        require_manifest=str(manifest) if manifest.is_file() else None,
        password=None, ssh_port=int(params.get("ssh_port", 2222)),
        user=params.get("user", DEFAULT_TARGET_USER), out=str(out)))
    if rc != 0:
        return False, f"verify rc={rc} (see {out.name}/)"
    ctx["artifacts"]["target_dir"] = str(out)
    return True, f"target matrix PASS (see {out.name}/)"


def _step_qemu_perf(ctx: dict[str, Any]) -> tuple[bool, str]:
    qt = _qt()
    params = ctx["params"]
    out = Path(ctx["work_dir"]) / "perf"
    rc = _unlocked(qt.cmd_perf)(argparse.Namespace(
        password=None, ssh_port=int(params.get("ssh_port", 2222)),
        user=params.get("user", DEFAULT_TARGET_USER),
        build_set=params.get("build_set"),
        samples=int(params.get("samples", 1000)), out=str(out)))
    if rc != 0:
        return False, f"perf rc={rc} (see {out.name}/)"
    ctx["artifacts"]["perf_dir"] = str(out)
    return True, f"perf done (see {out.name}/)"


def _step_qemu_stop(ctx: dict[str, Any]) -> tuple[bool, str]:
    import os
    import platform
    import signal

    qt = _qt()
    pidfile = Path(ctx["work_dir"]) / "qemu.pid"
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True, "nothing running (no pidfile)"
    # Never signal a pid that is not a verified live QEMU process
    # (PID reuse; our own interpreter image never matches).
    if not qt._pid_is_qemu(pid):
        try:
            pidfile.unlink()
        except OSError:
            pass
        return True, f"pid {pid} not live QEMU; stale pidfile cleared"
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError as exc:
        return False, f"cannot signal pid {pid}: {exc}"
    if not qt._wait_pid_gone(pid, 20):
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=30)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        if not qt._wait_pid_gone(pid, 10):
            return False, f"pid {pid} still alive; pidfile kept"
    try:
        pidfile.unlink()
    except OSError:
        pass
    runner: TargetRunner = ctx["runner"]
    with runner._lock:
        proc = runner._procs.pop(ctx["op_id"], None)
    if proc is not None:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
    return True, f"QEMU pid {pid} stopped"


def _step_seal(ctx: dict[str, Any]) -> tuple[bool, str]:
    """Seal an Evidence Passport: host sims + build + target records + gate.

    Mirrors run_pipeline's seal recipe (faultlab sims, build_passport,
    gate verdict, never a vacuous PASS). A gate FAIL fails the op: a
    COMPLETED op always carries a PASS passport.
    """
    from . import faultlab
    from .evidence import attach_verdict, build_passport, save_passport
    from .gate import evaluate
    from .projects import validate_any
    params = ctx["params"]
    work = Path(ctx["work_dir"])
    try:
        _, valid = validate_any(params["ir"])
    except Exception as exc:
        return False, f"invalid IR at seal: {exc}"
    # Refuse before running sims: seal requires generate+build artifacts.
    manifest_path = Path(ctx["artifacts"].get("gen_manifest", ""))
    if not manifest_path.is_file():
        return False, "no gen manifest (generate step did not run?)"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build_rec_path = ctx["artifacts"].get("qnx_build_record")
    if not build_rec_path or not Path(build_rec_path).is_file():
        return False, "no qnx build record (build step did not run?)"
    build_rec = json.loads(Path(build_rec_path).read_text(encoding="utf-8"))
    wanted = params.get("scenarios") or list(valid["verification"]["scenarios"])
    try:
        results = faultlab.run_all(valid, wanted)
    except Exception as exc:
        return False, f"host sims failed: {exc}"
    target_rec = None
    target_rec_path = work / "target" / "qnx-target-record.json"
    if target_rec_path.is_file():
        target_rec = json.loads(target_rec_path.read_text(encoding="utf-8"))
    perf_rec = None
    perf_rec_path = work / "perf" / "qnx-perf-record.json"
    if perf_rec_path.is_file():
        perf_rec = json.loads(perf_rec_path.read_text(encoding="utf-8"))
    try:
        passport = build_passport(ctx["op_id"], valid, manifest, results,
                                  build_rec, target_rec, None, perf_rec)
    except Exception as exc:
        return False, f"passport build failed: {exc}"
    verdict = evaluate(passport, wanted)
    attach_verdict(passport, verdict)
    passport_path = work / "passport.json"
    save_passport(passport, passport_path)
    ctx["artifacts"]["passport"] = str(passport_path)
    ctx["artifacts"]["verdict"] = verdict["verdict"]
    ctx["artifacts"]["wanted"] = wanted
    ctx["artifacts"]["qnx_verified"] = verdict["qnx_verified"]
    if verdict["verdict"] != "PASS":
        top = "; ".join(verdict.get("reasons", [])[:3])
        return False, f"gate FAIL: {top}"
    return True, (f"sealed PASS (qnx_verified={verdict['qnx_verified']}, "
                   f"{len(wanted)} scenarios)")


def _step_replay(ctx: dict[str, Any]) -> tuple[bool, str]:
    """Independent replay: recompute chain + gate from the sealed file."""
    from .evidence import load_passport, verify_chain
    from .gate import evaluate
    ppath = ctx["artifacts"].get("passport")
    if not ppath or not Path(ppath).is_file():
        return False, "no sealed passport (seal step did not run?)"
    try:
        passport = load_passport(ppath)
    except Exception as exc:
        return False, f"replay refused: {exc}"
    # Bind the file to THIS op: a valid passport sealed for another
    # op (or another IR) swapped onto our path must not replay as
    # ours, even when its verdict string happens to match.
    if passport.get("run_id") != ctx["op_id"]:
        return False, (f"replay refused: passport run_id "
                       f"{passport.get('run_id')!r} != op {ctx['op_id']}")
    ir_blocks = [r.get("body", {}) for r in passport.get("chain", [])
                 if isinstance(r, dict) and r.get("kind") == "ir"]
    sealed_sha = ctx["artifacts"].get("ir_sha256")
    if not ir_blocks or ir_blocks[0].get("ir_sha256") != sealed_sha:
        return False, ("replay refused: passport ir_sha256 "
                       f"{ir_blocks[0].get('ir_sha256') if ir_blocks else None!r} "
                       f"!= sealed {sealed_sha!r}")
    errors = verify_chain(passport)
    if errors:
        return False, f"chain invalid: {errors[0]}"
    wanted = ctx["artifacts"].get("wanted", [])
    verdict = evaluate(passport, wanted)
    sealed = ctx["artifacts"].get("verdict")
    if verdict["verdict"] != sealed:
        return False, (f"replay verdict {verdict['verdict']} differs from "
                       f"sealed {sealed}")
    ctx["artifacts"]["replay"] = {"verdict": verdict["verdict"],
                                  "qnx_verified": verdict["qnx_verified"]}
    return True, (f"replay matches ({verdict['verdict']}, "
                   f"qnx_verified={verdict['qnx_verified']})")


STEP_IMPLS: dict[str, StepFn] = {
    "validate": _step_validate,
    "env": _step_env,
    "generate": _step_generate,
    "build": _step_build,
    "probe_image": _step_probe_image,
    "qemu_boot": _step_qemu_boot,
    "wait_ssh": _step_wait_ssh,
    "qemu_put": _step_qemu_put,
    "qemu_verify": _step_qemu_verify,
    "qemu_perf": _step_qemu_perf,
    "qemu_stop": _step_qemu_stop,
    "seal": _step_seal,
    "replay": _step_replay,
}
