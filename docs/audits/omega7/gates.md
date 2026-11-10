# Phase-19 submission + quality-gate audit — branch `titan/omega7-v10-stale-arm`

Audited commit `7cb64d7` ("OMEGA7 count sync: 1525 collected
(1519+6 SDK-free) across facts + 7 docs") via a private scratch
worktree at detached HEAD of `origin/titan/omega7-v10-stale-arm`
(`<temp>/omega7-gate-7cb64d7`, removed
after the audit; a second baseline worktree at `origin/main` was used
for collect-only comparison and also removed). The shared checkout was
never touched (verified clean at the end) and no writes, commits,
tags, releases, PRs, or submissions were made. The only write of this
audit is this file, which lives outside the repo. Every body cited
below was opened and read; search output was used only to locate
candidates. Frozen evals v4–v9 were not read for content (freeze
verified by `git diff --name-status` only); the new v10 dataset was
verified by digest only.

Claim labels: VERIFIED FACT (opened body + confidence) / OBSERVATION /
ASSUMPTION. Source links are branch-relative paths unless noted.
Prior packets read first: fixer (15 commits `45a95f0`…`549eab6`, v10 +
v1.4 + arm B2/C) and stale-arm (`549eab6`…`7cb64d7`, stale-control
Phase A + count sync); their named gaps are carried below, not re-litigated.

## 1. Copy consistency (README → Final Draft → CLAIMS, incl. NEW v10/arm/sealed-stale claims)

| Field | README.md | docs/submission/DEVPOST_FINAL_DRAFT.md | docs/CLAIMS.md | Verdict |
|---|---|---|---|---|
| Title | "GENESIS RT — The Physical World Compiler" (L1) | identical (L10) | n/a (registry, no title) | VERIFIED FACT, high — consistent |
| Tagline | "From human intent to tested QNX-native machine software." (L3) | "From machine intent to QNX-native software — with verifiable proof." (L11-12) | n/a | OBSERVATION, high — same two deliberate variants as prior audits (page header vs form tagline); unchanged |
| Category | Developer Tooling & Host Tools (L19-20) | identical (L13) | n/a | VERIFIED FACT, high |
| Hero line | "generates inspectable evidence about the behavior of the code" (L5-7) | identical sentence opens Inspiration (L26-27) | n/a (registry carries no lede) | VERIFIED FACT, high — same sentence on both doors + Studio (flattened match); pin `test_hero_line_front_doored` green (§5) |
| Cold-start card | 30-second card: validate → demo (L9-14) | n/a (judge path carries the full clone sequence, L241-256) | n/a | VERIFIED FACT, high — unchanged from OMEGA6 |
| Solution/pipeline | 60s pitch: IR → native QNX controller → fault injection → passport (L28-36) | Specify→Compile→Run→Break→Prove→Explain (L39-65) | features list matches (L221-227) | VERIFIED FACT, high — same story, same vocabulary |
| Sponsor use (QNX) | codelab + native IPC pointers (L154-164) | "How we use QNX" block + footprint pointer (L87-107) | platform + matrix + oracle agrees (L41-57) | VERIFIED FACT, high |
| Innovation/AI (NEW v10) | v10: 159/184, 165/184 each, 15 unsafe/136, 0 wrong-kind, 29 of 26 consults, 0 missing + 3 explained; v9/v10 NOT comparable (L69-83) | same v10 block + class split + full ladder (L141-155, L156-200) | same v10 block + v1.4 paragraph + ladder (L86-169) | VERIFIED FACT, high — headline numbers agree token-for-token across all three; v9 demoted to "previous" in both registry and draft |
| Impact | "Human benefit is not yet measured (no pilots run)" (L24) | "No pilots, no customer measurements… HUMAN USER BENEFIT NOT YET MEASURED" + persona/buyer-hypothesis/win-loss (L202-239) | "No external customer pilots yet… no measured human productivity gain" (L216-217) | VERIFIED FACT, high — honest no-theatre wording in all three |
| Limitations | QEMU-only, no certification (L166-173) | full list (L261-273) — **BUT L268 cites v9 as latest (see P1)** | same list (L207-219) | VERIFIED FACT, high — one defect: P1 below; everything else agrees |
| Pack counts | n/a (points at packs) | "34 payload files + verify.py" / "36 payload files + verify.py" (L117) | identical (L61-64) | VERIFIED FACT, high — matches 35/37 files on disk (§5) |
| Arm quarantine (NEW) | n/a (no arm copy on front door) | n/a | n/a | VERIFIED FACT, high — arm wording is consistent where it lives: gate quarantines on kind OR `physics_note` (`gate.py`, `QUARANTINE_PREFIX`), card/dossier banner PHYSICS WARNING (`change.py`/`dossier.py`), jury copy (`KNOWN_LIMITATIONS.md` L44-49), full text (`limitations-and-safety.md` #10, incl. sealed-follow-up note), machine-ir caveat (`machine-ir.md` L10-13), anti-pattern (`EXTENDING_MACHINES.md` L51-57), scorecard OMEGA7 delta (L25-27). No doc claims an arm PASS anywhere |
| Sealed-stale (NEW mechanism) | "no sealed transcript ships in the packs" (L46-48) | "no sealed transcript in the packs" (L119-122) | "no sealed transcript ships in the packs; sealing it is future work" (L50-54) | VERIFIED FACT, high — all three agree no sealed stale pack exists; no doc claims the new stale-control workflow produced a sealed artifact. The workflow itself (Studio `stale-control` option, sealed-FAIL mechanism + 35 tests) is undisclosed in prose docs, which matches existing practice — no doc enumerates Studio workflow options (only `docs/runner/SELF_HOSTED_RUNNER.md` mentions `verify-only`, in a runner context) |

**P1 (copy defect, blocks Product):** `docs/submission/DEVPOST_FINAL_DRAFT.md`
L268-269 says "AI planner: latest blind v9 shows 5 unsafe accepts of
112 reject cases" in the Limitations section, while the same file's AI
disclosure (L141-155) correctly leads with v10 (15 unsafe of 136). It
is the only wrong "latest" pointer in any touched doc (grep for
"latest blind" hits v10 in README L71 and CLAIMS L88, v9 only here),
and it understates the headline safety residual (5 vs the measured
15) in the section judges read for honesty. Fix is two lines, no
re-measurement: replace with the v10 residual (15 unsafe of 136, same
15 deterministic-layer cases; 0 wrong-kind; 29 of 26 consults + 3
explained mismatches) and keep the "no broad-robustness claim" fence.
The 61/61 docs pins stay green because the unsafe/wrong-kind pins
check metric *presence*, not the "latest" pointer — a pin for the
Limitations latest-pointer is suggested follow-up, not a blocker.

Nits (non-blocking):
- OBSERVATION, high: `docs/jury/JUDGE_SCORECARD.md` L31 keeps the
  "facts 1434/1428" token inside the dated OMEGA5-evidence Tech cell
  (fixer packet's known gap #3); the current-section header still says
  "(OMEGA6)" (L7) while carrying OMEGA7 numbers + the OMEGA7 delta
  paragraph (L9-27). Numbers current, labels stale. Cosmetic — same
  class as the OMEGA6 audit's own header nit.
- OBSERVATION, high: `docs/devpost-draft.md` L180 still says "State:
  `main` post-PR-#11 (Omega2 merged 8 Nov 2026)". Same stale one-liner
  the OMEGA6 audit noted; still inside the explicitly history-kept
  superseded draft; the Final Draft governs. Not a regression.
- OBSERVATION, high: count-sync commit message "facts + 7 docs"
  (`7cb64d7`) is arithmetically exact this time (stat: `facts.py` + 7
  docs) — the OMEGA6 "9 docs" nit is not repeated.

## 2. Demo + video URL status

- VERIFIED FACT, high: video is correctly DEFERRED everywhere.
  `submission/VIDEO_DEFERRED.md` (L3: `DEFERRED — USER-REQUESTED`),
  README L63-65, CLAIMS.md L187-199 (`DEFERRED_BY_OWNER`,
  `PENDING_VIDEO`, "never claim a public URL until it exists"), Final
  Draft L3-6 + L19-22 + L322-323 — all agree.
- VERIFIED FACT, high: zero YouTube URLs. Grep for
  `youtube.com/watch|youtu.be/|youtube.com/embed|youtube.com/shorts`
  hits only the two self-referential regex mentions inside the
  historical `docs/audits/omega6/gates.md` and `titanv3/gates.md`
  records ("returns zero hits") — no watch/short/embed URL is claimed
  anywhere.
- VERIFIED FACT, high: the historical W12 cut (154.664 s) is never
  presented as the submission video; README L63-65, CLAIMS L192, and
  VIDEO_DEFERRED L11-15 all fence it as historical/predating the
  current Studio.
- VERIFIED FACT, high: Devpost is NOT filed.
  `SUBMISSION_STATUS = PENDING_FINAL_VIDEO` (Final Draft L3); grep for
  filed/submitted/completed phrasing across README, CLAIMS, and both
  drafts returns zero hits. Hard stop 15 Dec 2026 14:00 ET (Final
  Draft L328).

## 3. Repo readiness

- License: VERIFIED FACT, high — `LICENSE` is Apache-2.0 (L1-5);
  `docs/jury/COMPLIANCE.md` L9-14 states Apache-2.0 with the
  PolyForm-Strict rationale, matching README L180-184. Untouched by
  this branch; no drift.
- Secrets: VERIFIED FACT, high — no embedded secrets on the branch.
  `BEGIN .*PRIVATE KEY` hits only the pre-existing
  `tests/unit/test_signing.py` L171 (asserts a PEM header on a
  generated in-test fixture) plus prose mentions in historical gate
  records. Token-pattern grep (`ghp_|gho_|github_pat_|AKIA…`) returns
  zero hits; password grep returns only `password=None` code defaults
  and `--password` CLI args (default None); `GENESIS_TARGET_PASSWORD`
  appears only as an env-var name / `<your-target-password>`
  placeholder, never a value.
- Broken links in touched docs: VERIFIED FACT, high — CLEAN. All 15
  touched Markdown files checked by script: zero absolute local paths
  (the A5 absolute-path pattern, plus the UNC prefix), all 17
  `](…)` relative links resolve on disk, zero outside-repo links. The
  `/tmp/v10-*.json` paths in `OMEGA7_AI_EVALUATION.md` are example
  `--out` placeholders, not A5 violations (`/tmp` is outside the A5
  pattern by design). The A5 pins
  (`test_docs_have_no_absolute_local_paths`,
  `test_docs_have_no_outside_repo_links`) are green (§5).
- Evals freeze: VERIFIED FACT, high — exactly 6 `evals/` paths in the
  `origin/main...HEAD` diff, all status `A` (added), zero `M`
  (modified), and zero `evidence/` or `target/` paths:
  `evals/planning_holdout_v10.PROVENANCE.md`,
  `evals/planning_holdout_v10.SHA256`,
  `evals/planning_holdout_v10.json`,
  `evals/results/2026-11-10-omega7-v10/llama3.1-8b.json`,
  `evals/results/2026-11-10-omega7-v10/offline.json`,
  `evals/results/2026-11-10-omega7-v10/qwen2.5-7b.json`.
  Frozen v4–v9 content was not read. (AI numbers in §1 come from
  README/CLAIMS/draft prose + the audit report, never from `evals/`.)
- Branch hygiene: VERIFIED FACT, high — base `origin/main` = `d5c35d9`
  (PR #16 merge); 19 commits ahead on
  `origin/titan/omega7-v10-stale-arm` (`45a95f0`…`7cb64d7`); no merge
  commits; no workflow changes (`.github/` diff empty); no tags, no
  releases, no PR for this branch; shared checkout clean and
  untouched.

## 4. Branch CI status

- VERIFIED FACT, high: tip run `42735886631` on
  `titan/omega7-v10-stale-arm` finished **completed / success** — host
  job 5m06s, every step green (ruff lint, Chromium + axe-core E2E,
  unit + integration + fault + acceptance, IR check, verified demo
  pipeline). First poll showed `in_progress`; re-polled to completion
  via `gh run view` — no inference from a partial state.
- VERIFIED FACT, high: prior run `42731861622` (on `549eab6`,
  pre-stale) also completed success (4m58s). The mid-branch failure
  (`42720772410`, v10-freeze commit) and cancelled run
  (`42720693900`) are superseded work-in-progress states, not tip
  signal.
- OBSERVATION, high: the native `qnx.yml` lane remains BUILD-ONLY by
  design (untouched by this branch; CLAIMS.md L173-176) — disclosed,
  not a regression.

## 5. Test / evidence claims vs reality

- VERIFIED FACT, high: **1525 collected** — `pytest tests/
  --collect-only` in the branch worktree sums to exactly 1525 across
  102 files (exit 0), matching `facts.TESTS_WITH_SDK = 1525` and
  every doc (CLAIMS L12/L28, Final Draft L75-78/L255, REPRODUCE L16,
  START_HERE L30, COMMERCIAL_VISION L133, JUDGE_SCORECARD L9-11,
  working draft L156). Baseline worktree at `origin/main`: 1434
  across 101 files — delta +91, exactly the claimed +56 OMEGA7 / +35
  stale-control split.
- VERIFIED FACT, high: per-file deltas reconcile to the commit
  messages — `test_planning.py` 73→113 (+40, matches "40 OMEGA7
  red-green planner cases"), `test_llm_provider.py` 39→47 (+8),
  `test_evidence_gate.py` 16→20 (+4: 3× B2 + 1× C),
  `test_change.py` 17→19 (+2 C), `test_dossier.py` 44→46 (+2 C),
  new `test_stale_control.py` 35. Per-commit collection: rule 21 +11,
  rule 20 +6, rule 19 +5 (4 planning + 1 llm courtesy), rule 22 +19,
  rule 23 +8 new with 1 stale param row removed (net +7) — i.e. 49
  new red-green rule tests (CLAIMS L141-142 exact) netting +48, +8
  arm (3 B2 + 5 C), +35 stale = +91. Zero unexplained tests.
- VERIFIED FACT, high: **61/61 docs-consistency green** — ran
  `tests/unit/test_docs_consistency.py` on the branch this session:
  exit 0, 61 dots, zero F/E (61 `def test_` functions counted;
  unchanged from OMEGA6 — no new pins this branch, none needed for
  the synced counts).
- VERIFIED FACT, high: **41 E2E** — collect-only sums `tests/e2e/`
  to exactly 41, matching `facts.E2E_BROWSER_TESTS` and CLAIMS L20-33.
- VERIFIED FACT, high: **packs re-verified offline** — 35/37 files on
  disk (recursive count), both `verify.py` runs exit 0 (`VERIFY OK`,
  16/16, 1000 samples, `qnx_verified=True`), matching the "34/36
  payload files + verify.py" registry wording in CLAIMS + Final Draft.
  No sealed stale pack exists or is claimed (see §1); the sealed-Fail
  stale-control mechanism is code + 35 tests only, awaiting the owner
  QEMU run per the fixer/stale packets.
- VERIFIED FACT, high: **v10 digest binds** — `Get-FileHash` of
  `evals/planning_holdout_v10.json` equals the `.SHA256` file and the
  `d550b802…` digest cited in PROVENANCE.md, the audit report, and
  the digest pin (content not read beyond hashing).
- VERIFIED FACT, medium: full-suite green is corroborated, not re-run
  here — tip branch CI `success` runs the host suite + real-browser
  E2E (5m06s), and this audit ran collect-only plus the docs file
  plus both pack verifiers. The remaining `1348`/`1434` figures sit
  inside correctly fenced history (CLAIMS L29 OMEGA4 no-axe sentence;
  scorecard historical sections).
- ASSUMPTION, medium: SDK-gated skip arithmetic (1519+6 SDK-free /
  1523+2 SDK-without-axe / 1525+0 SDK+axe) is taken from the
  implementer runs + tip CI; this audit ran collect-only plus the
  docs file, not the full suite or browser E2E.
- OBSERVATION, high (carried, documented, out of scope): v10/v11
  follow-ups (15 unsafe incl. omission-reading disputes needing a
  contract call, 4 false rejects, 3 consult gaps, length-floor vs rule
  9 example) and the B2 propagation gap (`physics_note` sealed-body
  propagation; kind-check carries the quarantine today) are disclosed
  in `OMEGA7_AI_EVALUATION.md` and `limitations-and-safety.md` #10 —
  no hidden debt.

## 6. Phase-19 gate table

| Gate | Verdict | Exact blockers (none = shippable on this axis) |
|---|---|---|
| Product (submission copy + features) | **FAIL** | **P1** — Final Draft Limitations (L268-269) cites "latest blind v9, 5 unsafe of 112" while v10 (15 unsafe of 136) is latest everywhere else in the same file; understates the safety residual in the honesty section. Fix: two-line v10 update, no re-measurement, then re-run the 61 pins. Nits (non-blocking): OMEGA6-titled scorecard section carrying OMEGA7 numbers + stale "facts 1434/1428" token in the dated Tech cell; stale "post-PR-#11" line inside the history-kept working draft. |
| UX (judge path + Studio) | **PASS** | None. Zero broken links and zero absolute paths across all 15 touched docs; hero + cold-start + Prove CTA intact; new Studio `stale-control` option is additive chrome with no doc-enumeration drift (no doc lists Studio workflow options); disclosed gaps (no screen-reader session, dense page) owned, not regressed. |
| Engineering (branch health) | **PASS** | None. Tip CI success (42735886631, 5m06s); 1525 collected verified with per-commit reconciliation to zero unexplained tests; 61/61 pins green; packs VERIFY OK; Apache-2.0; no secrets; evals freeze holds (6 adds, 0 modifies); 19 commits, no merges/tags/releases/PRs/workflows; main untouched. |
| Evidence (claims match reality) | **PASS** | None. Counts (1525/1519+6/113/41/61), matrices (16/16), AI ladder (v10 159/165/165, 15 unsafe/136, 0 wrong-kind, 29/26 consults + 3 explained; v9 fenced as history), arm quarantine (code + 4 docs agree, native byte-identical), stale-control prose-grade label (no sealed pack claimed), UNSIGNED packs, build-only native lane, and video-deferred status all match the opened bodies; full green corroborated by tip CI success. |
| Competition (filing readiness) | **FAIL** | **C1** — final video still `DEFERRED_BY_OWNER`; no public YouTube URL exists (owner-only action). **C2** — Devpost NOT submitted (owner-only action; hard stop 15 Dec 2026 14:00 ET; canonical text ready modulo P1). |

**Phase-19 overall: NOT SHIPPABLE.** One code-side blocker (P1, a
two-line copy fix in the unfiled Final Draft — minutes, no
re-measurement) plus two owner-only submission blockers (C1 video, C2
filing) and zero engineering blockers. The branch is green, honest,
and internally consistent modulo P1 — after that fix it is waiting on
the owner, not on more code.
