# OMEGA7 Scheduler (Planner) Evaluation Note

Date: 10 Nov 2026. Branch: `titan/omega7-causal-engine`.

## No planner change → no new measurement

This cycle does not touch the planner, parser, validator,
schemas, or evaluation harness. Verified by file diff at PR
time: `host/genesis_rt/planning.py`, `planner.py` (if present),
`semantics.py`, `ir*.py`, `scripts/eval_planner.py`, and
`evals/` must show zero modifications.

Consequences:

- v10 (`d550b802`, 184 cases) stays frozen and measured-once
  (OMEGA7: offline 159/184, qwen/llama 165/184, unsafe 15
  deterministic-layer, wrong-kind 0). It is NOT re-run here;
  re-running a frozen holdout on any code state without a new
  freeze would void its blindness.
- No v11 (or later) holdout is required, because no
  generalization claim is made about changed planner behavior.
- The causal slice consults no model at all: ranking is
  deterministic signal matching, verdicts come from oracle
  outcomes. Planner contract stays v1.4.

## V10 provenance (recap, not a re-measurement)

Frozen pre-implementation on `titan/omega7-v10-stale-arm`,
measured once per provider, raw JSON committed, digests pinned.
Case contents were not read during this cycle's research phase
(only digests, counts, and the evaluation summary).

If a future cycle modifies planner behavior, it must freeze v11+
before implementation and measure once, per standing policy.
