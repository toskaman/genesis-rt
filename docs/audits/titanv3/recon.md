# GENESIS RT — Project Recon (v3 research)

Date: 2026-11-09. Scope: read-only map of `C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt`
(QNX hackathon submission, Developer Tooling & Host Tools).
Every code/doc body cited below was opened; search output was used only to locate candidates.
Labels: **VERIFIED FACT** (opened body +/or executed check) / **OBSERVATION** (measured,
needs interpretation) / **ASSUMPTION** (low confidence, needs follow-up).
No metrics, scores, feedback, or testimonials are invented: all numbers are quoted from
opened files or from commands executed this session.

## 1. Identity and repo state

- **VERIFIED FACT** (high): repo is GENESIS RT — "The Physical World Compiler":
  constrained machine description → typed Machine IR → deterministic QNX 8.0 C controller
  → native run + seeded fault injection → hash-linked evidence passport.
  Source: [README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/README.md:1-25).
- **VERIFIED FACT** (high): git HEAD is `60bfd53` "Merge pull request #14 from
  toskaman/titan-omega5"; working tree is clean (`git status --short` empty).
  Measured this session via `git log --oneline -8` / `git status --short`.
- **VERIFIED FACT** (high): status banner in README: "functional alpha",
  host verification fully working, QNX on-target execution verified
  (native `qcc` build 0 warnings, 16/16 on-target matrix, `qnx_verified: true`),
  QEMU x86_64 only, no safety certification, human benefit not measured.
  Source: [README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/README.md:8-13).
- **VERIFIED FACT** (high): license Apache-2.0; the OpenBridge PolyForm-Strict license
  was deliberately NOT reused because it is not open-source and would violate Devpost
  rules. Sources: [README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/README.md:167-172),
  [compliance-matrix.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/compliance-matrix.md:24-37).

## 2. Repository structure (top level)

- **VERIFIED FACT** (high, `Get-ChildItem` this session):

| Path | Contents |
|---|---|
| `host/genesis_rt/` | 36 Python modules (~604 KB), core stdlib-only |
| `target/qnx8/` | native C: guard, controller, device, status, supervisor, faultinject, cell, common, include, host_tests |
| `tests/` | 97 collected files: unit, integration, faults, qnx, ui, e2e, acceptance, property, snapshots |
| `docs/` | 176 files: architecture, CLAIMS, jury/, audits/ (41), codelab/, submission/, business/, design/, titan/, ascension/, demo/, etc. |
| `evals/` | 11 frozen planning datasets (published + paraphrase + holdouts v2–v9) + results/ per-model raws |
| `evidence/` | 8 entries: omega2-before/after (current), w11-before/after/after-rerun + w11-before-after (historical), b22cea1 (legacy), ipc-timeline |
| `schemas/` | `machine-ir-v1.schema.json`, `machine-ir-v2.schema.json` |
| `templates/` | 5 codegen templates (build mk, cell policy h, config h, machine c/h) + README |
| `scripts/` | `qnx_target.py` (88 KB campaign driver), `ci_ir_check.py`, `replay.py`, `run_verified_demo.py`, `qnx_env_check.py`, `qnx_rebuild_check.py`, `eval_planner.py`, `bench_host.py`, `build_set.py`, `build_evidence_pack.py`, `verify_evidence_pack.py`, `audit_eval_consults.py`, `bench_ref/`, `repro/` |
| `ui/` | `studio.html` (184 KB), `dashboard.html` (4.5 KB), `genesis_verify.js` (11 KB), README |
| `bench/productivity/` | METHODOLOGY.md, REPORT.json, analyze_pilot.py, pilot_timer.py, last-run/ (git-ignored scratch) |
| `examples/` | amr-demo (v1+v2+yaml), conveyor-demo (v1+v2), cell-demo (ok + broken), external-demo |
| `submission/` | `VIDEO_DEFERRED.md` only |
| `.github/workflows/` | `host-ci.yml`, `qnx.yml` |
| root | README, pyproject.toml, requirements.lock, LICENSE, SECURITY.md, CONTRIBUTING.md |

## 3. Features (host pipeline)

- **VERIFIED FACT** (high): pipeline is validate → codegen → build → verify →
  evidence → gate; CLI and pipeline dispatch v1/v2 through strict per-version loaders,
  v2 never reinterpreted as v1.
  Source: [architecture.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/architecture.md:36-46).
