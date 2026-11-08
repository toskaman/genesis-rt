# Canonical claim registry (Omega2/Omega3, 2026-11-08; mechanism since Wave 11/12)

Single prose source of truth for current-facing claims. Machine values
live in `host/genesis_rt/facts.py`; `tests/unit/test_docs_consistency.py`
pins the docs below to them. Dated reports under `docs/audits/` keep
their own historical numbers. Historical pack references (W11 and
earlier) are kept in the packs section as dated history, never as
current evidence.

## Test counts

- Collected total: **1331** (`facts.TESTS_WITH_SDK`; SDK-run skips are
  per-machine — the 2 axe scans skip without `node_modules/axe-core`).
- SDK-free (8 Nov 2026 + Omega3 INT jury-attack): **1325 passed + 6 honest skips** (3 QNX-build + 2 SDK-only
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
  the "2 skipped" in bare Windows + SDK runs (8 Nov 2026 Windows +
  SDK run: 1329 passed + 2 skipped of 1331, zero failures; an earlier
  run's single failure was a stale read from editing the devpost draft
  while the suite ran).
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

- Frozen sets: v4 32/32/31 of 36 (offline/qwen/llama), v5
  24/36 × 3 identical (12 unsafe accepts, 0 false rejects).
  72 untouched cases total; both sets small and same-author.
- 12 v5 unsafe-accept classes are measured and OPEN; the
  model never authorizes safety (deterministic gate decides).
- Model refusal reasons are unreliable; only accept/refuse
  outcomes scored. No general-robustness claim.
- Canonical: `docs/ascension/AI_EVALUATION.md`.

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
