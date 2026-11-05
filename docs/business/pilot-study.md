# GENESIS RT pilot kit (for 2–3 external engineering teams)

Status: protocol published, no pilot conducted yet. This kit is the
complete package a team needs to run a fair before/after evaluation.
No participants, testimonials, or savings figures exist — anything
added later must cite its dated raw data.

## 1. What the pilot measures

Whether an embedded team working on QNX-native controller software
completes representative verification chores faster and with fewer
escaped defects using GENESIS RT versus their current practice.

Primary outcomes (per task, both lanes):

- Wall-clock task time (operator-measured, start/stop timestamps).
- Command count (shell history) + manual steps (checklist below).
- Fault found? (yes/no + which injected fault).
- Evidence produced? (passport / dossier path, or "none").
- Operator confidence 1–5 (survey §5).

Explicitly NOT measured: hour-dollar savings, headcount effects,
certification credit.

## 2. Representative task set (90–120 min per lane)

Same tasks as `bench/productivity/` (methodology + REPORT.json),
performed by a human in each lane:

1. `validate` — accept/reject 3 machine contracts (1 has an
   unknown key, 1 violates a limit).
2. `generate` — produce build files for the AMR IR; confirm the
   guard limit in the generated header.
3. `campaign` — run the 8-scenario fault campaign; state the
   verdict per scenario.
4. `evidence` — hand a reviewer a package that proves the
   campaign verdict; the reviewer must verify without asking
   the operator anything.
5. `compare` — given two run dirs (limit 0.5 → 0.05), state
   exactly what changed and whether release is still OK.
6. `regression` — reproduce the stale-proximity failure on the
   tight-limit IR, apply the provided fix, confirm green.

Reference lane = the team's current practice (their editors,
scripts, CI). Genesis lane = this repo's CLI/Studio. Task order
is randomized per operator (coin flip: genesis-first or ref-first).

## 3. Baseline measurement template (reference lane)

Copy per task:

```
task:            validate | generate | campaign | evidence | compare | regression
operator:        <initials>          date: <UTC>
lane:            reference           started_utc: <ISO>
tools used:      <editors/scripts/commands, from history>
finished_utc:    <ISO>               interruptions_min: <n>
commands_run:    <n from history>
manual_steps:    <n + one line each>
fault_found:     yes <id> / no
evidence_path:   <path or NONE>
reviewer_check:  <reviewer initials + PASS/FAIL + minutes spent>
notes:           <anything surprising>
```

## 4. GENESIS measurement template

Same fields as §3, plus:

```
genesis_cmds:    <the exact CLI commands or Studio buttons used>
run_or_op_id:    <run-… / op-…>
passport_path:   <artifacts/…/passport.json>
passport_sha256: <first 16 hex>
gate_verdict:    <PASS/FAIL>   level: <…>   qnx_verified: <true/false>
replay_result:   <PASS/FAIL + command used>
```

## 5. Feedback survey (5 min, after both lanes)

1. Which lane made the verdict easier to trust? Why (1–2 lines)?
2. Where did you feel least sure of correctness (task + lane)?
3. What was the most tedious step in each lane?
4. Did any tool output mislead you? Paste it.
5. Confidence the evidence package is complete: 1–5 per lane.
6. Would you run your next controller change through the
   genesis lane? (yes / no / with changes: …)

## 6. Privacy guidance

- No source code leaves the team: all runs are local.
- Share only the filled templates (§3–§5), the `REPORT.json`
  files, and passport JSON files (they contain no credentials).
- Redact operator names to initials before sharing.
- QNX SDP binaries, images, and license files are never shared.

## 7. Technical limitations (read before starting)

- QNX-native steps need an SDP 8.0 + QEMU target (§10 record:
  `docs/audits/TASK4_FORMAL_CAMPAIGN.md`); without them the
  genesis lane is host-only and `qnx_verified` stays false.
- The bundled reference lane in `bench/productivity/` is
  synthetic; human teams use their own real practice instead.
- Machine scenarios are virtual; no physical actuation exists.
- Single local operator; no team/CI workflow yet.

## 8. Reproduction scripts

- Machine benchmark: `PYTHONPATH=host python -m genesis_rt.cli
  bench --out bench/productivity/last-run` (see METHODOLOGY.md).
- Task IRs: `examples/{amr-demo,conveyor-demo,cell-demo}/`.
- Injected faults per task: `bench/productivity/REPORT.json`
  (`fault` fields) — reuse verbatim for comparability.