- **VERIFIED FACT** (high): CLI exposes 22 subcommands (opened `cli.py:494-612`):
  validate, plan, generate, simulate, faults, demo, external-check,
  external-write-manifest, compare, graph, impact, explore, replay, bench, twin,
  check-env, serve, sign-pack, verify-pack, runner-submit, runner-status, runner-cancel.
  The 9 commands in the README table all exist with matching help text.
- **VERIFIED FACT** (high): Web API (`api.py:289-1097`) exposes ~50 routes:
  health, runs (+cancel/export/passport/raw), compare, jobs (+events SSE/files),
  target ops (+compare/dossier/decision/events), examples, validate, projects
  (+history/revisions/diff/export/impact), env, graphs (+compare), impact (+release),
  ipc-timeline, review/plan, explore (+replay), twin/frames, and static `/`, studio,
  dashboard, verify.js. Loopback-only: `uvicorn.run(..., host="127.0.0.1", port=8077)`.
  Sources: [cli.py](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/host/genesis_rt/cli.py:320-320),
  [cli.py](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/host/genesis_rt/cli.py:592-593).
- **VERIFIED FACT** (high): major subsystems and their homes (opened architecture.md):
  NL planner (`planner.py`, optional LLM, same validated path), Machine IR
  (`ir.py`/`ir_v2.py` + `schemas/`), deterministic codegen (`codegen*.py` +
  `templates/`), build adapter (`build_adapter.py`), simulator + Fault Lab
  (`simulator.py`, `faultlab.py`), evidence passport (`evidence.py`),
  release gate (`gate.py`), jobs/SSE (`jobs.py`, `api.py`), Studio Live,
  Evidence Graph (`evidence_graph.py`), Requirements-to-Release/impact (`impact.py`),
  Counterexample Explorer (`explorer.py` + `explorer_conformance.py`),
  Digital Twin 2.0 (`twin.py`), productivity benchmark (`bench_productivity.py`),
  IR numeric canonicalization (`ir*.py`).
- **VERIFIED FACT** (high): `no-test => no-pass` gate semantics; missing/skipped/
  crashed/tampered evidence yields FAIL (test file `tests/unit/test_evidence_gate.py`
  exists; claim in [README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/README.md:174-176)).
- **VERIFIED FACT** (high): without an SDK the build adapter returns
  `{"status": "blocked", ...}` — never success, never silent skip.
  Source: [build_adapter.py](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/host/genesis_rt/build_adapter.py:113-117).
- **VERIFIED FACT** (high): QNX-native target (`target/qnx8/`, 15 C/H/MK files):
  `genesis_guard` (name_attach/MsgReceive/MsgReply), `genesis_controller`
  (name_open/MsgSend), `genesis_device` (virtual, no physical I/O), `genesis_status`
  (resmgr `/dev/genesis/status`), `genesis_supervisor` (sole reset authority),
  shared `common/guard_policy.c` proven identical to the Python mirror by the
  `guard_vector` conformance harness (`tests/integration/test_c_conformance.py`).
  Source: [architecture.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/architecture.md:146-157).
- **VERIFIED FACT** (high): fault campaign sizes claimed in README
  (AMR 8, conveyor 5, cell 4) match the example IRs exactly — measured this session
  by counting `verification.scenarios` in the three example files (8/5/4).
- **VERIFIED FACT** (high): time/deadline correctness uses RFC 1982 serial arithmetic
  over uint32 wire clocks in both C and Python, conformance-tested; pairs 2^31+ ms
  apart are ambiguous by construction (disclosed residual).
  Sources: [architecture.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/architecture.md:126-129),
  [limitations-and-safety.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/limitations-and-safety.md:14-22).

## 4. Workflows (how it is used)

- **VERIFIED FACT** (high): no-SDK judge path (2 min): install → `run_verified_demo.py`
  → `replay.py <passport>` → expect `verdict: PASS, qnx_verified: false, chain: valid,
  gate: PASS` → load passport in `ui/dashboard.html`.
  Source: [START_HERE.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/START_HERE.md:10-22).
- **VERIFIED FACT** (high): live workbench: `genesis-rt serve` → Studio at
  `http://127.0.0.1:8077/`; without backend, 6 inspector tabs keep working on local files.
  Source: [ui/README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/README.md:9-22).
