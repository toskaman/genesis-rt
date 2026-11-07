# Real-model planning eval — qwen2.5:7b-instruct (7 Nov 2026)

**Setup.** Throwaway Vultr VM `vhp-12c-24gb-amd` (12 vCPU AMD, 24 GB, CPU
only, Paris), Ubuntu 24.04, Ollama 0.40.15 bound to 127.0.0.1,
`qwen2.5:7b-instruct` (Q4, 4.7 GB), temperature 0, JSON mode. Repo at
`472a388` plus the `planning.py` revision named in each round's
`campaign.log` (sha256 printed). VM destroyed after the run. Scored by
`scripts/eval_planner.py`, never by the model.

## Results

| Round | Architecture | 28-case eval (shipped config) | valid | reject | unsafe accepts | w/o regex pre-filter | s/req |
|---|---|---|---|---|---|---|---|
| 0 | offline keyword planner | **28/28** | 10/10 | 18/18 | 0 | 20/28 (8 accepts) | 0.00 |
| 1 | model writes full IR | 19/28 | **2/10** | 17/18 | 1 | 19/28 | 8.6 |
| 2 | model → intent → deterministic template | 24/28 | 10/10 | 14/18 | 4 | 22/28 | 1.4 |
| 3 | round 2 + deterministic unit/range/ambiguity guards first | **28/28** | 10/10 | 18/18 | **0** | 26/28 (2 accepts) | 0.95 |

Paraphrase set (`evals/planning_paraphrase.json`, 8 requests written
before any model saw them, outside the keyword vocabulary):

| Provider | Passed |
|---|---|
| offline keyword planner | 3/8 |
| llm (round 3) | **8/8**, 0 unsafe, 2.7 s/req |

## What we learned (and changed in code)

1. **Round 1:** a 7B model asked to write whole IR invents machine kinds
   (`conveyor_belt`, `mobile_rover`) and anchors on the example's
   1.2 m/s. `validate_ir` rejected every invalid proposal — the gate held —
   but usefulness was 2/10.
2. **Round 2:** the model now emits only `{kind, period_ms,
   max_linear_speed_mps, refusal}`; the deterministic planner builds the
   IR and the result is cross-checked. Valid 10/10, but the model returned
   `null` for "5 km/h" / "1 second", letting defaults fill in.
3. **Round 3:** units, ranges, length and ambiguity are judged by the
   deterministic parser *before* the model; only phrasing the parser
   cannot map reaches the model. 28/28 with 0 unsafe accepts.
4. Without the regex pre-filter the two misses ("no speed limit", a prompt
   injection) still produce a bounded, simulation-only IR from the
   template — the model cannot write limits or `simulation_only`.

## End-to-end

`amr-llm-01.json` (model-planned: "warehouse AMR, 20 ms control period,
max speed 0.8 m/s") → `generate` → `demo` → `passport-amr-llm-01.json`:
gate PASS, 8/8 host scenarios, `replay` valid, level `HOST_TESTED`,
`qnx_verified=false` (no SDK on the VM — host evidence only, by design).
"…actual motors on our factory floor at 25 m/s" → refused
(`max speed 25.0 m/s out of range`); "belt that runs at 9 km/h" →
refused (`not m/s`).

## Limits

One model, one quantization, CPU only, temperature 0, 36 prompts total.
No claim about other models. The 28-case set was authored for the
keyword planner; the paraphrase set is small. Not a safety evaluation of
the model — safety comes from the deterministic gate.
