# TITAN wave 1 — readiness (7 Nov 2026)

Base `c0acdd3` (PR #4). Scope of this wave: honesty fixes found by
reproducing the brief's leads, the Studio design system (themes, tokens,
plain-language trust text) and an automated WCAG 2.2 scan in CI.
**No video work** (`submission/VIDEO_DEFERRED.md`).

## Leads from the brief — reproduced and resolved

| # | Lead | Reproduced? | Resolution |
|---|---|---|---|
| 1 | `qnx.yml` builds but advertises a target run | **Yes** (`name: qnx-target`, job `qnx-build-and-run`, no QEMU/verify step) | Renamed to `qnx-native-build`, stages numbered, explicit `Native target campaign: NOT EXECUTED` step; test `test_qnx_workflow_does_not_overclaim_target_run` |
| 2 | Native campaign not rerun | Yes | Still not rerun (QEMU needs hardware virtualization, currently off in the owner's BIOS). Committed BEFORE/AFTER packs re-verified. |
| 3 | W12 video presented as the final video | **Yes** (README, CLAIMS, scorecard) | All current-facing docs now say `DEFERRED BY OWNER`; test `test_video_status_deferred_everywhere` |
| 4 | Environment-dependent tests | Fixed in PR #4 (stdlib-verify test) | — |
| 5 | Limitations misdescribe RFC 1982 wrap | **Yes** ("documents the boundary instead") | Rewritten with code + test references and residual limits; test `test_limitations_match_rfc1982_implementation` |
| 6 | No WCAG 2.2 audit | Yes | axe-core scan in CI, fixes, `docs/design/ACCESSIBILITY_AUDIT.md` |
| 7 | Navigation / visuals | Partly | Token design system, light/dark/system theme, no-flash init, theme selector (`docs/design/DESIGN_SYSTEM.md`) |
| 8 | No external pilot | Yes | Unchanged; pilot kit exists (`docs/business/pilot-study.md`), zero participants |
| 9 | Planner is not an LLM | Yes | Unchanged and still disclosed |
| 10 | Native / host / archived labelling | Partly | Plain-language `trustSentence()` beside every `qnx_verified`/`release_eligible` display |

## Measured

| Check | Result |
|---|---|
| Full suite, Linux SDK-free (Py 3.13) | **1141 passed, 5 skipped** (1146 collected) |
| axe WCAG 2.2 A/AA, 12 tabs × 2 themes | 0 serious/critical; 0 at any level incl. best-practice (manual run) |
| 320 px reflow, 12 tabs | no horizontal page scroll |
| UI + browser E2E | green |

The Windows + QNX SDK run (1140/0 skips) belongs to PR #4; it was not
repeated for the three tests added here.

## Official rules re-check (fetched 7 Nov 2026)

Deadline 15 Dec 2026 2 pm EST; judging 15–29 Jan 2027; project must stay
testable until judging ends; one Overall + one Bonus + one Community
Choice max; build instructions must state QNX version, target (QEMU) and
toolchain (present: `docs/quickstart-qnx8-qemu.md`, qcc 12.2.0);
**license must be visible in the repo About section** — to confirm on
GitHub; **video must show the project running on the intended device**
(note for the deferred video: show the QEMU target, not only the host).

## Not done in this wave (honest)

Full IA rebuild into Machines / Build & Run / Verify / Evidence /
Explore pages, AI provider adapter, competitive re-research, 50-question
audit, jury simulation, fresh native campaign, screen-reader session.

## Verdicts

- Software: **`SOFTWARE_READY_WITH_LIMITATIONS`**
- Submission: **`SUBMISSION_PENDING_DEFERRED_VIDEO`**
