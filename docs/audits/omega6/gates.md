# Phase-19 submission + quality-gate audit — branch `titan/omega6-product-proof`

Audited commit `fa9aeb7` ("OMEGA6 count sync: 1431 collected
(1425+6 SDK-free, 41 E2E, 61 pins) across facts + 9 docs") via a
private scratch worktree at detached HEAD of
`origin/titan/omega6-product-proof`; the shared checkout was never
touched (verified clean at the end: `## titan/omega6-product-proof`
with zero modified files) and no writes, commits, tags, releases,
PRs, or submissions were made. Every body cited below was opened
and read; search output was used only to locate candidates. Frozen
evals (`evals/*.json`, `evals/results/*`) were not read for content
and are untouched by the branch (zero `evals/` paths in
`origin/main...origin/titan/omega6-product-proof`).

Claim labels: VERIFIED FACT (opened body + confidence) / OBSERVATION /
ASSUMPTION. Source links are branch-relative paths unless noted.

## 1. Copy consistency (title → impact, incl. new hero + cold-start + Demo-A)

| Field | README.md | docs/submission/DEVPOST_FINAL_DRAFT.md | docs/CLAIMS.md | Verdict |
|---|---|---|---|---|
| Title | "GENESIS RT — The Physical World Compiler" (L1) | identical (L10) | n/a (registry, no title) | VERIFIED FACT, high — consistent |
| Tagline | "From human intent to tested QNX-native machine software." (L3) | "From machine intent to QNX-native software — with verifiable proof." (L11-12) | n/a | OBSERVATION, high — same two deliberate variants as the v3 audit (page header vs form tagline); form copy unchanged |
| Category | Developer Tooling & Host Tools (L19-20) | identical (L13) + filing checklist re-pins it | n/a | VERIFIED FACT, high — also matches COMPLIANCE.md L6 |
| Hero line (NEW, OMEGA6 C1) | "generates inspectable evidence about the behavior of the code" (L5-7) | identical sentence opens Inspiration (L26-27) | n/a (registry carries no lede) | VERIFIED FACT, high — same sentence on both doors + Studio lede (studio.html L223-225); pin `test_hero_line_front_doored` green |
| Cold-start card (NEW, OMEGA6 C2) | 30-second card: validate → demo --ir → PASS + passport in ~2 s (L9-14) | n/a (judge path carries the full clone sequence instead, L233-246) | n/a | VERIFIED FACT, high — README card matches Studio note `ov-coldstart` word-for-word incl. "~2 s" (studio.html L226-229); absent from form/registry copy by scope, not drift |
| Demo-A timing table (NEW, OMEGA6 C4) | pointer "timed in `docs/jury/REPRODUCE.md`" (L13-14) | n/a | n/a | VERIFIED FACT, high — table lives in REPRODUCE.md L25-34 (1.2/1.2/1.2 s + 0.2/0.1/0.1 s, budgets ≤1.6/≤0.3 s); Demo A defined in DEMO_WALKTHROUGH.md L7 |
| Solution/pipeline | 60s pitch: IR → native QNX controller → fault injection → evidence passport (L28-36) | Specify→Compile→Run→Break→Prove→Explain (L39-65) | features list matches (L199-205) | VERIFIED FACT, high — same story, same vocabulary |
| Architecture | ASCII diagram + `docs/architecture.md` pointer (L86-107) | "How we built it" chain (L69-75) | CI-behavior section agrees (host-ci + build-only qnx lane, L149-154) | VERIFIED FACT, high |
| Sponsor use (QNX) | codelab + native IPC pointers (L153-163) | "How we use QNX" block + footprint pointer to WHY_QNX.md (L87-107) | platform + matrix + oracle section agrees (L41-57) | VERIFIED FACT, high |
| Features | commands table incl. `verify-change` (L137-151) | judge path + Studio description (L54-65, L231-246) | features list (L199-205) | VERIFIED FACT, high |
| Innovation/AI | v9: 142/160, 150/160 each, 5 unsafe/112, 0 wrong-kind, 34 of 36 consults, 14 explained mismatches (L69-82) | same v9 numbers + full ladder (L138-190) | same v9 block (L86-147) | VERIFIED FACT, high — headline numbers agree token-for-token across all three |
| Impact | "Human benefit is not yet measured (no pilots run)" (L24) + limitations (L165-172) | "No pilots, no customer measurements… HUMAN USER BENEFIT NOT YET MEASURED" + persona/buyer-hypothesis/win-loss/bit-rebuild blocks (L192-229) | "No external customer pilots yet… no measured human productivity gain" (L185-197) | VERIFIED FACT, high — honest no-theatre wording in all three; new E3 prose explicitly labels buyer "HYPOTHESIS, unvalidated" |
| Limitations | QEMU-only, no certification (L165-172) | full list incl. UNSIGNED packs, build-only native lane, 5 unsafe, SR outstanding (L251-263) | same list (L185-197) + v10 trigger rule via KNOWN_LIMITATIONS.md | VERIFIED FACT, high |
| Pack counts (B-19 fix) | n/a | "34 payload files + verify.py" / "36 payload files + verify.py" (L117) | identical (L61-64) | VERIFIED FACT, high — the v3 off-by-one nit is CLOSED: exclusion now stated in both docs + pin; 35/37 files on disk verified (§5) |

Nits (non-blocking):
- OBSERVATION, high: count-sync commit message says "facts + 9 docs"
  but the commit stat shows `facts.py` + 8 docs (CLAIMS,
  BUYER_BRIEF, COMMERCIAL_VISION, devpost-draft, JUDGE_SCORECARD,
  REPRODUCE, START_HERE, DEVPOST_FINAL_DRAFT). Commit-message
  arithmetic only — every `1431` site was grepped and is present
  (§5). No doc is missing the sync.
- OBSERVATION, high: `docs/jury/JUDGE_SCORECARD.md` current section
  is still titled "(OMEGA5)" (L8) while carrying OMEGA6 numbers
  (1431/61/41, L9-16). Numbers current, header label stale; the
  OMEGA6 self-column delta lives in SCORECARD_DELTA_OMEGA6.md
  (INTERNAL 31.5, +0.5 Design only). Cosmetic.
- OBSERVATION, high: `docs/devpost-draft.md` L180 still says "State:
  `main` post-PR-#11 (Omega2 merged 8 Nov 2026)". Same stale
  one-liner the v3 audit noted (moved from L175 by the new
  SUPERSEDED banner, L3-6). Still inside the explicitly
  history-kept superseded draft; the Final Draft governs. Not a
  regression.

## 2. Demo + video URL status

- VERIFIED FACT, high: video is correctly DEFERRED everywhere.
  `submission/VIDEO_DEFERRED.md` (L3: `DEFERRED — USER-REQUESTED`),
  README L63-65, CLAIMS.md L165-177 (`DEFERRED_BY_OWNER`,
  `PENDING_VIDEO`, "never claim a public URL until it exists"),
  Final Draft L3-6 + L19-22 + L312-313, working draft (banner +
  L-series video-pending notes), FILING_DRY_RUN_OMEGA6.md L10-13
  ("STILL BLOCKED (owner)… Binding blocker") — all agree.
- VERIFIED FACT, high: no YouTube watch/short URL is claimed anywhere
  in README, either Devpost draft, CLAIMS, or VIDEO_DEFERRED (grep
  for `youtube.com/watch|youtu.be/` returns zero hits).
- VERIFIED FACT, high: the historical W12 cut (154.664 s) is never
  presented as the submission video; README L63-65, CLAIMS L169,
  and VIDEO_DEFERRED L11-15 all fence it as historical/predating
  the current Studio.
- VERIFIED FACT, high: Devpost is NOT filed.
  `SUBMISSION_STATUS = PENDING_FINAL_VIDEO` (Final Draft L3);
  dry run L6 says "unfiled", L32-33 "N/A until filed"; no
  filed/submitted/completed claim exists in any touched doc (grep
  for completion phrasing returns zero hits). Hard stop 15 Dec
  2026 14:00 ET, tracked in the dry run (L14) and checklist.

## 3. Repo readiness

- License: VERIFIED FACT, high — `LICENSE` is Apache-2.0 (L1-3);
  `docs/jury/COMPLIANCE.md` L9-14 states Apache-2.0 with the
  PolyForm-Strict rationale, matching README L179-184. No drift.
- Secrets: VERIFIED FACT, high — no embedded secrets on the branch.
  `git grep 'BEGIN .*PRIVATE KEY'` hits only the pre-existing
  `tests/unit/test_signing.py` L171 (asserts a PEM header on a
  generated in-test fixture) plus a prose mention in the historical
  `docs/audits/titanv3/gates.md` record. Token-pattern grep
  (`ghp_|gho_|sk-ant-|AKIA…|xox[bap]-`) returns zero hits; no
  `.pem`/`.key`/`.p12` files; `GENESIS_RUNNER_TOKEN` appears only
  as an env-var read/export-template, never a value. The branch
  additionally REDACTED two live username paths
  (`<user-profile>\…` → `%LOCALAPPDATA%\…` in both OWNER_ACTIONS
  files) and three `<drive>:/tmp`-style occurrences (PROGRESS,
  READINESS, GAUNTLET) — all redaction diffs opened and confirmed.
- Broken links in touched docs: VERIFIED FACT, high — CLEAN.
  All 24 touched Markdown files were checked: zero absolute local
  paths (the A5 absolute-path pattern), all 17 `](…)` relative links
  resolve on disk, zero outside-repo links (the only `../..`
  hit is a code span, `GENESIS_SRC=../../target/qnx8` in
  PROGRESS.md L521, not a link). Repo-wide, the single remaining
  drive-rooted occurrence is the redacted placeholder inside the
  historical v3 gates record (gates.md L143) describing old E1 —
  prose, not a link, and the 61/61 docs pins (incl. the A5
  no-absolute-path / no-outside-link tests) are green.
- Prior E1 stays fixed: VERIFIED FACT, high — the four v3
  audit-copy files ship zero absolute paths and zero
  `../v3-research/` markdown links on this branch (only prose /
  code-span mentions remain); the fix rode in on `main` via
  PR #15 and this branch introduces no regression.
- Evals freeze: VERIFIED FACT, high — zero `evals/` paths in the
  40-file branch diff; no eval content was read. (AI numbers above
  come from README/CLAIMS/draft prose + `facts.py`, never from
  `evals/`.)
- Branch hygiene: VERIFIED FACT, high — `origin/main` still
  `cdd70da` (PR #15 merge); 19 commits ahead on
  `origin/titan/omega6-product-proof` (`27dd60d`…`fa9aeb7`); no
  tags, no releases, no PR, no merge, no history rewrite. Shared
  checkout clean and untouched.

## 4. Branch CI status

- VERIFIED FACT, high: `host-ci` run `42706904873` on
  `titan/omega6-product-proof` finished `completed / success` in
  5m10s (pushed 9 Nov 2026 21:54:29Z, completed 21:59:39Z;
  observed after completion via `gh run view`). This is the only
  branch run. (First poll showed `in_progress` at 4m09s; re-polled
  to completion — no inference from a partial state.)
- VERIFIED FACT, high: the branch's only workflow change is
  additive and non-blocking — a `pip-audit` step with
  `continue-on-error: true` (host-ci.yml diff, +5 lines), triaged
  in `docs/security/SUPPLY_CHAIN_TRIAGE.md` (pytest PYSEC-2026-1845
  ACCEPT, test-only, UNIX-/tmp-specific, dated 2026-11-09).
- OBSERVATION, high: the native `qnx.yml` lane remains BUILD-ONLY
  by design (untouched by this branch; CLAIMS.md L151-154) —
  disclosed, not a regression.

## 5. Test / evidence claims vs reality

- VERIFIED FACT, high: **1431 collected** — `pytest tests/
  --collect-only` in the branch worktree sums to exactly 1431
  across 101 files (exit 0), matching `facts.TESTS_WITH_SDK =
  1431` and every doc (CLAIMS L12/L28, Final Draft L75-76/L245,
  REPRODUCE L16, START_HERE L30, COMMERCIAL_VISION L133,
  BUYER_BRIEF L96, JUDGE_SCORECARD L9/L20, working draft L156).
- VERIFIED FACT, high: **61/61 docs-consistency green** — ran
  `tests/unit/test_docs_consistency.py` on the branch this
  session: exit 0, 61 dots, zero F/E (61 `def test_` functions
  counted in the file). Includes the OMEGA6 pins spot-opened:
  hero-line front doors, QNX footprint table (guard 6641 /
  faultinject 8136 / ntox86_64-size / "No resident-set claim"),
  v10 trigger rule, pack-count exclusion, no-absolute-path and
  no-outside-link lints.
- VERIFIED FACT, high: **41 E2E, incl. 9 Prove-acceptance** —
  collect-only sums `tests/e2e/` to exactly 41
  (`test_prove_browser.py`: 9), matching `facts.E2E_BROWSER_TESTS`
  and CLAIMS L20-33 (23 journey + 3 axe/reflow + 6 shell + 9 K1).
- VERIFIED FACT, high: **packs re-verified offline** — 35/37 files
  on disk (recursive count), both `verify.py` runs exit 0
  (`VERIFY OK`, 16/16, 1000 samples, `qnx_verified=True`),
  matching the "34/36 payload files + verify.py" registry wording
  in CLAIMS + Final Draft.
- VERIFIED FACT, high: K1 Prove-my-change is wired end to end —
  `POST /changes` + `GET /changes/{id}` (api.py L487/L587), CLI
  `verify-change` (cli.py L595, README table L147, walkthrough
  L71), Studio "Prove a change" panel (studio.html L479) + new
  overview hero card `ov-prove-hero` (L236-244) + Prove CTA (L233);
  new tests collect (`test_prove_browser.py`: 9).
- VERIFIED FACT, high: Demo-A table and cold-start card are
  internally consistent — REPRODUCE L31-34 timings
  (1.2/1.2/1.2 s + 0.2/0.1/0.1 s, ±30% budget note) sit under a
  dated host-only header; README L9-14 "~2 s" cold-start claim
  matches the Studio note (L226-229) and has headroom over the
  table. Beat timings in DEMO_BEATS_TIMED.md (1 s / 0.0 s /
  5.7 s / 2.4 s / 8.5 s) match DEMO_FALLBACK_LADDER.md rung 0
  exactly.
- VERIFIED FACT, medium: full-suite green is corroborated, not
  re-run here — branch CI `success` runs the host suite +
  real-browser E2E (5m10s), and this audit ran collect-only plus
  the docs file plus both pack verifiers. The remaining `1348`
  figures sit inside correctly fenced history (CLAIMS L29 OMEGA4
  no-axe sentence; JUDGE_SCORECARD L43 "Historical assessment —
  Omega4"); GAUNTLET L315 "21 real-browser E2E" sits in a report
  dated 2026-11-06 (HEAD `12e662e`) — all legitimately dated.
- ASSUMPTION, medium: SDK-gated skip arithmetic (1425+6 SDK-free /
  1429+2 SDK-without-axe / 1431+0 SDK+axe) is taken from the
  implementer run + branch CI; this audit ran collect-only plus
  the docs file, not the full suite or browser E2E.

## 6. Phase-19 gate table

| Gate | Verdict | Exact blockers (none = shippable on this axis) |
|---|---|---|
| Product (submission copy + features) | **PASS** | None. Title/category/solution/architecture/sponsor-use/features/innovation/impact/limitations agree across README, Final Draft, and CLAIMS; hero line on all three front doors (pin-held); cold-start card + Demo-A table consistent; B-19 pack exclusion stated; K1 hero card + Prove CTA additive with tabs kept. Nits: "9 docs" commit-message arithmetic (8 docs + facts); OMEGA5-titled scorecard section carrying OMEGA6 numbers; stale "post-PR-#11" line inside history-kept working draft. |
| UX (judge path + Studio) | **PASS** | None. Zero broken links on the judge path and all touched docs; walkthrough covers `verify-change`; cold-start + hero + Prove CTA on Studio overview; honest archived-vs-live labeling on proof cards; disclosed gaps (no screen-reader session, no cold-read proof, dense page) owned in HARDEST_QA_LIVE, not regressed. |
| Engineering (branch health) | **PASS** | None. CI success (42706904873, 5m10s); 1431 collected verified; 61/61 pins green; packs VERIFY OK; Apache-2.0; no secrets (2 username paths + 3 drive paths redacted this branch); evals frozen; main untouched; prior E1 stays fixed with no regression. |
| Evidence (claims match reality) | **PASS** | None. Counts (1431/1425+6/41/61), matrices (16/16), AI ladder (v9 142/150/150, 5 unsafe/112, 0 wrong-kind, 34/36 consults), footprint table (6641/8136 via ntox86_64-size, RSS honestly unmeasured), stale-control prose-grade label, UNSIGNED packs, build-only native lane, and video-deferred status all match the opened bodies; full green corroborated by branch CI success. |
| Competition (filing readiness) | **FAIL** | **C1** — final video still `DEFERRED_BY_OWNER`; no public YouTube URL exists (owner-only action). **C2** — Devpost NOT submitted (owner-only action; hard stop 15 Dec 2026 14:00 ET; filing checklist + canonical text ready; owner must re-open Rules in a real browser — automation got 403). |

**Phase-19 overall: NOT SHIPPABLE.** Two owner-only submission blockers
(C1 video, C2 filing) and zero engineering blockers. The branch is
green, honest, and internally consistent — it is waiting on the owner,
not on more code.
