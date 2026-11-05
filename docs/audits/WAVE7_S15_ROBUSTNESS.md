# Wave 7 M4 §15 — Long-Session Robustness Audit

Date: 2026-11-05. Scope: `host/genesis_rt/jobs.py`, SSE endpoint
(`/jobs/{id}/events` in `host/genesis_rt/api.py`), worker/subprocess,
SQLite, logging. Method: read the code paths, fix confirmed gaps only.

## Findings (already sound — no change)

- Workers: `ThreadPoolExecutor(max_workers=2)`, named threads,
  `close()` shuts down with `wait=True, cancel_futures=True`;
  API lifespan calls `mgr.close()`. No orphan threads.
- Subprocesses: pipeline runs in-process; target SSH/QEMU paths carry
  their own timeouts/penalty-box (see §14). No unbounded child trees.
- SQLite: WAL, 30 s busy timeout, one short-lived connection per
  operation, always closed in `finally`. Additive `summary` migration
  is idempotent. Concurrent readers/writer safe.
- Events: per-job cap 1000 rows (`MAX_EVENTS_PER_JOB`), per-message
  2000 chars, SSE read limit 500, heartbeat ~15 s, terminal close,
  `GeneratorExit`/`CancelledError` handled, `Last-Event-ID` resume.
  No unbounded in-memory buffer (DB-backed).
- Cancellation: queued→cancelled synchronously; running→`request_cancel`
  with 5 s bounded poll; idempotent; terminal states never success.
- Recovery: `queued`/`running` rows from a dead process become
  `interrupted` on init with an event row. Fail-closed.
- Timing: `time.monotonic()` for durations/polls; wall clock only for
  stored timestamps.

## Gaps fixed

1. **Unbounded `_done` dict** (`jobs.py`): every submitted job kept a
   `threading.Event` forever. Added `MAX_TRACKED_JOBS = 200` with
   oldest-terminal-first eviction on submit; `wait()` already falls
   back to a DB read for evicted/unknown jobs, so eviction is safe.
2. **No structured logging**: added `genesis.jobs` logger with
   `job=<id>` correlation on submit / running / terminal
   (succeeded+verdict, failed+error, cancelled) / recovery.

## Tests

`tests/unit/test_jobs_lifecycle.py` (6): track-cap eviction + DB
fallback, submit-after-close, event-cap ceiling, recovery→interrupted
with log line, `job=` log correlation, idempotent close.
Full suite: 758 passed with SDK (SDK-free 755 + 3 honest QNX-build
skips); `tests/integration/test_jobs.py` (16) still green.

## Residual risks (accepted, documented)

- `jobs`/`events` DB rows grow without retention; evidence store is
  deliberately append-only for audit. Operators prune `runs.db`
  offline if disk pressure arises.
- SSE clients that never disconnect hold one coroutine each; FastAPI
  default limits apply. No per-IP cap (loopback-only API).
- Frontend memory: Studio closes SSE on tab switch (M2 verified);
  no new long-lived subscriptions added here.
