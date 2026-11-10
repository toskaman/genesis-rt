# OMEGA7 Experiment Model

## Hypothesis table (bounded, versioned in `host/genesis_rt/causal.py`)

| ID | Cause | Host scenario (cell / base) | Native check |
|---|---|---|---|
| H-estop | ESTOP interlock propagation | cell_estop_during_transfer / estop_pressed | estop_target |
| H-crash | process crash + supervisor | none / planner_process_crash | controller_crash |
| H-stalebin | staged binary older than contract | manifest check (unwired) | v2_transitions |
| H-seq | IPC sequence failure | none / dropped_message | faultinject |
| H-jam | conveyor belt jam | cell_transfer_jam / belt_jam | none (PARTIAL) |
| H-stale-sensor | stale presence observation | cell_stale_presence / stale_proximity_150ms | none (PARTIAL) |

PARTIAL = host oracles exist but no native injector (verified:
`sensor_age=0` hardcoded in `genesis_controller.c`, `belt_set_jam`
never called, no matrix jam/stale step). Each entry also carries a
mechanism description, signal vocabulary, and a falsifier experiment.

## Ranking

Score = count of signal substrings (case-insensitive) in
title + observed details. Sort by score descending, table order as
deterministic tiebreak. Ranks are 1-based; all hypotheses are
always returned (no silent drops).

## Verdict semantics (oracle-verified)

A faultlab "pass" means the mechanism responded as designed —
verified against oracle bodies (e.g. `_o_cell_estop` asserts
deny+latch+no-motion+no-recovery; `_o_cell_jam` asserts safe abort
+ supervised recovery + completion). Therefore:

- pass + incident carries the mechanism's markers → SUPPORTED
- pass + no marker match → INCONCLUSIVE (healthy, wrong signature)
- fail + markers match → INCONCLUSIVE (testbed contradicts the
  field observation; failing checks attached for investigation)
- fail + no markers → REFUTED
- crash → NOT_TESTABLE (tooling failure, never support)
- missing/unknown → INCONCLUSIVE

Failing check names are recorded per experiment. Winner = first
SUPPORTED in rank order; none → conclusive=false.

## Experiment lifecycle (states)

INCIDENT_RECEIVED → HYPOTHESES_RANKED → (per hypothesis)
EXPERIMENT_PLANNED → HOST_REPRO → NATIVE_GROUNDING →
HYPOTHESIS_EVALUATED → DOSSIER_SEALED → (optional)
FIX_CANDIDATE → K1_BEFORE_AFTER → DOSSIER_RESEALED.
Terminal non-progress states: INCONCLUSIVE, NOT_TESTABLE,
BLOCKED (bad intake), FAILED (infra error, never a verdict).

## Determinism

Same incident + same IR + same code → same ranks, same run_ids
(fresh-dir), same verdicts. Re-runs into occupied dirs get
`-r2…` run-id suffixes, recorded in the dossier (never silent
overwrites; pipeline collisions still fail loud underneath).
