# Demo video plan (target 2:40–2:55, hard cap < 3:00)

Record only genuine runs. Studio-first shot list (the CLI-only cut is
retired: pipelines and target ops run from Studio Live since Wave 7/8):

| Time | Shot (screen capture) | Narration |
|---|---|---|
| 0:00–0:15 | Studio: open AMR cell project, IR contract + safety limits | "A machine contract you can read — and the tooling rejects invalid specs." |
| 0:15–0:40 | Studio: run pipeline (SSE progress) → generated QNX C sources | "One click: deterministic codegen, same contract, byte-identical QNX build files." |
| 0:40–1:10 | Studio Target tab: phase checklist → 16/16 matrix PASS on QNX 8.0 | "Native QNX 8.0 on a real target: guard, controller, supervision — verified, not asserted." |
| 1:10–1:40 | Studio: inject stale-sensor fault → DENY + safe-stop in trace | "We break it on purpose — the guard denies and the machine stops safe." |
| 1:40–2:10 | Counterexample Explorer + Evidence Graph on the failure | "The failure becomes a linked, inspectable counterexample — cause, not vibes." |
| 2:10–2:35 | Apply fix → rerun → PASS passport + independent replay | "Fix, rerun, prove: the passport and its replay say whether it worked." |
| 2:35–2:55 | Release eligibility + export dossier | "A reviewable evidence dossier — and an honest gate when proof is missing." |

Rules: public YouTube upload, no copyrighted audio, no mockups, editable
subtitles — if a step is not yet recorded on target, show the host run
and label it honestly.

Wave 10 assets (all in `docs/demo/`): `CAPTURE_PLAN.md` (shot list +
status), `NARRATION.md`, `subtitles.srt` (timed, editable),
`SHOT_EVIDENCE.md` (every claim → file/op/command), 3 verified
1080p screenshots, and `footage-raw-studio-2026-11-05.webm`
(42 s authentic take: judge A→C + real fault job + BEFORE
decision + BEFORE/AFTER compare). Voice track + final edit +
YouTube upload remain an owner handoff.
