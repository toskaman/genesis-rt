# P2 #19b design: target perf bench (QNX_PERFORMANCE_MEASURED tier)

## Intent

Close the gate's top tier honestly: measure native IPC round-trip +
guard decision latency ON the QNX 8.0/QEMU target (target monotonic
clock), ship the samples to the host for analysis, and attach a
`qnx_perf` record to passports. G7-clean: target clock only, QEMU
labeled (reproducibility, never a hardware timing guarantee), host
and target numbers never mixed.

## Decomposition (ship as one slice)

- **Target probe:** `genesis_faultinject bench <n>` (n in 1..100000):
  n sequential nominal `MsgSend` round trips, `CLOCK_MONOTONIC`
  timestamps, prints `SAMPLE <us>` per trip + `PERF_DONE n=<n>`.
  No stats in C (raw data only, auditable).
- **Host producer:** `qnx_target.py perf` (SSH): start guard, run
  bench, slay guard, parse samples, compute nearest-rank
  distribution (count/min/p50/p95/p99/max), write
  `qnx-perf-record.json` `{status: ok, measurements:
  {ipc_roundtrip_us: {...}}, raw_samples_us: [...], method, clocks,
  target}`.
- **Matrix 10 -> 11:** `target_perf` step (guard + `bench 200`;
  asserts `PERF_DONE n=200` + 200 SAMPLE lines + finite values).
- **Pipeline:** `run_pipeline(..., perf_record=...)` +
  `demo --perf-record` -> `build_passport(..., qnx_perf=...)`;
  gate docstring updated (producer exists now).

## Contracts

- Measured quantity: sender-observed `MsgSend` round trip
  (controller->guard decide->reply) in microseconds, sequential,
  fresh seq each trip, no other load asserted.
- Percentiles: nearest-rank on sorted samples, documented in the
  record (`method.percentile: nearest-rank`).
- No budgets, no thresholds: the tier is informational
  (RELEASE_MIN stays QNX_BEHAVIOR_VERIFIED).
- Parser + distribution + pipeline tests on synthetic data; the
  on-target run (n=1000 x2) remains the proof; numbers land in
  `docs/perf-baseline.md` (separate target table).

## Self-review

- No placeholders; commands, formats, and tier wiring fixed above.
- Consistent: matrix idioms (slay cleanup), evidence chain kinds,
  CLI record flags (`--target-record` precedent).
- Scope: perf + codelab step 5 + HAM probe in one QEMU session; no
  Studio, no video in this slice.
