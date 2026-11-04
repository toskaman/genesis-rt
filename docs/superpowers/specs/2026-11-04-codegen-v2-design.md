# Codegen v2 design (P1 #11 host slice)

Autonomous mode: no interactive gates per standing order (full autonomy
until done). Approaches were weighed inline; this spec records the
decision. Plan: `docs/superpowers/plans/2026-11-04-p1-11-codegen-v2.md`.

## Intent

Generate machine-specific C from IR v2 so two machines produce
structurally different sources (not renamed constants): state machines,
command validators, telemetry maps, fault responses. Host-provable now
(snapshot, differentiation, behavioral harness, `qcc` 0-warning);
native behavior demo and guard call-site after the P0 #4 target proof.

## Approaches considered

1. **Template-rendered module + host harness (chosen).** Same
   `string.Template` pattern as v1 codegen: deterministic, dependency-free,
   jury-reviewable. Generated `switch` logic per machine.
2. AST/code-builder generation (rejected): harder to review, overkill for
   tables + switches, new failure modes.
3. Extend v1 `codegen.generate` in place (rejected): risks v1 pipeline
   regressions; v1 is frozen while the target proof is pending.

## Components

- `host/genesis_rt/codegen_v2.py`: `c_ident()`, `generate_v2(v2, out_dir,
  genesis_src)` → renders `genesis_machine_gen.{h,c}` + v1-style config and
  makefile (freshness = min over sensors, documented) + manifest.
- `templates/genesis_machine_gen.{h.tmpl,c.tmpl}`: state/event enums,
  `genesis_machine_can_transition()`, command bounds tables +
  `genesis_machine_cmd_*()` accessors, telemetry map, fault-response
  table + `genesis_machine_fault_response()`.
- `target/qnx8/host_tests/machine_vector.c`: stdin-driven harness
  (transition/command/fault queries) for host behavioral tests.
- Tests: `tests/unit/test_codegen_v2.py` (snapshot, differentiation,
  collision), `tests/integration/test_codegen_v2_behavior.py` (host cc
  build + IR-derived vectors), `tests/qnx/test_qnx_build_v2.py` (qcc).

## Data flow

v2 IR (validated) → `generate_v2` → gen dir → (a) host cc + harness →
behavioral asserts; (b) `make qnx` → native objects linked into
`genesis_guard` (compile proof, no call-site yet).

## Error handling

- C-identifier collision after `upper/-→_` + `GENESIS_M_` prefix →
  `ValueError` naming both v2 ids (fail-closed, tested).
- `generate_v2` re-validates via `validate_v2` (never trusts callers).
- Harness build warnings fail the test; `qcc` warnings counted, must be 0.

## Testing

Per plan Task 2–4. Vectors derived FROM the v2 IR in-test (never a
hardcoded copy of template output). v1 pipeline untouched and green.

## Self-review

- No placeholders; all names and files fixed above.
- Consistent: v1 frozen, v2 additive; no guard behavior change.
- Scope: host slice only; target demo + guard call-site deferred and
  recorded in PROGRESS (not silently dropped).
- Ambiguity resolved: freshness=min(sensors); harness input is
  line-oriented text like `guard_vector` (`T <from> <to> <event>`,
  `C <cmd> <field> <value>`, `F <fault>`).
