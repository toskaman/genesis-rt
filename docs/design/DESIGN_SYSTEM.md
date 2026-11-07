# GENESIS Studio design system

Single file: all tokens live at the top of `ui/studio.html` (`:root`).
No framework, no build step: the Studio stays a self-contained page so
it works offline and from a fresh clone.

## Tokens

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#0d1117` | `#ffffff` | page |
| `--panel` / `--surface` | `#0f141b` / `#161b22` | `#f6f8fa` | cards, controls |
| `--border` | `#30363d` | `#8c959f` | 3:1 non-text contrast in light |
| `--fg` / `--mut` | `#e6edf3` / `#9da7b3` | `#1f2328` / `#57606a` | text / secondary text |
| `--accent` / `--on-accent` | `#1f6feb` / `#fff` | `#0969da` / `#fff` | primary action, selected tab |
| `--ok` / `--bad` / `--warn` | green / red / amber | darker variants | verdicts — always paired with a word (PASS/DENY/…) |
| `--focus` | `#79c0ff` | `#0550ae` | `:focus-visible` ring |
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
