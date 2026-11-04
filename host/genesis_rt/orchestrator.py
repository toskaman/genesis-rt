# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Orchestrator: validate -> codegen -> build -> verify -> evidence -> gate.

Single-entry pipeline used by the CLI, API and demo script. Every step
records a structured outcome; QNX steps without an SDK are recorded as
"blocked" and never as passed.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import build_adapter, codegen, evidence, faultlab, gate
from .ir import load_ir_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_SRC = REPO_ROOT / "target" / "qnx8"


class PipelineError(RuntimeError):
    """A pipeline step failed; partial evidence was written to run_dir."""


class CancelledRun(Exception):
    """A run aborted by cancellation request; cancel evidence on disk."""

    def __init__(self, run_id: str, run_dir: Path):
        super().__init__(f"run {run_id} cancelled by request")
        self.run_id = run_id
        self.run_dir = str(run_dir)


_ACTIVE: set[str] = set()
_CANCELLED: set[str] = set()
_ACTIVE_LOCK = threading.Lock()


def request_cancel(run_id: str) -> bool:
    """Flag an active run for cancellation. False when no such active run."""
    with _ACTIVE_LOCK:
        if run_id in _ACTIVE:
            _CANCELLED.add(run_id)
            return True
        return False


def _check_cancelled(run_id: str, run_dir: Path, steps: dict[str, Any]) -> None:
    with _ACTIVE_LOCK:
        cancelled = run_id in _CANCELLED
    if cancelled:
        failure = {"step": "cancelled",
                   "error": "CancelledRun: run cancelled by request"}
        _write_failure(run_dir, steps, failure)
        raise CancelledRun(run_id, run_dir)


def _fail(step: str, exc: BaseException) -> dict[str, Any]:
    return {"step": step, "error": f"{type(exc).__name__}: {exc}"}


def _write_failure(run_dir: Path, steps: dict[str, Any],
                   failure: dict[str, Any]) -> Path:
    path = run_dir / "failure.json"
    path.write_text(json.dumps({"steps": steps, "failure": failure},
                               indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_pipeline(ir_path: str | Path, artifacts_dir: str | Path,
                 run_id: str | None = None,
                 scenarios: list[str] | None = None,
                 target_record: str | Path | None = None) -> dict[str, Any]:
    t0 = time.monotonic()
    explicit_id = run_id is not None
    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    adir = Path(artifacts_dir)
    run_dir = adir / run_id
    if explicit_id and (run_dir / "passport.json").exists():
        raise PipelineError(f"run_id collision: {run_dir / 'passport.json'} exists")
    run_dir.mkdir(parents=True, exist_ok=True)
    steps: dict[str, Any] = {}
    failure: dict[str, Any] | None = None
    with _ACTIVE_LOCK:
        _ACTIVE.add(run_id)
    try:
        _check_cancelled(run_id, run_dir, steps)
        try:
            ir = load_ir_file(ir_path)
        except Exception as exc:
            # No valid IR => no passport identity; write failure evidence,
            # re-raise so callers (API 400 mapping, CLI exit 2) stay fail-closed.
            steps["validate"] = {"status": "error",
                                 "error": f"{type(exc).__name__}: {exc}"}
            _write_failure(run_dir, steps, _fail("validate", exc))
            raise
        steps["validate"] = {"status": "ok", "machine": ir["machine"]["id"]}

        _check_cancelled(run_id, run_dir, steps)
        gen_dir = run_dir / "generated"
        try:
            manifest = codegen.generate(ir, gen_dir, genesis_src=str(TARGET_SRC))
        except Exception as exc:
            failure = failure or _fail("codegen", exc)
            manifest = {"status": "error", "error": failure["error"],
                        "ir_sha256": codegen.ir_sha256(ir),
                        "generator_version": codegen.GENERATOR_VERSION,
                        "template_version": codegen.TEMPLATE_VERSION,
                        "files": {}}
            steps["codegen"] = {"status": "error", "error": failure["error"]}
        else:
            steps["codegen"] = {"status": "ok", "manifest": manifest}

        _check_cancelled(run_id, run_dir, steps)
        steps["host_cc_check"] = build_adapter.check_host_cc(gen_dir, TARGET_SRC)

        _check_cancelled(run_id, run_dir, steps)
        qnx_record = build_adapter.build_qnx(gen_dir)
        steps["qnx_build"] = {k: v for k, v in qnx_record.items() if k != "environment"}
        steps["qnx_build"]["environment_sdk_present"] = bool(
            qnx_record.get("environment", {}).get("sdk_present", False))

        _check_cancelled(run_id, run_dir, steps)
        wanted = scenarios or list(ir["verification"]["scenarios"])
        try:
            results = faultlab.run_all(ir, wanted)
        except Exception as exc:
            failure = failure or _fail("verification", exc)
            results = []
            steps["verification"] = {"status": "error", "error": failure["error"],
                                     "scenarios": {}}
        else:
            failed = [r for r in results if r["status"] != "pass"]
            steps["verification"] = {
                "status": "ok" if not failed else "fail",
                "scenarios": {r["scenario"]: r["status"] for r in results},
            }

        _check_cancelled(run_id, run_dir, steps)
        qnx_target = None
        if target_record:
            try:
                parsed = json.loads(Path(target_record).read_text(encoding="utf-8"))
                if not isinstance(parsed, dict) or "status" not in parsed:
                    raise ValueError("target record must be a JSON object with a 'status' key")
                qnx_target = parsed
            except Exception as exc:
                failure = failure or _fail("qnx_target", exc)
                qnx_target = {"status": "error", "record": str(target_record),
                              "error": failure["error"]}
                steps["qnx_target"] = {"status": "error", "record": str(target_record),
                                       "error": failure["error"]}
            else:
                steps["qnx_target"] = {"status": qnx_target.get("status"),
                                       "record": str(target_record)}
        passport = evidence.build_passport(run_id, ir, manifest, results,
                                           qnx_record, qnx_target,
                                           pipeline_error=failure)
        verdict = gate.evaluate(passport, wanted)
        evidence.attach_verdict(passport, verdict)
        ppath = evidence.save_passport(passport, run_dir / "passport.json")
        steps["gate"] = verdict

        return {"run_id": run_id, "run_dir": str(run_dir),
                "passport": str(ppath), "verdict": verdict["verdict"],
                "qnx_verified": verdict["qnx_verified"],
                "level": verdict["level"],
                "release_eligible": verdict["release_eligible"], "steps": steps,
                "failure": failure, "elapsed_s": round(time.monotonic() - t0, 2)}
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.discard(run_id)
            _CANCELLED.discard(run_id)
