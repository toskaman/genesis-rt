# Wave 11 release report — native proof excellence (2026-11-06)

Wave 11 question: can an engineer change a valid machine contract,
rebuild the controller, observe the predicted behavior change, and
hold a new valid body of evidence — while a genuinely wrong change is
still rejected? Status: **IMPLEMENTED**, end to end, with the
externals (voice track, YouTube upload, Devpost submission) pending
owner action.

## 1. Latest GitHub state

- Repo: `https://github.com/toskaman/genesis-rt`, branch `main`.
- Wave 11 commits (this session): `c45beb1` Phase A (oracle +
  BEFORE/AFTER passports, 994/994), `321d22d` Phase B (E2E + video),
  `4d225a9` + `89afce5` Phase B fixes (SDK-less CI, openJob
  re-attach), `805ef7b` Phase C (CI check + dossier + IPC timeline +
  bench), `6a0fe75` Phase D (SSE storm + store pressure + soak100).
  Phase E commit follows this report.
- CI (`host-ci`, SDK-less Ubuntu): success on `89afce5`
  (run 42139173723, 10m54s) and `805ef7b` (run 42143731534, incl. the
  live GENESIS IR check step: diff 89afce5...805ef7b, 0 IR files,
  verdict PASS) and `6a0fe75` (run 42144193668, success).
- Local suite: 1051/1051 green with SDK (0 skips); SDK-free shape
  1046 + 5 honest skips (3 QNX-build + 1 SDK-only codelab + 1
  real-build target op), pinned by `host/genesis_rt/facts.py` and
  `tests/unit/test_docs_consistency.py`.

## 2. Engineering changes

- Phase A: `host/genesis_rt/native_oracle.py` (contract-aware
  oracle: EXPECTED_DENY/ALLOW/SAFE_STOP/ERROR/INCONCLUSIVE/
  UNSUPPORTED from the validated IR, float32 wire fidelity),
  bound `limits_differ` parser, 87 oracle/binding unit tests.
- Phase B: change-proof compare UX (§7: limit, #define, guard sha,
  1.5 probe, compare ZIP), 19 negative + 2 judge real-browser E2E
  (`tests/e2e/`), two Studio bug fixes (tab-switch re-attach,
  `/validate` ir_sha256 pin), `openJob` always-stream re-attach fix.
- Phase C: `scripts/ci_ir_check.py` + host-ci wiring (per-push IR
  validation + impact + retest verdict), dossier TOC/coverage/print
  CSS, env-gated `GENESIS_IPC_TRACE` in guard + faultinject with
  `host/genesis_rt/ipc_timeline.py` parser, benchmark re-run.
- Phase D: SSE storm tests, store-pressure tests, 100-job soak.
- Counts: 906 (Wave 10) → 994 (A) → 1014 (B) → 1015 (openJob
  regression) → 1046 (C, +31) → 1051 (D, +5). Every delta is named
  tests; no count was edited without a matching run.

## 3. Contract-aware verification

Root cause: `limits_differ` compared native guard behavior against a
fixed threshold assumption. BEFORE (1.2 m/s) DENY at 1.5 was correct;
AFTER (1.6 m/s) ALLOW at 1.5 was equally correct — the expectation,
not the guard, was wrong. A changed behavioral expectation is not a
safety regression.

Fix: the oracle derives the expected verdict from the validated IR +
machine kind + generated policy (below/at/above limit probes,
boundary float32 vectors, invalid states, estop, stale sensors,
deadlines, provenance freshness). Unsupported machine kinds fail
closed as UNSUPPORTED; legacy single-probe logs under a binding fail
closed. The fixed-threshold path is kept for unattested legacy logs
only.

Anti-cheating: expectations are IR-derived, not observed-fitted;
`test_vectors_are_not_vacuous_mutation` plus flipped-verdict /
wrong-machine / wrong-limit tests prove an incorrect guard still
fails. Files: `native_oracle.py`, `tests/unit/test_native_oracle.py`
(60), `test_limits_differ.py` (16), `test_limits_differ_binding.py`
(11).

## 4. Native BEFORE/AFTER evidence

- Campaign A (BEFORE, 1.2 m/s): `op-d08d3d3ea346`, IR 1.2,
  COMPLETED, 16/16 PASS, sealed passport, replay clean.
- Campaign B (AFTER, 1.6 m/s): `op-67a5595a858f`, IR 1.6,
  COMPLETED, 16/16 PASS, sealed passport, replay clean. IR digest,
  generated policy, binary digest and the 1.5 m/s probe (DENY→ALLOW)
  all moved in the predicted direction; safety invariants held.
- Packs: `evidence/qnx8-x86_64-w11-before` and
  `evidence/qnx8-x86_64-w11-after` (34 files each), both `verify.py`
  OK on 2026-11-06 (op COMPLETED, gate PASS, 16/16, 1000 samples,
  qnx_verified True). Comparison manifest:
  `evidence/w11-before-after/COMPARISON.md` + `comparison.json`
  (provenance chains kept independent, never conflated).