- **VERIFIED FACT** (high): native loop: `qnx_env_check.py` → `quickstart-qnx8-qemu.md`
  → `scripts/qnx_target.py` (boot/put/run/verify incl. `perf`, `sched` campaigns).
  Target password comes from `GENESIS_TARGET_PASSWORD` env var (preferred over
  `--password`); also `GENESIS_TARGET_LOCK` for op locking. Measured via search hits
  in `qnx_target.py:635` and 6 sibling call sites.
- **VERIFIED FACT** (high): CI IR bridge: `scripts/ci_ir_check.py` validates changed
  Machine IRs (examples/projects, renames tracked, deletions verdict-neutral), reports
  impact, emits `proofos-plan.json` (never grants release eligibility alone); PRs diff
  against genuine PR base, pushes against push base, first-push zero-SHA falls back
  to all IRs. Source: [CLAIMS.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/CLAIMS.md:152-160).
- **VERIFIED FACT** (high): review dossier: one-click ZIP export (report.html + TOC/
  coverage/print CSS + manifest + VERIFY.md) via `GET /target/ops/{id}/dossier`,
  plus plain-language release-decision panel via `.../decision`.
  Source: [JUDGE_SCORECARD.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/JUDGE_SCORECARD.md:137-137).

## 5. UI

- **VERIFIED FACT** (high): `ui/studio.html` (183,789 bytes) has 13 tabs
  (opened tab bar, lines 185-201): Overview, Guided demo (7-stage Judge Mode),
  Projects, Machine designer, Generated C, Host pipeline, QNX target runner,
  Fault lab, Evidence passport, Before/After, Evidence graph, Digital twin,
  CLI commands. No build step, no npm; pipeline steps execute the same orchestrator
  as the CLI; no mock runs.
- **VERIFIED FACT** (high): `ui/dashboard.html` (4,530 bytes) is a dependency-free
  passport inspector working straight from `file://`; `ui/genesis_verify.js`
  (11,394 bytes) is the shared pure core (SHA-256, canonical form, chain verify),
  node-tested against the Python toolchain from `tests/ui/test_dashboard_verify.py`.
  Source: [ui/README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/README.md:18-28).
- **OBSERVATION** (medium): self-assessed Design residual is "dense single page;
  no screen-reader session" (axe scans in CI only); reviewer caps Design at 7/10
  for density + no SR session + no video.
  Source: [JUDGE_SCORECARD.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/JUDGE_SCORECARD.md:20-21).

## 6. APIs (contract surface)

- **VERIFIED FACT** (high): REST (FastAPI, needs `api` extra): sync `POST /runs`
  facade + async jobs (`POST /jobs` → 202, `GET /jobs/{id}`, SSE
  `GET .../events` with job_id + ordered seq, `DELETE` cancel); target ops CRUD +
  compare/dossier/decision/events; projects CRUD + history/revisions/diff/export/
  impact; validate, examples (+file), env, graphs, impact, ipc-timeline,
  review/plan, explore, twin/frames. Local-first, no auth, loopback-only,
  foreign-Origin writes 403. Source: route table in `api.py` (opened lines 289-1097).
- **VERIFIED FACT** (high): Machine IR contracts: `schemas/machine-ir-v1.schema.json`
  + `machine-ir-v2.schema.json`; strict whitelist, fail-closed; `simulation_only: true`
  required; v2 validates AMR/conveyor; `industrial_cell` stays v1-only (v2 validation
  and v1→v2 migration reject it loudly).
  Sources: [architecture.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/architecture.md:42-46),
  [limitations-and-safety.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/limitations-and-safety.md:29-30).
- **VERIFIED FACT** (high): passport contract: dict with `chain` (15 links, measured
  in omega2-after), `gate` (PASS), `environment` (genesis_version, git_commit,
  platform, python, qnx), hash-chained, replayable via `scripts/replay.py`,
  offline-verifiable via stdlib-only per-pack `verify.py`.

## 7. Tests and CI state (fast targeted subset only — full E2E NOT run)

- **VERIFIED FACT** (high): collected total this session = **1376 tests in 97 files**
  (`pytest tests --collect-only`, pytest 9.2.0) — exactly equals
  `facts.TESTS_WITH_SDK = 1376`.
  Source: [facts.py](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/host/genesis_rt/facts.py:15-15).
