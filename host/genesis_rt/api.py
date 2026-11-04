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
import threading
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = REPO_ROOT / "artifacts" / "runs"

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
        from pydantic import BaseModel  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("API extra missing: pip install -e '.[api]'") from exc

    from .ir import IRValidationError, validate_ir
    from .orchestrator import run_pipeline

    app = FastAPI(title="GENESIS RT orchestrator", version="0.1.0")
    db_path = ARTIFACTS / "runs.db"

    class RunRequest(BaseModel):
        example: str | None = None  # e.g. "amr-demo"
        ir: dict[str, Any] | None = None
        scenarios: list[str] | None = None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    def start_run(req: RunRequest) -> JSONResponse:
        tmp_ir = ARTIFACTS / "_upload.ir.json"
        try:
            if req.ir is not None:
                ir = validate_ir(req.ir)
                tmp_ir.write_text(json.dumps(ir), encoding="utf-8")
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
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        with _lock:  # bounded: one pipeline at a time on local hardware
            summary = run_pipeline(ir_path, ARTIFACTS, scenarios=req.scenarios)
        passport_text = Path(summary["passport"]).read_text(encoding="utf-8")
        conn = _db(db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?)",
                         (summary["run_id"], summary["verdict"], passport_text))
            conn.commit()
        finally:
            conn.close()
        return JSONResponse(summary)

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        if not run_id.replace("-", "").replace("_", "").isalnum():
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
