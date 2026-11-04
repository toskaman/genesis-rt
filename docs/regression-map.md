# Regression map: confirmed defects and their tests

Every defect confirmed during development keeps a focused regression test
(quality gate, mission section 15). On-target rows need the QNX/QEMU
harness (`scripts/qnx_target.py verify`); all other rows run in host CI.

| # | Confirmed defect | Fix | Regression test |
|---|------------------|-----|-----------------|
| 1 | Guard/controller used hardcoded limits (`1.2/1.0/100`, period 10) instead of generated values | `genesis_config_gen.h` included by guard/controller/faultinject; derived period/cruise; `probe` mode | `tests/integration/test_limit_wiring.py` (headers differ, identical command → different decisions) + matrix `limits_differ` step |
| 2 | Generated makefile missed `common/` include dir (found by real `qcc`) | `-I$(GENESIS_SRC)/common` in generated flags | `tests/unit/test_codegen_determinism.py::test_makefile_covers_all_include_dirs` + `tests/qnx/test_qnx_build.py` (native build, 0 warnings) |
| 3 | Native link missed `-lm`; `dispatch_block` QNX8 context; missing `stdlib.h` (found by real `qcc`) | Build/template fixes | `tests/qnx/test_qnx_build.py` (native build must succeed) |
| 4 | Resmgr `io_read` offset/EOF handling wrong; device process exited; SSH/exec waits had no timeout (found on target) | Resmgr + device + timeout fixes | On-target matrix: `status_live`, `device_resident`, `controller_flow` steps |
| 5 | Guard answered pulses; ignored sender `msglen` (no real `BAD_SIZE`); no endpoint stats | `MsgReceive`+`_msg_info` size validation, pulse skip, stats endpoint | On-target matrix: `faultinject` 9/9 incl. `short_frame`; red-green proven (old binaries → 2/6) |
| 6 | Supervisor respawned blindly (orphan survivors, no give-up) | Bounded RESPAWN ×3 with 1/2/4 s backoff + GIVE_UP halt | On-target matrix: `supervisor_respawn`, `supervisor_giveup` steps |
| 7 | Controller used unexamined `usleep()` loop; no send timeout; unfilled frames | `clock_nanosleep` absolute, `TimerTimeout` 2 s, `0xFF` fail-closed fill | On-target matrix: `controller_flow` + `faultinject` checks |
| 8 | Static status strings instead of live state | Live IPC query per read (2 s timeout) | On-target matrix: `status_live` exact counters |
| 9 | Guest SSH `PerSourcePenalties` banned rapid retries; probing during ban extended it | 4 patient attempts × 45 s gap + single 300 s cooldown on penalty signature (`banner` or `Not allowed at this time`) | `tests/unit/test_ssh_policy.py` (17 tests: pinned constants, signature matrix, scripted retry/cooldown behavior, no network) |
| 10 | Host PASS readable as release authorization; target evidence not bound to native build | Earned-tier levels `NONE..QNX_PERFORMANCE_MEASURED`, `release_eligible` from `QNX_BEHAVIOR_VERIFIED` only | `tests/unit/test_evidence_gate.py` (tiers, executed-vs-verified, build binding, NONE on failure) |
| 11 | Disabled guard (all-ALLOW) could pass fault scenarios | Deny-dependent oracles in every fault scenario | `tests/faults/test_fault_oracles.py::test_always_allow_guard_mutant_fails_scenarios_and_gate` + per-oracle sabotage tests |
| 12 | Watchdog crash scenario could pass with motion during the gap | `watchdog_zero_motion` displacement oracle | `test_watchdog_oracle_catches_motion_during_gap` + `test_watchdog_break_end_to_end_fails_scenario_and_gate` |
| 13 | Dropped-message scenario could pass with commands applied during the gap | `no_allow_without_command` oracle over real trace | `test_no_allow_oracle_catches_tick_during_drop` + `test_forged_tick_in_real_drop_trace_detected` |
| 14 | Python guard crashed/raised on malformed limits instead of fail-closed deny | Fail-closed `decide` (OverflowError, malformed limits, C parity) | `tests/unit/test_guard_policy.py` (48 tests) + `tests/integration/test_c_conformance.py` (17 NaN/inf vectors) |
| 15 | API shared temp IR files across requests; unhandled error shapes | Per-request temp IR, 400/422 handling, 1 worker | `tests/integration/test_api.py` |
| 16 | Dashboard rendered uploaded JSON unescaped (XSS) | Escaping + pure-JS chain re-verification | `tests/ui/test_dashboard_verify.py` |
| 17 | Golden demo test could pass vacuously | Non-vacuous golden assertions | `tests/acceptance/test_golden_demo.py` |
| 18 | CLI `validate` output contract (`valid:`) broken by v2 dispatch change | Output keeps `valid:` prefix with version suffix | `tests/integration/test_pipeline.py::test_cli_validate_and_faults` (caught it red, then green) |
| 19 | `device_chain` step FAIL: `/tmp/genesis-status-node` missing on target | OPEN — root cause not yet established; target work suspended until host reboot | `tests/integration/test_device_chain.py` (fails loudly until fixed; must go 8/8 on target) |
| 20 | `seq <= last_seq` wedged the guard after uint32 wraparound (2^32-1 → 0 denied forever, no reset path since STALE_SEQ does not latch) | Serial-number arithmetic (RFC 1982) in both mirrors: accept iff 1 ≤ (seq−last) mod 2^32 < 2^31 | `test_seq_wraparound_accepted`, `test_seq_old_replay_denied`, `test_seq_huge_forward_jump_denied` + 4 C/Python conformance vectors (wrap, replay, dup, jump); old predicate → 3 FAIL |

## Rules

- A row is added the moment a defect is confirmed, and the test must exist
  before the fix is merged.
- Weak-oracle audits (§6.4): no oracle may unconditionally return pass;
  every oracle has at least one sabotage test proving it can fail.
- Vacuous-validator check: fault-oracle and IR-validation tests must fail
  against a stubbed always-pass implementation (proven for
  `tests/unit/test_ir_v2.py`: 51 FAIL against identity validator).
