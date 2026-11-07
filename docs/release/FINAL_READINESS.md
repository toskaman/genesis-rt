# Pre-submission readiness — 7 Nov 2026

Base: `b379e6d` (public `main`, unchanged since the last audit; no open
PRs found locally; three stale `muse/*` branches left untouched).
Scope: software hardening only. **No video work was done** (see
`submission/VIDEO_DEFERRED.md`).

## What was executed (this pass, Linux cloud workspace, Python 3.13)

| Check | Command | Result |
|---|---|---|
| Full host suite | `python -m pytest tests/ -q` | **1135 passed, 5 skipped** (5 = QNX-SDK-gated, honest skips), 1140 collected |
| Browser E2E | `python -m pytest tests/e2e -q` | **21/21** (headless Chromium) |
| UI + E2E after redesign | `python -m pytest tests/ui tests/e2e -q` | **80/80** |
| BEFORE pack | `python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before` | exit 0, 34/34 digests, 15-link chain, matrix 16/16, 1000 samples |
| AFTER pack | same for `-w11-after` | exit 0, same shape, distinct IR digest |
| Legacy pack (historical) | `…verified-b22cea1/verify.py` | exit 0 |
| Tamper: cross-op passport swap (copy) | AFTER `passport.json` into a BEFORE copy | **rejected, exit 2** (run_id + anchor mismatch) |
| Tamper: verdict flip (copy) | `SPEED_OVER_LIMIT`→`OK` in a transcript | **rejected, exit 2** (digest mismatch) |
| Stale-binary logic | `tests/unit/test_limits_differ.py` + adversarial suite | 40/40 |
| Keyboard | Playwright: Tab → skip link; Arrow/Home/End across tabs | works |

**Not executed here:** a fresh native QNX/QEMU campaign (no SDK in the
cloud workspace; the owner's machine shell was unavailable because
hardware virtualization is off). Native claims rest on the committed,
re-verified packs. The stale-build native negative control
(op-ad562b34f8de) is local-only evidence on the owner's machine. The
Windows run of the suite was not repeated in this pass.

## Defects found and fixed

1. **P1 — stale canonical claims.** `facts.py` said 1078 tests; 1139
   were collected. Updated registry + jury/devpost/commercial docs to the
   measured run, and added `test_total_count_matches_collected` so the
   number can no longer drift silently.
2. **P1 — environment-dependent test.** `test_pack_verifies_outside_checkout`
   failed whenever `genesis_rt` was pip-installed (editable `.pth` made the
   repo importable). Now runs the verifier with `python -S`, so the stdlib
   fallback is genuinely exercised.
3. **P1 — REPRODUCE.md** pointed at the legacy b22cea1 pack as primary;
   now the BEFORE/AFTER packs are canonical, legacy kept as history.
4. **P1 — video status wording** in devpost draft + compliance matrix
   implied a finished video; now `DEFERRED BY USER`, URL placeholder
   `PENDING — FINAL VIDEO DEFERRED BY USER`.
5. **P1 — Studio navigation:** 12 flat tabs → 5 labelled groups
   (Guided demo · Build · Verify · Evidence · Explore) with clearer
   labels; new overview panel (headline, archived BEFORE/AFTER proof
   table clearly marked not-live, two CTAs); skip link, `<main>`
   landmark, `aria-controls`/`aria-labelledby`, roving tabindex with
   arrow keys, `:focus-visible`, reduced-motion, phone-width wrap
   (390 px overflow test passes). All 12 features and data-tab ids kept.

## Remaining limitations (honest)

- Native evidence is QEMU x86_64 on QNX 8.0; no real hardware, no HAM,
  no hardware attestation, no safety certification.
- Native CI lane needs a self-hosted SDK/QEMU runner; host CI is not a
  native run.
- Planner is the documented constrained offline planner, not an LLM.
- WCAG 2.2 AA: keyboard + structure improved and tested; no full
  screen-reader or contrast audit performed in this pass.
- Not re-done in this pass: codelab command replay, 40-question
  adversarial audit, competitive re-research (prior versions remain in
  `docs/codelab/`, `docs/audits/`, `docs/business/`).

## Verdicts

- **A. Software readiness: `SOFTWARE READY WITH LIMITATIONS`** (above).
- **B. Full submission readiness: `SUBMISSION PENDING DEFERRED VIDEO`.**
  Devpost not submitted; no video uploaded.
