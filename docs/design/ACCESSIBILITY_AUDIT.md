# Accessibility audit — Studio (7 Nov 2026)

Target: WCAG 2.2 AA. **Status: automated scan clean + keyboard checks;
no manual screen-reader pass yet — full conformance is NOT claimed.**

## Automated (repeatable)

`tests/e2e/test_a11y_axe.py` (runs in host CI with axe-core 4.10.2):

- axe-core, tags `wcag2a wcag2aa wcag21a wcag21aa wcag22aa`, every one of
  the 12 Studio tabs, **dark and light** themes: 0 serious/critical.
- Manual one-off run including `best-practice` and all impact levels:
  0 violations.
- 320 CSS px viewport, every tab: no page-level horizontal scroll
  (WCAG 1.4.10).
- Existing E2E: 390/768/1366 viewport audits, zero console errors.

## Found and fixed in this pass

| Criterion | Finding | Fix |
|---|---|---|
| 1.4.3 Contrast | selected tab text `#e6edf3` on `#1f6feb` ≈ 4.0:1 | selected tab uses `--on-accent` (#fff, ≥4.5:1) |
| 1.3.1 / 4.1.2 Labels | 4 file inputs had no accessible name (`#srcfiles`, `#ppfile`, `#diffile-a/b`) | `aria-label` added |
| 1.4.10 Reflow | proof table overflowed by 27 px at 320 px | table scrolls inside itself on narrow screens |
| Landmarks (best practice) | header content outside any landmark | `<header>` + `<nav>` + `<main>` |
| Empty header cell | proof table corner `<th>` empty | visually hidden "Property" |
| 2.4.1 Bypass | (earlier pass) | skip link |
| 2.1.1 Keyboard / tabs pattern | (earlier pass) | roving tabindex, Arrow/Home/End, `aria-controls` |

## Manual checks performed

- Keyboard: Tab reaches the skip link first; tablist arrows/Home/End
  move and activate; focus ring visible in both themes (Playwright).
- Visual review of light/dark screenshots at 1440 px and 390 px.

## Not yet done (limitations)

- No NVDA/JAWS/VoiceOver session; live-region wording for long jobs is
  unreviewed by a screen-reader user.
- Canvas-based Digital Twin has text tables beside it but the canvas
  itself is not described element-by-element.
- 200 %/400 % browser zoom was checked via the 320 px reflow proxy only.
