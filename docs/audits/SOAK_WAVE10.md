# Soak campaign — Wave 10 Sprint E3 (§19)

Date: 2026-11-05. Host: Windows 11, Python 3.14, no QNX SDK needed.
Test: `tests/unit/test_soak.py` (2 tests, committed, CI-safe, ~14 s).

## Workload

`test_soak_mixed_load_leaves_no_residue`: 1 warmup + 24 sequential jobs
through the real `JobManager` + `run_pipeline` — 8 success (AMR IR),
8 fail-fast (missing IR file), 8 malformed (garbage JSON).
Every job reached a terminal state; no timeouts, no hangs.

`test_soak_cancel_storm_settles_cleanly`: 4 gated jobs, all cancelled
while queued/running, then settled — every job `cancelled`, none lost,
manager closes cleanly.

## Observed residue (the numbers that matter)

| Signal | Before load | After 25 jobs | Tripwire |
|---|---|---|---|
| Live threads | 2 | 2 | must be equal |
| Python heap growth (tracemalloc) | — | +18 KiB | < 2 MiB |
| SQLite store (db + WAL) | — | 1.1 MiB | < 5 MiB |
| Completion-event tracks | — | ≤ 200 cap | ≤ 200 |
| Stray files outside store/artifacts/IR | — | none | none |

## Interpretation

- No thread leak: pool workers return to idle; counts identical.
- Heap growth is noise-level (+18 KiB over 25 full pipelines).
- The 1.1 MiB store is **deliberate evidence retention** (one passport
  per job in the `runs` table), not a leak — it scales linearly in job
  count by design. The 5 MiB tripwire catches superlinear blowup.
- Malformed inputs fail fast as `failed`, never `succeeded`, never crash.

## Covered elsewhere (not repeated here)

- Overload admission + 50-burst: `tests/unit/test_jobs_admission.py`.
- Target lock contention + op cancellation: `tests/unit/test_target_ops.py`.
- QEMU process cleanup: `tests/unit/test_qemu_stop.py`.
- Crash recovery ownership: `tests/unit/test_jobs_lifecycle.py`.

## Honest gaps (NOT covered)

- SSE reconnection storms and browser-restart mid-run: no automation.
- API process restart under load: exercised manually only.
- Disk-pressure behavior (full disk): not tested.
- Multi-hour wall-clock soak: this campaign is load-shaped (~25 jobs),
  not time-shaped; a 24 h run was not performed.
