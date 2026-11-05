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

    class CompareRequest(BaseModel):
        run_a: str
        run_b: str

else:  # pragma: no cover - import-time fallback without the api extra
    RunRequest = None  # type: ignore[assignment, misc]
    CompareRequest = None  # type: ignore[assignment, misc]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = REPO_ROOT / "artifacts" / "runs"

MAX_IR_BYTES = 256 * 1024
MAX_SCENARIOS = 32

# Canonical run_id rule lives in orchestrator (single source of truth);
# the API re-checks early for 400 mapping, run_pipeline enforces it.
from .jobs import JobConflict, JobManager, JobNotFound
from .orchestrator import MAX_RUN_ID_LEN, valid_run_id as _valid_run_id


def _db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS runs "
                 "(run_id TEXT PRIMARY KEY, verdict TEXT, passport TEXT)")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
    if "run_dir" not in cols:  # additive migration for /compare
        conn.execute("ALTER TABLE runs ADD COLUMN run_dir TEXT")
        conn.commit()
    return conn


def _loopback_origin(origin: str) -> bool:
    """True when an Origin header points at this loopback machine."""
    from urllib.parse import urlsplit

    try:
        host = (urlsplit(origin).hostname or "").lower()
    except ValueError:
        return False
    return host in ("localhost", "127.0.0.1", "::1")


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Header, HTTPException, Request  # type: ignore[import-not-found]
        from fastapi.responses import (JSONResponse,  # type: ignore[import-not-found]
                                       StreamingResponse)
    except ImportError as exc:
        raise RuntimeError("API extra missing: pip install -e '.[api]'") from exc
    if RunRequest is None:
        raise RuntimeError("API extra missing: pip install -e '.[api]'")

    from contextlib import asynccontextmanager

    from .compare import compare_runs
    from .ir import IRValidationError, SCENARIO_IDS, validate_ir
    from .ir_v2 import validate_v2
    from .orchestrator import active_runs, request_cancel

    db_path = ARTIFACTS / "runs.db"
    mgr = JobManager(db_path, ARTIFACTS)

    @asynccontextmanager
    async def _lifespan(app: Any) -> Any:
        yield
        mgr.close()

    app = FastAPI(title="GENESIS RT orchestrator", version="0.2.0",
                  lifespan=_lifespan)
    app.state.jobs = mgr

    @app.middleware("http")
    async def _origin_guard(request: Request, call_next: Any) -> Any:
        # Loopback is the trust boundary; a foreign Origin on a
        # state-changing request is a drive-by from another site.
        if request.method in ("POST", "DELETE"):
            origin = request.headers.get("origin")
            if origin and not _loopback_origin(origin):
                return JSONResponse({"error": "cross-origin write rejected"},
                                    status_code=403)
        return await call_next(request)

    def _check_common(req: RunRequest) -> None:
        if req.run_id is not None and not _valid_run_id(req.run_id):
            raise HTTPException(400, "invalid run_id")
        if req.scenarios is not None:
            if len(req.scenarios) > MAX_SCENARIOS:
                raise HTTPException(400, "too many scenarios requested")
            unknown = [s for s in req.scenarios if s not in SCENARIO_IDS]
            if unknown:
                raise HTTPException(400, f"unknown scenarios: {sorted(unknown)}")

    def _prepare_ir(req: RunRequest) -> tuple[Path, Path | None]:
        """Validate the payload; return (ir_path, tmp_upload|None).

        Tmp uploads are deleted by the job worker when the job settles;
        callers delete them only when submit itself is refused.
        """
        try:
            if req.ir is not None:
                try:
                    version = (req.ir.get("schema_version")
                               if isinstance(req.ir, dict) else None)
                    if version == 2:
                        ir = validate_v2(req.ir)
                    elif version == 1:
                        ir = validate_ir(req.ir)
                    else:
                        raise IRValidationError(
                            f"unsupported schema_version={version!r}")
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
                return tmp_ir, tmp_ir
            if req.example:
                candidate = (REPO_ROOT / "examples" / req.example / "machine-ir.json").resolve()
                if REPO_ROOT / "examples" not in candidate.parents:
                    raise HTTPException(400, "invalid example name")
                if not candidate.exists():
                    raise HTTPException(404, "unknown example")
                return candidate, None
            raise HTTPException(400, "provide 'example' or 'ir'")
        except HTTPException:
            raise
        except (ValueError, OSError) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc

    def _drop(path: Path | None) -> None:
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs")
    def start_run(req: RunRequest) -> JSONResponse:
        """Sync facade: submit to the job pool and wait (shape unchanged)."""
        _check_common(req)
        ir_path, tmp_ir = _prepare_ir(req)
        try:
            job_id = mgr.submit(ir_path, scenarios=req.scenarios,
                                run_id=req.run_id, cleanup=tmp_ir)
        except ValueError as exc:
            _drop(tmp_ir)
            raise HTTPException(400, f"bad request: {exc}") from exc
        except JobConflict as exc:
            _drop(tmp_ir)
            return JSONResponse({"error": f"run conflict: {exc}"}, status_code=409)
        try:
            rec = mgr.wait(job_id, timeout=900)
        except TimeoutError:
            return JSONResponse({"job_id": job_id, "status": "active"},
                                status_code=503)
        if rec["state"] == "cancelled":
            return JSONResponse({"run_id": job_id, "status": "cancelled",
                                 "run_dir": rec["run_dir"]}, status_code=409)
        if rec["state"] == "failed":
            err = rec["error"] or "pipeline failed"
            head = err.split(":", 1)[0]
            if head == "PipelineError":
                return JSONResponse({"error": f"run conflict: {err}"},
                                    status_code=409)
            if head in ("ValueError", "IRValidationError"):
                raise HTTPException(400, f"bad request: {err}")
            return JSONResponse({"error": err}, status_code=500)
        if rec["state"] != "succeeded" or not rec["summary"]:
            return JSONResponse({"error": f"run {rec['state']}: {rec['error']}"},
                                status_code=500)
        return JSONResponse(json.loads(rec["summary"]))

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
            if run_id in active_runs():
                return JSONResponse({"run_id": run_id, "status": "active"},
                                    status_code=202)
            raise HTTPException(404, "unknown run")
        return JSONResponse(json.loads(row[0]))

    @app.get("/runs")
    def list_runs(limit: int = 50) -> JSONResponse:
        if not 1 <= limit <= 200:
            raise HTTPException(400, "limit must be 1..200")
        conn = _db(db_path)
        try:
            rows = conn.execute(
                "SELECT run_id, verdict FROM runs ORDER BY rowid DESC"
                " LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
        return JSONResponse({"runs": [{"run_id": r[0], "verdict": r[1]}
                                      for r in rows]})

    @app.get("/runs/{run_id}/export")
    def export_run(run_id: str) -> JSONResponse:
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
        return JSONResponse(
            json.loads(row[0]),
            headers={"Content-Disposition":
                     f"attachment; filename={run_id}.passport.json"})

    @app.post("/compare")
    def compare_stored(req: CompareRequest) -> JSONResponse:
        for rid in (req.run_a, req.run_b):
            if not _valid_run_id(rid):
                raise HTTPException(400, f"invalid run id: {rid!r}")
        conn = _db(db_path)
        try:
            rows = {r[0]: r[1] for r in conn.execute(
                "SELECT run_id, run_dir FROM runs WHERE run_id IN (?,?)",
                (req.run_a, req.run_b)).fetchall()}
        finally:
            conn.close()
        missing = [r for r in (req.run_a, req.run_b) if r not in rows]
        if missing:
            raise HTTPException(404, f"unknown runs: {missing}")
        dirs = []
        base = ARTIFACTS.resolve()
        for rid in (req.run_a, req.run_b):
            stored = rows[rid]
            if not stored:
                raise HTTPException(
                    409, f"run {rid} predates run_dir tracking")
            candidate = Path(stored).resolve()
            if base not in candidate.parents and candidate != base:
                raise HTTPException(409, f"run {rid} dir escapes artifacts")
            if not (candidate / "passport.json").is_file():
                raise HTTPException(
                    409, f"run {rid} artifacts no longer on disk")
            dirs.append(candidate)
        try:
            comp = compare_runs(dirs[0], dirs[1])
        except ValueError as exc:
            raise HTTPException(409, f"cannot compare: {exc}") from exc
        return JSONResponse(comp)

    @app.post("/jobs", status_code=202)
    def create_job(req: RunRequest) -> JSONResponse:
        """Async submit: 202 immediately, poll /jobs/{id} or stream events."""
        _check_common(req)
        ir_path, tmp_ir = _prepare_ir(req)
        try:
            job_id = mgr.submit(ir_path, scenarios=req.scenarios,
                                run_id=req.run_id, cleanup=tmp_ir)
        except ValueError as exc:
            _drop(tmp_ir)
            raise HTTPException(400, f"bad request: {exc}") from exc
        except JobConflict as exc:
            _drop(tmp_ir)
            return JSONResponse({"error": f"run conflict: {exc}"}, status_code=409)
        return JSONResponse({"job_id": job_id, "state": "queued"},
                            status_code=202)

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> JSONResponse:
        if not _valid_run_id(job_id):
            raise HTTPException(400, "invalid job id")
        rec = mgr.get(job_id)
        if rec is None:
            raise HTTPException(404, "unknown job")
        return JSONResponse({k: rec[k] for k in
                             ("job_id", "state", "verdict", "run_dir", "error",
                              "created", "updated")})

    @app.get("/jobs")
    def list_jobs(limit: int = 50) -> JSONResponse:
        return JSONResponse({"jobs": mgr.list_jobs(limit)})

    @app.delete("/jobs/{job_id}")
    def cancel_job(job_id: str) -> JSONResponse:
        if not _valid_run_id(job_id):
            raise HTTPException(400, "invalid job id")
        try:
            rec = mgr.cancel(job_id)
        except JobNotFound:
            raise HTTPException(404, "unknown job") from None
        code = 200 if rec["state"] in ("succeeded", "failed", "cancelled",
                                       "interrupted") else 202
        return JSONResponse({"job_id": job_id, "state": rec["state"]},
                            status_code=code)

    @app.get("/jobs/{job_id}/events")
    async def job_events(job_id: str, after: int = -1,
                         last_event_id: str | None = Header(default=None)
                         ) -> StreamingResponse:
        """SSE: every event carries job_id + ordered seq; reconnect-safe.

        NOTE: the resume header is a Header() param, not `request: Request`:
        with `from __future__ import annotations` a locally-imported Request
        is unresolvable in module globals and FastAPI 422s (same trap as the
        RunRequest NOTE above).
        """
        import asyncio

        if not _valid_run_id(job_id):
            raise HTTPException(400, "invalid job id")
        if mgr.get(job_id) is None:
            raise HTTPException(404, "unknown job")
        if last_event_id and last_event_id.strip().isdigit():
            after = max(after, int(last_event_id.strip()))

        async def _stream() -> Any:
            last = max(-1, after)
            idle_slices = 0
            try:
                while True:
                    rows = mgr.events(job_id, after=last)
                    for row in rows:
                        last = row["seq"]
                        yield (f"id: {row['seq']}\nevent: {row['kind']}\n"
                               f"data: {json.dumps(row)}\n\n")
                        if row["kind"] in ("done", "failed", "cancelled",
                                           "interrupted"):
                            return
                    rec = mgr.get(job_id)
                    if rec is None:  # job row vanished mid-stream
                        return
                    if not rows and rec["state"] in ("succeeded", "failed",
                                                     "cancelled", "interrupted"):
                        return  # caught up on a terminal job: resume got all
                    await asyncio.sleep(0.05)
                    idle_slices += 1
                    if idle_slices >= 300:  # ~15 s heartbeat
                        idle_slices = 0
                        yield ": ping\n\n"
            except (GeneratorExit, asyncio.CancelledError):
                return

        return StreamingResponse(_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    return app
