# Pilot onboarding (5 minutes)

You will do six everyday verification chores twice: once with your
normal tools (**reference** lane) and once with GENESIS RT (**genesis**
lane), about 90–120 minutes per lane. A 5-minute survey follows.
There are no wrong answers — abandoned tasks count as data.

## 1. Before you start (checklist)

- [ ] Read `docs/business/pilot-study.md` §§1–2 (what is measured, the
  six tasks) and `docs/business/pilot-consent.md` (consent terms).
- [ ] Know your setup: QNX SDP 8.0 + QEMU target, or host-only (both
  are fine; host-only keeps `qnx_verified` false).
- [ ] Pick your anonymous team id (the coordinator gives you one,
  e.g. `T1` — never use real names in data files).
- [ ] Get your lane order and save it:
  `python bench/productivity/pilot_timer.py --team T1 --plan --seed <n> --plan-out session-T1.json`
  (the seed replays the order; run the lanes in the printed order).
- [ ] Turn on shell-history capture (see §2) **before** the first task.

## 2. Recording procedure (both lanes, every task)

The timer walks you through each task and timestamps it:

```
python bench/productivity/pilot_timer.py --team T1 --lane reference --out data/T1.jsonl
python bench/productivity/pilot_timer.py --team T1 --lane genesis --out data/T1.jsonl
```

Rules:

1. Run the lanes in your planned order; do all six tasks per lane.
2. Start the clock, do the task, stop the clock. Interruptions:
   report the minutes when asked — do not subtract them yourself.
3. Count commands from shell history, not memory:
   - bash: `history -a; wc -l ~/.bash_history` before/after, or
     `HISTTIMEFORMAT='%F %T ' history > lane-task.txt`.
   - PowerShell: `Get-History | Export-Csv lane-task.csv`.
4. The `evidence` task needs a second person as reviewer: hand them
   ONLY the evidence package and time them with the reviewer
   checklist (`pilot-study.md` §10).
5. If you abandon a task, say so when asked — it is recorded as
   attempted, never as a completion, never silently dropped.
6. Notes field: one line about anything surprising. Paste misleading
   tool output here.

No screen recording is required. Do not paste secrets, hostnames, or
absolute paths into notes (see §4).

## 3. Consent

Participant rows require your explicit consent at record time: the
timer asks per task, and declining records nothing for that task.
You can stop the pilot at any time; already-recorded rows are deleted
on request to the coordinator.

## 4. What to send back

Apply the anonymization protocol (`pilot-study.md` §6), then send:

- `data/<TEAM>.jsonl` (append-only timer rows),
- `session-<TEAM>.json` (your lane-order plan),
- filled survey answers (`pilot-study.md` §5),
- reviewer checklist results (§10).

Keep your shell-history captures until the coordinator confirms the
aggregate — they resolve counting disputes. Never send source code,
SDK material, images, keys, or passwords.
