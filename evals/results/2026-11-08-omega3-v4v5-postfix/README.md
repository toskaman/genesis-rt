# Omega3: v4/v5 offline regression after hardening-2 (8 Nov 2026)

Code: `titan-omega3` with hardening-2 (post-`c6085f2`, uncommitted
at run time; see `docs/audits/OMEGA3_AI_EVALUATION.md` for the
commit SHA). Offline provider only.

| Dataset | Total | Valid | Reject | False-rej |
|---|---:|---:|---:|---:|
| v4 | 36/36 | 12/12 | 24/24 | 0 |
| v5 | 36/36 | 12/12 | 24/24 | 0 |

Baselines on pre-Omega3 code: v4 32/36, v5 24/36 (offline).

REGRESSION-ONLY: these sets are contaminated for generalization
claims (fixes were informed by v5/v6 failure classes). Frozen
datasets untouched on disk (digest pins green). The honest
generalization measurement of hardening-2 requires a fresh v7 set.

```sh
PYTHONPATH=host python scripts/eval_planner.py --provider offline \
--dataset planning_holdout_v4.json --out offline-v4.json
```
