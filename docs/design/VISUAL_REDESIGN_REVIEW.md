# Visual redesign review (Ascension, 7 Nov 2026)

Captured with Playwright Chromium (headless), from a local
`genesis_rt.cli serve`. "Before" = `400da70` (PR #9). "After" = this
branch. Files in `docs/ascension/screens/` (`<state>-<theme>-<width>.png`;
`-designer/-target/-evidence/-diff` = that page at 1440×900, dark setting).
Note: headless Chromium reports a light OS preference, so the "dark"
captures of pages opened without the saved preference render light.

| Issue in "before" | Change in "after" |
|---|---|
| Hero + BEFORE/AFTER table repeated above **every** page; the work area started half-way down | Dedicated Overview page; every other page starts at the top of the work area |
| 13 nav buttons in two wrapped rows | Sidebar with 5 labelled groups, persistent active state, breadcrumb |
| 64 rem max width wasted desktop space | Work area up to 88 rem, prose capped at 78 ch |
| Proof as a dense table | Three proof cards: Before DENY, After ALLOW, stale binary REJECTED; ARCHIVED label |
| Page titles ≠ nav labels ("Proof passport", "Broken vs fixed", "Run the pipeline" under "Run results") | Titles match nav; CLI page renamed and moved to Explore |
| Several pages without any orientation text | One-line intro on each page: what, what to do, what next |
| Dark control borders 1.6:1 | Dedicated control-border token ≥ 3:1 (WCAG 1.4.11) |

Not yet redesigned in depth: Machine designer layout (still a form over
a JSON textarea), Target runner result hierarchy, Evidence graph
search/filters, Digital twin controls. These are the next design items.

## After the independent review (same day)

| Reviewer finding | Fix |
|---|---|
| "Run on target" looks available with no SDK/QEMU | readiness line beside it (`Not ready: QNX SDK and QEMU not found …`); the button still explains on click (existing tested behaviour) |
| Mobile: 14-link nav cloud above the content | collapsed behind a `Menu` button (`aria-expanded`), closes after choosing a page |
| Sidebar status was a 5-line sentence | two short lines |
| verify command wrapped inside prose; truncated "rerun" label | copyable code block; explicit "Re-executed from scratch" label |
| empty selects ~40 px wide | `min-width: 8rem` |
| Designer, Evidence graph still form dumps | **open** — next design item |
