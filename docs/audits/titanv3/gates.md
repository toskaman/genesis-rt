# Phase-19 submission + quality-gate audit — branch `titan-omega-v3`

Audited commit `8b35839` ("Titan v3: K1 prove-my-change + B-03/B-14/B-17/B-18
(1395 tests green)") via a private scratch worktree of
`origin/titan-omega-v3`; the shared checkout was never touched and no
writes, commits, tags, releases, or submissions were made. Every body
cited below was opened and read; search output was used only to locate
candidates. Frozen evals (`evals/*.json`, `evals/results/*`) were not
read for content and are untouched by the branch (zero `evals/` paths
in `origin/main...origin/titan-omega-v3`).

Claim labels: VERIFIED FACT (opened body + confidence) / OBSERVATION /
ASSUMPTION. Source links are branch-relative paths unless noted.

## 1. Copy consistency (title → impact)

| Field | README.md | docs/submission/DEVPOST_FINAL_DRAFT.md | docs/CLAIMS.md | Verdict |
|---|---|---|---|---|
| Title | "GENESIS RT — The Physical World Compiler" (L1) | identical (L10) | n/a (registry, no title) | VERIFIED FACT, high — consistent |
| Tagline | "From human intent to tested QNX-native machine software." (L3) | "From machine intent to QNX-native software — with verifiable proof." (L11-12) | n/a | OBSERVATION, high — two deliberate variants (page header vs form tagline); working draft `docs/devpost-draft.md` L27 matches the Final Draft wording, so the form copy is pinned, not drifting |
| Category | Developer Tooling & Host Tools (L8-9) | identical (L13) + filing checklist re-pins it | n/a | VERIFIED FACT, high |
| Solution/pipeline | validate→generate→run→prove 60s pitch (L17-25) | Specify→Compile→Run→Break→Prove→Explain (L38-62) | product features list matches (L196-202) | VERIFIED FACT, high — same six stages, same vocabulary |
| Architecture | ASCII diagram + `docs/architecture.md` pointer (L75-96) | "How we built it" chain (L66-72) mirrors `docs/architecture.md` (orchestrator → planner/IR → validation → codegen → build adapter → QNX target → evidence → gate, L3-33) | CI-behavior section agrees (host-ci + build-only qnx lane, L146-160) | VERIFIED FACT, high |
| Sponsor use (QNX) | codelab + native IPC pointers (L142-152) | "How we use QNX" paste-ready block (L84-100), test-pinned token-by-token (`test_bonus_b2_surface_pinned`, tests/unit/test_docs_consistency.py L719-732) | platform + matrix + oracle section agrees (L38-54) | VERIFIED FACT, high |
| Features | commands table incl. new `verify-change` (L126-141) | judge path + Studio description (L57-62, L201-216) | features list (L196-202) | VERIFIED FACT, high |
| Innovation/AI | v9: 142/150/150, 5 unsafe/112, 0 wrong-kind (L60-71) | same v9 numbers + full ladder (L131-183) | same v9 block (L83-144) | VERIFIED FACT, high — byte-level agreement on headline numbers |
| Impact | "Human benefit is not yet measured (no pilots run)" (L13) | "No pilots, no customer measurements… HUMAN USER BENEFIT NOT YET MEASURED" (L194-199) | "No external customer pilots yet… no measured human productivity gain" (L191-192) | VERIFIED FACT, high — honest no-theatre wording in all three |
| Limitations | QEMU-only, no certification (L154-161) | full list incl. UNSIGNED packs, build-only native lane, 5 unsafe, SR outstanding (L221-233) | same list (L182-194) | VERIFIED FACT, high |

Nits (non-blocking):
- OBSERVATION, high: `docs/devpost-draft.md` L175-176 still says "State:
  `main` post-PR-#11 (Omega2 merged 8 Nov 2026)". The file is explicitly
  fenced as a superseded working draft kept for history (L1-9), and its
  test-count line WAS updated to 1395 (L151), so this is a stale
  one-liner inside a history-kept file, not submission copy. The Final
  Draft governs (filing checklist L28-32).
- OBSERVATION, high: Omega2 pack file counts say 34/36 files
  (CLAIMS.md L58-61, Final Draft L110, working draft L91) but the
  directories contain 35/37 files on disk (counted in the worktree).
  Off-by-one persists from the pre-branch tree; the `verify.py`
  exclusion hypothesis fits exactly but is stated nowhere.

## 2. Demo + video URL status

- VERIFIED FACT, high: video is correctly DEFERRED everywhere.
  `submission/VIDEO_DEFERRED.md` (L3: `DEFERRED — USER-REQUESTED`),
  README L52-54, CLAIMS.md L162-174 (`DEFERRED_BY_OWNER`,
  `PENDING_VIDEO`, "never claim a public URL until it exists"), Final
  Draft L3-6 + L19-22, working draft L12-17, scorecard L36-37 — all agree.
- VERIFIED FACT, high: no YouTube watch/short URL is claimed anywhere in
  README, either Devpost draft, or CLAIMS (grep for
  `youtube.com/watch|youtu.be/` returns zero hits).
- VERIFIED FACT, high: the historical W12 cut (154.664 s) is never
  presented as the submission video; README L52-54 and every draft say
  it predates the current Studio.
- OBSERVATION, medium: `docs/demo-video-plan.md` (untouched by this
  branch) reads as a production plan ("Only the YouTube upload remains
  an owner handoff", L6) — plan, not a completion claim. No conflict
  with DEFERRED status.

## 3. Repo readiness

- License: VERIFIED FACT, high — `LICENSE` is Apache-2.0 (L1-3);
  `docs/jury/COMPLIANCE.md` L9-13 states Apache-2.0 with the
  PolyForm-Strict rationale, matching README L168-173. No license drift.
- Secrets: VERIFIED FACT, high — no embedded secrets on the branch.
  `git grep 'BEGIN .*PRIVATE KEY' origin/titan-omega-v3` hits only
  `tests/unit/test_signing.py` L171, which asserts a PEM header on a
  generated in-test fixture (`alice@example.com`, pre-existing file,
  untouched by this branch). `GENESIS_RUNNER_TOKEN` appears only as an
  env-var read, never a value. No `.pem`/key files added (32-file diff
  contains none).
- Broken links in touched docs: VERIFIED FACT, high — MIXED.
  All 22 touched Markdown files were link-checked. Judge-path and
  submission docs (README, CLAIMS, both Devpost drafts, START_HERE,
  GLOSSARY, REPRODUCE, COMPLIANCE, walkthrough, checklist,
  second-host, storyboard, security model, commercial vision) have
  zero broken relative links. BUT the seven new provenance copies in
  `docs/audits/titanv3/` ship broken links:
  - ~120 markdown links with absolute local paths
    (`<local-workspace>/...` with `:line` suffixes,
    e.g. `backlog.md` L31/L36/L47) — dead on GitHub AND leak the local
    username/directory layout. Affected: `backlog.md`, `demo-story.md`,
    `killer-feature.md`, `recon.md`. (`competitors.md`,
    `qnx-forensics.md`, `winners-delta.md` are clean.)
  - 4 links to `../v3-research/*.md` (`backlog.md` L17-20) — that
    directory is outside the repo, so they 404 on GitHub (the sibling
    copies sit in the same directory and should be `./`-linked).
  - Recommended pre-merge fix: rewrite absolute links as repo-relative
    paths or plain code spans, and repoint the four `../v3-research/`
    links at the same-directory copies. Internal audit dir, not the
    judge path — quality/privacy blemish, not a submission blocker.
- Evals freeze: VERIFIED FACT, high — zero `evals/` paths in the branch
  diff; no eval content was read.
- Branch hygiene: VERIFIED FACT, high — `origin/main` still
  `60bfd53`; single commit `8b35839` on `origin/titan-omega-v3`; no
  tags, no releases, no PR, no merge, no history rewrite.

## 4. Branch CI status

- VERIFIED FACT, high: `host-ci` run `42691278320` on `titan-omega-v3`
  finished `completed / success` in 4m40s (pushed 9 Nov 2026
  20:15:50Z; observed after completion). This is the only branch run.
- OBSERVATION, high: the native `qnx.yml` lane remains BUILD-ONLY by
  design (no self-hosted runner; CLAIMS.md L148-151) — disclosed, not a
  regression.

## 5. Test / evidence claims vs reality

- VERIFIED FACT, high: **1395 collected** — `pytest tests/
  --collect-only` in the branch worktree sums to exactly 1395 across
  all files, matching `facts.TESTS_WITH_SDK = 1395` and every doc
  (CLAIMS L12, Final Draft L72-75, scorecard L9-11, REPRODUCE L16,
  COMMERCIAL_VISION L133, working draft L151).
- VERIFIED FACT, high: **55/55 docs-consistency green** — ran
  `tests/unit/test_docs_consistency.py` on the branch this session:
  `55 passed in 4.66s`, including the 4 new Titan-v3 pins (filing
  checklist L709, B2 surfacing L719, glossary L735, second-host L747).
- VERIFIED FACT, high: K1 Prove-my-change is wired end to end —
  `POST /changes` + `GET /changes/{id}` (api.py L487/L587), CLI
  `verify-change` (cli.py L192, README table L136, walkthrough L71),
  Studio "Prove a change" panel (studio.html L462); new tests collect
  (`test_change.py`: 8, `test_changes_api.py`: 6).
- VERIFIED FACT, high: GET inventory 36→37 is consistent —
  `local-security-model.md` L50 and `AUDITED_GET_ROUTES`
  (test_rebinding_posture.py L75) agree.
- VERIFIED FACT, medium: full-suite green is corroborated, not re-run
  here — branch CI `success` runs the host suite + real-browser E2E,
  and the implementer reports 1395 passed / 0 failures locally. The
  historical 1348 figure in JUDGE_SCORECARD.md L43 sits inside the
  fenced "Historical assessment — Omega4" section (L41), correctly
  historical.
- ASSUMPTION, medium: SDK-gated skip arithmetic (1389+6 / 1393+2) is
  taken from the implementer run + CI; this audit ran collect-only
  plus the docs file, not the full suite or browser E2E.

## 6. Phase-19 gate table

| Gate | Verdict | Exact blockers (none = shippable on this axis) |
|---|---|---|
| Product (submission copy + features) | **PASS** | None. Title/category/solution/architecture/sponsor-use/features/innovation/impact agree across README, Final Draft, and CLAIMS; K1 shipped and wired; B-03/B-14/B-17/B-18 delivered with pins. Nits: pack 34/36-vs-35/37 off-by-one; stale "post-PR-#11" line inside history-kept working draft. |
| UX (judge path + Studio) | **PASS** | None. Glossary exists and is linked from START_HERE; walkthrough covers `verify-change`; zero broken links on the judge path. Known disclosed gaps (no screen-reader session, dense page) are owned limitations, not regressions. |
| Engineering (branch health) | **FAIL** | **E1** — `docs/audits/titanv3/{backlog,demo-story,killer-feature,recon}.md` ship ~120 broken absolute-path links (also leak local `C:/Users/...` paths) + 4 broken `../v3-research/` links in `backlog.md`. Fix before merge to `main` (repoint relative / code-span). Everything else green: CI success, 1395 collected verified, 55/55 pins green, Apache-2.0, no secrets, evals frozen, main untouched. |
| Evidence (claims match reality) | **PASS** | None. Counts, matrices, AI ladder, stale-control prose-grade label, UNSIGNED packs, build-only native lane, and video-deferred status all match the opened bodies; full green corroborated by branch CI success. |
| Competition (filing readiness) | **FAIL** | **C1** — final video still `DEFERRED_BY_OWNER`; no public YouTube URL exists (owner-only action). **C2** — Devpost NOT submitted (owner-only action; hard stop 15 Dec 2026 14:00 ET; filing checklist ready). |

**Phase-19 overall: NOT SHIPPABLE.** Two owner-only submission blockers
(C1 video, C2 filing) plus one recommended pre-merge branch fix (E1
audit-copy links). No engineering surprise: the branch is green,
honest, and internally consistent — it is waiting on the owner, not on
more code.
