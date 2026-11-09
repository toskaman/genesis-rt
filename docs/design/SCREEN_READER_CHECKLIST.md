# Screen-reader checklist — Studio (NOT YET EXECUTED)

Status: **prepared, not performed.** No NVDA/JAWS/VoiceOver session has
been run. Do not cite this file as evidence of a completed
screen-reader pass.

## Setup

- Build: record exact commit SHA + Studio page under test.
- Screen reader: NVDA (Windows) or VoiceOver (macOS) + browser + versions.
- Theme: run once in dark, once in light. Motion: OS reduce-motion ON.

## Per-page pass (all 13 Studio pages)

1. Landmarks: exactly one `main`, nav labelled, header/footer found once.
2. Page title announced and unique per page.
3. Headings form a logical outline (no skipped levels for structure).
4. Skip link is first Tab stop and moves focus to main content.
5. All interactive controls have accessible names (no "button", "edit" w/o label).
6. File inputs announce purpose (`aria-label` present).
7. Tables: headers announced for data cells incl. the proof table corner cell.
8. Tabs (sidebar): arrow keys move, selection announced, panels labelled.
9. Long jobs: start/progress/complete announced via live region, no spam.
10. Errors: announced assertively, focus moves to or near the error text.
11. Evidence Graph: list/tree alternative conveys the same trust facts
    (ARCHIVED vs LIVE, qnx_verified, digests) without the canvas.
12. Digital Twin canvas: adjacent text tables convey state; canvas has
    a text alternative label.
13. Dialogs (if any): focus trapped while open, restored to trigger on close.
14. 200 % zoom: no clipped announcements, no unreachable controls.

## Verdict recording

For each page: PASS / FAIL + reader + version + date + tester.
Any FAIL blocks a WCAG-conformance claim for that page.
File the completed sheet under `docs/design/SCREEN_READER_RESULTS.md`
(separate file; this checklist stays the blank protocol).
