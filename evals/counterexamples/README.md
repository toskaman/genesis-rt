# Pinned counterexamples (regression evidence)

Each file is a real `explorer.explore` finding, committed verbatim
so a reviewer can replay the violation and its fix without
re-running the search. Derivation is never hand-written: the
command, seed, budgets, and IR digest are recorded below per
finding, and the pinning test fails closed on IR drift
(re-derive, don't hand-edit).

## ce-001-over-limit-allow

- Invariant `no_over_limit_allow`, params `max_allow_linear=0.9`,
  strategy `boundary`, seed 7, budgets `max_scripts=200`,
  `max_findings=1` (explorer v1).
- Found against `examples/amr-demo/machine-ir.json`, ir_sha256
  `356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d`
  (the Wave 10 §12 BEFORE revision).
- The boundary strategy emitted a 1-step script; shrink confirmed
  it minimal (1 step in, 1 step out — recorded, not improved).
- Fix: `control.max_linear_speed_mps` 1.2 → 0.9. The same minimal
  script violates on the original IR and holds on the fixed IR.
- Replay:
  `genesis-rt replay evals/counterexamples/ce-001-over-limit-allow.json examples/amr-demo/machine-ir.json`
  (add `--json`, or `--conformance` for the compiled-C tier).
- Pinned by `tests/unit/test_explorer.py::test_pinned_ce001_*`.

## Adding ce-002+

Run explore, save `findings[0]` verbatim, record the derivation
here, and pin a replay test (violates original / holds fixed /
drift fails closed).
