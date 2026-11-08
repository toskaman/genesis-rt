# Omega2 audit 4/7: AI evaluation (P1b)

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c`. Status:
MEASURED (no tuning performed; findings recorded as open).

Canonical record: `docs/ascension/AI_EVALUATION.md`
(Omega2 P1b section) +
`evals/results/2026-11-08-omega2-v5/README.md`.

## v4 regression rerun

Once per provider on omega2 code: offline 32/36, qwen 32/36,
llama 31/36 — scores AND miss lists identical to the frozen
Titan measurement (r01/r03/r04/r20, +r14 llama). No
regression, no fix derived. The rerun confirms the Wave-10
values-before-kind fix did not change the frozen v4-r14
outcome ("night rate" yields no second period candidate).

## v5 fresh measurement

`evals/planning_holdout_v5.json` (12 valid + 24 reject, novel
phrasings, 9 pre-registered probes), authored from the v4
failure taxonomy and frozen in commit `10493f6` BEFORE the
first v5 run (provenance by commit order; sha256 pinned in
`tests/unit/test_planning.py`). Measured once per provider:
24/36 × 3 with the IDENTICAL 12-case fail set, 0 false
rejects, 12/12 strict refusals. Both r14-class probes refused
deterministically on every provider (Wave-10 fix confirmed on
fresh phrasings); 7/9 probes failed as uncertain.

## Open (12 classes)

6 unsafe paraphrases, contradiction last-wins, silent unit
defaulting, fractional-ms mishandling, bare schema field,
fleet ambiguity, bracketed injection. Fixing any of them
contaminates v5 and requires a v6 set. Both frozen sets are
small (72 cases) and same-author; model refusal reasons are
unreliable; only accept/refuse outcomes were scored.

## Out of scope

The owner pilot run needs the owner (blocked, external).
"B6/B7/B8" codes cited in planning notes have no referent in
the repo and were not pursued.
