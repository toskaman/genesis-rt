# Machine IR v1

Typed intermediate representation: the contract between intent and codegen.
Schema: `schemas/machine-ir-v1.schema.json`. Validator: `host/genesis_rt/ir.py`.

## Sections

- `machine`: id, kind (`differential_drive_robot` | `conveyor` |
  `robotic_arm_virtual`), `execution_target` (must be `qnx8_x86_64_qemu`),
  `simulation_only` (must be `true` in the MVP). Caveat: the arm kind
  has no arm kinematics — the release gate quarantines its campaigns
  (see `limitations-and-safety.md` #10), so no arm PASS reads as
  arm verification.
- `actuators`: 1–16 `{id, type}` from a fixed type list.
- `sensors`: 1–32 `{id, type, freshness_limit_ms}`; the guard enforces the
  strictest freshness limit.
- `control`: `period_ms` 1–1000, linear (0,10] m/s, angular (0,20] rad/s,
  `guarded_state_transitions: true`.
- `safety_contracts`: 1–64 `{name, if, then}` where `if`/`then` are
  identifiers from a strict whitelist — never expressions, never code.
- `verification.scenarios`: 1–32 scenario IDs from the fixed catalog.

## Whitelists

`if`: `proximity_is_stale`, `speed_exceeds_limit`, `simulator_disconnected`,
`command_overdue`, `sequence_regressed`, `message_malformed`, `device_fault`.

`then`: `command_virtual_stop`, `reject_command`, `enter_safe_state`,
`hold_last_valid`, `raise_telemetry_alarm`.

Scenarios: `nominal_navigation`, `speed_command_over_limit`,
`stale_proximity_150ms`, `planner_process_crash`, `delayed_command`,
`dropped_message`, `corrupted_message`, `simulator_disconnect`.

## Rules

- Unknown keys anywhere → reject. Unknown enum → reject. Out-of-range
  number → reject. The validator never guesses or coerces.
- Normalization: scenarios/contracts/actuators/sensors sorted; this keeps
  codegen and evidence deterministic regardless of file key order.
- `guard_limits()` extracts the single numeric limit set shared by the
  Python policy mirror, the C policy and codegen — one source of truth.
