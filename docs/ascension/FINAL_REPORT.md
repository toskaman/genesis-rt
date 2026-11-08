# Ascension — final report (7 Nov 2026)

Branch `ascension` → merged as **PR #10** into `main` (`5bb2fc4`).
No video work; Devpost not submitted.

## What changed

**Design.** Studio is now an application: sidebar with Start / Build /
Verify / Evidence / Explore, a dedicated Overview (headline, three proof
cards — BEFORE DENY, AFTER ALLOW, stale binary REJECTED — with an
Archived label, workflow, status vocabulary), breadcrumbs, `#/page` deep
links with back/forward, mobile menu, one-line intro on every page,
titles that match navigation, a target-readiness line, new palette with
measured contrast and ≥ 3:1 control borders. Before/after screenshots:
`docs/ascension/screens/`, review: `docs/design/VISUAL_REDESIGN_REVIEW.md`.

**Accessibility.** axe-core WCAG 2.2 A/AA: 0 serious/critical on 13
pages × 2 themes (CI). New browser tests: 320 px reflow, 200 %/400 %
zoom emulated by CSS-pixel viewports, vertical arrow keys, history. **No
screen-reader session** (none available here).

**QNX.** The earlier "qcc builds are not byte-reproducible" was wrong:
all 18 published binaries of the three packs rebuild bit-for-bit from
their commits (`scripts/qnx_rebuild_check.py`, one Windows host); the
BEFORE→AFTER contract change appears in exactly the 3 binaries that
compile in the limits. Native CI remains build-only (no runner) —
`docs/ascension/NATIVE_CI_STATUS.md`.

**AI.** 98-case holdout + 2 models (qwen2.5:7b, llama3.1:8b) on a
throwaway CPU VM: qwen 87/98, llama 81/98, offline 74/98; 11–17
accepted-should-refuse at run time, all bounded and simulation-only.
Deterministic fixes for the measured gaps, then 6 false refusals found by
an independent review fixed too. Post-fix model run not done.
`docs/ascension/AI_EVALUATION.md`.

**Impact.** `HUMAN USER BENEFIT NOT YET MEASURED`. New
`bench/productivity/pilot_timer.py` makes an owner-operated or external
session a 2 × 45-minute job. `docs/ascension/IMPACT_STUDY.md`.

**Docs.** Test-count vocabulary (collected vs passed vs skipped) and the
E2E count fixed with a consistency test; scorecard shows the current
assessment first, history below.

## Scorecard

| Criterion | Start | Now | Gap to 10 |
|---|---|---|---|
| Technological Implementation | 9 | 9 | native CI runner; second build host; non-TCG timing |
| Design | 7 | 7.5 | designer / evidence graph / target runner depth; screen-reader session |
| Potential Impact | 5 | 5 | any human measurement |
| Innovation & AI | 8 | 8 | post-fix model run; third-party holdout |

## Verdict

**`SUBSTANTIAL IMPROVEMENT — FURTHER EVIDENCE REQUIRED`**

Software: `SOFTWARE_READY_WITH_LIMITATIONS`. Submission:
`SUBMISSION_PENDING_DEFERRED_VIDEO`.
