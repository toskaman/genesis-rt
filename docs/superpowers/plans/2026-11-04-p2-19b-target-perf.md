# P2 #19b Implementation Plan: target perf bench

> **For agentic workers:** implement task-by-task, keep the suite green.

**Goal:** `qnx_perf` record from real target measurement; gate can
reach QNX_PERFORMANCE_MEASURED; matrix 11/11.

---

### Task 1: Target bench probe

**Files:**
- Modify: `target/qnx8/faultinject/genesis_faultinject.c`

- [ ] Step 1: `bench <n>` mode (1..100000): sequential nominal
      round trips, CLOCK_MONOTONIC ns deltas, `SAMPLE %.3f` (us)
      per trip, `PERF_DONE n=<n>`; usage/IPC errors exit 2.
      9 checks + `probe` untouched.
- [ ] Step 2: `qcc -Werror` compile check.

### Task 2: Host producer + pipeline

**Files:**
- Modify: `scripts/qnx_target.py`, `host/genesis_rt/evidence.py`,
  `host/genesis_rt/orchestrator.py`, `host/genesis_rt/cli.py`,
  `host/genesis_rt/gate.py` (docstring)

- [ ] Step 1: `qnx_target.py perf` (SSH): guard up, `bench N`,
      guard down; parse SAMPLEs; nearest-rank distribution; write
      `qnx-perf-record.json` (+ transcript).
- [ ] Step 2: `build_passport(..., qnx_perf=...)` appends the
      record; `run_pipeline(..., perf_record=...)` loads+validates
      it (dict with status key, like target_record);
      `demo --perf-record` flag.
- [ ] Step 3: Gate docstring: producer exists (no logic change).

### Task 3: Matrix step + tests

**Files:**
- Modify: `scripts/qnx_target.py`, `tests/unit/test_qemu_argv.py`,
  `tests/unit/test_bench.py` (or new test module),
  `tests/integration/test_pipeline.py`

- [ ] Step 1: `target_perf` matrix step (`bench 200`) + parser
      branch (PERF_DONE + 200 SAMPLEs + finite).
- [ ] Step 2: Parser tests (synthetic pass/fail); distribution
      test (known samples -> exact percentiles); pipeline test
      (synthetic perf record -> PERFORMANCE_MEASURED tier).
- [ ] Step 3: Full suite green (host).

### Task 4: Target session (one QEMU boot)

- [ ] Step 1: Rebuild stage (bench binary), boot, wait-ssh, put.
- [ ] Step 2: `perf --samples 1000` x2 runs -> records; `verify`
      -> 11/11 PASS.
- [ ] Step 3: Codelab step 5 replay (supervisor/status/controller
      manual path); HAM presence probe (`pidin`, `ham` binary?).
- [ ] Step 4: `demo --target-record --perf-record` -> tier
      QNX_PERFORMANCE_MEASURED.

### Task 5: Docs + commit

**Files:**
- Modify: `docs/PROGRESS.md`, `docs/perf-baseline.md` (target
  table), `docs/quickstart-qnx8-qemu.md` (11/11 + perf),
  `docs/jury/*` (counts), `docs/regression-map.md` (if defects)

- [ ] Step 1: Target numbers (2 runs, method + QEMU caveats).
- [ ] Step 2: Counts 11/11; codelab step 5 checked box.
- [ ] Step 3: Commit (spec+plan+code+tests+docs) -> push -> CI.

## Self-Review

- Spec coverage: probe ✓, producer ✓, matrix ✓, pipeline ✓,
  proof ✓. Exact formats and files named.
- Type consistency: record shapes mirror `qnx_target` handling.
