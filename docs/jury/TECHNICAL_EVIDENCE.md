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
| Honest QNX absence | `host/genesis_rt/build_adapter.py` (`blocked` records) | `tests/qnx/test_qnx_build.py` (explicit skip) |
| On-target proof (QNX 8.0 QEMU) | `scripts/qnx_target.py verify` (5-step SSH matrix) | `target/qnx8/faultinject/` (6/6 IPC checks), run transcripts |
| Clock separation | `docs/evidence-methodology.md` | sim `t_ms` vs envelope `created_utc` |

QNX-specific technology bonus mapping: native synchronous message passing
(guard/controller), resource manager (status), monotonic timers + periodic
scheduling (controller), process supervision (supervisor; HAM documented as
a complementary deployment option in `docs/quickstart-qnx8-qemu.md`).
