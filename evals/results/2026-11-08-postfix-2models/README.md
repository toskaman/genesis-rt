# Post-fix 2-model campaign (8 Nov 2026, Titan wave)

Code: `titan-ascension` branch — deterministic-first model path
(offline-accept wins, model only on unknown-kind), plural kind hints,
coordinated-period contradiction, unsupported-vehicle + non-machine +
safety-removal + schema-smuggling guards, sign-aware numbers.

Models (local Ollama, same quantizations as the 7 Nov campaign):
`qwen2.5:7b-instruct`, `llama3.1:8b-instruct-q4_K_M`.

| Set | Offline | Qwen | Llama |
|---|---|---|---|
| published 28 | 28/28, 0 unsafe | 28/28, 0 unsafe | 28/28, 0 unsafe |
| paraphrase 8 | 3/8 (5 unknown-kind) | 8/8 | 7/8 (para-amr-01 wrong kind, values right) |
| v1 holdout 98 (CONTAMINATED) | 91/98, 0 unsafe | 98/98, 0 unsafe | 98/98, 0 unsafe |
| v2 holdout 30 (see note) | 30/30 | 30/30 | 30/30 |

v1/v2 scores measure fix effectiveness, NOT generalization: v1 was
already development-contaminated, and v2 became development-touched
when the forklift/crane guards were derived from v2-r12/r13 (marked
in-file). Fresh-generalization measurement: `planning_holdout_v3.json`
(frozen; measure once, never tune).

Reproduce (Ollama with the two models on :11434):

```sh
GENESIS_AI_ENDPOINT=http://127.0.0.1:11434/v1 \
GENESIS_AI_MODEL=qwen2.5:7b-instruct PYTHONPATH=host \
python scripts/eval_planner.py --provider llm \
--dataset planning_holdout_v2.json --out qwen-v2.json
```

Raw per-case JSON for all 12 runs is in this directory.
