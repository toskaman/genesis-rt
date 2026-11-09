# Demo fallback ladder (OMEGA6 F1)

Live first; every rung below is rehearsed and honest about
what it is. Never present a lower rung as a higher one.

## Rung 0 — LIVE (preferred)

| moment | action | measured (9 Nov 2026) |
|---|---|---|
| hook | open Studio Overview, read the hero + stale line | page serves locally ~1 s |
| WOW | `python scripts/demo_stale_refusal.py` → STALE | 0.0 s (budget 30 s) |
| proof | Studio Before/After: pick IRs, press **Prove** → card | 5.7 s wall (budget 60 s) |
| proof (CLI) | `genesis-rt verify-change --before … --after …` | 2.4 s (budget 90 s) |
| full tour | Judge Mode stages A→G, 2 live host jobs | 8.5 s (E2E, 3 passed) |

Needs: this repo + Python + browser. No SDK, no QEMU, no
network (all localhost).

## Rung 1 — CACHED (backend down, files on disk)

- Pre-run `verdict.json`: run the CLI proof once before the
  demo, keep the file; `render_card_text` output is the card.
- Passport replay: `scripts/replay.py artifacts/runs/*/passport.json`
  → `chain: valid, gate: PASS` (0.1 s, no server).
- `ui/dashboard.html`: open the file, load the passport —
  every verdict re-verifies in the browser, zero install.
- Committed sample: `artifacts/samples/golden_demo_passport.example.json`.

## Rung 2 — ARCHIVED (nothing runs)

- Omega2 packs: `python evidence/qnx8-x86_64-omega2-after/verify.py
  evidence/qnx8-x86_64-omega2-after` → VERIFY OK (stdlib only).
- `REPRODUCE.md` timing table + `WHY_QNX.md`
  footprint table: numbers with method, no live run needed.
- Storyboard stills + committed screenshots (`docs/demo/*.png`).

## Degraded-path rehearsal (9 Nov 2026, performed)

Path: backend dies after the IRs load, presenter presses Prove.

- Rehearsal: `tests/e2e/test_prove_browser.py::test_prove_backend_dead_fails_honest`
  (kills its own uvicorn mid-flow, real Chromium) — GREEN.
- Observed: `#change-out` shows "Prove failed: …" (fetch
  error text, escaped); no card, no stale content, no
  console/page JS errors.
- Presenter line: "The backend is down, so there is no live
  verdict — note it says so instead of showing an old card.
  Falling back to rung 1:" then open the pre-run
  `verdict.json` / replay the passport from disk.
- Gap found: none blocking. The loading state ("Proving…")
  is transient (~2 s) and was asserted in code review, not
  trapped in the test — acceptable, the settled states are.
