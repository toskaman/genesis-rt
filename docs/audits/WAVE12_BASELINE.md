# Wave 12 baseline — TITAN-1 reconnaissance (2026-11-06)

HEAD: `fcc3542` (Wave 11 Phase E), worktree CLEAN, 0 PRs, 0 issues.
CI: last 3 `host-ci` runs SUCCESS (42148205691 Phase E 3m15s,
42144193668 Phase D, 42143731534 Phase C). Workflows: host-ci.yml,
qnx.yml. Rules page: HTTP 403 to bots; fallback press release
(2026-11-02): deadline Dec 15 2026, winners Feb 2027, $50,000.

## Test suite — VERIFIED

- 1051/1051 with SDK, 1046+5 skips SDK-free (`facts.py`).
- Adversarial 24, planning eval 28/28, soak 24-job tripwire in suite.
- Weakness: full-suite runs flake on loaded Windows boxes (3
  transient classes, all green on re-run, never in CI).
- Commercial: regression safety net. Competition: tech depth.
- Priority: keep green; extend only for new behavior.

## Native matrix — VERIFIED

- QNX SDP 8.0, qcc 12.2.0, x86_64 QEMU; 16 checks, 1000 samples.
- Newest op `op-ca900c25406f` COMPLETED/PASS/qnx_verified (02:52).
- Weakness: QEMU-only, no HW attestation, no HAM.
- Priority: preserve; re-run after C changes.

## BEFORE/AFTER packs — VERIFIED

- Both `verify.py` EXIT 0: 34/34 digests, 15-link chain, run_id/IR/
  anchor bindings, 16/16, qnx_verified.
- BEFORE `op-d08d3d3ea346` (IR 356dc135…), AFTER `op-67a4595a858f`
  (IR fb2dbb3d…); `evidence/w11-before-after/COMPARISON.md`.
- Weakness: none known. Priority: reference, don't rebuild.

## Contract-aware oracle — VERIFIED

- `host/genesis_rt/native_oracle.py`: IR-derived
  EXPECTED_DENY/ALLOW/SAFE_STOP/ERROR/INCONCLUSIVE/UNSUPPORTED,
  float32 wire fidelity; 60+16+11 unit tests incl. mutation and
  flipped-verdict anti-cheating; negative Campaign C fails closed.
- Docs: `docs/jury/BEFORE_AFTER_NATIVE.md`. Entry: target verify.
- Weakness: README never mentions it (§5 fix).
- Commercial: the "changed expectation vs regression" differentiator.

## IPC timeline — VERIFIED

- `evidence/ipc-timeline/` (8 files): 5 ALLOW probes, 0 errors,
  SEND→RECV→REPLY→DONE from CLOCK_MONOTONIC; parser
  `host/genesis_rt/ipc_timeline.py` (10 unit + 6 native-sample tests).
- Weakness: CLI/evidence only, no Studio view (§11).
- Priority: Studio integration (P1).

## Studio + dossier — VERIFIED

- `ui/studio.html` (3489 lines): designer, Target Runner, Judge Mode,
  Evidence Graph, Twin, Explorer, compare, dossier ZIP (TOC/coverage/
  print). openJob stream-replay fix verified in CI.
- Weakness: reviewer journey spans tabs; no single review page (§10).
- Priority: review workspace, IPC links.

## E2E browser — VERIFIED

- 21 tests collected (`test_judge_browser.py` + 19 negative):
  guidance, cancel/refresh/navigation, tamper, target errors,
  flagship compare, outage, 3 viewports. Green in CI.
- Weakness: host-path only in CI (no QEMU/SDK lane).
- Priority: extend for new review/timeline UI.

## Video + audio — PARTIAL

- `genesis-rt-demo-w11.mp4`: 5,170,254 B, 154.664 s, h264
  1920×1080 30fps, video-only (ffprobe: no audio stream).
- `NARRATION_W11.md` (~300-word script), 21-cue SRT, assemble script.
- BLOCKED items: voice track (no TTS/mic last wave — re-check),
  YouTube publish (no connected account).
- Priority: P0 §4 (audio investigate → mux → validate → handoff).

## Docs sync — PARTIAL

- STALE (confirmed quotes): `docs/compliance-matrix.md` L11 (42 s
  footage, edit pending), `docs/demo-video-plan.md` L1-26 (Wave 10
  storyboard), README (zero hits for the 5 Wave 11 terms).
- Guards: `test_docs_consistency.py` pins counts + 28/28 eval.
- Priority: P0 §5 (claim registry + fixes + guards).

## Devpost draft — PARTIAL

- Category set, codelab URL set, counts current (1051/1046+5);
  video URL placeholder unfilled; points at stale video plan.
- Priority: P0 (sync with §4/§5 outcomes).

## Commercial kit — PARTIAL

- `docs/business/`: vision, landscape, pilot kit (10 sections,
  zero invitations sent — honest). Bench v2 REPORT.json 2026-11-06:
  8 vs 30+10, faults 5/5 vs 3/5, reproducible, no labor claims.
- Weakness: zero external pilots/participants (the Impact cap).
- Priority: §12 pilot ops assets (no invented customers).

## Codelabs — VERIFIED

- Base (~45 min) + advanced QNX; CI harness
  `test_codelab_advanced.py`; Devpost bonus URLs stable and
  cross-referenced. `cell-controller.md` planned-only, absent.
- Priority: keep CI-enforced; re-verify commands in Wave 12.

## CI bridge — IMPLEMENTED

- `scripts/ci_ir_check.py` + host-ci step (live, proven in run
  42143731534): validates changed IRs, impact + retest verdict.
- Weakness: `github.event.before` push-only semantics, shallow-clone
  fallback, no PR-base handling, no target leg (§7).
- Priority: P1 harden + ProofOS plan (§6).

## Evidence trust — IMPLEMENTED

- Hash-linked passport + independent replay + tamper tests; local
  operator COULD rewrite + recompute (no signing). No auth attestation.
- Priority: P1 §9 (optional Ed25519 signing, unsigned stays usable).

## Reliability — VERIFIED

- Soak100 (108 s, threads 2→2, +202 KiB), SSE storm (50+5),
  store pressure, bounded admission (429), lifecycle/recovery tests.
- Gaps: no 24 h run, no full-disk fill, no API-restart-mid-SSE (§16).
- Priority: §16 extensions with isolated stores.

## AI assistance — MISSING (by design)

- Offline keyword planner only, 28/28 eval; no provider, no adapter.
- Priority: P2 §18 — evaluate only if a legitimate provider exists.

## Second example — MISSING (deferred)

- Warehouse sorting: full 11-gate requirement list; flagship-first.
- Priority: P2 §17 — defer unless time remains.

## Status confirmation method

Every VERIFIED line above was re-observed in this audit (command
output or opened file bodies), not copied from Wave 11 claims —
except Studio/E2E behavior, re-confirmed via file presence + collect
(21 tests) + last CI success; full re-run happens at §19 T+28-34.
