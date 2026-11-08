# Omega3 UX review (P1b, 8 Nov 2026)

Commit: `titan-omega3` P1b (after `1eb8722`).
Method: served the real backend (`genesis_rt.api` + uvicorn,
tmp artifact store) and walked all 13 Studio tabs in headless
Chromium at 1366 px and 390 px viewports; collected pageerrors
+ console errors/warnings (zero on both widths); recorded the
first 12 keyboard tab stops on the overview (skip link →
tabs → theme → primary CTAs, sane order, visible focus).
Recon screenshots: throwaway, `/tmp/studio-p1b-*` (before)
and `/tmp/studio-p1b-ok66hjjw` (after); not committed.

## Persona A — newcomer (software, no QNX)

- Overview answers what/why in one screen; the guided demo
  is the obvious first action. Good.
- Machine Designer opens empty ("No IR loaded", three
  pickers): the first action is guessable but not guided.
  NOT fixed in P1b: preloading an example changes shared
  state semantics and needs a wider test pass; recorded as
  future work.
- Judge stage A said "The virtual industrial cell" while the
  stage opens the AMR example. FIXED (see below).

## Persona B — embedded engineer (QNX, IPC, codegen)

- Target Runner states are unmistakable (Ready/SDK+QEMU
  detected vs "No target op yet"/"Not loaded"); no simulated
  success is shown as native. Good.
- Trust tags (Native / Host only / Archived / Live) are used
  consistently. Good.
- Flagship overview proof cited only the W11 packs while the
  canonical current-source evidence is the Omega2 pair
  (schema-v2 machine). A reviewer asking "is this current?"
  had no first-screen answer. FIXED (see below).
- Evidence Graph is honest (empty states, tamper refusal
  explained) but form-heavy. NOT redesigned in P1b: every
  displayed relationship is real backend state, and a visual
  redesign without new backend affordances would be
  decoration. Scoped content over decoration.

## Persona C — buyer (adoption, trust, workflow fit)

- The first screen proves independent replay ("Verify
  offline, no QNX SDK needed") with copy-paste commands.
  Strong.
- Same gap as persona B: no visible current-source proof.
  FIXED (see below).
- No pricing/licensing trap: Apache-2.0 is stated in the
  docs; Studio makes no support/SLA claim. Good.

## Fixes implemented (scoped, both content-only)

1. Overview: a "Current-source packs" strip under the W11
   verify command, naming
   `evidence/qnx8-x86_64-omega2-before` →
   `evidence/qnx8-x86_64-omega2-after` (same 16/16 native
   matrix, schema-v2 machine) with its own verify command.
   The command was executed: VERIFY OK, 16/16,
   qnx_verified=True. The W11 behavioral cards stay: they
   are genuine archived evidence with a negative control
   the Omega2 pair does not restate.
2. Judge stage A copy: "The virtual industrial cell" →
   "The virtual AMR", matching the `amr-demo` example the
   stage actually opens (`judgeGotoDesignerWithExample`
   selects `amr-demo|`; stage C/D jobs POST the same IR).

Regression test (Playwright, real backend):
`tests/e2e/test_judge_browser.py::test_overview_current_source_and_stage_a_copy`
— asserts the Omega2 paths + kept flagship header on the
overview, "The virtual AMR" on the judge tab, and no
"industrial cell" anywhere on it. Green: 1 passed, 3.54 s.

## Verification

- New test green (above); console/page/HTTP error hooks in
  the `page` fixture fail on any browser error.
- After-screenshots (13 tabs × 2 widths): zero pageerrors,
  zero console errors/warnings; mobile overview stacks
  without overflow; 320 px reflow stays covered by
  `test_reflow_320px_every_tab` in the suite.
- Full-suite result: see the P1b commit message (counts
  1328 → 1329 with the new E2E test).

## Limitations (disclosed, not fixed)

- No real screen-reader pass (NVDA/JAWS/VoiceOver
  unavailable on this machine). Keyboard order, labels,
  focus visibility and the axe-based scans (where
  installed) were verified; full WCAG 2.2 AA conformance
  is NOT claimed.
- No human usability timing: see `HUMAN USER BENEFIT NOT
  YET MEASURED` (`docs/ascension/IMPACT_STUDY.md`).
