# Shot → evidence mapping

Every demo claim resolves to a file, an op, or a command. Nothing
on screen is staged.

## Ops (local target store `artifacts/runs/target-ops/`)

- BEFORE `op-0350e9bd4818`: COMPLETED 13/13 stages, matrix 16/16
  PASS, 1000 perf samples, gate PASS `QNX_PERFORMANCE_MEASURED`,
  replay MATCH, `qnx_verified` true.
  IR digest `356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d`.
- AFTER `op-df9b3668e5f7`: FAILED at `qemu_verify` (9/13), matrix
  15/16, `limits_differ` FAIL, no sealed passport (by design:
  failed runs never seal). IR limit 1.2 → 1.6 flips the 1.5 m/s
  probe DENY → ALLOW — the behavior change the video shows.
  IR digest `fb2dbb3de8a19546d29be71b55e9f89bc37241627339430d11fea40c319e4d5c`.
- Detail: `docs/jury/BEFORE_AFTER_NATIVE.md`.

## Public evidence pack (no SDK needed)

- `evidence/qnx8-x86_64-verified-b22cea1/`: BEFORE passport,
  target + perf records, transcripts, `verify.py`,
  `EXPECTED_RESULTS.md` (34 files, manifest-pinned).
- Tamper control: the pack verifier rejects modified bundles
  (negative tests in `tests/integration/test_evidence_pack.py`).

## Shots

| Shot | Evidence |
|---|---|
| 1–2 machine + contract | `examples/amr-demo/machine-ir.json` (live Studio) |
| 3 generated C | `target/qnx8/` + codegen output, `qcc` 0 warnings (BEFORE `qnx-build-record.json`) |
| 4 native execution | BEFORE op: `transcripts/qnx-target-record.json` (16/16), `performance/qnx-perf-record.json` (1000 samples) |
| 5 fault | Real host job `stale_proximity_150ms` (seeded, reproducible); native guard DENY in BEFORE transcripts |
| 6 diagnosis | Job passport + Evidence Graph (live Studio) |
| 7 before/after | `/target/ops/compare?before=op-0350e9bd4818&after=op-df9b3668e5f7` |
| 8 passport + replay | BEFORE `passport.json` + `scripts/replay.py` MATCH |
| 9 value + dossier | `/target/ops/op-0350e9bd4818/dossier` (.zip: report + manifest + raw + VERIFY.md) |

## Verification commands (reviewer)

```sh
python evidence/qnx8-x86_64-verified-b22cea1/verify.py
PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json
python -m pytest tests/ -q   # 890 with SDK, 885 + 5 skips without
```
