# Timed demo beats (OMEGA6 F2, rehearsed 9 Nov 2026)

Demo beats, rehearsed
against the BUILT product (real CLI, real browser, real
pipelines — never mocks). All timings: Windows, Python
3.14, host-only, this box.

| beat | budget | measured | evidence |
|---|---|---|---|
| 15 s hook — landing hero + "the wrong binary cannot pass" | 15 s | ~1 s page serve + read | Studio Overview serves locally (every E2E `goto` + `networkidle`) |
| 30 s WOW — stale-refusal verdict | 30 s | 0.0 s | `python scripts/demo_stale_refusal.py` → STALE, exit 0 |
| 60 s proof — K1 browser Prove click → card | 60 s | 5.7 s wall | `test_prove_click_renders_verdict_card` (server boot + 2 pipelines incl.) |
| 90 s proof — CLI `verify-change` FAIL→PASS | 90 s | 2.4 s | `genesis-rt verify-change --before …-broken … --after …` |
| full — Judge journey A→G, 2 live jobs | — | 8.5 s | `tests/e2e/test_judge_browser.py`, 3 passed |

Notes:

- Every budget has ≥6× headroom on this box; ±30%
  machine variance (per `REPRODUCE.md`) keeps all beats green.
- The 30 s WOW is the host digest-level refusal
  (`external-check` STALE). The native behavioral refusal
  (14/16 on `estop_target` + `v2_transitions`) is
  QEMU-only and shown from committed packs (rung 2),
  labeled archived — never faked live.
- Total live-demo floor (hook + WOW + browser proof):
  under 10 s of product time; the rest is narration.
