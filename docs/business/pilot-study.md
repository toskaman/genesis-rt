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

## 6. Privacy guidance + anonymization protocol

Before sharing anything outside your team, apply all four steps:

1. Replace operator/reviewer names with initials (§3–§5 fields).
2. Strip hostnames, usernames, and absolute paths from pasted
   shell history (keep command names + flags).
3. Confirm no target passwords, SSH keys, SDP license files, or
   target images are inside the bundle (`grep -ri` for
   `password`, `secret`, `BEGIN.*PRIVATE` over the shared files).
4. Share only: filled templates (§§3–5, 10), `REPORT.json`
   files, and passport JSON files (they contain no credentials).

Standing rules: all runs are local, no source code leaves the
team, and QNX SDP binaries/images/license files are never shared.

## 7. Technical limitations (read before starting)

- QNX-native steps need an SDP 8.0 + QEMU target (current
  record: `evidence/qnx8-x86_64-verified-b22cea1/` +
  `docs/audits/WAVE10_BASELINE.md`); without them the genesis
  lane is host-only and `qnx_verified` stays false.
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

## 9. Technical invitation (copy/paste to a candidate team)

> Subject: pilot invitation — GENESIS RT evidence-driven QNX
> workflow (two half-days)
>
> We are looking for 2–3 embedded teams to trial GENESIS RT
> (Apache-2.0, local-only, no data leaves your machines) on six
> representative verification chores (§2): once with your current
> practice and once with GENESIS RT (randomized order, ~90–120
> min per lane). You keep the filled measurement templates, the
> evidence passports/dossiers, and the benchmark REPORT.json.
> We ask for the anonymized templates + survey (§§3–6, 10) and
> a 30-min debrief. No source code, SDK material, or names are
> shared (anonymization protocol, §6). No payment, no obligation
> to adopt anything; all tooling stays open-source. Interested?
> Reply with your QNX/SDP setup (or "host-only") and two
> candidate half-days.

Status: draft — zero invitations sent so far.

## 10. Reviewer checklist (for the `evidence` task, both lanes)

The reviewer receives ONLY the evidence package — no side
channel with the operator — and records PASS/FAIL per line
plus minutes spent:

1. [ ] I can state the campaign verdict (PASS/FAIL) from the package alone.
2. [ ] I can name every scenario covered and spot any missing one.
3. [ ] I can re-run the verification independently (paste the command).
4. [ ] I can tell which IR revision + binary the verdict binds to.
5. [ ] I can detect a 1-byte tamper (apply it, re-verify, show refusal).
6. [ ] Minutes spent: ___; blocking questions for the operator: ___.

Reference lane: replace 3–5 with "what I had to reconstruct by hand".
