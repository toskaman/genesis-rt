# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Optional local web API (FastAPI). Requires the `api` extra.

Local-first for the hackathon: runs the same orchestrator pipeline and
serves passports from a SQLite WAL store. No arbitrary code execution:
only committed example IR files or validated uploads are accepted.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel
except ImportError:  # api extra not installed; create_app() reports this
    BaseModel = None  # type: ignore[assignment, misc]

# NOTE: the request model MUST live at module level. It was previously
# defined inside create_app(), and with `from __future__ import
# annotations` FastAPI could not resolve the "RunRequest" string
# annotation from that local scope, so POST /runs treated `req` as a
# required query parameter and returned 422 for every call.
if BaseModel is not None:

    class RunRequest(BaseModel):
        example: str | None = None  # e.g. "amr-demo"
        ir: dict[str, Any] | None = None
        scenarios: list[str] | None = None
        run_id: str | None = None  # client-chosen id (cancellable runs)

else:  # pragma: no cover - import-time fallback without the api extra
    RunRequest = None  # type: ignore[assignment, misc]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = REPO_ROOT / "artifacts" / "runs"

MAX_IR_BYTES = 256 * 1024
MAX_SCENARIOS = 32

# Canonical run_id rule lives in orchestrator (single source of truth);
# the API re-checks early for 400 mapping, run_pipeline enforces it.
from .orchestrator import MAX_RUN_ID_LEN, valid_run_id as _valid_run_id

_lock = threading.Lock()


def _db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS runs "
                 "(run_id TEXT PRIMARY KEY, verdict TEXT, passport TEXT)")
    return conn


def create_app() -> Any:
    try:
        from fastapi import FastAPI, HTTPException  # type: ignore[import-not-found]
        from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("API extra missing: pip install -e '.[api]'") from exc
    if RunRequest is None:
        raise RuntimeError("API extra missing: pip install -e '.[api]'")

    from .ir import IRValidationError, SCENARIO_IDS, validate_ir
    from .orchestrator import CancelledRun, PipelineError, request_cancel, run_pipeline

    app = FastAPI(title="GENESIS RT orchestrator", version="0.1.0")
    db_path = ARTIFACTS / "runs.db"

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    def start_run(req: RunRequest) -> JSONResponse:
        if req.run_id is not None and not _valid_run_id(req.run_id):
            raise HTTPException(400, "invalid run_id")
        if req.scenarios is not None:
            if len(req.scenarios) > MAX_SCENARIOS:
                raise HTTPException(400, "too many scenarios requested")
            unknown = [s for s in req.scenarios if s not in SCENARIO_IDS]
            if unknown:
                raise HTTPException(400, f"unknown scenarios: {sorted(unknown)}")
        tmp_ir: Path | None = None
        try:
            if req.ir is not None:
                try:
                    ir = validate_ir(req.ir)
                except IRValidationError as exc:
                    raise HTTPException(400, f"invalid IR: {exc}") from exc
                raw = json.dumps(ir).encode("utf-8")
                if len(raw) > MAX_IR_BYTES:
                    raise HTTPException(400, "IR payload too large")
                ARTIFACTS.mkdir(parents=True, exist_ok=True)
                # Per-request temp file: concurrent uploads never share a path.
                with tempfile.NamedTemporaryFile(
                        mode="wb", suffix=".ir.json", prefix="upload-",
                        dir=ARTIFACTS, delete=False) as fh:
                    fh.write(raw)
                    tmp_ir = Path(fh.name)
                ir_path = tmp_ir
            elif req.example:
                candidate = (REPO_ROOT / "examples" / req.example / "machine-ir.json").resolve()
                if REPO_ROOT / "examples" not in candidate.parents:
                    raise HTTPException(400, "invalid example name")
                if not candidate.exists():
                    raise HTTPException(404, "unknown example")
                ir_path = candidate
            else:
                raise HTTPException(400, "provide 'example' or 'ir'")
        except HTTPException:
            raise
        except (ValueError, OSError) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        try:
            with _lock:  # bounded: one pipeline at a time on local hardware
                summary = run_pipeline(ir_path, ARTIFACTS, run_id=req.run_id,
                                       scenarios=req.scenarios)
        except CancelledRun as exc:
            return JSONResponse({"run_id": exc.run_id, "status": "cancelled",
                                 "run_dir": exc.run_dir}, status_code=409)
        except PipelineError as exc:
            return JSONResponse({"error": f"run conflict: {exc}"}, status_code=409)
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        finally:
            if tmp_ir is not None:
                tmp_ir.unlink(missing_ok=True)
        passport_text = Path(summary["passport"]).read_text(encoding="utf-8")
        conn = _db(db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?)",
                         (summary["run_id"], summary["verdict"], passport_text))
            conn.commit()
        finally:
            conn.close()
        return JSONResponse(summary)

    @app.delete("/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> JSONResponse:
        if not _valid_run_id(run_id):
            raise HTTPException(400, "invalid run id")
        if not request_cancel(run_id):
            raise HTTPException(404, "no active run with that id")
        return JSONResponse({"run_id": run_id, "status": "cancelling"},
                            status_code=202)

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        if not _valid_run_id(run_id):
            raise HTTPException(400, "invalid run id")
        conn = _db(db_path)
        try:
            row = conn.execute("SELECT passport FROM runs WHERE run_id=?",
                               (run_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "unknown run")
        return JSONResponse(json.loads(row[0]))

    return app
