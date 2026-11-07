# Canonical claim registry (Wave 12, 2026-11-06)

Single prose source of truth for current-facing claims. Machine values
live in `host/genesis_rt/facts.py`; `tests/unit/test_docs_consistency.py`
pins the docs below to them. Dated reports under `docs/audits/` keep
their own historical numbers.

## Test counts

- Collected total: **1166** (`facts.TESTS_WITH_SDK`; with the SDK all run, 0 skips).
- SDK-free (measured 7 Nov 2026): **1161 passed + 5 honest skips** (3 QNX-build + 1 SDK-only
  codelab + 1 real-build target op).
- Adversarial passport suite: **24** (`facts.ADVERSARIAL_TESTS`).
- Planning eval: **28/28** (`facts.PLANNING_EVAL_CASES`).
- Real-browser E2E: **21** collected from `tests/e2e/` (in CI).

Verify: `python -m pytest tests/ -q`
(# with SDK / SDK-free per environment).

## Native QNX verification

- Platform: `qnx8_x86_64_qemu` — QNX SDP 8.0, qcc 12.2.0, QEMU x86_64.
- Matrix: **16/16** (`facts.TARGET_MATRIX_CHECKS`), 1000 perf samples,
  9/9 native fault-injection checks over IPC.
- Change proof: BEFORE (IR 1.2 m/s, op-d08d3d3ea346) and AFTER
  (IR 1.6 m/s, op-67a4595a858f) both PASS; 1.5 m/s probe flips
  DENY → ALLOW; stale-build Campaign C refused with no passport.
- Contract-aware oracle: expectations derive from the validated IR,
  not fixed thresholds (`scripts/qnx_target.py`, `v2_transitions` /
  `limits_differ`).

## Evidence packs (current)

- `evidence/qnx8-x86_64-w11-before/` — BEFORE passport + transcripts.
- `evidence/qnx8-x86_64-w11-after/` — AFTER passport + transcripts.
- `evidence/w11-before-after/` — comparison manifest (links only).
- Each pack: 34 files, 15-link passport chain, stdlib `verify.py`
  (no SDK needed). Legacy `evidence/qnx8-x86_64-verified-b22cea1/`
  is superseded for current claims.

Verify: `python <pack>/verify.py <pack>` → exit 0, `VERIFY OK`.

## Supported platforms

- Host: Windows + Linux (see `docs/INSTALL.md`).
- Target: QNX 8.0 x86_64 on QEMU (see
  `docs/quickstart-qnx8-qemu.md`). No physical hardware required;
  no hardware behavior claimed beyond QEMU observations.

## CI behavior

- `.github/workflows/host-ci.yml`: host suite + real-browser E2E.
- `.github/workflows/qnx.yml`: QNX-gated native workflow.
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
