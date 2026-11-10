# OMEGA7 Proof Capsule — Dossier Schema & Verification

## Layout (`artifacts/dossiers/<incident-id>/`)

- `dossier.json` — sealed dossier (seal covers content; only
  `dossier_path` is attached post-seal, mirroring K1 `verdict_path`).
- `before-ir.json` — byte copy of the investigated IR (self-contained
  proof; API temp uploads would otherwise rot).

## Schema (dossier_version 1)

- `incident`: full validated incident + canonical `digest`.
- `machine`: `{ir, kind, ir_sha256}` (ir points at before-ir.json).
- `hypotheses[]`: `{id, cause, mechanism, rank, matched_signals,
  verdict, experiment_id}`.
- `experiments[]`: `{id, hypothesis_id, scenario, seed, run_id,
  passport, outcome, note, checks_failed, native_grounding}`.
- `causality`: `{winning_hypothesis, conclusive, verdict_counts}`.
- `target_mode`, `created_utc`, `seal`.
- After fix: `fix: {change_id, verdict, before_verdict,
  after_verdict, verdict_path}` + `supersedes: <prior seal>`.

## Verification (`verify_dossier`, fail-closed, never raises)

1. Version must equal 1.
2. Seal recomputed over content-minus-seal must match (any edit
   invalidates).
3. Embedded incident digest must recompute (when the full doc is
   present).
4. `before-ir.json` must exist with matching sha256.
5. Every experiment passport must exist with a valid hash chain
   (`verify_chain`).
6. Fix `verdict.json` must exist when a fix is recorded.

`verify_fix` refuses tampered dossiers (`DossierError`) before
running K1. Negative paths tested: tampered verdict, deleted
before-IR, broken chains (via seal), double-seal refusal.

## Trust level

Hash-sealed integrity, UNSIGNED (no signing root — same posture
as evidence packs). The seal proves the dossier is byte-identical
to what the pipeline sealed, not who sealed it.
