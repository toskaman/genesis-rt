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
- `qcc_build`: wall time of one real native `make qnx` (6 binaries per
  machine build; 7 staged on target for the full matrix) plus warning
  count; `blocked` without an SDK.
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
| qcc 6 binaries/machine | 769.8 ms, 0 warnings | 693.1 ms, 0 warnings |

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

## Recorded target runs (n=1000 each)

| Metric (IPC round trip, µs) | Run 1 (2026-11-04) | Run 2 (2026-11-04) | Run 3 (2026-11-05, cell, prov. v2) |
|---|---|---|---|
| min | 180.3 | 155.9 | 128.2 |
| p50 | 323.1 | 305.4 | 254.7 |
| p95 | 551.9 | 519.3 | 399.9 |
| p99 | 665.7 | 638.8 | 493.7 |
| max | 1094.3 | 844.0 | 825.1 |

Reading: native round trip costs ~0.3 ms at p50 under TCG with a long
scheduling tail (max ~1 ms). Reproducible within ~20% across runs;
relative-regression signal only. Feeds the gate's
`QNX_PERFORMANCE_MEASURED` tier (informational; release needs
behavior, not budgets).

## Target scheduling comparison (2026-11-05, n=200 per config)

- Tool: `python scripts/qnx_target.py sched --samples N --out <dir>`
  (SSH; per config: guard up under `on -p <prio>[r|f|o]`,
  policy verified post-launch via pidin, `genesis_faultinject
  bench N` under its own `on -p` spec, guard down).
- Same probe as `perf` (sender-observed MsgSend round trip,
  CLOCK_MONOTONIC, nearest-rank). Raw samples kept in
  `qnx-sched-record.json`. No gate tier attached: informational.
- Context: QNX 8.0.0 x86_64 (QSTI 2026/06/05), QEMU 11.1.0 TCG
  `-cpu max`, 4 vCPU, 4G RAM, qnxuser (no root needed:
  `on -p 20f/20r` accepted). Default inheritance observed as `10r`.
- Machine dependence: IPC latency is machine-independent by
  construction (all guards share one code path; the IR only
  changes constants), so the campaign runs once per target,
  not per machine.

| Config (guard / bench) | Observed guard | min | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| baseline (default / default) | 10r | 203.5 | 509.2 | 953.3 | 1787.0 | 60885.3 |
| fifo_guard (20f / default) | 20f | 236.2 | 534.9 | 1089.8 | 1498.4 | 2125.3 |
| fifo_both (20f / 20f) | 20f | 196.1 | 311.4 | 504.2 | 618.5 | 803.1 |
| rr_both (20r / 20r) | 20r | 148.5 | 269.3 | 450.2 | 573.5 | 591.7 |

Reading: raising both endpoints to RT priority cuts p50 ~45% and
p99 ~65% versus baseline, and collapses the tail (max 60.9 ms →
0.6 ms): under TCG the sender side dominates the observed
latency. Raising the guard alone barely moves p50, which is
consistent with that reading. Figure `60885.3` is one 60 ms
emulation stall, kept in the table (p99 is robust to it).
Scheduling contrast only — not a hardware timing guarantee,
not a real-time claim.

## Regression hooks

`tests/unit/test_bench.py` runs the harness with a small N and asserts
the report schema (metric names, units, sample counts, non-negative
finite values) -- never timing thresholds, which would be flaky.
Timing regressions are caught by re-running this page's table and
comparing, not by CI asserts. `tests/unit/test_sched.py` pins the
sched campaign wiring (4 configs, `on -p` composition, pidin
policy parsing) with no timing assertions.
