# Canonical claim registry (Omega4 baseline 2026-11-09, OMEGA5 current; mechanism since Wave 11/12)

Single prose source of truth for current-facing claims. Machine values
live in `host/genesis_rt/facts.py`; `tests/unit/test_docs_consistency.py`
pins the docs below to them. Dated reports under `docs/audits/` keep
their own historical numbers. Historical pack references (W11 and
earlier) are kept in the packs section as dated history, never as
current evidence.

## Test counts

- Collected total: **1431** (`facts.TESTS_WITH_SDK`; SDK-run skips are
  per-machine — the 2 axe scans skip without `node_modules/axe-core`).
- SDK-free (9 Nov 2026 + OMEGA6): **1425 passed + 6 honest skips** (3 QNX-build + 2 SDK-only
  codelab + 1 real-build target op).
- Adversarial passport suite: **24** (`facts.ADVERSARIAL_TESTS`).
- Planning eval: **28/28** (`facts.PLANNING_EVAL_CASES`, the 28-case
  published eval dataset — distinct from the 73 planning unit
  regression tests in `tests/unit/test_planning.py`).
- Real-browser E2E: **41** collected from `tests/e2e/` (`facts.E2E_BROWSER_TESTS`):
  23 judge-journey + negative-path tests, 3 axe-core WCAG 2.2 / 320 px
  reflow tests, 6 application-shell tests (routing, history, keyboard,
  200 %/400 % zoom emulation), 9 K1 Prove-acceptance tests (real click,
  states, widths, keyboard, zoom, degraded). All 41 run in host CI
  (all 41 also run SDK-free — no E2E test is SDK-gated). On a machine
  without `axe-core` in `node_modules` the 2 axe scans **skip**
  visibly — that is the "2 skipped" in bare Windows + SDK runs
  (bare SDK run without axe: 1429 passed + 2 skipped of 1431
  expected — the OMEGA4 no-axe run measured 1346 + 2 of 1348,
  and the +28 OMEGA5, +19 TITAN V3 and +36 OMEGA6
  tests are axe-independent; the previous 1337-tree run needed one retry after a
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
  `v2_transitions` as designed (operator-recorded negative
  control — prose-grade, no sealed transcript ships in the
  packs; sealing it is future work).
- Contract-aware oracle: expectations derive from the validated IR,
  not fixed thresholds (`scripts/qnx_target.py`, `v2_transitions` /
  `limits_differ`).

## Evidence packs (current)

- `evidence/qnx8-x86_64-omega2-before/` — BEFORE passport +
  transcripts (34 payload files + verify.py, op-d91bd4133590).
- `evidence/qnx8-x86_64-omega2-after/` — AFTER passport +
  transcripts (36 payload files + verify.py, op-6840da0e9f69).
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

- Latest blind set: **v9** (160 cases, 48 valid + 112 reject,
  EN/FR/DE/ES x40, 36-case fallback cohort, separately
  agent-authored against contract v1.3 with NO format example,
  frozen 54e08384): offline **142/160**, Qwen 2.5 7B and Llama
  3.1 8B **150/160** each — **5 unsafe accepts of 112**
  reject-labelled cases (4.5%, same 5 deterministic-layer cases
  on all providers), **0 wrong-kind accepts** (kind-evidence
  boundary held), 34 direct consults of 36 eligible per model.
  Consultation conformance enforced: 8 missing (bare value-less
  nouns blocked by the limit-gate — code violates rule 18 as
  written) + 6 unexpected (5 unsupported-vocabulary gaps, 1
  missing German "Greifer" alias), all 14 explained
  deterministically, identical on both models.
- Previous blind set v8 (100 cases, v1.2 code): offline 82/100,
  Qwen 90/100 (4 wrong-kind), Llama 92/100 (3 wrong-kind);
  4 unsafe accepts; 25 consults per model. Provenance,
  qualified: separately agent-authored, zero verbatim overlap,
  with limited prior-set format-preview exposure (one v7 case
  shown for format; a tool preview exposed ~20 v7 valids).
  NEVER rerun on changed code.
- Previous blind set v7 (120 cases, v1.1 code): offline
  83/120 (30 unsafe accepts), Qwen 82/120 (37), Llama
  79/120 (39); 20 consults per model; 30 shared
  deterministic-layer accepts. Motivated fix-1; NEVER rerun.
- Previous blind set v6 (72 cases): 46/72 on all three
  providers identically, 26 unsafe accepts, model consulted
  zero times (latency-inferred; deterministic layer only).
  3 bare-kind contract disputes adjudicated in v1.1, NOT
  silently reclassified. Outcomes preserved.
- v1.3 implementation (built after frozen v8, measured on fresh v9): semantic
  safety frames + scoped negation, Förderband tier-1 alias,
  tugger tier-2 registry, kind-evidence boundary with
  clarification-required (model proposes, registry disposes),
  explicit-value protection. Covered by 12 red-then-green test
  cases (8 test functions, one 5-way parametrized) with fresh
  phrasings — v8 was NEVER rerun on this code.
- Metric vocabulary (never merged): unsafe accepts (reject→IR —
  code-defined, so v9's 5 include the v9-110 fleet-count accept
  alongside 4 safety-semantic accepts), wrong-kind accepts (valid
  label, wrong-kind IR), true false rejects (valid label,
  refused), exact valid accepts, expected-vs-actual consults.
  Overall accuracy alone proves nothing about safety.
- Post-fix regression (NOT generalization): v4/v5 offline
  36/36 after hardening-2 — development-touched sets,
  reported for regression only.
- Measurement ladder (never merged into one percentage):
  frozen history (98-case, v2/v3) → regression
  (v4/v5 postfix) → blind agent-authored (v6, v7, v8-qualified, v9) →
  model-fallback (v7: 20 consults; v8: 25; v9: 34 of 36
  eligible, 14 mismatches explained) → human (none).
- No general-robustness claim from 100-160 cases. Model
  refusal reasons are unreliable; only accept/refuse
  outcomes scored. The model never authorizes safety — the
  deterministic gate decides (pinned by tests).
- Canonical: `docs/audits/OMEGA5_AI_EVALUATION.md` (+ raw
  `evals/results/2026-11-09-omega5-v9/`); consultation audit in
  `docs/audits/OMEGA5_CONSULTATION_AUDIT.md`; v7/v8 report in
  `docs/audits/OMEGA4_AI_EVALUATION.md` (with the 9 Nov
  consultation addendum); v6 in `docs/audits/OMEGA3_AI_EVALUATION.md`;
  history in `docs/ascension/AI_EVALUATION.md`.

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
