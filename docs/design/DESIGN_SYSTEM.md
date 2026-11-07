# GENESIS Studio design system

Single file: all tokens live at the top of `ui/studio.html` (`:root`).
No framework, no build step: the Studio stays a self-contained page so
it works offline and from a fresh clone.

## Tokens

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#0b1017` | `#ffffff` | page |
| `--panel` | `#10161f` | `#f6f8fa` | sidebar |
| `--surface` / `--surface-2` | `#151c26` / `#1c2632` | `#f6f8fa` / `#eaeef2` | cards, selected nav item |
| `--border` | `#2c3949` | `#8c959f` | decorative separators only |
| `--control-border` | `#5b6c82` | `#6e7781` | inputs, selects, secondary buttons (≥ 3:1, WCAG 1.4.11) |
| `--fg` / `--mut` | `#f2f5f9` / `#a8b7c8` | `#1f2328` / `#57606a` | text / secondary text |
| `--accent` / `--on-accent` | `#2f6fbf` / `#fff` | `#0969da` / `#fff` | primary button fill (5.06:1 / 5.19:1) |
| `--accent-fg` | `#669cda` | `#0969da` | accent used as text or a line |
| `--ok` / `--bad` / `--warn` | `#50c6a6` / `#e87982` / `#e3b36a` | `#1a7f37` / `#cf222e` / `#9a6700` | verdicts — always paired with a word |
| `--focus` | `#8bb8ec` | `#0550ae` | `:focus-visible` ring |
| `--radius`, `--space-1..4`, `--font-ui`, `--font-mono`, `--motion` | | | shape, rhythm, type, motion |

## Themes

- Default follows the OS (`prefers-color-scheme`); the **Theme** selector
  (System / Dark / Light) overrides it and persists in `localStorage`
  (try/catch: storage may be blocked).
- An inline script in `<head>` applies the saved theme before first
  paint, so there is no flash.
- Canvas instrument panels (Digital Twin) intentionally stay dark in both
  themes; their colors are drawn in JS.

## Rules

- Status is never color-only: every colored verdict carries its word.
- Archived evidence is labelled `ARCHIVED … not a live run`.
- Technical fields stay visible; a plain-language sentence
  (`trustSentence()`, `.explain`) translates `qnx_verified` /
  `release_eligible` for non-experts next to them.
- Motion is minimal and disabled under `prefers-reduced-motion`.


## Measured contrast (7 Nov 2026, WCAG relative luminance)

Dark: fg 17.5:1 on bg, mut 9.3, accent-fg 6.7, ok 9.1, bad 6.8, warn 9.9
(all ≥ 5.3 even on `--surface-2`); white on primary button 5.06.
Light: fg 15.8, mut 6.4, accent 5.2, ok 5.1, bad 5.4, warn 4.9 on bg.
Light accent/ok/warn on `--surface-2` fall to 4.2–4.5, so those colours
are not used as text on `--surface-2` (only the selected nav item uses
that surface, with `--fg` text). Script: values reproduced from the hex
tokens with the WCAG 2.2 formula; axe-core in CI checks the rendered page.

## Application shell (Ascension)

- Sidebar (15.5 rem) with five groups — Start, Build, Verify, Evidence,
  Explore — and the environment status + theme at its foot; collapses
  into a wrapped bar under 56 rem.
- Breadcrumb `Section / Page` above every page; `#/<page>` deep links;
  browser back/forward replays page switches.
- Work area fills the window up to 88 rem; prose stays ≤ 78 ch.
- Every page opens with a one-line `.page-intro`: what it is, what to do,
  what comes next.
- Status tags with fixed meaning: **Native**, **Host only**, **Archived**,
  **Live**.
