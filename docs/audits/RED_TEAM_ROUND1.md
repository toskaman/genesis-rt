# Red-team round 1 — evidence & release falsification (Wave 9 §25)

Date: 2026-11-05. Scope: project environment only. Method: attempt
each §25 falsification against the committed code; a HOLD means an
existing test pins the refusal, a FIND means the attack worked and
was fixed in this round.

## New attacks attempted this round

- **A1 evidence swap at replay: FIND → FIXED.** `_step_replay`
  recomputed chain + gate but never checked the file belongs to
  THIS op: a valid passport sealed for op A (same verdict string)
  swapped onto op B's path replayed as B's. Proven failing, then
  fixed: replay now requires `passport.run_id == op_id` and
  `ir.ir_sha256 == sealed ir_sha256`.
  Tests: `test_replay_rejects_foreign_op_passport`,
  `test_replay_rejects_ir_mismatch` (fail pre-fix, pass post-fix);
  real SDK path still green
  (`test_build_only_op_real_build_seal_replay`).

## §25 item mapping (all other items HOLD)

| Claim attacked | Result | Pinned by |
|---|---|---|
| Fake release eligibility | HOLD | `test_omitted_scenarios_still_block_release`, release banner TARGETED/PENDING tests |
| Fake `qnx_verified` | HOLD | adversarial forged/cross/stale suites (18 collected) |
| Binary provenance / swap | HOLD (point-in-time) | `test_cross_build_record_refused`, `test_modified_staged_binary_refused`, stage-manifest check |
| Target transcripts | HOLD | `test_missing_transcript_digests_capped` |
| Build-set identity | HOLD | `tests/unit/test_buildset.py` rule suite |
| Graph nodes/edges | HOLD | `test_evidence_graph.py` bound True/False; verdict→target edge only when bound |
| Requirements→release | HOLD | `test_impact.py` + `test_impact_api.py` |
| Counterexample reproduction | HOLD | `test_explorer.py` + replay conformance tests |
| Performance records | HOLD | `test_forged_perf_capped_below_top_tier`, `test_perf_without_samples_capped` |
| Job completion status | HOLD | `test_jobs_lifecycle.py` (sticky terminal, cancel never succeeds) |
| Stale passport reuse | HOLD | `test_stale_ir_record_refused` + A1 fix |
| Target record for another IR | HOLD | `test_cross_machine_record_refused`, `test_stale_ir_record_refused` |
| Graph implying unverified QNX | HOLD | target node `unverified` + no verdict edge unless bound (tested) |
| Targeted check → release | HOLD | coverage `omitted` blocks `release_eligible` (tested) |
| Incomplete campaign → PASS | HOLD | `test_incomplete_check_list_capped` (verdict PASS is host-genuine; release False) |
| Cancelled op → completed | HOLD | runner cancel tests (`CANCELLED` sticky, verified live in campaigns) |
| Malformed import crashes API | HOLD | graphs 409/tamper/malformed tests, form-POST 422 test |
| Origin protection bypass | HOLD | guard tests (simple + preflight + inventory pins) |

## Accepted residuals (documented, not fixed)

- Evidence is point-in-time: a binary swapped on target AFTER
  `verify` snapshotted cksums is not detected by that record.
  Mitigation: hermetic staging + manifest check at verify time;
  re-verify after any target-side change.
- Op records (`op-*.json`) and the jobs DB are server-side files
  with no tamper-evident seal (unlike passports). Trust follows
  the local-operator model (`docs/local-security-model.md`):
  anyone with FS write already owns the evidence. No change.
