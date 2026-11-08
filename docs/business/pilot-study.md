# GENESIS RT pilot kit (for 2–3 external engineering teams)

Status: protocol published, no pilot conducted yet. This kit is the
complete package a team needs to run a fair before/after evaluation.
No participants, testimonials, or savings figures exist — anything
added later must cite its dated raw data.

Companion files: `pilot-onboarding.md` (5-min start + recording
procedure), `pilot-consent.md` (consent + confidentiality),
`buyer-interview.md` (30-min interview guide),
`decision-maker-survey.md` (post-pilot survey),
`bench/productivity/pilot_timer.py` (session timer + lane-order
randomization), and `bench/productivity/analyze_pilot.py` (results
aggregation + CSV export).

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
performed by a human in each lane. Budget basis (8 Nov 2026
expert dry run, genesis lane): machine time ≈ 6 s/lane
(negligible); expert-operator floor ~40 min/lane excluding the
reviewer loop; the 90–120 min covers first-contact onboarding,
learning, template recording and the ~10–15 min reviewer
checklist (§10). The reviewer's minutes are recorded
separately (`reviewer_check`), never folded into operator time.

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

## 2.1 Quick tier (optional, 3 tasks, ~60–90 min total)

Added 8 Nov 2026 (Omega3 §6.2). A low-friction alternative to
the full six-task study for teams that cannot spare two
half-days. Tasks, in lane order:

1. `generate` — change a machine requirement and generate the
   corresponding software (§2 task 2).
2. `campaign` — execute the 8-scenario fault campaign
   (§2 task 3).
3. `evidence` — produce and independently verify the evidence
   package, including the 1-byte tamper check (§2 task 4,
   reviewer checklist §10).

Time basis (ESTIMATE, pending an owner dry run): the 8 Nov
2026 expert dry run floors these three tasks at ~21 min/lane
(T2 4 + T3 5 + T4 12 min), i.e. ~45 min for both lanes;
setup, onboarding and the survey add ~15–45 min. Budget
60–90 min total. Machine time is negligible (< 1 s/lane for
the host-only core, measured 8 Nov 2026).

Run it with the timer preset (exactly these three tasks, both
lanes, randomized order):

```sh
python bench/productivity/pilot_timer.py --team T1 --plan
python bench/productivity/pilot_timer.py --team T1 --lane genesis --quick --out bench/productivity/data/t1.jsonl
python bench/productivity/pilot_timer.py --team T1 --lane reference --quick --out bench/productivity/data/t1.jsonl
python bench/productivity/analyze_pilot.py bench/productivity/data/t1.jsonl
```

The analyzer reports `QUICK_PAIRED_PILOT` (limitations:
`quick-tier-only`, `n=2-teams-minimum` when applicable). A
quick pilot is NEVER equivalent to a completed six-task
study: neither a quick dataset, nor quick-plus-extra-tasks
data, can produce the `COMPLETE` label — only two
independent teams pairing all six tasks can. Owner-operated
quick runs are labelled `OWNER_ONLY_EXPLORATORY`.

Reference lane = the team's current practice (their editors,
scripts, CI). Genesis lane = this repo's CLI/Studio. Lane order
is randomized per operator (`pilot_timer.py --team T1 --plan
--seed <n> --plan-out session-T1.json`; the seed replays the
order — a coin flip is an acceptable substitute, noted in the
session file).

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

## 4.1 Machine record format (v2) + validity ladder

`bench/productivity/pilot_timer.py` converts §§3–4 answers into one
JSON line per (team, task, lane) for `analyze_pilot.py`. Required
machine fields beyond §§3–4: `team` (anonymous id; `OWNER*` =
owner-operated), `operator_kind` (owner/participant),
`started_utc`/`finished_utc` (ISO with timezone, ordered),
`abandoned` (true = attempted but not finished; counted separately,
never a completion), `consent` (participant rows require true —
declining records nothing).

A comparison is valid only over **paired** tasks: the same team
completing the same task in **both** lanes. The analyzer reports:

- `NO_HUMAN_DATA` — no rows at all (current state: no pilot run yet).
- `OWNER_ONLY_EXPLORATORY` — owner rows only; never independent proof.
- `INCOMPLETE_PAIRED_DATA` — participants exist but nothing is paired
  (e.g. two teams that each ran one lane).
- `PAIRED_PILOT_LIMITED` — some paired tasks, below the bar.
- `INDEPENDENT_PILOT_COMPLETE` — ≥2 participant teams with all six
  tasks paired.
- `generalization: INSUFFICIENT_FOR_GENERALIZATION` — always: a pilot
  sizes a future study, it never generalizes.

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
  record: `evidence/qnx8-x86_64-w11-before/` and
  `evidence/qnx8-x86_64-w11-after/`, 16/16 each; see
  `docs/audits/WAVE11_RELEASE.md`); without them the genesis
  lane is host-only and `qnx_verified` stays false.
- The bundled reference lane in `bench/productivity/` is
  synthetic; human teams use their own real practice instead.
- Machine scenarios are virtual; no physical actuation exists.
- Single local operator per lane; the CI/team workflow exists
  as a self-hosted reference (`docs/runner/SELF_HOSTED_RUNNER.md`,
  needs a licensed runner host) — not as a hosted service.
- Aggregate filled templates with
  `bench/productivity/analyze_pilot.py` (JSONL schema in its
  docstring); it refuses to compare samples below 2 teams.

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

Ready-to-send quick-tier variants (engineer + manager) and
target-community research: `pilot-outreach.md` (Omega3
§6.5). Also drafts — nothing sent.

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
