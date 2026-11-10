# OMEGA7 Architecture — Causal Slice

## New modules (flat, repo convention; K1/faultlab/runner untouched)

- `host/genesis_rt/incident.py` — intake schema v1, fail-closed
  validation (bounded `OBSERVED_KINDS`), canonical sha256 digest.
- `host/genesis_rt/causal.py` — bounded hypothesis table, ranking,
  kind-aware scenario resolution, signature-based elimination.
- `host/genesis_rt/causal_run.py` — plans, host repro via
  `run_pipeline`, archived/live native grounding, K1 fix leg via
  `verify_change`, dossier seal/verify.

## Reuse map (no rewrites)

| Need | Reused | How |
|---|---|---|
| host repro legs | `orchestrator.run_pipeline` | one leg per scenario; outcome from `steps.verification.scenarios` |
| fix proof | `change.verify_change` | BEFORE/AFTER + compare + chains; appended + resealed |
| native live | `target.TargetRunner` | `verify-only` workflow + bounded poll + timeout-cancel |
| native archived | Omega2 pack transcripts | sha256-pinned bytes, mode labeled |
| passports | `evidence.build/verify_chain` | per-experiment passports re-verified by dossier check |
| seeds/checks | passport `scenario:*` records | seed + failing checks attached per experiment |

## Surfaces

- CLI: `causal-repro` (exit 0 conclusive / 1 inconclusive / 2
  error), `causal-fix` (mirrors K1: 0 PASS / 1 else / 2 error).
- API: `POST /causal/dossiers`, `GET /causal/dossiers/{id}` (returns
  `{valid, errors, dossier}`), `POST /causal/dossiers/{id}/fix`,
  `GET /causal/flagship` (read-only flagship pair). Inline IR
  payloads with `MAX_IR_BYTES` guard; temp files dropped after use;
  traversal guards mirror `/changes/{id}`.
- Studio: Judge stage H "The causal proof" (flagship → POST →
  inline winner/verdicts/seal render; all values escaped).
  Pure-core node tests pin 8 stages + clamp; E2E pins H wiring
  (navigation only — the full run executes six pipelines).

## Data flow (reproduce)

incident.json → validate → machine kind → rank → plan →
per hypothesis: [scenario → run_pipeline → outcome → verdict] +
native grounding → winner → seal → `dossiers/<id>/dossier.json`
(+ self-contained `before-ir.json`) → `verify_dossier` re-checks
seal, incident digest, before-IR hash, every passport chain.

## Concurrency / isolation

Pipelines reuse the orchestrator's run-id registry and collision
rules; live grounding reuses the target lock (one op at a time;
`TargetBusy` surfaces honestly as start-failed). No shared mutable
state between hypotheses: one run dir per experiment.
