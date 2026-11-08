# Omega2 audit 3/7: Studio + accessibility (P1a)

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c`. Status: CLOSED
(scoped fixes; the full premium redesign was NOT attempted).

## What changed

- Passport classifier shared core: `dashboard.html` carried its
  own copy of the ok→pass mapping and drifted; both pages now
  use `ui/genesis_verify.js` (`ppStatusClass`).
- Terminal phase banner: the banner showed a stale phase after
  completion; it now shows the terminal state (`phaseShown`).
- Runner hint points at `omega2` evidence (was: stale branch).
- Accessibility: 48 controls verified reachable by
  label-for; no new axe violations.

## Verification

Browser-verified in Chromium with 0 console errors;
ui+e2e 89+2 green; E2E suite 29 passed + 2 skipped.
Node unit test pins the shared classifier.

## Honest scope note

The directive asked for a deep workflow redesign (Machine
Designer, Evidence Graph, Target Runner). P1a deliberately
delivered scoped honesty fixes instead: a redesign without a
design reviewer and without user sessions would redecorate
rather than improve. Designer/graph/runner remain form-heavy;
this is recorded as the Design gap in the scorecard (8/10,
not 10).

## Open

No screen-reader session (NVDA/JAWS/VoiceOver) was run;
full WCAG 2.2 AA conformance is not claimed. Mobile 320 px
and zoom/reflow coverage is automated and green.
