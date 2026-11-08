# Omega2 audit 7/7: release readiness

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c` (this audit
ships in the PR; merge SHA to be recorded at merge time).

## Verdict: SOFTWARE_READY_WITH_LIMITATIONS

## Green

- Suite: 1293 collected; SDK run 1291 passed + 2 skipped,
  zero failures (this box); SDK-free 1287 + 6 honest skips;
  E2E 29 + 2; codelab 6/6; ui+e2e 89+2. Host CI green.
- Native: BEFORE/AFTER sealed PASS qnx_verified=True on
  current source + STALE-as-designed; 5 natively found bugs
  fixed red-then-green; qcc 0 warnings (36 binaries).
- Trust: fail-closed release, fatal verify, redacted
  display, hash-only packs honestly labeled UNSIGNED.
- AI: v4 no-regression + v5 frozen-before-run measurement,
  72 untouched cases, zero tuning.
- Docs: scorecard 31.5/40 (internal), claims registry
  consistent (pinned by tests), codelab re-executed,
  compliance matrix current.

## Limitations (blocking nothing, hiding nothing)

- `SUBMISSION_PENDING_FINAL_VIDEO`, `VIDEO_STATUS =
  DEFERRED_BY_OWNER`: no Devpost submit without the video.
- `HUMAN USER BENEFIT NOT YET MEASURED`: pilot kit ready,
  zero invitations sent; owner run blocked on the owner.
- Hardware claims unverified (QEMU/TCG only); cross-SDP and
  Linux-host reproducibility unverified; native CI
  build-only; image still on the default password.
- 12 v5 unsafe-accept classes open (v6 set required to fix
  honestly); residual M/H races audited, not fixed.

## Merge plan

PR `omega2` → `main` (20 commits, merge commit per repo
convention), main CI must go green, then tag nothing until
the video lands (no release while submission-critical media
is deferred).

## Remaining for the owner (not automatable)

Record and publish the <3 min video; run one pilot session;
change the target password; submit to Devpost before
15 Dec 2026 14:00 EST.
