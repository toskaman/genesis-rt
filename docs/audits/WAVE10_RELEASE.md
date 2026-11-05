# Wave 10 release report — Grand Prize finalization

Date: 2026-11-05. HEAD: `e44a5ab` (Sprint E) + Sprint F gates (this
commit). CI host-ci on Sprint E: SUCCESS (run 42115128259, 2m42s);
Sprint F docs-only delta re-verified locally (docs guard 11/11)
and covered by the CI run on this commit (see run history).

## Engineering results

- Full suite green with SDK: **906/906, 0 skips** (621 unit + 285
  rest, incl. 2 real-browser E2E). SDK-free: 901 passed + the same 5
  long-standing honest skips (no new SDK-gated test in Wave 10 E/F).
- QNX: `qcc` 0 warnings; 16/16 on-target matrix from the Sprint A
  fresh campaign; qnx_build tests green locally.
- Codegen deterministic (pinned by suite); C/Python conformance now
  covers 41 vectors incl. float32 wire-fidelity boundaries (E3 found
  and fixed an exact-limit oracle divergence).

## Product (judge journeys)

- Machine→native-QNX→passport from Studio (Target Runner tab).
- 7-stage guided Judge Mode, real-browser E2E in CI (2 live jobs,
  zero console errors); host path only — no QEMU in CI.
- One-click dossier ZIP (`/target/ops/{id}/dossier`), inline
  release-decision panel (`/decision`), before/after op compare
  (`/compare`).
- Counterexample Explorer with pinned ce-001 + before/after
  regression; Evidence Graph with no-dangling-edge invariant (E3).

## Security

- Round 1: cross-operation substitution fixed. Round 2 (E3,
  `docs/audits/RED_TEAM_ROUND2.md`): 5 attacks — cross-target perf
  splice FIXED, op-id reuse FIXED, false `verified_by` edges FIXED,
  version games RESISTED+pinned, clock games RESISTED+pinned.
- Residuals: operator-asserted timestamps (no trusted clock), no
  hardware attestation, point-in-time swap after verify, unsealed
  op-record files, QEMU-only.

## Evidence

- Public pack `evidence/qnx8-x86_64-verified-b22cea1/`: passport
  chain 15 links, 16/16 matrix, 1000 samples, anchor-verified;
  `verify.py` OK from a fresh GitHub clone (Sprint F).
- Tamper control: verifier rejects the mutated bundle (suite).
- Soak (`docs/audits/SOAK_WAVE10.md`): 25 mixed jobs + cancel storm,
  threads 2→2, +18 KiB heap, 1.1 MiB deliberate retention, no
  strays. Gaps disclosed: no SSE/browser-restart automation, no
  disk-pressure test, no 24 h run.

## Judge experience

- Fresh-clone path: clone → pack verify OK → smoke 49/49 green.
- Codelabs base + advanced verified; Devpost draft + video assets
  (42 s genuine footage, narration, subtitles, shot map) ready.
- NOT done by the agent: final edit, voice track, YouTube upload
  (owner handoff — see `docs/demo/` + video plan).

## Commercial impact

- Bench v2 vs a competent stock-jsonschema reference (8 vs 30+10
  commands, 5/5 vs 3/5 faults), machine/human time separated.
- F9 competitive matrix graded (verified/vendor-claim/assessment/
  hypothesis); pilot kit complete; no invented customers.
- F7: no AI provider available — offline planner stays sole
  provider, documented. F8: no second scenario — flagship quality
  protected, `docs/EXTENDING_MACHINES.md` instead.

## Competition compliance

`docs/compliance-matrix.md` re-checked 5 Nov 2026 against the live
rules: deadline Dec 15 2026 2pm EST, Developer Tooling & Host Tools,
Apache-2.0 detectable, repo created Nov 4 inside the entry window,
zero QNX-proprietary paths tracked, video/publication pending owner.

## Scores (self-assessment, evidence-backed)

Technology 9/10 (10 needs real hardware + HAM). Design 8/10 (CI E2E
is host-only; no dossier PDF). Impact 7/10 (pilots unvalidated).
Innovation 8/10 (no LLM adapter). See `docs/jury/JUDGE_SCORECARD.md`.

## Remaining work (priority order)

1. Owner: video edit + voice + YouTube upload + Devpost submit.
2. Optional pilots (kit ready) to move Impact past hypothesis.
3. 24 h wall-clock soak; SSE-reconnect automation.
4. ARM/real-board campaign when hardware is available.
