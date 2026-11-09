# Canonical claim registry (Omega2/Omega3, 2026-11-08; mechanism since Wave 11/12)

Single prose source of truth for current-facing claims. Machine values
live in `host/genesis_rt/facts.py`; `tests/unit/test_docs_consistency.py`
pins the docs below to them. Dated reports under `docs/audits/` keep
their own historical numbers. Historical pack references (W11 and
earlier) are kept in the packs section as dated history, never as
current evidence.

## Test counts

- Collected total: **1340** (`facts.TESTS_WITH_SDK`; SDK-run skips are
  per-machine — the 2 axe scans skip without `node_modules/axe-core`).
- SDK-free (9 Nov 2026 + Omega4 P0 contract): **1334 passed + 6 honest skips** (3 QNX-build + 2 SDK-only
  codelab + 1 real-build target op).
- Adversarial passport suite: **24** (`facts.ADVERSARIAL_TESTS`).
- Planning eval: **28/28** (`facts.PLANNING_EVAL_CASES`, the 28-case
  published eval dataset — distinct from the 52 planning unit
  regression tests in `tests/unit/test_planning.py`).
- Real-browser E2E: **32** collected from `tests/e2e/` (`facts.E2E_BROWSER_TESTS`):
  23 judge-journey + negative-path tests, 3 axe-core WCAG 2.2 / 320 px
  reflow tests, 6 application-shell tests (routing, history, keyboard,
  200 %/400 % zoom emulation). All 32 run in host CI. On a machine without
  `axe-core` in `node_modules` the 2 axe scans **skip** visibly — that is
  the "2 skipped" in bare Windows + SDK runs (9 Nov 2026 Windows +
  SDK run: 1338 passed + 2 skipped of 1340, zero failures, first
  attempt; the previous 1337-tree run needed one retry after a
  transient Playwright `networkidle` E2E timeout that passed in
  isolation — no browser-served file changed, so not a regression).
