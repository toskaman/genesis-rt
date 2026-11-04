# Performance baseline (host-only)

> These numbers describe the **dev machine**, not the QNX target. They
> exist to detect host-side regressions and to document methodology.
> Target timings (native IPC latency, guard time on QNX, control-loop
> jitter) need the QEMU harness and will be recorded separately,
> post-reboot. The two must never be mixed into one claim.

## Method

- Tool: `python scripts/bench_host.py [--samples N] [--out report.json]`
  (pure stdlib, `time.perf_counter`).
- `guard`: N back-to-back `guard_policy.decide()` ALLOW calls, fresh
  sequence each call; reports mean/min/max/p50/p95/p99 in microseconds.
- `campaign`: wall time of one full `faultlab.run_all()` (8 scenarios).
- `codegen`: wall time of one `codegen.generate()` (2 files).
- `qcc_build`: wall time of one real native `make qnx` (6 binaries)
  plus warning count; `blocked` without an SDK.
- Environment: Windows 10 (`Windows-10-10.0.19045-SP0`), CPython 3.14.4,
  16 CPUs, N = 20000 for the guard distribution.

## Recorded runs (2026-11-04)

| Metric | Run 1 | Run 2 |
|---|---|---|
| guard decide p50 | 3.4 µs | 2.1 µs |
| guard decide p95 | 4.7 µs | 3.9 µs |
| guard decide p99 | 6.7 µs | 4.3 µs |
| guard decide max | 111.6 µs | 28.3 µs |
| campaign 8 scenarios | 18.9 ms | 13.8 ms |
| codegen 2 files | 1.97 ms | 1.53 ms |
| qcc 6 binaries | 769.8 ms, 0 warnings | 693.1 ms, 0 warnings |

Reading: host guard decisions cost single-digit microseconds at p99
(spikes are OS scheduling, hence max ≫ p99); a full host campaign runs
in ~15 ms; a native build takes ~0.7 s with 0 warnings. No performance
claim about QNX is made from these numbers.

## Regression hooks

`tests/unit/test_bench.py` runs the harness with a small N and asserts
the report schema (metric names, units, sample counts, non-negative
finite values) -- never timing thresholds, which would be flaky.
Timing regressions are caught by re-running this page's table and
comparing, not by CI asserts.