- **VERIFIED FACT** (high): `tests/unit/test_docs_consistency.py` → **51 passed
  in 5.13 s** this session (matches the scorecard's "51 documentation-consistency
  tests green"). It pins jury/devpost/commercial counts to `facts.py`, pack paths,
  video file/duration, E2E/adversarial/planning counts, and ~20 anti-drift guards.
- **VERIFIED FACT** (high): pinned sub-counts re-measured this session via
  `--collect-only`: planning unit 73, adversarial 24, E2E 32 (3 a11y + 3 judge +
  20 negative + 6 shell); planning eval dataset 28 cases; fault scenarios 8/5/4.
  All match `docs/CLAIMS.md` and `facts.py`.
- **VERIFIED FACT** (high): host CI (`.github/workflows/host-ci.yml`, opened):
  ruff bug-class lint (F401/F841/F541/B017) → host C `guard_vector` check →
  full `pytest tests/` → `ci_ir_check.py` (+proofos-plan artifact) → verified demo +
  replay. Concurrency-cancel per ref. Chromium + axe-core installed for browser E2E.
- **VERIFIED FACT** (high): QNX lane (`.github/workflows/qnx.yml`, opened) is
  BUILD-ONLY, `workflow_dispatch` only, needs a self-hosted `qnx` runner; it never
  boots QEMU or runs the 16-step matrix. A docs-consistency test enforces the
  NOT EXECUTED / BUILD-ONLY markers while no campaign step exists.
- **VERIFIED FACT** (high): both Omega2 packs re-verified this session —
  `verify.py` exit OK: `op=COMPLETED gate=PASS matrix=16/16 samples=1000
  qnx_verified=True` for before AND after; passport chain length 15. No SDK needed.
- **OBSERVATION** (medium): on-disk pack file counts are 35 (before) / 37 (after)
  including `verify.py`, while docs claim "34 files" / "36 files" — off by exactly
  one each, consistent with the docs excluding `verify.py` itself. Not covered by
  any docs-consistency pin (no test asserts file counts). Minor wording gap, not an
  integrity issue (both packs VERIFY OK).
- **OBSERVATION** (medium): environment this session already satisfies the "owner
  run" conditions: `node_modules/axe-core` present, playwright importable — so the
  full suite should collect 1376 with 0 skips here (not executed per task limits).
- **VERIFIED FACT** (high): `requirements.lock` pins cryptography 50.0.2 (meets the
  >=49 floor; a test pins it), pytest 7.4.0, playwright 1.63.0, fastapi/uvicorn/
  httpx/jsonschema/paramiko/pyyaml. Note the installed session pytest is 9.2.0,
  newer than the lock's 7.4.0 — collection still totals 1376.

## 8. Claim verification (README + CLAIMS.md vs code)

| Headline claim | Verdict | Evidence |
|---|---|---|
| 1376 collected; SDK-free 1370+6 | VERIFIED (this session) | collect-only sum 1376/97 files; facts.py:15-18; docs-consistency 51 passed |
| Omega2 BEFORE/AFTER 16/16 PASS sealed, qnx_verified:true | VERIFIED (this session) | both `verify.py` → VERIFY OK, 16/16, 1000 samples, qnx_verified=True |
| Stale control 14/16 on estop_target+v2_transitions | DISCLOSED AS PROSE-GRADE | README + CLAIMS both state operator-recorded, no sealed transcript in packs; sealing is future work |
| Native IPC timeline from real CLOCK_MONOTONIC | VERIFIED (files) | `evidence/ipc-timeline/` (timeline.json/txt, run-meta, bench log); API `GET /ipc-timeline` |
| CI IR bridge on every push/PR | VERIFIED (code) | `scripts/ci_ir_check.py` + host-ci.yml invocation + proofos-plan artifact |
| One-click dossier ZIP export | VERIFIED (code) | `GET /target/ops/{id}/dossier` in api.py:646; Studio button per ui/README |
| Historical W11 packs, 18/18 rebuilds | REFERENCED (not re-run) | packs on disk; rebuild checker `scripts/qnx_rebuild_check.py` exists; qnx.yml stage 5 references them |
| Blind v9: 142/150/150, 5 unsafe/112, 0 wrong-kind, 34/36 consults | REFERENCED (frozen, not re-run — reruns forbidden) | `evals/planning_holdout_v9.json` + `evals/results/2026-11-09-omega5-v9/` (3 provider files); report OMEGA5_AI_EVALUATION.md |
| Deterministic codegen byte-identical | VERIFIED (tests exist) | `test_codegen_determinism.py`, `test_codegen_v2.py`, snapshots under tests/snapshots |
| C/Python guard identical via guard_vector | VERIFIED (wiring) | `target/qnx8/common/guard_policy.c` + `host_tests/guard_vector.c` + `test_c_conformance.py` + host-ci C step |
| no-test => no-pass | VERIFIED (tests exist) | `tests/unit/test_evidence_gate.py` (collected in suite) |
| Video DEFERRED_BY_OWNER, submission PENDING | VERIFIED | submission/VIDEO_DEFERRED.md; 5 docs pinned by `test_video_status_deferred_everywhere` |
| No safety certification claimed | VERIFIED | "certified" absent from README/CLAIMS/devpost (pinned by test); "no safety certification" present |
| Human benefit not measured | VERIFIED | pilot-study "zero invitations sent" (pinned); IMPACT_STUDY "HUMAN USER BENEFIT NOT YET MEASURED" (pinned) |
| Packs UNSIGNED / hash-only | VERIFIED | CLAIMS "UNSIGNED"+"hash-only" (pinned); sign-pack/verify-pack CLI exist but packs ship unsigned |
| Pack file counts 34/36 | OFF BY ONE (docs undercount) | disk shows 35/37 incl. verify.py; see §7 observation |

## 9. Docs, submission materials, env/config

- **VERIFIED FACT** (high): docs inventory (176 files): jury kit (START_HERE,
  REPRODUCE, TECHNICAL_EVIDENCE, KNOWN_LIMITATIONS, COMPLIANCE, DEMO_WALKTHROUGH,
  WHY_QNX, WHY_GENESIS_RT, JUDGE_SCORECARD, BEFORE_AFTER_NATIVE), 3 codelabs
  (README + ADVANCED-QNX + EXTERNAL-BUILD, CI-harnessed via test_codelab_advanced),
  41 audit files (WAVE7–WAVE12 baselines, TITAN/ASCENSION/OMEGA2–OMEGA5, red-team ×2,
  soak ×2, AI evals v6→v9 + consultation audit), business (COMMERCIAL_VISION,
  COMPETITIVE_LANDSCAPE with evidence grades, pilot-study + pilot-onboarding),
  perf-baseline (host + target tables, withdrawn 5-Nov speedup reading with 8-Nov
  non-replication), evidence-methodology/trust, PLANNER_CONTRACT, planning-eval,
  PROGRESS.md (52 KB).
- **VERIFIED FACT** (high): submission materials: `docs/submission/
  DEVPOST_FINAL_DRAFT.md` (prepared 8 Nov, NOT submitted, v9-synced),
  `VIDEO_STORYBOARD_DEFERRED.md`, `OMEGA4/OMEGA5_OWNER_ACTIONS.md`,
  `submission/VIDEO_DEFERRED.md`; working draft `docs/devpost-draft.md` kept as
  history; historical video cut `docs/demo/genesis-rt-demo-w12.mp4` (154.664 s,
  6.8 MB) + subtitles + Piper-TTS voiceover + MEDIA_VALIDATION_W12 +
  PUBLICATION_HANDOFF_W12 — explicitly NOT the final video.
- **VERIFIED FACT** (high): env/config: Python ≥3.12; install `pip install -e
  ".[dev]"` (+`[e2e]` for browser tests, `[qnx]` for paramiko target loop);
  env vars `GENESIS_TARGET_PASSWORD` (secret, never in passports),
  `GENESIS_TARGET_LOCK`, `QNX_HOST`/`QNX_TARGET`/`QNX_CONFIGURATION` (probed);
  optional QEMU, Chromium, C compiler; `.gitignore` excludes runs, studio state,
  SDK/images (*.ifs/*.qfs), secrets (*.key/*.pem/.env), node_modules; artifacts
  and bench last-run are git-ignored scratch.
- **VERIFIED FACT** (high): self-scores (internal, not official): 31/40 OMEGA5
  (9.5/8/5/8.5; independent reviewer 29/40). Compliance matrix:
  `SOFTWARE_READY_WITH_LIMITATIONS`, `SUBMISSION_PENDING_DEFERRED_VIDEO`.
- **OBSERVATION** (low): `docs/PROGRESS.md` is newest-first for the Nov 4–5 entries
  but the two Nov-8 Omega2 entries are appended at the END (lines 904-919) instead
  of prepended — cosmetic ordering quirk.

## 10. TODOs and tech debt

- **VERIFIED FACT** (high): zero TODO/FIXME/XXX/HACK markers in `host/`, `scripts/`,
  `target/qnx8/include/`, `ui/` (searched this session); every "PENDING" hit is
  legitimate state-machine vocabulary (target op states, ProofOS states, Studio
  phase list).
- **VERIFIED FACT** (high): disclosed debt / residuals (from KNOWN_LIMITATIONS,
  limitations-and-safety, scorecard, owner actions — all opened):
  QEMU-only (no hardware, no HAM, no attestation); TCG timing relative;
  uint32 clock residual (2^31 ambiguity; no native 2^32-crossing vector);
  `robotic_arm_virtual` aliased onto diff-drive physics (labeled in evidence);
  v2 has no cell semantics; no auth on local API; default QNX image password
  not yet rotated (owner action); global-interpreter cryptography still 43.0.3
  on owner box vs 50.0.2 lock (owner action); v9 AI residuals (5 unsafe/112,
  14 explained consult mismatches, rule-18 limit-gate gap, missing "Greifer" alias);
  no screen-reader session; no pilots; no native CI runner (deliberate: licensed
  SDK + untrusted PR code = exfiltration risk); STALE 14/16 control unsealed
  (prose-grade); frozen evals must never be rerun on changed code.

## 11. Status judgments

- **Works** (verified this session): full host test collection (1376) + docs-consistency
  gate (51 green); CLI surface (22 commands incl. all README ones); ~50-route loopback
  API; offline pack verification (both Omega2 packs VERIFY OK, 15-link chains,
  16/16, qnx_verified=True); fail-closed `blocked` behavior without SDK; Studio
  13-tab structure + dependency-free dashboard/verify core.
- **Partial**: native story is author-machine evidence (packs + transcripts), not CI —
  by design (qnx.yml build-only, no runner); browser E2E covers host path only in CI.
- **Simulated** (honestly labeled): host fault campaigns run against the host guard
  mirror; only the 16-step target matrix runs natively; every passport carries
  `qnx_verified` explicitly.
- **Broken**: nothing found broken in the verified subset. Only blemish: the 34/36
  pack-file-count wording vs 35/37 on disk (§7).
- **Unfinished**: final video (blocks submission); Devpost NOT submitted; no release/tag
  (correctly deferred); no pilots; no screen-reader pass; crypto floor + password
  rotation owner actions open.
- **Distinctive**: contract-aware native oracle (IR-derived expectations, stale-binary
  behavioral rejection); sealed BEFORE/AFTER native pair; 15-link hash passports with
  stdlib offline verify; docs-consistency test gate (51 pins incl. semantic ones);
  blind AI holdout ladder v6→v9 with published raws and a consultation audit;
  Evidence Graph / Digital Twin / Counterexample Explorer / impact-release checks.
- **Low-value-impressive**: none identified — the 706-line docs-consistency file and
  41 audits could look like process theatre, but each pin traces to a real past
  incident named in test docstrings (truncation markers, crypto floor, v8 exposure).
- **Hard-to-understand**: the AI-eval ladder vocabulary (unsafe vs wrong-kind vs
  false-reject vs consults, blind vs qualified-blind, frozen vs regression sets)
  needs its glossary (present in CLAIMS.md but dense); ProofOS state machine and
  multi-build provenance (build_set, 9 staged binaries) are the steepest code areas.
- **High-friction**: native reproduction requires QNX SDP 8.0 + QEMU + SSH setup
  (documented in quickstart-qnx8-qemu.md but heavy); full suite needs playwright +
  Chromium + axe-core for the zero-skip run.
- **Judge-blockers** (from OMEGA5_OWNER_ACTIONS + compliance matrix): (1) final video
  missing → submission cannot be filed; (2) Devpost draft prepared but NOT submitted;
  (3) repo must stay public through 29 Jan 2027; (4) video must show the project on
  the target (QEMU) and be public YouTube <3:00.

## 12. Confidence notes

- High confidence: structure, CLI/API/UI inventories, test counts, pack verification,
  CI behavior, claim-vs-code table rows marked VERIFIED — all from opened bodies or
  commands executed this session (collect-only sums, 51-test docs run, both verify.py).
- Medium confidence: E2E/adversarial/planning sub-counts (collection-verified, bodies
  not executed); pack file-count interpretation (verify.py exclusion hypothesis fits
  35→34 and 37→36 exactly but is not stated anywhere).
- Not verified (out of scope per task limits): full test-suite execution, browser E2E
  execution, native QNX campaign re-run, AI-eval reproduction (forbidden by freeze
  policy), line-by-line audit of the 41 audit docs or PROGRESS.md body.
