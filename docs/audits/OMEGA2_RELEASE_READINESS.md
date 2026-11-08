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

## Merge plan (pre-merge, kept historical)

PR `omega2` → `main` (20 commits at audit time — 21 at merge,
merge commit per repo convention), main CI must go green,
then tag nothing until the video lands (no release while
submission-critical media is deferred).

## Post-merge verification (Omega3 §4.1, 8 Nov 2026)

- PR #11 merged: `9098564` ("Merge pull request #11 from
  toskaman/omega2"); 21 commits `5bb2fc4..0fd173f`.
- Final main SHA at Omega3 branch point: `cee9c9d`
  (+ PROGRESS merge note; `main` == `origin/main`, tree clean).
- Main CI green twice: `42491599766` (merge, 4m34s) and
  `42492043838` (PROGRESS note, 4m32s), SDK-free
  1287 passed + 6 honest skips.
- Owner-box suite re-measured post-merge: 1293 collected,
  1291 passed + 2 skipped, 0 failures; E2E 29 + 2;
  docs-consistency 27/27.
- Native packs re-verified post-merge: `omega2-before`
  34/34 + `omega2-after` 36/36 digests OK, VERIFY OK,
  matrix 16/16, qnx_verified=True; `verify-pack --trust
  local` UNSIGNED exit 2 both (hash-only, as labeled).
- No release or tag created (video still deferred).
- Owner-only blockers unchanged: final video, one pilot
  session, target password change, Devpost submission.

## Remaining for the owner (not automatable)

Record and publish the <3 min video; run one pilot session;
change the target password; submit to Devpost before
15 Dec 2026 14:00 EST.
