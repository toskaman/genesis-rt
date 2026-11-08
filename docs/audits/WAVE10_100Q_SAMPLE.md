# Wave 10 — 100-question adversarial audit, sampled execution (8 Nov 2026)

Directive §24 asks for 100 adversarial questions across 10 categories,
each reproduced and fixed where justified. Prior waves already audited
several categories in depth (security sweep Wave 8, AI frozen-set
campaign Wave 5, reproducibility, codelab harness, jury A–E reviews).
This file records a fresh 30-question sample (3 per category) executed
against the uncommitted Wave-10 tree on 8 Nov 2026, with real commands,
real verdicts, and the fixes they triggered.

Ground truth for this sample: HEAD `1c640db` collects 1229 (verified in
a clean worktree); the tree collects 1251 (+18 BYOQNX files that were
never committed, +4 Wave-10 tests).

## QNX technical implementation (directive: 15)

| # | Question | Verdict + evidence |
|---|---|---|
| Q1 | Do all faultinject IPC sites carry a timeout after the jury-A fix? | PASS. `arm_ipc_timeout()` (one `TimerTimeout` def) is called before all 4 `MsgSend` sites (`genesis_faultinject.c:53,108,148,202`); qcc rebuilt 0 warnings (campaign build logs). |
| Q2 | Is the device pid pinning enforced, not just logged? | PASS with noted residual. First valid forward pins `fwd_pid`; later forwards from other pids get `MsgError(EPERM)` + REJECT log (`genesis_device.c:72-82`). First-forward TOCTOU documented, not eliminated. |
| Q3 | Is supervisor respawn genuinely bounded? | PASS. Per-child death counter, `g_deaths > MAX_RESTARTS` → `GIVE_UP` + halt (`genesis_supervisor.c:114-118`); codelab 6.4 asserts the flip natively. |

## Native reproducibility (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q4 | Are fresh qcc builds deterministic across output dirs? | PASS. Same sources → identical sha256 across 4 fresh dirs (device `338362e3…` ×4, status ×4, supervisor ×4); per-machine configs correctly differ. |
| Q5 | Does the 18/18 rebuild claim still hold? | PASS by citation (not re-run tonight). `docs/ascension/rebuild-2026-11-08.log`, same host class; Linux/cross-SDP still unverified, still labeled so. |
| Q6 | Do the 3 published packs still verify after the jury C-source fixes? | PASS. `verify_evidence_pack.py` on all three packs → VERIFY OK (exit 0) 8 Nov 2026. Packs are historical; new sources change hashes, which is expected. |

## Evidence and trust (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q7 | Is stale-binary reuse refused? | PASS. `tests/unit/test_buildset.py` (31 tests incl. wrong-machine/old-binary/tampered-provenance) green. |
| Q8 | Is passport tamper refused on replay? | PASS. `tests/integration/test_replay.py` (tamper/anchor/transcript-dir) green. |
| Q9 | Is imported external evidence capped below verified execution? | PASS. `tests/unit/test_external.py` 15/15: UNVERIFIED_CLAIM, no gate/target imports (AST-pinned), stale on tamper. |

## Security (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q10 | Any secrets or keys in tracked code? | PASS. Pattern sweep over host/ui/scripts/tests: one hit, a test asserting on a *generated* PEM header (fixture, not a leak). No committed scan script exists — the sweep stays ad-hoc. |
| Q11 | Are oversize payloads refused before parsing? | PASS. `test_dossier_size_cap_413` + `test_oversize_body_rejected_before_parse` green. |
| Q12 | Does the native-campaign script leak the target password? | PASS, fixed by construction + `.gitignore`. Script logs only candidate *numbers*; `artifacts/campaign-*/` added to `.gitignore` tonight after the audit found the dir untracked-but-unignored. |

## Reliability (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q13 | Do concurrent target ops serialize instead of corrupting? | PASS. Target lock + `test_target_duplicate_live_409` green (46-test batch incl. Q7/Q8/Q11). |
| Q14 | Does a failed verify leave the target/Vm in a diagnosable state? | PASS by procedure. Campaign script leaves QEMU running on verify failure, stops it only on green; `stop` clears the pidfile. |
| Q15 | Does a browser refresh mid-run lose the job? | PASS. Jobs persist in sqlite (`jobs.py` runs/jobs/events tables); E2E `test_refresh_mid_run_recovers_honest_state` + reattach test green in a real browser. |

## UI/UX and accessibility (directive: 15)

