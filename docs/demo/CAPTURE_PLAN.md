# Demo capture plan (all shots authentic, Studio-first)

Source: Wave 10 §10 storyboard. Record at 1920x1080 against a live
backend (`PYTHONPATH=host python -m genesis_rt.cli serve`). The
scripted capture harness is `/tmp/record.py` (Playwright, real
server, real ops, real jobs — no staged DOM); raw clip
`footage/raw-studio-2026-11-05.webm` (42 s, 3.5 MB) already covers
shots 1, 5, and 7 end-to-end.

## Shot list

| # | Time | Shot (exact steps) | Expected authentic outcome |
|---|---|---|---|
| 1 | 0:00–0:12 | Judge tab → stage A “The machine” | Guided tour, LIVE badge, IR source shown |
| 2 | 0:12–0:30 | Designer tab: open `examples/amr-demo/machine-ir.json`, limits visible | Readable contract + safety limits |
| 3 | 0:30–0:52 | Source tab: generated C + `target/qnx8` tree; scroll guard IPC code | Real generated sources |
| 4 | 0:52–1:15 | Target tab: open `op-0350e9bd4818`, phase checklist + release panel | COMPLETED, 16/16, PASS, replay clean |
| 5 | 1:15–1:38 | Judge stage C action → fault job `stale_proximity_150ms` runs in Pipeline | Real job, DENY + safe-stop in trace |
| 6 | 1:38–2:00 | Evidence tab: graph node → linked check → requirement | Failure traced to requirement |
| 7 | 2:00–2:25 | Target tab compare: before `op-0350e9bd4818` vs after `op-df9b3668e5f7` | PASS→FAIL, 16/16→15/16, `limits_differ` |
| 8 | 2:25–2:43 | Passport tab: open BEFORE passport + dossier `VERIFY.md` replay steps | Chain replays clean; tamper note shown |
| 9 | 2:43–2:55 | Judge stage G: release eligibility + dossier export link | Value close, export visible |

## Capture status (5 Nov 2026)

- DONE (in `footage/`): shots 1, 4, 5, 7 — one continuous 42 s take,
  frame-verified (judge tour, real fault job start, BEFORE decision,
  BEFORE/AFTER compare).
- TODO (same harness, owner or next run): close-ups for shots 2, 3,
  6, 8, 9; terminal insert for `verify.py` + tamper rejection.
- Voice track: NOT RECORDED — no authorized TTS/voice option on this
  box. Narration script + timed subtitles are ready for the owner.
- Final edit + YouTube upload: OWNER HANDOFF (needs account + voice).

## Rules (binding)

- No mockups, no precomputed PASS, no hardware claims. QEMU is
  labeled “QNX 8.0 under QEMU” wherever it appears.
- Host simulation vs native target is labeled on screen per shot.
- If a step cannot run live, show the closest real run and label it.
