# OMEGA5 consultation audit (P0 §2, 9 Nov 2026)

Branch `titan-omega5`. Environment: owner Windows box, Python 3.14
(the audit itself is pure file I/O — no provider, no network).
Tool: `scripts/audit_eval_consults.py` (read-only over committed
files). Pinned by `tests/unit/test_consult_audit.py` (8 tests).

## Term definitions (enforced, never interchangeable)

- `expect_consult`: per-case dataset label (true/false/absent).
- `actual_consults`: recorded `LLMProvider.consults` per row.
- `fallback_eligible`: cases labeled `expect_consult=true`.
- `fallback_cases`: rows with `actual_consults > 0`.
- `total_consults`: sum of `actual_consults` over rows.

## v7 findings (frozen, preserved)

Dataset `evals/planning_holdout_v7.json` (`d91e3956…`).
Raws: `evals/results/2026-11-09-omega4-v7/` (offline `598ff9bc…`,
qwen `2d31880a…`, llama `1aa1b9eb…`).

- Expected 24, actual 20+20. Missing on both models:
  `v7-v07`, `v7-r57`, `v7-r58`, `v7-r61` — all four passed via
  deterministic short-circuit (correct resolutions, wrong labels).
- Unexpected: none. Multi-call: none. Cross-provider diffs: none.

## v8 findings (frozen, preserved)

Dataset `evals/planning_holdout_v8.json` (`cb3820fd…`).
Raws: `evals/results/2026-11-09-omega4-v8/` (offline `60381ad9…`,
qwen `49a352e6…`, llama `fa51a9a9…`).

- Expected 21, actual 25+25. Unexpected on both models:
  `v8-004`, `v8-021`, `v8-028`, `v8-034` — valid German
  `Förderband` requests the offline layer rejects as unknown
  kind; both models returned the expected conveyor IR
  (alias-coverage defect + label error, not unsafe accepts).
- Missing: none. Multi-call: none. Cross-provider diffs: none.

## Reproduce

```powershell
python scripts/audit_eval_consults.py --dataset planning_holdout_v7.json --results evals/results/2026-11-09-omega4-v7/qwen2.5-7b.json evals/results/2026-11-09-omega4-v7/llama3.1-8b.json
python scripts/audit_eval_consults.py --dataset planning_holdout_v8.json --results evals/results/2026-11-09-omega4-v8/qwen2.5-7b.json evals/results/2026-11-09-omega4-v8/llama3.1-8b.json
python -m pytest tests/unit/test_consult_audit.py -q
```

## Consequence

`scripts/eval_planner.py` now enforces the contract for new sets:
llm runs require exactly 1 call when expected, 0 when forbidden;
unlabeled cases and offline runs are never violations; all rows
are preserved; mismatches exit 1 unless `--no-strict`. Rows carry
`expected_consult`; summaries separate `wrong_kind_accepts`,
`veto_refusals`, `fallback_eligible`, missing/unexpected lists,
and per-language pass rates.
