# Final readiness report — Titan Ascension Wave 10 (8 Nov 2026)

Branch `titan-ascension`. Status labels (§27):
`SOFTWARE_READY_WITH_LIMITATIONS` + `SUBMISSION_PENDING_FINAL_VIDEO`.
`VIDEO_STATUS = DEFERRED_BY_OWNER` (unchanged, owner-gated).

## 1–3. Lineage

- Starting HEAD: `1c640db` (pushed, CI 42437529429 green).
- Final HEAD: `75b9811` (pushed; CI running at write time).
- Commits: `a5ffe69` Wave 10 (53 files, +1376/−103),
  `5ff4a58` Linux traversal fix + boot-trap docs, `d0b031b`
  lockfile hygiene, `75b9811` campaign report. CI green on
  `d0b031b` (run 42441670341); `a5ffe69` CI failed once
  (Linux-only traversal test — fixed, never re-broken).

## 4–5. Bugs fixed / features added

- Count-pin drift 1229→1251 synced across 8 files (found by
  the 100-Q sample, Q28) + E2E prose 30/30→31/31.
- Codelab coverage break from the new checklist heading —
  fixed by heading wording, test unchanged.
- Linux-only `external._confined` bypass (`..\<name>`, `<drive>:/<name>`
  resolve inside the workspace on POSIX) — lexical rejects,
  18/18 green on Windows, full suite green on Linux CI.
- `boot`-kills-QEMU trap + SLIRP-early-accept documented
  (quickstart §4, codelab Lab 6) after both bit the campaign.
- Features landed: BYOQNX adapter (`external.py` + CLI +
  18 tests + codelab + sample), pilot `--plan`/`--to-csv` +
  onboarding, planner value-before-kind reorder +2 tests,
  faultinject timeouts, device pid pinning, Studio copy
  fixes, codelab TOC + Lab 5/6 acceptance checklist.

## 6. Tests run and exact outcomes

- Full suite with SDK (this box, one run): **1249 passed +
  2 skipped** (axe-core absent — honest skips).
- Full suite SDK-free (Linux CI 42441670341): **1245 passed
  + 6 skipped** (6 enumerated SDK-gated tests), 0 failed —
  tally-verified from per-test marks (summary line absent
  from the downloaded log; 1251 marks, 6 `s`, 0 `F/E`).
- Native: **16/16 matrix PASS**, perf 1000/1000
  (p50 228.9 µs TCG), sched 4×200 PASS on the jury-fixed
  sources (see `CAMPAIGN_2026-11-08.md`).
- Evidence packs: 3/3 VERIFY OK after all changes.
- Lint: ruff bug classes clean (local + CI).

## 7–8. QNX native / AI status

- Native: green on current sources; faultinject 9/9 with
  timeouts, device_chain NONGUARD=0 with pinning. QEMU/TCG
  only — no hardware claims.
- AI: no model runs tonight (was: v1 91/98 + v2 30/30
  re-run post-reorder with identical misses; v4 frozen,
  deliberately NOT re-run post-reorder — stated in
  `AI_EVALUATION.md`, not silently upgraded).

## 9–11. Design / accessibility / impact

- Design: Studio copy/label fixes (screenshot-verified
  earlier), codelab TOC + acceptance checklist. Residuals
  from the design review stand: empty-state preload, card
  language, error actions.
- Accessibility: axe scans green in CI (both themes,
  320 px reflow, zoom E2E). No screen-reader pass —
  disclosed, not claimed.
- Impact: pilot kit complete and tested, but
  `NO_HUMAN_DATA` — zero invitations sent, nothing
  fabricated. The human-productivity claim stays unproven.

## 12–14. Commercial / compliance / bonuses

- BYOQNX adapter: digest-consistency only,
  UNVERIFIED_CLAIM, `release_eligible` always False,
  no gate code path (AST-pinned). Commercial docs keep
  market claims labeled hypothesis with a gated roadmap.
- Compliance: Apache-2.0, original work, no SDK/binaries/
  secrets in the repo, QNX Everywhere non-commercial use;
  video + Devpost submission remain owner actions.
- Bonuses: codelab URL ready in the bonus box; QNX-tech
  mapping (IPC/resmgr/supervisor/provenance) in
  `TECHNICAL_EVIDENCE.md` + fresh 16/16 transcripts.

## 15. Remaining limitations (explicit, not fixed)

1. No independent pilot participants; no WTP/ROI data.
2. No hardware run; no HAM; uint32 ms clocks.
3. v4 eval not re-run after the planner reorder.
4. Device pin TOCTOU + `reset_armed` dead path (jury A
   residual) documented, not eliminated.
5. No 4th evidence pack for the new sources (matrix
   record + transcripts preserved instead).
6. Design residuals (§9) + v5 third-party eval set.

## 16. Fix-verification pass (jury findings → evidence)

Every Wave-10 fix below is verified by the cited artifact;
nothing is scored on prose:

- Faultinject hangs → `TimerTimeout` at 4 sites, qcc 0
  warnings, 9/9 live (campaign).
- Device impostor forwards → pid pinning + EPERM, APPLIES
  83 / NONGUARD=0 live (campaign); TOCTOU disclosed.
- Planner kind-before-values → reorder +2 tests, v1/v2
  re-run identical (eval records).
- Single-lane "pilots" → paired ladder + plan/CSV tests
  18/18; state still NO_HUMAN_DATA (no invention).
- External trust overreach → UNVERIFIED_CLAIM + 15 tests
  incl. the Linux traversal case (CI green).
- Count drift → 1251 pins + 26/26 consistency tests.
- Codelab rot → harness green + TOC/checklist (3/3).
- Boot-trap → docs + a campaign that survived it.

## 17–18. Readiness / video

`SOFTWARE_READY_WITH_LIMITATIONS` (limits = §15 list).
`SUBMISSION_PENDING_FINAL_VIDEO`, `VIDEO_STATUS =
DEFERRED_BY_OWNER`. No video work performed; historical
cuts are labeled non-submission. No Devpost submission made.
