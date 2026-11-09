# Planner input contract (versioned)

Governs what the intent planner accepts, what it refuses, and
what the emitted Machine IR guarantees. The v7 evaluator
labels cases against v1.1. History is preserved below; never
rewritten.

## v1.1 (Omega4, 9 Nov 2026) — adjudication of the v6 disputes

**Decision: bare-kind input stays ACCEPTED, only with
machine-readable output disclosure (option A hardened).
Fail-closed (option B) was rejected.**

Rationale:

- The product compiles simulation-only machines with
  bounded safe-side defaults (period 10 ms, speed
  1.2 m/s — mid-range, never the 10 m/s ceiling).
- The shipped UX explicitly invites omission-for-default
  (`planner.py` rejection guidance); failing closed now
  would contradict shipped guidance and break the pinned
  `test_explicit_provider_instance_accepted` behavior.
- The v6 objection was valid in one respect: defaults
  were SILENT in the IR. Silence, not acceptance, was
  the defect. v1.1 removes the silence.

Rules (v1.1):

1. Bare kind, no values ("a conveyor"): ACCEPT with
   `defaults_applied: ["max_linear_speed_mps",
   "period_ms"]` in the emitted IR.
2. Explicit values: ACCEPT with NO `defaults_applied`
   key (omit-when-empty; explicit IRs are byte-identical
   to v1.0).
3. Partial values: ACCEPT with the defaulted subset only
   (e.g. `["max_linear_speed_mps"]`).
4. Named-but-valueless parameters ("speed TBD", "unknown
   period", "speed:"): REJECT (fail closed, unchanged).
5. `defaults_applied`, when present, MUST be 1..2 unique
   items from `[period_ms, max_linear_speed_mps]`;
   anything else fails validation. Both validators
   enforce this (`ir.validate_ir` + JSON schema).
6. Downstream consumers (codegen, passports, Studio) MUST
   surface the marker rather than present defaulted
   values as user-stated. (`genesis-rt plan` prints the
   IR JSON, so the marker is visible with no CLI change.)

Compatibility: additive and non-breaking. v1.0 readers
that reject unknown keys will refuse v1.1 IRs carrying
the marker — that is correct strictness, not a
regression; v1.0-era IRs without the marker still
validate. No emitted explicit IR changed bytes.

v6 dispute note: the three `reject:missing` bare-kind
cases were measured as ACCEPTED under v1.0 (silent).
Their historical outcomes are PRESERVED unchanged. Under
v1.1 the same requests are ACCEPTED-WITH-DISCLOSURE —
the dispute is resolved prospectively, never by
rewriting v6.

## v1.0 (Titan–Omega3) — historical

- Bare kind accepted; defaults (period 10 ms, speed
  1.2 m/s) applied SILENTLY (no IR marker). OMEGA3
  described this as "output-disclosed"; code inspection
  (Omega4 baseline) found no marker — the description
  was wrong and is superseded by v1.1.
- Named-but-valueless fails closed (§5.3 rule).
- Model path: intent only; deterministic gate decides.
