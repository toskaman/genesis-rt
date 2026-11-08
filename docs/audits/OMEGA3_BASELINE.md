# OMEGA3 baseline (verified 8 Nov 2026, branch `titan-omega3` @ main `cee9c9d`)

Machine-readable core:

```json
{
  "branch": "titan-omega3",
  "base": "main@cee9c9d46cd0eeb55c11e1b10615ef5e4d593c37",
  "merge_pr11": "9098564dfcaef9c3729b54da3f99facfa8d20884",
  "tree": "clean at branch point", "open_prs": 0, "open_issues": 0,
  "ci_head": {"run": 42492043838, "result": "success"},
  "tests_collected": 1293,
  "with_sdk": {"passed": 1291, "skipped": 2, "note": "owner box, 8 Nov"},
  "sdk_free_ci": {"passed": 1287, "skipped": 6, "run": 42492043838},
  "e2e_browser": "29 passed + 2 skipped of 31",
  "native": {"matrix": "16/16 x2 (omega2 packs)", "stale": "14/16 as designed",
             "packs_verify": "2/2 OK", "trust": "UNSIGNED hash-only"},
  "ai": {"v4": "32/32/31 frozen", "v5": "24/36 x3 frozen, 12 open gaps",
         "v6": "absent"},
  "impact": "NO_HUMAN_DATA",
  "video": "DEFERRED_BY_OWNER",
  "scorecard": "31.5/40 internal (9.5/8/5/8.5)"
}
```

## Verified HEAD and CI

- `main` == `origin/main` @ `cee9c9d`; PR #11 MERGED; no open
  PRs/issues; no releases; Apache-2.0; 9 topics (incl. qemu).
- Main CI green twice post-merge (`42491599766`, `42492043838`).

## Exact test outcomes by environment (pre-Omega3-change)

- Owner box + SDK: 1293 collected, 1291 passed + 2 skipped
  (axe scans, no `node_modules/axe-core`), 0 failures.
- SDK-free CI (Linux): 1287 passed + 6 honest skips, 0 failures.
- E2E browser: 29 + 2. Docs-consistency: 27/27. Planning pin: 30/30.

## Native pack status

- `omega2-before` 34/34 + `omega2-after` 36/36 digests OK,
  VERIFY OK, matrix 16/16, qnx_verified=True (re-verified
  post-merge, this box). `verify-pack --trust local`:
  UNSIGNED exit 2 both — hash-only, documented, no signer.

## AI evaluation status

- v4 (frozen): 32/32/31, rerun identical on Omega2 code.
- v5 (frozen, commit-before-run): 24/36 x3 identical fail
  set, 12 unsafe accepts, 0 false rejects. 12 classes OPEN.
- v6: absent — Omega3 P0 creates it blind, then fixes v5
  classes, then measures once per provider.

## Current internal scorecard

31.5/40 (Tech 9.5, Design 8, Impact 5, AI 8.5). Impact is the
largest gap (no human data); AI second (v5 gaps open).

## Open security residuals (from Omega2 audit 6/7)

M1-M5/M9-M11, H4-H7 races (audited, not fixed); image on
default password; native CI build-only; no localhost-API
auth-boundary review; no fresh dependency audit; hash-only
packs (no trust root for signing). Triage is Omega3 §8 work.

## Documentation inconsistencies found (Omega3 §4 scope)

1. Release readiness kept a pending merge plan (§4.1).
2. Baseline carried a future-dated (9 Nov) Wave-1 audit (§4.2).
3. CLAIMS headed Wave-12 with W11 packs as current (§4.3).
4. Devpost draft W11-focused, v5 undisclosed (§4.4).
5. Pilot duration: 90-120 min/lane vs 2x45 min (§4.5).
6. Commercial 45-min claim read as new-user evidence (§4.6).
7. Count checks existed but no semantic pins (§4.7).

## Owner-only actions (unchanged)

Final video; one pilot session; target password change;
Devpost submission (deadline 15 Dec 2026 14:00 EST).

## Prioritized remediation

P0: §4 doc drift (this wave) → v6 blind dataset → planner
fixes → v6 measurement. P1: pilot quick-tier, Studio
highest-value journey, security triage, commercial brief,
submission package. Then jury attack, scorecard, PR, merge.