- Vocabulary: *collected* = found by pytest; *passed*/*skipped* = outcome
  of one run on one machine. A collected total is never reported as a
  pass count.

Verify: `python -m pytest tests/ -q`
(# with SDK / SDK-free per environment).

## Native QNX verification

- Platform: `qnx8_x86_64_qemu` — QNX SDP 8.0, qcc 12.2.0, QEMU x86_64.
- Matrix: **16/16** (`facts.TARGET_MATRIX_CHECKS`), 1000 perf samples,
  9/9 native fault-injection checks over IPC.
- Change proof (Omega2, 8 Nov 2026): BEFORE amr v1
  (op-d91bd4133590) and AFTER amr v2 (op-6840da0e9f69), both
  sealed PASS, qnx_verified=True, replay matches. The v1→v2
  change is governance (guarded transitions), not limits
  (1.2/1.0 m/s both) — stale is caught behaviorally:
  STALE control 14/16, failing exactly on `estop_target` +
  `v2_transitions` as designed.
- Contract-aware oracle: expectations derive from the validated IR,
  not fixed thresholds (`scripts/qnx_target.py`, `v2_transitions` /
  `limits_differ`).

## Evidence packs (current)

- `evidence/qnx8-x86_64-omega2-before/` — BEFORE passport +
  transcripts (34 files, op-d91bd4133590).
- `evidence/qnx8-x86_64-omega2-after/` — AFTER passport +
  transcripts (36 files, op-6840da0e9f69).
- Each pack: 15-link passport chain, stdlib `verify.py`
  (no SDK needed). Trust: hash-only, UNSIGNED
  (`verify-pack --trust local` → exit 2, no signer bound;
  integrity is SHA-256, not cryptographic attestation).
- Historical (superseded for current claims):
  `evidence/qnx8-x86_64-w11-before/`,
  `evidence/qnx8-x86_64-w11-after/`,
  `evidence/qnx8-x86_64-w11-after-rerun/` (7 Nov 2026,
  op-24fecbf11df8, third binary set for the 18/18 rebuild),
  `evidence/w11-before-after/` (comparison manifest),
  legacy `evidence/qnx8-x86_64-verified-b22cea1/`.

Verify: `python <pack>/verify.py <pack>` → exit 0, `VERIFY OK`.

## Supported platforms

- Host: Windows + Linux (see `docs/INSTALL.md`).
- Target: QNX 8.0 x86_64 on QEMU (see
  `docs/quickstart-qnx8-qemu.md`). No physical hardware required;
  no hardware behavior claimed beyond QEMU observations.

## AI evaluation (current)

- Latest blind set: **v6** (72 cases, 24 valid + 48 reject,
  separately agent-authored, frozen before the fixes):
  **46/72 on offline, Qwen 2.5 7B and Llama 3.1 8B
  identically** — 24/24 valid, 22/48 rejects,
  **26 unsafe accepts**, 0 false rejects. The model was consulted
  **zero times** (deterministic short-circuit on every
  case); v6 measures the deterministic layer only.
- v6 open findings: 26 accepted reject-labelled cases
  (novel paraphrases, multilingual removal, evasion,
  injections); 3 bare-kind cases are explicit contract
  disputes (adjudicated in the v1 planner contract —
  bare kind accepted only with output-disclosed
  defaults), NOT silently reclassified.
- Post-fix regression (NOT generalization): v4/v5 offline
  36/36 after hardening-2 — development-touched sets,
  reported for regression only. The 12 v5 failure
  classes are fixed; v6's 26 are the open set.
- Measurement ladder (never merged into one percentage):
  frozen history (98-case, v2/v3) → regression
  (v4/v5 postfix) → blind agent-authored (v6) →
  model-fallback (unmeasured until v7) → human (none).
- **v7 required**: ≥120 fresh blind cases with a real
  model-fallback cohort and direct consult counts before
  any new generalization claim. No general-robustness
  claim from 72 cases.
- Model refusal reasons are unreliable; only accept/refuse
  outcomes scored. The model never authorizes safety —
  the deterministic gate decides (pinned by tests).
- Canonical: `docs/audits/OMEGA3_AI_EVALUATION.md` (+ raw
  `evals/results/2026-11-08-omega3-v6/`); history in
  `docs/ascension/AI_EVALUATION.md`.

## CI behavior

- `.github/workflows/host-ci.yml`: host suite + real-browser E2E.
- `.github/workflows/qnx.yml`: BUILD-ONLY, NOT EXECUTED — no
  registered self-hosted runner; native evidence comes from
  owner-machine campaigns, honestly labeled per run.
- `scripts/ci_ir_check.py`: validates changed Machine IRs
  (`examples/**/*.json`, `projects/**/*.json`, renames tracked,
  deletions verdict-neutral) and reports impact; also emits the
  ProofOS verification plan (`proofos-plan.json`, schema
  `host/genesis_rt/proofos.py`), which never grants release
  eligibility by itself.
- PR checks diff against the genuine PR base; push checks against
  the push base (first-push zero-SHA falls back to all IRs).
  Public runners never see QNX credentials or proprietary assets.

## Video status

- **Status: `DEFERRED_BY_OWNER`; final submission `PENDING_VIDEO`**
  (`submission/VIDEO_DEFERRED.md`). The entries below describe the
  historical W12 cut only — it is not the final submission video.
- Historical cut: `docs/demo/genesis-rt-demo-w12.mp4`
  (**154.664 s**, 1920x1080 H.264 + AAC voiceover, faststart).
- Captions: `docs/demo/subtitles-w12.srt` (21 cues, verbatim).
- Voice source: `docs/demo/voiceover-w12.flac` + `voiceover-w12.txt`
  (local Piper TTS, deterministic render).
- Validation: `docs/demo/MEDIA_VALIDATION_W12.md`.
- **YouTube publication PENDING** (owner account action) — never
  claim a public URL until it exists (`PUBLICATION_HANDOFF_W12.md`).

## Codelab URLs

- https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/README.md
- https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/ADVANCED-QNX.md
- https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/EXTERNAL-BUILD.md

## Known limitations (current)

- Host fault results are simulated; only the target matrix runs
  natively (labeled `qnx_verified` in every passport).
- QEMU timing is for regression comparison, not production or
  worst-case guarantees.
- Simulation-only outputs; prototype-grade; no functional-safety
  qualification and no safety certification claimed; no hardware
  attestation.
- No external customer pilots yet (`docs/business/pilot-study.md`
  records zero invitations); no measured human productivity gain.
- Demo voiceover is synthetic (Piper TTS) and phoneme/level-verified;
  owner listen-once still pending.

## Product features (current)

- Machine IR designer, deterministic QNX codegen, Target Runner,
  guided Judge Mode, Evidence Graph, Digital Twin, Counterexample
  Explorer, change-impact analysis, release-decision explanation,
  native before/after comparison, IPC execution timeline
  (`evidence/ipc-timeline/`), engineering dossier ZIP export.
