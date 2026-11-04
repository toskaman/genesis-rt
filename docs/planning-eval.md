# Planning interface and evaluation

`host/genesis_rt/planning.py` is the provider-independent seam between
natural-language requests and validated Machine IR.

## Contract

- Providers implement one method: `propose_raw(request, machine_id)`.
- Provider output is **untrusted**: `plan_machine` re-validates every
  proposal through the same strict `validate_ir` gate. Non-objects,
  unknown keys, bad units, and out-of-range values are rejected with
  `PlannerRejection` (never a crash, never a silent fix-up).
- Providers cannot override safety policy, bypass the verification
  gate, or mark tests passed: they only produce candidate IR.
- Unsafe requests (guard removal, unbounded actuation, real-hardware
  deployment, prompt-injection phrasing, out-of-scope uses) are refused
  **before** any provider is called, with a precise explanation.

## Bundled providers

| Name      | Behavior | Network | Cost |
|-----------|----------|---------|------|
| `offline` | Deterministic keyword planner (`planner.py`) | No | Free |

No LLM provider is bundled and none is required for the demo. Third
parties add one by implementing `propose_raw` and registering it in
`PROVIDERS`; the new provider is then measured against the eval set
below. Do not claim an LLM integration is operational when only
`offline` is registered: `sorted(PROVIDERS)` is the honest answer.

## Evaluation set

`evals/planning_eval.json` (15 cases: 8 valid across the three machine
kinds, 7 refusals across unsafe/range/unknown-kind/too-short classes).
`tests/unit/test_planning.py::test_published_eval_offline_scores_100`
runs the set and fails on any miss.

Latest measured result (2026-11-04, this repo):

- `offline`: **15/15 (100%)**

The set caught one real bug before release: substring hint matching
classified "robotic arm" as a differential-drive robot ("robot" matched
inside "robotic"). Fixed with whole-word matching; the eval case pins
the fix.
