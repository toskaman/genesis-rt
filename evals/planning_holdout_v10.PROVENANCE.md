# OMEGA7 v10 blind holdout — provenance note

- Dataset: `evals/planning_holdout_v10.json` (184 cases: 48 valid, 136 reject;
  fallback cohort 26; languages en/fr/de/es)
- Digest (SHA-256): `d550b802edab3c3993bad7b14d4fd2c705da95476dc8a3cdba80be3c4fbeb584`
- Frozen: 2026-11-09 (UTC). Branch: `titan/omega7-v10-stale-arm`.
- Author: separately-delegated OMEGA7 v10 evaluation author (blind dataset creation).

## Blindness provenance

Contract-only authoring. The ONLY sources consulted were:

- `docs/PLANNER_CONTRACT.md` (v1.3 behavior contract),
- `schemas/machine-ir-v1.schema.json` (the Machine-IR schema; kinds, ranges,
  `defaults_applied`),
- `docs/jury/KNOWN_LIMITATIONS.md` (failure classes only: v9 counts of
  5 reject→IR accepts in safety-semantic + fleet-count classes and
  14 consultation mismatches — classes, never case text),
- `scripts/eval_planner.py`, read SOLELY for the dataset JSON format
  (`cases[]` with `expect`/`expect_reject`, `expect_consult`) and the
  `expect_consult` enforcement semantics.

Explicitly NEVER touched: `host/genesis_rt/planning.py` and all other
planner/validator sources, any `tests/`, any `evals/*.json` content, any
`evals/results/*` content, any prior v4–v9 case text, and the planner was
never executed. All 184 phrasings are fresh inventions from the contract
text; no residual case was seen, so none could be translated or paraphrased.

## Labeling basis (predictions, not observations)

- `expect_consult=false`: tier-1 kinds (incl. DE `Förderband`), generic nouns,
  unsafe requests (veto before any call), unsupported-kind predictions.
- `expect_consult=true`: tier-2 `tugger` valids (exactly one consult) and
  novel unknown/ambiguous aliases (one consult ending in
  clarification-required refusal). 26-case fallback cohort.
- `match` is asserted ONLY where the contract/harness evidences the refusal
  substring (`clarification required`, `ambiguous machine kind`); otherwise
  omitted so strict-matching never fabricates refusal text.
- Unsupported-kind, non-EN unsafe-verb, unit-ambiguity, and residual
  unicode-evasion cases are honest blind predictions; each rationale states
  its contract rule and, where the contract notes a residual risk, the
  expected-finding direction.
