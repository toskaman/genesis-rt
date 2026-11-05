# Technical evidence map

| Claim | Primary evidence | Secondary evidence |
|---|---|---|
| Native QNX IPC guard/server | `target/qnx8/guard/genesis_guard.c` (`name_attach`, `MsgReceive`, `MsgReply`) | `target/qnx8/controller/genesis_controller.c` (`name_open`, `MsgSend`) |
| Fixed versioned protocol | `target/qnx8/include/genesis_ipc.h` | `schemas/machine-ir-v1.schema.json` |
| Fail-closed policy | `target/qnx8/common/guard_policy.c` | `host/genesis_rt/guard_policy.py` (mirror) |
| C/Python identity | `tests/integration/test_c_conformance.py` | `target/qnx8/host_tests/guard_vector.c` |
| Resource manager | `target/qnx8/status/genesis_status.c` (`/dev/genesis/status`) | `target/qnx8/README.md` |
| Supervisor + reset authority | `target/qnx8/supervisor/genesis_supervisor.c` | fault-lab `supervisor_reset_armed` trace events |
| Deterministic codegen | `host/genesis_rt/codegen.py`, `templates/` | `tests/unit/test_codegen_determinism.py` |
| Seeded faults + oracles | `host/genesis_rt/faultlab.py` | `tests/faults/test_fault_oracles.py` |
| Hash-linked passport | `host/genesis_rt/evidence.py` | `artifacts/samples/golden_demo_passport.example.json` |
| Fail-closed gate | `host/genesis_rt/gate.py` | `tests/unit/test_evidence_gate.py`, `tests/acceptance/` |
| Verification levels (host PASS ≠ release) | `gate.py` (`NONE…QNX_PERFORMANCE_MEASURED`, `release_eligible`) | `tests/unit/test_evidence_gate.py` (tier/binding tests), CLI `demo` output |
| Honest QNX absence | `host/genesis_rt/build_adapter.py` (`blocked` records) | `tests/qnx/test_qnx_build.py` (explicit skip) |
| On-target proof (QNX 8.0 QEMU) | `scripts/qnx_target.py verify` (14-step SSH matrix) | `target/qnx8/faultinject/` (9/9 IPC checks), run transcripts |
| Guard-crash containment | guard killed mid-stream inside the matrix step | `guard_crash` step (apply-count freeze ≤3, NONGUARD=0, guard gone, client MsgSend fails) |
| Cell interlock policy (native) | `target/qnx8/cell/genesis_cellcheck.c` (9 interlock vectors + 3 policy checks) | `cell_policy` matrix step (`CELL_POLICY: PASS 12/12`), IR-bound `limits_differ` slot-1 banner |
| Guarded device path | guard→device forward + `target/qnx8/common/device_model.c` | `device_chain` step (APPLIES≥20, NONGUARD=0, virtual robot moved) |
| Generated limits drive runtime | guard/controller/faultinject include `genesis_config_gen.h` | `limits_differ` step (probe 1.5 DENY vs ALLOW), `tests/integration/test_limit_wiring.py` |
| Live telemetry | `target/qnx8/status/genesis_status.c` (per-read IPC stats query) | `status_live` matrix step (allows/denies/state asserted) |
| Bounded supervision | `target/qnx8/supervisor/genesis_supervisor.c` (RESPAWN×3 + GIVE_UP halt) | `supervisor_respawn`/`supervisor_giveup` matrix steps |
| Generated transitions drive runtime | `host/genesis_rt/codegen_v2.py` + guard v2 tail (`-DGENESIS_MACHINE_V2`) | `v2_transitions` step (v1/v2 bidirect. contrast, 9/9 on v2 binary) |
| Oracle bite (red-green) | old guard/status/supervisor vs new oracles → 2/6 FAIL | `docs/PROGRESS.md` (Wave B entry, reproducible method) |
| Counterfactual compare | `host/genesis_rt/compare.py` (contract diff, fixed/broken, perf delta, binaries hashed) + `POST /compare` | `tests/integration/test_compare.py` (cell 0.3→1.2: 3 fixed), `examples/cell-demo/README.md` (Demo C) |
| Local run history/export | `host/genesis_rt/api.py` (`GET /runs`, `GET /runs/{id}/export`, active→202) | `tests/integration/test_api.py` (history/compare/export/409 paths) |
| Clock separation | `docs/evidence-methodology.md` | sim `t_ms` vs envelope `created_utc` |

QNX-specific technology bonus mapping: native synchronous message passing
(guard/controller), resource manager (status), monotonic timers + periodic
scheduling (controller), process supervision (supervisor; HAM documented as
a complementary deployment option in `docs/quickstart-qnx8-qemu.md`).
