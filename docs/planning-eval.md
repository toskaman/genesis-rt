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
- The `genesis-rt plan` CLI routes through `plan_machine`, so CLI users
  get the same refusals (exit code 2, `error: PlannerRejection: ...`).

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

`evals/planning_eval.json` — 28 request cases, all pinned by
`tests/unit/test_planning.py::test_published_eval_offline_scores_100`:

| Class (§11) | Cases | Expected behavior |
|---|---|---|
| Valid instructions | 10 | kind + period + speed pinned exactly |
| Ambiguous instructions | 2 | refuse, name the colliding kinds |
| Dangerous instructions | 7 | refuse before any provider call |
| Wrong units | 3 | refuse with the correct unit (m/s, ms) |
| Out-of-domain requests | 2 | refuse as unknown machine kind |
| Range / too-short | 4 | refuse with the valid range |

Provider-output faults (impossible guard-vocabulary transitions,
dangling cell references, over-limit speeds, `simulation_only: false`,
non-objects, crashes) are covered separately by stub-provider unit
tests in `tests/unit/test_planning.py`, since they are faults in
returned IR rather than in the request text.

## Acceptance criteria

1. The bundled `offline` provider scores 28/28 on the published set.
2. Every refusal class above has at least one pinned case; any miss
   fails the suite (no partial credit, no skipped cases).
3. All stub-provider fault tests pass: no provider output can reach a
   validated IR without passing `validate_ir`.
4. A new provider is accepted only with its measured score on this same
   set published next to `offline`'s.

## Latest measured result (2026-11-05, this repo)

- `offline`: **28/28 (100%)** — `pytest tests/unit/test_planning.py`
  (15 tests incl. the eval runner, all green; full suite 525/525).

## Regressions the set caught

1. Substring hint matching classified "robotic arm" as a
   differential-drive robot ("robot" matched inside "robotic"). Fixed
   with whole-word matching; the eval case pins the fix.
2. Ambiguous requests ("robot arm beside a conveyor belt") silently
   picked the first matching kind. Now refused with the colliding
   kinds listed; two eval cases pin the fix.
3. Wrong-unit speeds ("5 km/h") silently fell back to the 1.2 m/s
   default. Now refused with guidance to state m/s (likewise seconds
   for the period); three eval cases pin the fix.

## Limits

- The bundled provider is a keyword planner, not an LLM: English
  keywords, one machine per request, schema v1 only, no dialogue.
- Ambiguity detection is lexical (colliding kind hints), not semantic.
- Refusal patterns are regexes over the lowered request; adversarial
  paraphrases outside the pinned classes are not claimed to be caught.
- Scores measure refusal/interpretation behavior only, not the quality
  of any downstream code — that is what the evidence passport covers.