| # | Question | Verdict + evidence |
|---|---|---|
| Q16 | Do the a11y scans run and pass? | PASS in CI, honest skip locally. 2 axe scans skip without `node_modules/axe-core` (the measured "2 skipped"); CI installs axe-core 4.10.2 and runs them. |
| Q17 | Are the Wave-10 Studio copy fixes covered by E2E? | PASS. E2E diff is copy-only ("Pipeline page", guidance text) and the suite passes 29+2; shell-navigation keyboard test green. |
| Q18 | Is reduced motion respected? | PASS (shallow). `prefers-reduced-motion` present in `ui/studio.html`; no full screen-reader pass — still disclosed, not claimed. |

## User impact (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q19 | Does the analyzer reject single-lane "comparisons"? | PASS. `test_pilot_analysis.py` 18/18 incl. paired-data ladder + CSV reserialization of validated rows only. |
| Q20 | Is the timer monotonic and replayable? | PASS. `test_session_plan_covers_both_lanes_and_replays` green; `--plan`/`plan_session` cover both lanes. |
| Q21 | Is the human-data state reported honestly? | PASS. `pilot-study.md` states `NO_HUMAN_DATA` — "no pilot run yet". Zero invitations sent; nothing fabricated. |

## Commercial viability (directive: 10)

| # | Question | Verdict + evidence |
|---|---|---|
| Q22 | Are competitor claims graded, not asserted? | PASS. `COMPETITIVE_LANDSCAPE.md` carries vendor-doc/assessment/hypothesis grades (pin-tested); COMMERCIAL_VISION labels every market claim a hypothesis until measured. |
| Q23 | Does the roadmap separate now from later? | PASS. "Days 1–30 / 31–60 / …" gated on measurement; day-one section is measured-only. |
| Q24 | Does the BYOQNX adapter work on a real sample? | PASS by prior evidence (not re-run tonight). Live qcc demo CONSISTENT→STALE recorded pre-freeze; 15 adapter tests green tonight. |

## AI innovation (directive: 5)

| # | Question | Verdict + evidence |
|---|---|---|
| Q25 | Is the v4 eval set frozen and pre-registered? | PASS. `evals/planning_holdout_v4.json`: 36 cases + frozen marker; probes pre-registered. |
| Q26 | Is intent-safety separated from structural safety? | PASS (vocabulary differs). `AI_EVALUATION.md` tracks accepted-should-refuse separately from schema-valid/bounded, marks v1 contaminated, keeps the deterministic layer authoritative. |
| Q27 | Are post-fix model results honestly labeled? | PASS. v1/v2 re-run after the reorder fix; v4 explicitly NOT re-run after the reorder (structural validation only) — stated in the eval doc, not silently upgraded. |

## Hackathon compliance and prizes (directive: 5)

| # | Question | Verdict + evidence |
|---|---|---|
| Q28 | Are public test counts current? | **FAIL → FIXED TONIGHT.** Six current-facing docs + `facts.py` still pinned 1229/1224+5 while the tree collects 1251. Synced to 1251 / 1245+6 / 1249+2 across `facts.py`, CLAIMS, devpost-draft, scorecard, REPRODUCE, START_HERE, COMMERCIAL_VISION, requirements.lock. SDK-free 1245+6 is predicted from 6 enumerated SDK-gated tests; CI confirms after push. |
| Q29 | Is the codelab URL ready for the bonus box? | PASS. ADVANCED-QNX.md footer carries the blob URL; TOC + Lab 5/6 acceptance checklist + Takeaway added tonight (anchors slug-verified, checklist literals grep-verified, coverage test updated by heading rename). |
| Q30 | Is the video status honest everywhere? | PASS. `PENDING — FINAL VIDEO DEFERRED BY USER` in devpost-draft; "final video DEFERRED BY OWNER" in scorecard; pin-tested (`test_video_status_deferred_everywhere`). |

## Fixes triggered by this sample

1. Count sync 1229→1251 across 8 files (Q28) + E2E prose 30/30→31/31.
2. `artifacts/campaign-*/` added to `.gitignore` (Q12).
3. Codelab TOC + acceptance checklist + Takeaway; new heading worded to keep the 6-lab coverage test green (test itself unchanged) (Q29).
4. Codelab coverage test failure caught and fixed before commit (found via full-suite run during the audit).

## What this sample did NOT do

- The remaining ~70 questions of the full 100 (directive spread 15/10/10/10/10/15/10/10/5/5).
- Fresh native re-verification (campaign running in parallel; result lands separately).
- Fresh model reruns (v4 deliberately not re-run post-reorder).
- Screen-reader pass, second-host reproducibility, external pilot recruitment.

No finding in this sample upgrades a score by itself; each verdict
points at the command or file that reproduces it.