- Jury narrative: `docs/jury/BEFORE_AFTER_NATIVE.md` (digests + flip).
- Final-sources confirmation op `op-ca900c25406f` (amr-demo, full
  workflow over the Wave 11 tree incl. the env-gated trace, fresh
  `w11-formal` build set): COMPLETED, gate PASS, 16/16, 1000 perf
  samples, qnx_verified True, replay PASS — the trace code changes
  nothing with the flag off. Local record
  `artifacts/runs/target-ops/op-ca900c25406f/` (reproducible via the
  Task-4 recipe with `artifacts/runs/w11-formal/`).

## 5. Negative safety evidence

- Campaign C: `op-ad562b34f8de` (stale-build fixture), FAILED on
  `limits_differ` only, no passport sealed — the oracle detects the
  violation, the gate refuses, the error is actionable and
  reproducible (`docs/jury/BEFORE_AFTER_NATIVE.md`, Phase A notes).
- Live fail-closed proof: `op-03090cb5e414` (final-sources run
  whose QEMU guest was killed externally mid-matrix) FAILED honestly
  at `qemu_verify` ("SSH session not active"), ran cleanup, sealed
  no passport — a dead target can never yield a green verdict.
- Host-level negatives stay green: dossier tamper rejection,
  passport chain tamper E2E, bogus image dir, invalid IR/JSON,
  backend outage — all fail closed with honest UI states, covered by
  `tests/e2e/test_negative_browser.py` (19 paths) running in CI.

## 6. Studio experience

- One-click machine→native-QNX→passport flow preserved from Wave 10;
  Wave 11 adds the change-proof compare (contract, code, binary,
  behavior, verification, evidence, release, provenance in one
  synchronized view, `host/genesis_rt/dossier.py` compare + ZIP).
- Real bug found and fixed by CI: `openJob` rendered finished jobs
  as "state active / phase queued" (empty-events terminal path).
  Slow runners re-attached after completion and hit it every time.
  Fix: always re-attach via the event stream (server replays ordered
  history, then closes) — the pattern `openTargetOp` already used.
  Regression: `test_reattach_to_finished_job_shows_terminal_state`
  (proven red pre-fix via a 30 s replay gate, green post-fix).
- E2E: 21/21 green locally and in CI (2 judge journey + 19
  negative: guidance, designer, cancel/refresh/navigation, tampered
  passport, target errors, flagship limit-change compare, outage,
  3-viewport audit). SDK-less branches verified locally by pointing
  QNX_TARGET at a nonexistent dir (sdk_present False).
- Dossier review UX: section TOC + anchors, coverage row
  (full/targeted/unknown from the gate record), print CSS.

## 7. Demonstration video

- Final: `docs/demo/genesis-rt-demo-w11.mp4`, 154.6 s, 1920×1080,
  H264/yuv420p, 5.2 MB, silent by design + `subtitles-w11.srt`
  (21 cues) + `NARRATION_W11.md` + `SHOT_EVIDENCE.md` mapping every
  shot to verifiable software (capture: `capture_w11.py`,
  assemble: `assemble_w11.py`, duration asserted < 180 s).
- Covers: problem, cell, IR→C→qcc, QEMU target run, fault injection,
  Twin/Explorer/Graph diagnosis, before/after contract change with
  two valid passports, tamper rejection, dossier close.
- PENDING (owner handoffs, explicitly not claimed done): voice track
  (no TTS/mic in this environment) and public YouTube upload.

## 8. Security

- No new attack surface in Wave 11: the CI script shells to git via
  argv lists (no shell), diffs pinned paths, and writes a local JSON
  report; the C trace is a default-off printf path; the timeline
  parser is a pure function over log text.
- Standing posture (Wave 9–10, re-verified by suite): all
  state-changing API methods covered, localhost trust model
  documented, no generic shell for the frontend (allowlisted ops),
  bounded job admission (429), path validation, secrets server-side
  (`GENESIS_TARGET_PASSWORD` env-only, never committed or logged).
- Residuals: point-in-time swap after verify, unsealed op event
  rows, operator-asserted clocks, no hardware attestation. No
  safety-certification claims anywhere; dossiers disclaim it.

## 9. Reliability

- `docs/audits/SOAK_WAVE11.md`: 100-job one-shot, 108.1 s, 90 ok /
  10 fail-fast, threads 2→2, heap +202 KiB, DB 57 KiB→2.9 MiB
  (passports retained by design, linear).
- SSE storms: 50 sequential + 5 concurrent reconnects replay the
  full ordered history; worker count unchanged
  (`tests/integration/test_sse_storm.py`).
- Store pressure (contained, no real-volume fill): unusable
  artifact root fails the job honestly with cause; a healthy
  manager keeps serving (`tests/unit/test_store_pressure.py`).
- E2E lifecycle: cancel/refresh/navigation races hardened
  (`_pick_slowest_example`, `_cancelled_or_completed`); full-suite
  runs on this loaded Windows box hit three transient flake classes
  (Playwright driver deaths; build-only op FAILED 2/6; one op stuck
  non-terminal 120 s with the suite at 6m10s vs ~4 min), each green
  on isolated re-run (this one: 5.47 s standalone) and never in CI.
  Final 1051/1051 recorded from a clean idle-box run.
