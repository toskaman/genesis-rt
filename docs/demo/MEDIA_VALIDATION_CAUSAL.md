# Media validation — causal hero + brag cuts (2026-11-10)

> WITHDRAWN 2026-11-10: both validated files were removed from the tree for an
> owner remake. Durations, hashes and pipeline notes below are a dated
> historical record, not a claim that the files ship.

Two new cuts were produced from real Studio footage (Playwright driving the live
`genesis_rt` API; the H run executes the real causal endpoint). Upload to YouTube
and Devpost submission remain OWNER-ONLY and DEFERRED.

## Files

| File | Duration (s) | SHA-256 |
|---|---|---|
| `docs/demo/genesis-rt-causal-hero.mp4` | 64.16 | `C5022619C5E82F915482A98EB49CF783061FFEEC113E721D64CB9BF20F4B59DC` |
| `docs/demo/genesis-rt-brag.mp4` | 20.766667 | `6548BE78C973F4D1628D841471BEC3A3F1D04B2F871928050431230B29EEB0C2` |

- Hero: 1920x1080p25, Kokoro-82M narration (am_adam, en-us, 44.288 s, see
  `narration-causal-hero.txt`), burned captions (`subtitles-causal-hero.srt`,
  17 cues, word-proportional timing ±0.5 s, not forced alignment).
- Hero edit: cold open on verdicts + journey at x1.5 (disclosed) + realtime hold.
- Brag: 1080x1920, 20.77 s, hyperframes render; `hyperframes check` passed
  (layout 9 samples, motion 0, contrast 12/12 WCAG AA, craft 0, audio 0).
- Music (brag only): "Happy Beats / Business Moves Vol. 10" by Sascha Ende
  (ende.app), CC BY 4.0, commercial + YouTube use allowed, credited.
- Posters: `poster-causal-hero.jpg` (hero frame), `poster-brag.jpg` (brag frame 0).

## Honesty record

- All pixels are real product output. No staged UI, no mock verdicts.
- The in-frame "archived grounding" label is preserved; no copy claims a live
  QNX target run.
- SFX omitted (restraint); audio-reactive skipped (helper not wired). Full
  provenance: `docs/demo/LEDGER_CAUSAL.md`.
- These cuts do NOT replace the W12 voiced cut as any "final" submission video:
  the final upload decision and Devpost filing stay with the owner (DEFERRED).
  Owner upload checklist: `docs/demo/PUBLICATION_HANDOFF_CAUSAL.md`.

Verify: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 <file>`
and `Get-FileHash <file> -Algorithm SHA256`.
