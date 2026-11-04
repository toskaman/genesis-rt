# Evidence methodology

## What a passport is

`artifacts/runs/<id>/passport.json`: a machine-readable, hash-linked record
of one pipeline run. Records: `ir` → `codegen` → `qnx_build` →
`scenario:<id>…` → `summary` → `gate_verdict`.

## Chain rule

`record.hash = sha256(canonical_json(body) + prev_hash)`, genesis
`prev_hash = "GENESIS" + "0"*57`. Canonical JSON: sorted keys, compact
separators. Wall-clock timestamps live only in the envelope and never
enter hashes — identical runs produce identical chains (tested).

Each scenario record carries: seed, status, per-check oracle results,
stats (allows/denies/reasons/final state), and a bounded trace excerpt
plus the full-trace digest.

## Measurement boundaries

- Simulator ticks use virtual `t_ms` (fixed step). Host wall time is
  metadata only.
- QNX-side latencies (control-loop elapsed, IPC round trip, guard decision,
  missed deadlines) are measured on target with `CLOCK_MONOTONIC` when an
  SDK target is available; host↔guest delays are reported separately and
  never mixed into QNX numbers.
- QEMU numbers are for reproducibility/regression, not production timing
  guarantees. Reports state count, p50/p95/p99/max, load and target config.

## Replay

`python scripts/replay.py <passport.json>` recomputes the chain and
re-evaluates the gate. Exit 0 requires a valid chain AND a PASS verdict.
Any tampering, missing record or non-pass scenario fails loudly.

## No-test ⇒ no-pass

The gate (`host/genesis_rt/gate.py`) passes only when: chain valid, every
required scenario present with status `pass`, a `qnx_build` record present,
and no failures/crashes among required scenarios. An empty required set is
rejected (no vacuous pass). `qnx_verified` is reported alongside, never
conflated with, the host verdict.
