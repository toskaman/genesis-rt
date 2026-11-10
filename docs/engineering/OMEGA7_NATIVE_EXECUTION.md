# OMEGA7 Native Execution — Archived vs Live

## Archived grounding (default, measured)

For each hypothesis with a `native_check`, the slice pins the
committed Omega2 transcript `target-<check>.log` by sha256 and
records `{mode: archived, status: present|absent}`. Absent files
and check-less mechanisms (jam, stale-sensor) are recorded
honestly — never synthesized, never skipped silently.

Flagship grounding: `target-estop_target.log` shows PROBE
DENY/ESTOP state=3, `/dev/genesis/status` state=3
last_reason=ESTOP, operator SIGUSR1 reset, post-reset ALLOW —
inside committed matrix step `estop_target` (16/16 PASS pack).

## Live grounding (implemented, NOT executed here)

`target=live` starts a TargetRunner `verify-only` op, polls to a
terminal state with a bounded timeout (default 900 s), cancels on
timeout, and records `{mode: live, status, op_id, state,
artifacts}`. Statuses: completed / op-failed / timeout /
start-failed / unknown. Covered by scripted fake-runner tests
only; no QEMU session exists in this environment, so no live
claim is made. Owner handoff: run with a booted image and record
the op id + transcript refs before citing live evidence.

## Label discipline (enforced in data, shown in UI)

Every experiment carries `native_grounding.mode`; the Judge H
render prints it next to the seal. Dossier text, CLI cards, and
API responses never say "native" without the archived/live
qualifier. QEMU timing is not a hardware guarantee
(unchanged platform limitation).
