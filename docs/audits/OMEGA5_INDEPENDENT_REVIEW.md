# OMEGA5 independent review (§7 attack)

Date: 9 Nov 2026. Branch `titan-omega5`. Reviewer: separate agent
that implemented nothing (read-only; all evidence from commands
it ran itself). Scope at review time: HEAD `c684466` + dirty
worktree (13 modified files + 1 untracked report); the reviewer
distinguished COMMITTED from WORKTREE throughout. Every finding
below carries a disposition with a test or artifact — nothing was
marked fixed by prose.

## Per-item verdicts

1. v9 provenance — VERIFIED (one sub-claim withdrawn, see P2-1).
   Digest `54e08384…b10eb34a` byte-exact vs the pin; worktree
   file == freeze blob `0cf4e52`. Shape 160 = 48 + 112,
   EN/FR/DE/ES x40, 36 fallback-eligible. Normalized-prompt
   intersection 0/160 vs v4–v8, 0 internal dups (reviewer script
   + new `test_v9_no_verbatim_overlap_with_prior_sets`).
   Contract v1.3 `a9760ce` predates v9 freeze `0cf4e52` in git
   log; rules 13–18 verbatim since; impl `3bb84bf` touched only
   planner/planning/semantics + tests.
2. v9 metrics — VERIFIED (terminology tightened, see P2-3/P2-4).
   Recomputed from raws: offline 142/160, qwen/llama 150/160;
   5 unsafe shared incl. offline (deterministic-layer);
   0 wrong-kind; 34/36 consults each model (28 hits + 6
   unexpected); 14 mismatches identical across models; veto
   split qwen 30 / llama 34 confirmed; raw sha256s match pins.
3. Consultation audit — VERIFIED (wiring test added, see P2-2).
   v7 24/20 + 4 missing, v8 21/25 + 4 unexpected, reproduced by
   running `scripts/audit_eval_consults.py`. Harness
   `consult_verdict` pure and correct; exit-1 path now executed
   by `test_eval_main_exits_1_on_missing_consult`.
4. Planner v1.3 — VERIFIED (count fixed, see P1-1). Code traces
   to contract rules 13–18; every v9 residual/mismatch traces
   to exact code (missing entities, fleet lists, EN-only
   unsupported list, rule-18 gate overreach); 42 omega5 test
   literals 0-verbatim in v4–v9; v8 never rerun (git log).
5. Docs integrity — 3 BREAKS FOUND, all fixed (P1-1/P1-2/P1-3).
   Frozen v4–v8 byte-identical vs origin/main (only 4 added
   files under evals/). No human-benefit/hardware/signing
   overclaim (all hits are explicit negations).
6. Counts — VERIFIED in the final worktree (was P0, fixed by
   committing). tests/ 1376, planning 73, docs pins 51, e2e 32;
   facts.py + all current docs agree. Both Omega2 packs VERIFY
   OK 16/16. No target/ changes vs origin/main.

## Findings and dispositions

- P0 (uncommitted green state; v9 report untracked; HEAD tip red
  on its own count test): FIXED by committing the full final
  tree + re-running the suite green before the PR.
- P1-1 ("11 vs 12" red-green contradiction): FIXED — truth is 8
  test functions / 12 parametrized cases; CLAIMS now says so
  (scorecard/Devpost already said 12). Commit-message wording
  in `3bb84bf` is history and stays.
- P1-2 (`KNOWN_LIMITATIONS.md` stale v8-citing, outside the
  pin): FIXED — rewritten to v9 with qualified v8, and the file
  added to `test_v8_blindness_always_qualified`.
- P1-3 (Devpost raw-log pointer omitted v9): FIXED — leads with
  v9 raws + OMEGA5 report (+ v7/v8/consult-audit pointers).
- P2-1 ("8 pairs" irreproducible): WITHDRAWN — replaced with the
  reproducible scan (198 pairs max-4, all boilerplate, method
  stated) + reviewer's 57 noted; only 0-verbatim is pinned.
- P2-2 (exit-1 wiring untested; v8 wrong-kind IDs unpinned):
  FIXED — stub-provider main() test added; IDs pinned in the
  report (qwen v8-007/010/012/014, llama v8-007/012/014).
- P2-3 (`unsafe_accepts` folds the v9-110 fleet accept): FIXED —
  CLAIMS/Devpost/scorecard now say "4 safety + 1 fleet".
- P2-4 (latency prose nick): FIXED — per-provider p95/max from
  raws (0.86/13.08 qwen, 0.90/14.82 llama). True hits 28/36
  made explicit next to "34/36".

## Independent scorecard: 29/40 (self: 31/40)

Tech 9 (structural: QEMU-only, single host, no native CI, local
crypto 43.0.3 — all disclosed); Design 7 (no SR session, video
deferred, dense page — unchanged since Omega4); Impact 5
(agrees); AI 8 (genuine no-example blind loop, wrong-kind 4/3 →
0 recomputed, enforcement fires; −0.5 open 5/112 + rule-18 +
targeted scope). No 10/10 anywhere. Internal estimate, never an
official prediction.

## Residual risks (explicit, still open)

Rule-18 gate overreach needs v10 contract/code reconciliation;
5 unsafe entity/verb gaps (`interverrouillage`,
`Schutzeinrichtung`, `stummschalten`, bare `paro`, `Roboter`
fleet); Greifer-class tier-1 and non-EN unsupported-vocab gaps;
local crypto 43.0.3 + default QNX password owner-pending; video
deferred; zero pilots. Broad safety: NOT MEASURED.
