# Performance baseline (host + target, never mixed)

> Two separate tables below: host numbers describe the **dev
> machine** (host regressions + methodology); target numbers describe
> **QNX 8.0 under QEMU/TCG** (reproducibility only — never a hardware
> timing guarantee, never a real-time claim). The two must never be
> mixed into one claim.

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

## Target method

- Tool: `python scripts/qnx_target.py perf --samples N --out <dir>`
  (SSH; guard up, `genesis_faultinject bench N`, guard down).
- Measured: sender-observed `MsgSend` round trip (nominal command →
  guard `decide()` → reply), sequential, fresh seq each trip,
  `CLOCK_MONOTONIC` nanoseconds on target, reported in microseconds.
- Analysis: nearest-rank percentiles on the raw samples (kept in
  `qnx-perf-record.json` for independent re-analysis).
- Target: QNX 8.0.0 x86_64 on QEMU 11.1.0, TCG `-cpu max`, 4G RAM.
  Emulation overhead dominates: expect ~100× the host Python guard.

## Recorded target runs (2026-11-04, n=1000 each)

| Metric (IPC round trip, µs) | Run 1 | Run 2 |
|---|---|---|
| min | 180.3 | 155.9 |
| p50 | 323.1 | 305.4 |
| p95 | 551.9 | 519.3 |
| p99 | 665.7 | 638.8 |
| max | 1094.3 | 844.0 |

Reading: native round trip costs ~0.3 ms at p50 under TCG with a long
scheduling tail (max ~1 ms). Reproducible within ~10% across runs;
relative-regression signal only. Feeds the gate's
`QNX_PERFORMANCE_MEASURED` tier (informational; release needs
behavior, not budgets).

## Regression hooks

`tests/unit/test_bench.py` runs the harness with a small N and asserts
the report schema (metric names, units, sample counts, non-negative
finite values) -- never timing thresholds, which would be flaky.
Timing regressions are caught by re-running this page's table and
comparing, not by CI asserts.
