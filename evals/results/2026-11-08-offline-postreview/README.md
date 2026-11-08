# Offline post-review rerun (8 Nov 2026, repo HEAD `5bb2fc4` + uncommitted Titan docs)

Reproduces the independent-review addendum number with raw per-case
output: offline planner on the (contaminated, regression-only) v1
holdout scores **85/98** with **6 accepted-should-refuse** and
7 false rejects.

- `v1-offline-85of98.json` — full per-case record from
  `scripts/eval_planner.py --provider offline --dataset
  planning_holdout.json`.

Command:

```sh
PYTHONPATH=host python scripts/eval_planner.py --provider offline \
  --dataset planning_holdout.json --out v1-offline-85of98.json
```

This backs `docs/ascension/AI_EVALUATION.md` "Independent review
addendum". Models were NOT rerun here: post-fix model safety remains
unverified.
