# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Optional local web API (FastAPI). Requires the `api` extra.

Local-first for the hackathon: runs the same orchestrator pipeline and
serves passports from a SQLite WAL store. No arbitrary code execution:
only committed example IR files or validated uploads are accepted.
"""

from __future__ import annotations

import json
import re
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

    class ValidateRequest(BaseModel):
        ir: dict[str, Any]

    class ProjectCreate(BaseModel):
        name: str | None = None
        from_example: str | None = None
        from_file: str | None = None
        ir: dict[str, Any] | None = None

    class ProjectUpdate(BaseModel):
        ir: dict[str, Any]

    class ProjectDuplicate(BaseModel):
        name: str

    class GraphRequest(BaseModel):
        # dict, or the raw passport JSON text. Browsers MUST send text:
        # a JS parse/reserialize turns 1.0 into 1, which breaks the
        # hash chain; server-side parsing of the raw text is exact.
        passport: dict[str, Any] | str
        ir: dict[str, Any] | None = None

    class GraphCompareRequest(BaseModel):
        passport_a: dict[str, Any] | str
        passport_b: dict[str, Any] | str
        ir: dict[str, Any] | None = None

    class ImpactRequest(BaseModel):
        ir_before: dict[str, Any]
        ir_after: dict[str, Any]

    class ImpactReleaseRequest(BaseModel):
        ir_before: dict[str, Any]
        ir_after: dict[str, Any]
        passport: dict[str, Any] | str
        passport_before: dict[str, Any] | str | None = None

    class ExploreRequest(BaseModel):
        ir: dict[str, Any]
        invariant: str = "no_over_limit_allow"
        params: dict[str, Any] | None = None
        strategies: list[str] | None = None
        budgets: dict[str, Any] | None = None
        seed: int = 0

    class ExploreReplayRequest(BaseModel):
        record: dict[str, Any]
        ir: dict[str, Any]

    class TwinRequest(BaseModel):
        passport: dict[str, Any] | str
        scenario: str

else:  # pragma: no cover - import-time fallback without the api extra
    RunRequest = None  # type: ignore[assignment, misc]
    CompareRequest = None  # type: ignore[assignment, misc]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = REPO_ROOT / "artifacts" / "runs"

MAX_IR_BYTES = 256 * 1024
MAX_SCENARIOS = 32
MAX_PASSPORT_TEXT = 3 * 1024 * 1024

# Canonical run_id rule lives in orchestrator (single source of truth);
# the API re-checks early for 400 mapping, run_pipeline enforces it.
from .evidence_graph import (GraphTooLarge, InvalidPassport, build_graph,
                                 compare_graphs)
from .explorer import (ExplorerInputError, ExplorerUnsupported, explore,
                       replay)
from .impact import analyze_impact, release_status
from .jobs import JobConflict, JobManager, JobNotFound, JobOverloaded
from .target import TargetBusy, TargetOpError, TargetRunner, valid_op_id
from .orchestrator import MAX_RUN_ID_LEN, valid_run_id as _valid_run_id
from .twin import TwinChainError, TwinInputError, TwinTooLarge, track_from_passport

# Studio Live: committed example files openable as projects (allowlist;
# the intentionally-broken cell fixture is excluded from listings).
EXAMPLE_FILES: dict[str, tuple[str, ...]] = {
    "amr-demo": ("machine-ir.json", "machine-ir-v2.json"),
    "conveyor-demo": ("machine-ir.json", "machine-ir-v2.json"),
    "cell-demo": ("cell-ir.json",),
}


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


if BaseModel is not None:

    class TargetOpRequest(BaseModel):
        workflow: str = "full"
        params: dict[str, Any] = {}


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Header, HTTPException, Request  # type: ignore[import-not-found]
        from fastapi.responses import (FileResponse,  # type: ignore[import-not-found]
                                       JSONResponse,
                                       StreamingResponse)
    except ImportError as exc:
        raise RuntimeError("API extra missing: pip install -e '.[api]'") from exc
    if RunRequest is None:
        raise RuntimeError("API extra missing: pip install -e '.[api]'")

    from contextlib import asynccontextmanager

    from .build_adapter import probe as probe_env
    from .compare import compare_runs
    from .ir import IRValidationError, SCENARIO_IDS, validate_ir
    from .ir_v2 import validate_v2
    from .orchestrator import active_runs, request_cancel
    from .projects import (ProjectFull, ProjectNotFound, ProjectStore,
                           summarize, validate_any, valid_project_id)

    db_path = ARTIFACTS / "runs.db"
    mgr = JobManager(db_path, ARTIFACTS)
    store = ProjectStore(ARTIFACTS.parent / "studio" / "projects")
    # Same lock file as the qnx_target.py CLI default (artifacts/.target.lock):
    # API ops and CLI campaigns coordinate instead of interfering.
    trunner = TargetRunner(ARTIFACTS / "target-ops",
                           ARTIFACTS.parent / ".target.lock")

    @asynccontextmanager
    async def _lifespan(app: Any) -> Any:
        yield
        mgr.close()
        trunner.close()

    app = FastAPI(title="GENESIS RT orchestrator", version="0.2.0",
                  lifespan=_lifespan)
    app.state.jobs = mgr
    app.state.target = trunner

    @app.middleware("http")
    async def _origin_guard(request: Request, call_next: Any) -> Any:
        # Loopback is the trust boundary; a foreign Origin on a
        # state-changing request is a drive-by from another site.
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
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
        except JobOverloaded as exc:
            _drop(tmp_ir)
            return JSONResponse({"error": f"server busy: {exc}"},
                                status_code=429, headers={"Retry-After": "5"})
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

    @app.get("/runs/{run_id}/passport/raw")
    def raw_passport(run_id: str) -> Any:
        from fastapi.responses import Response  # type: ignore[import-not-found]

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
        # Exact stored bytes (not re-serialized): browser chain
        # re-verification is literal-sensitive by design.
        return Response(content=row[0], media_type="application/json")

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
        except JobOverloaded as exc:
            _drop(tmp_ir)
            return JSONResponse({"error": f"server busy: {exc}"},
                                status_code=429, headers={"Retry-After": "5"})
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

    _GEN_SUFFIXES = (".h", ".c", ".mk")
    _GEN_NAME = re.compile(r"genesis_[A-Za-z0-9_.\-]+")
    _GEN_MAX_BYTES = 512 * 1024

    def _job_gen_dir(job_id: str) -> Path:
        if not _valid_run_id(job_id):
            raise HTTPException(400, "invalid job id")
        rec = mgr.get(job_id)
        if rec is None:
            raise HTTPException(404, "unknown job")
        if not rec["run_dir"]:
            raise HTTPException(409, "job has no artifacts yet")
        candidate = (Path(rec["run_dir"]) / "generated").resolve()
        base = ARTIFACTS.resolve()
        if base not in candidate.parents and candidate != base:
            raise HTTPException(409, "job dir escapes artifacts")
        if not candidate.is_dir():
            raise HTTPException(409, "generated sources not on disk")
        return candidate

    @app.get("/jobs/{job_id}/files")
    def list_job_files(job_id: str) -> JSONResponse:
        gen_dir = _job_gen_dir(job_id)
        files = []
        for child in sorted(gen_dir.iterdir(), key=lambda p: p.name):
            if (child.is_file() and _GEN_NAME.fullmatch(child.name)
                    and child.suffix in _GEN_SUFFIXES):
                files.append({"name": child.name,
                              "bytes": child.stat().st_size})
        return JSONResponse({"job_id": job_id, "files": files})

    @app.get("/jobs/{job_id}/files/{name}")
    def read_job_file(job_id: str, name: str) -> JSONResponse:
        gen_dir = _job_gen_dir(job_id)
        if not _GEN_NAME.fullmatch(name) or Path(name).suffix not in _GEN_SUFFIXES:
            raise HTTPException(400, "invalid file name")
        target = (gen_dir / name).resolve()
        if gen_dir != target.parent:
            raise HTTPException(400, "invalid file name")
        if not target.is_file():
            raise HTTPException(404, "unknown file")
        size = target.stat().st_size
        if size > _GEN_MAX_BYTES:
            raise HTTPException(409, f"file too large to preview ({size} bytes)")
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            raise HTTPException(409, f"file unreadable: {exc}") from exc
        return JSONResponse({"job_id": job_id, "name": name, "text": text})

    # -- Wave 8 §5: native QNX target ops --
    @app.post("/target/ops", status_code=202)
    def create_target_op(req: TargetOpRequest) -> JSONResponse:
        """Start a target op: 202 immediately, poll /target/ops/{id}."""
        try:
            rec = trunner.start(req.workflow, params=req.params)
        except TargetBusy as exc:
            raise HTTPException(409, f"target busy: {exc}") from exc
        except TargetOpError as exc:
            raise HTTPException(400, f"bad target op: {exc}") from exc
        return JSONResponse({"op_id": rec["op_id"], "state": rec["state"]},
                            status_code=202)

    @app.get("/target/ops")
    def list_target_ops(limit: int = 20) -> JSONResponse:
        return JSONResponse({"ops": trunner.list_ops(limit)})

    @app.get("/target/ops/{op_id}")
    def get_target_op(op_id: str) -> JSONResponse:
        if not valid_op_id(op_id):
            raise HTTPException(400, "invalid op id")
        rec = trunner.get(op_id)
        if rec is None:
            raise HTTPException(404, "unknown op")
        return JSONResponse(rec)

    @app.get("/target/ops/{op_id}/dossier")
    def get_target_dossier(op_id: str) -> Any:
        from fastapi.responses import Response  # type: ignore[import-not-found]

        from .dossier import DossierError, build_dossier_zip
        if not valid_op_id(op_id):
            raise HTTPException(400, "invalid op id")
        try:
            blob = build_dossier_zip(trunner.ops_dir, op_id, ARTIFACTS)
        except DossierError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        return Response(
            content=blob, media_type="application/zip",
            headers={"Content-Disposition":
                     f"attachment; filename=dossier-{op_id}.zip"})

    @app.get("/target/ops/{op_id}/decision")
    def get_target_decision(op_id: str) -> JSONResponse:
        from .dossier import DossierError, assess_op, collect_op_files
        if not valid_op_id(op_id):
            raise HTTPException(400, "invalid op id")
        try:
            files, rec, _red = collect_op_files(trunner.ops_dir, op_id,
                                                ARTIFACTS)
        except DossierError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        return JSONResponse(assess_op(op_id, rec, files))

    @app.delete("/target/ops/{op_id}")
    def cancel_target_op(op_id: str) -> JSONResponse:
        if not valid_op_id(op_id):
            raise HTTPException(400, "invalid op id")
        try:
            rec = trunner.cancel(op_id)
        except TargetOpError:
            raise HTTPException(404, "unknown op") from None
        return JSONResponse({"op_id": op_id, "state": rec["state"]})

    @app.get("/target/ops/{op_id}/events")
    async def target_op_events(op_id: str, after: int = -1,
                               ) -> StreamingResponse:
        import asyncio

        if not valid_op_id(op_id):
            raise HTTPException(400, "invalid op id")
        if trunner.get(op_id) is None:
            raise HTTPException(404, "unknown op")

        async def _stream() -> Any:
            last = max(-1, after)
            idle_slices = 0
            try:
                while True:
                    rows = trunner.events(op_id, after=last)
                    for row in rows:
                        last = row["seq"]
                        yield (f"id: {row['seq']}\nevent: {row['kind']}\n"
                               f"data: {json.dumps(row)}\n\n")
                    rec = trunner.get(op_id)
                    if rec is None:
                        return
                    if not rows and rec["state"] in ("COMPLETED", "FAILED",
                                                     "CANCELLED", "BLOCKED",
                                                     "INTERRUPTED"):
                        return
                    await asyncio.sleep(0.05)
                    idle_slices += 1
                    if idle_slices >= 300:  # ~15 s heartbeat
                        idle_slices = 0
                        yield ": ping\n\n"
            except (GeneratorExit, asyncio.CancelledError):
                return

        return StreamingResponse(_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    # -- Studio Live: examples, validation, projects, env, static --
    def _example_doc(example: str, file: str) -> dict[str, Any]:
        if example not in EXAMPLE_FILES or file not in EXAMPLE_FILES[example]:
            raise HTTPException(400, "unknown example file")
        candidate = (REPO_ROOT / "examples" / example / file).resolve()
        if REPO_ROOT / "examples" not in candidate.parents:
            raise HTTPException(400, "invalid example name")
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise HTTPException(409, f"example unreadable: {exc}") from exc

    @app.get("/examples")
    def list_examples() -> JSONResponse:
        out = []
        for example, files in EXAMPLE_FILES.items():
            entries = []
            for file in files:
                try:
                    doc = _example_doc(example, file)
                    version, valid = validate_any(doc)
                    entries.append({"file": file, "ok": True,
                                    "summary": summarize(version, valid)})
                except (HTTPException, IRValidationError) as exc:
                    entries.append({"file": file, "ok": False,
                                    "error": str(exc)})
            out.append({"example": example, "files": entries})
        return JSONResponse({"examples": out})

    @app.get("/examples/{example}/{file}")
    def read_example(example: str, file: str) -> JSONResponse:
        return JSONResponse({"example": example, "file": file,
                             "ir": _example_doc(example, file)})

    @app.post("/validate")
    def validate_payload(req: ValidateRequest) -> JSONResponse:
        raw = json.dumps(req.ir).encode("utf-8")
        if len(raw) > MAX_IR_BYTES:
            raise HTTPException(400, "IR payload too large")
        try:
            version, valid = validate_any(req.ir)
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        return JSONResponse({"ok": True, "summary": summarize(version, valid)})

    def _project_or_404(pid: str) -> str:
        if not valid_project_id(pid):
            raise HTTPException(400, "invalid project id")
        return pid

    @app.post("/projects", status_code=201)
    def create_project(req: ProjectCreate) -> JSONResponse:
        sources = [req.ir is not None, req.from_example is not None]
        if sum(sources) != 1:
            raise HTTPException(400, "provide exactly one of 'ir', 'from_example'")
        if req.from_file is not None and req.from_example is None:
            raise HTTPException(400, "'from_file' needs 'from_example'")
        try:
            if req.ir is not None:
                doc = req.ir
            else:
                assert req.from_example is not None
                if req.from_example not in EXAMPLE_FILES:
                    raise HTTPException(404, "unknown example")
                fname = req.from_file or EXAMPLE_FILES[req.from_example][0]
                doc = _example_doc(req.from_example, fname)
            name = req.name
            if name is None:
                try:
                    _, valid = validate_any(doc)
                    name = valid.get("machine", {}).get("id") or req.from_example or "untitled"
                except IRValidationError:
                    name = req.from_example or "untitled"
            created = store.create(name, doc)
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(created, status_code=201)

    @app.get("/projects")
    def list_projects() -> JSONResponse:
        return JSONResponse({"projects": store.list()})

    @app.get("/projects/{pid}")
    def get_project(pid: str) -> JSONResponse:
        try:
            return JSONResponse(store.get(_project_or_404(pid)))
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.put("/projects/{pid}")
    def save_project(pid: str, req: ProjectUpdate) -> JSONResponse:
        try:
            return JSONResponse(store.save_revision(_project_or_404(pid), req.ir))
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        except ProjectFull as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc

    @app.post("/projects/{pid}/duplicate", status_code=201)
    def duplicate_project(pid: str, req: ProjectDuplicate) -> JSONResponse:
        try:
            created = store.duplicate(_project_or_404(pid), req.name)
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except (ValueError, IRValidationError) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(created, status_code=201)

    @app.get("/projects/{pid}/history")
    def project_history(pid: str) -> JSONResponse:
        try:
            return JSONResponse({"revisions": store.history(_project_or_404(pid))})
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/projects/{pid}/revisions/{rev}")
    def project_revision(pid: str, rev: int) -> JSONResponse:
        try:
            return JSONResponse(store.revision(_project_or_404(pid), rev))
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/projects/{pid}/diff")
    def project_diff(pid: str, rev_from: int = 1, rev_to: int = 0) -> JSONResponse:
        try:
            head = store.get(_project_or_404(pid))["head"]
            diff = store.diff(pid, rev_from, rev_to or head)
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        return JSONResponse(diff)

    @app.get("/projects/{pid}/export")
    def export_project(pid: str) -> JSONResponse:
        try:
            bundle = store.export(_project_or_404(pid))
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        return JSONResponse(
            bundle, headers={"Content-Disposition":
                             f"attachment; filename={pid}.genesis-project.json"})

    @app.get("/env")
    def read_env() -> JSONResponse:
        return JSONResponse({"api": "0.2.0", "environment": probe_env()})

    def _posted_passport(value: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if len(value) > MAX_PASSPORT_TEXT:
            raise GraphTooLarge("passport text exceeds 3 MiB")
        try:
            doc = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"passport text is not valid JSON: {exc}") from exc
        if not isinstance(doc, dict):
            raise ValueError("passport text must decode to an object")
        return doc

    @app.post("/graphs")
    def post_graph(req: GraphRequest) -> JSONResponse:
        try:
            doc = _posted_passport(req.passport)
            return JSONResponse(build_graph(doc, req.ir))
        except InvalidPassport as exc:
            raise HTTPException(409, f"passport unusable: {exc}") from exc
        except GraphTooLarge as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc

    @app.post("/graphs/compare")
    def post_graph_compare(req: GraphCompareRequest) -> JSONResponse:
        try:
            older = build_graph(_posted_passport(req.passport_a), req.ir)
            newer = build_graph(_posted_passport(req.passport_b), req.ir)
        except InvalidPassport as exc:
            raise HTTPException(409, f"passport unusable: {exc}") from exc
        except GraphTooLarge as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(compare_graphs(older, newer))

    def _capped_ir(doc: Any) -> dict[str, Any]:
        raw = json.dumps(doc).encode("utf-8")
        if len(raw) > MAX_IR_BYTES:
            raise HTTPException(400, "IR payload too large")
        if not isinstance(doc, dict):
            raise HTTPException(400, "IR must be an object")
        return doc

    @app.post("/impact")
    def post_impact(req: ImpactRequest) -> JSONResponse:
        try:
            report = analyze_impact(_capped_ir(req.ir_before),
                                    _capped_ir(req.ir_after))
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        return JSONResponse(report)

    @app.post("/impact/release")
    def post_impact_release(req: ImpactReleaseRequest) -> JSONResponse:
        try:
            doc = _posted_passport(req.passport)
            base = _posted_passport(req.passport_before) \
                if req.passport_before is not None else None
            status = release_status(_capped_ir(req.ir_before),
                                    _capped_ir(req.ir_after), doc, base)
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        except GraphTooLarge as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(status)

    @app.post("/explore")
    def post_explore(req: ExploreRequest) -> JSONResponse:
        try:
            report = explore(_capped_ir(req.ir),
                             invariant=req.invariant,
                             params=req.params,
                             strategies=req.strategies,
                             budgets=req.budgets, seed=req.seed)
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        except (ExplorerInputError, ExplorerUnsupported) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(report)

    @app.post("/explore/replay")
    def post_explore_replay(req: ExploreReplayRequest) -> JSONResponse:
        try:
            raw = json.dumps(req.record).encode("utf-8")
            if len(raw) > MAX_PASSPORT_TEXT:
                raise HTTPException(400, "record payload too large")
            result = replay(req.record, _capped_ir(req.ir))
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        except (ExplorerInputError, ExplorerUnsupported) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(result)

    @app.post("/twin/frames")
    def post_twin_frames(req: TwinRequest) -> JSONResponse:
        try:
            track = track_from_passport(_posted_passport(req.passport),
                                        req.scenario)
        except TwinChainError as exc:
            raise HTTPException(409, f"passport unusable: {exc}") from exc
        except TwinTooLarge as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        except (TwinInputError, ValueError) as exc:
            raise HTTPException(400, f"bad request: {exc}") from exc
        return JSONResponse(track)

    @app.get("/projects/{pid}/impact")
    def project_impact(pid: str, rev_from: int = 1,
                       rev_to: int = 0) -> JSONResponse:
        try:
            head = store.get(_project_or_404(pid))["head"]
            ra = store.revision(pid, rev_from)
            rb = store.revision(pid, rev_to or head)
            report = analyze_impact(ra["ir"], rb["ir"])
        except ProjectNotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except IRValidationError as exc:
            raise HTTPException(400, f"invalid IR: {exc}") from exc
        report["from"] = rev_from
        report["to"] = rev_to or head
        return JSONResponse(report)

    _UI_FILES = {"studio.html": "text/html",
                 "dashboard.html": "text/html",
                 "genesis_verify.js": "text/javascript"}

    def _ui_file(name: str) -> FileResponse:
        return FileResponse(REPO_ROOT / "ui" / name,
                            media_type=_UI_FILES[name],
                            headers={"Cache-Control": "no-cache"})

    @app.get("/")
    def _index() -> FileResponse:
        return _ui_file("studio.html")

    @app.get("/studio.html")
    def _studio() -> FileResponse:
        return _ui_file("studio.html")

    @app.get("/dashboard.html")
    def _dashboard() -> FileResponse:
        return _ui_file("dashboard.html")

    @app.get("/genesis_verify.js")
    def _verify_js() -> FileResponse:
        return _ui_file("genesis_verify.js")

    return app