- Gaps (not claimed): no 24 h wall-clock run, no full-disk fill, no
  multi-day retention aging, transient build-only FAILED 2/6 under
  load documented as suspected Windows toolchain hiccup with diag
  (5 greens since; re-open if it recurs).

## 10. Commercial value

- Benchmark v2 re-run 2026-11-06 (`bench/productivity/REPORT.json`):
  identical totals — 8 GENESIS vs 30 reference + 10 manual steps,
  faults 5/5 vs 3/5, reproducible True. Machine time only, synthetic
  reference labeled, no labor-savings estimate, no pilot claimed.
- Pilot kit (`docs/business/pilot-study.md`): task set, both-lane
  templates, survey, privacy/anonymization, repro scripts, reviewer
  checklist — ready to send, zero teams run yet (honest).
- Adoption bridge (§11, NEW): `scripts/ci_ir_check.py` in `host-ci`
  validates changed IRs per push, reports impact + retest verdict +
  step summary + report artifact (proven live in CI run 42143731534).
- Buyer docs: commercial vision, competitive landscape, value
  methodology all current-dated. No fabricated customers, revenue,
  or superiority claims.

## 11. QNX depth

- Contract-aware oracle over the real 16-check native matrix;
  qcc 12.2.0 builds with 0 warnings (incl. the new trace code).
- NEW: native IPC execution timeline from real CLOCK_MONOTONIC
  stamps (`evidence/ipc-timeline/`, QEMU-tcg, 5 probes, 0 errors):

  | probe | round trip | guard span | decision |
  | ----- | ---------- | ---------- | -------- |
  | 1 | 1292.211 µs | 520.292 µs | ALLOW |
  | 2 | 392.869 µs | 123.575 µs | ALLOW |
  | 3 | 981.641 µs | 205.878 µs | ALLOW |
  | 4 | 641.882 µs | 192.832 µs | ALLOW |
  | 5 | 872.675 µs | 211.911 µs | ALLOW |

  Each bench SAMPLE delta independently equals the parser's
  DONE−SEND. QEMU timings are regression aids, not hardware
  guarantees; device-forward events have no stamps and render as
  unknown, never invented.
- 16/16 matrix + 1000 native perf samples per campaign; supervisor,
  crash containment, stale-sensor, estop and deadline behavior all
  exercised on target. No HAM (absent from image), no real board.

## 12. Competition compliance

- Public repo, Apache-2.0, genuine QNX 8.0 relevance, accurate
  build/run instructions, toolchain/target identified (qcc 12.2.0,
  QEMU x86_64 tcg), one category: Developer Tooling & Host Tools.
- Demo video < 3 min, authentic footage, editable subtitles; voice
  + YouTube upload PENDING (external).
- Codelabs preserved (prompt + advanced QNX tutorial); stable URLs
  in repo docs.
- Rules re-checked 2026-11-06: deadline Tue Dec 15, 2026 2:00 PM
  EST confirmed via secondary sources (direct rules page 403 to
  bots; owner to confirm on Devpost before submitting). No
  proprietary QNX redistribution, no secrets committed, no
  safety-certification claims, virtual scenarios only.
- Pending externals: Devpost submission text (draft current),
  YouTube publish, voice track, pilot teams.

## 13. Scorecard (evidence-supported, internal only)

- Technology 9/10: oracle + mutation proofs, 2 valid passports +
  negative, IPC timeline, 1051 tests, 16/16 native. Cap: QEMU-only,
  no HW attestation. Evidence: §3–§5, §11.
- Design 9/10: coherent end-to-end product, change-proof UX,
  dossier review UX, 21/21 browser E2E in CI, subtitled video.
  Cap: host-path E2E in CI only, voice missing. Evidence: §6–§7.
- Impact 8/10: pilot kit, refreshed bench, live CI bridge, dossier
  reviews. Cap: zero pilots run, human gains unmeasured (labeled).
  Evidence: §10.
- Innovation 9/10: expectation-vs-regression oracle distinction,
  IPC waterfall, proof-to-decision chain. Cap: offline planner
  only, no LLM adapter. Evidence: §3, §11, evals.
- Not official scores; no placement promised. Full matrix in
  `docs/jury/JUDGE_SCORECARD.md` (Wave 11 row refresh).

## 14. Remaining work

1. Owner: record voice track, publish YouTube, file Devpost entry.
2. Run 2–3 pilots from the kit; record before/after numbers.
3. Real-board/ARM campaign + HAM when available; 24 h soak; full-disk
   and retention aging if a scratch volume appears.
4. Second industrial scenario (warehouse sorting) deferred: flagship
   quality over breadth. LLM adapter deferred: no provider; core
   stays offline-capable.
5. Re-open if recurs: transient build-only FAILED under load;
   Playwright driver flake on loaded Windows boxes.
