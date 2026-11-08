# Omega3 AI evaluation (8 Nov 2026)

Date: 2026-11-08. Branch `titan-omega3`. Blind set frozen `a8f2d48`,
§5.3 fixes `c6085f2`, hardening-2 + this report uncommitted at
writing (commit SHA recorded at commit time).

Owner-only actions: none. No paid APIs used (local Ollama only).

## 1. Protocol and provenance

- v6 (`evals/planning_holdout_v6.json`, 24 valid + 48 reject, sha256
  `e5fbcd49…9fde`) authored blind by a separate agent, frozen in
  `a8f2d48` BEFORE the §5.3 fix commit `c6085f2` (provenance by
  commit order). Digest pinned in `tests/unit/test_planning.py`.
- v6 measured exactly ONCE per provider on `c6085f2`, never re-run
  after. Post-measurement fixes used fresh self-authored phrasings,
  never v6 strings.
- v4/v5 frozen and untouched on disk (digest pins green); post-fix
  runs are REGRESSION-ONLY — contaminated for generalization
  claims since fixes were informed by v5/v6 failure classes.

## 2. v6 results (frozen measurement of `c6085f2`)

| Provider | Total | Valid | Reject | Unsafe | False-rej |
|---|---:|---:|---:|---:|---:|
| offline | 46/72 | 24/24 | 22/48 | 26 | 0 |
| qwen2.5:7b | 46/72 | 24/24 | 22/48 | 26 | 0 |
| llama3.1:8b | 46/72 | 24/24 | 22/48 | 26 | 0 |

Fail sets byte-identical across providers (verified by diff).
Max per-case latency 0.01 s on both LLM providers: the model was
consulted ZERO times (deterministic-first short-circuit — no v6
case reaches "unknown machine kind"). v6 therefore does not
exercise the model-fallback path; v7 must include unknown-kind
cases with stated limits.

Fail classes (26): novel removal/disable paraphrases (lifted,
silenced, lacking, minus, switched-to-inactive, powered down,
jumpered, bridged, redundant, no-guarding-needed), multilingual
removal (DE/ES), authority appeal + removal noun, zero-width and
spaced-letter evasion, bare rate / throughput units, unitless
contrast values, bare `kind=`, `[note: ...]` carrier, counted
fleet ("six conveyors").

Three `reject:missing` cases (bare kind, no values) are CONTRACT
DISPUTES: bare-kind-with-defaults is pre-existing pinned behavior
(`test_explicit_provider_instance_accepted`) with documented,
output-disclosed defaults; the dataset expects rejection. Kept
deliberately; flagged for a future major-version decision.

Raw evidence: `evals/results/2026-11-08-omega3-v6/` (3 JSON +
README).

## 3. Hardening-2 (post-measurement, NOT v6-validated)

Fixes for the v6 failure classes (blind-v6 §5.4 forbids re-running
v6 to claim improvement):

- `planning.py`: input canonicalization (zero-width strip,
  spaced-letter rejoin); governing-verb + disabled-state +
  removal-noun + lack/minus + verb-mediated-inactive + power-loss
  + -free/-less + no-X-needed + DE/ES/FR removal entries;
  explicit-count fleet rule; bare `kind=`; negation tolerance.
- `planner.py`: bare `knots`, throughput `N things per time`,
  unitless-decimal-in-contrast-frame refusal.
- 9 new regression tests (51/51 planning green), all with fresh
  self-authored phrasings; §5.5 gaps closed (intent extras
  dropped, refusal passthrough, no-consult pins, template
  disagreement).

v4/v5 offline regression after hardening-2: **36/36 and 36/36**
(12/12 valid, 24/24 reject, 0 false rejects), from 32/36 and
24/36. Raw: `evals/results/2026-11-08-omega3-v4v5-postfix/`.
These measure regression, NOT generalization.

## 4. Honest limitations

- No general robustness claim from 72 (or 36+36) cases.
- Regex-category patching does not close the semantic gap: each
  blind round found novel paraphrases. v7 (fresh blind set) is
  required to measure hardening-2 honestly.
- Known residuals: bare-integer contrasts ("1 m/s days, 2 at
  night"), period-side unitless contrasts, alarm-device coverage,
  model-intent-vs-request value cross-check (model may restate a
  different in-range value for unknown-kind requests).
- Bare-kind defaults and the 3 missing-disputes stand as a
  documented contract decision.

## 5. Test command and outcome

`python -m pytest tests/ -q` (SDK, Windows, Python 3.14):
1320 passed + 2 pre-existing axe skips of 1322, zero failures.
