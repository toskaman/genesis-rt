# Ledger — GENESIS RT brag run 2026-11-10

> WITHDRAWN 2026-11-10: listed video artifacts were removed from the tree for
> an owner remake. This ledger stays as the provenance record of the run.

## Artifacts
- `brag.mp4` — discovery cut, 1080x1920, 20.77s, hyperframes render (check passed:
  layout 9 samples, motion 0, contrast 12/12 WCAG AA, craft 0, audio 0).
- `genesis-rt-hero.mp4` — commissioned hero film, 1920x1080, 64.16s, Kokoro
  narration (am_adam, 44.3s), burned captions (hero.srt, 17 cues).
- `features/judge-{run,verdict,proof}.mp4` — 3 consecutive vertical cuts of the
  same 22s capture (x=290 framing on verdict zone, verified by bbox probe).
- `footage/studio/studio-judge-H-estop.webm` — master 22s, 1920x1080p25, live
  backend, errors:none. `footage/studio-slow/studio-judge-full-slow.webm` — 86s
  slow master for the hero cut.
- `poster.jpg` (hero), `brag-poster.jpg` (frame 0 of brag.mp4).

## Tech notes (honesty record)
- All pixels are real product output: Playwright drives the actual Studio +
  genesis_rt API; the H run executes the real causal endpoint (POST
  /causal/dossiers, estop flagship). No staged UI, no mock verdicts.
- Hero cut: cold open on verdicts + journey at x1.5 + realtime hold. Speed ramp
  disclosed; no content reordered within the run.
- SRT timings are word-proportional estimates, not forced alignment (±0.5s).
- In-frame "archived grounding" label preserved; copy never claims live QNX target.
- Music: "Happy Beats / Business Moves Vol. 10" by Sascha Ende (ende.app),
  CC BY 4.0, commercial + YouTube use allowed. Attribution voluntary per author;
  credited here and in share copy anyway.
- Narration: Kokoro-82M local via `hyperframes tts`, voice am_adam, en-us.
- Studio appears in light theme (headless default); product also ships dark.
- SFX omitted (restraint); audio-reactive skipped (helper not wired) — both
  documented in composition-brief.md.
- Skills loaded this run: brag, hyperframes-core (+minimal/trim refs). Animation,
  creative, keyframes, cli domain skills not loaded; composition uses only
  core-contract features and passed `hyperframes check`.

## Provenance
- Capture scripts: `capture_studio.py`, `capture_studio_slow.py` (workspace root).
- Composition: `composition/index.html` (standalone, monolithic).
- Check report: `composition/.hyperframes/artifacts/checks/745bfc67-*.json`.
