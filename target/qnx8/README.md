# QNX 8.0 target components

Native multi-process control prototype. Shared policy in `common/`, transport
in per-process sources. QNX-only code is fenced with `#ifdef __QNXNTO__` so
host compilers verify the shared logic without pretending to test IPC.

| Process | Role | QNX APIs |
|---|---|---|
| `genesis_guard` | policy-enforcing command server | `name_attach`, `MsgReceive`, `MsgReply` |
| `genesis_controller` | periodic client, never bypasses guard | `name_open`, `MsgSend`, `CLOCK_MONOTONIC` |
| `genesis_device` | SIMULATED actuator/sensor endpoint | none (virtual state only) |
| `genesis_status` | read-only `/dev/genesis/status` | resource manager (`resmgr_attach`) |
| `genesis_supervisor` | spawn + monitor + reset authority | `posix_spawn`, `wait` |

Protocol: `include/genesis_ipc.h` (magic `GEN1`, version 1, fixed frames,
monotonic sequence IDs, deadlines).

Build on a QNX SDP 8.0 host (after `qnxsdp-env.sh`):

```sh
cd <generated-dir>   # produced by `genesis-rt generate`
make -f genesis_build_gen.mk qnx
```

Host policy check (no SDK needed):

```sh
make -f genesis_build_gen.mk host
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 0.5 0.0 1 0 1 0 1\n' | ./guard_vector
# expect: ALLOW OK 1
```

`host_tests/guard_vector.c` is the conformance harness proving the C policy
and `host/genesis_rt/guard_policy.py` return identical decisions on the
same vectors (see `tests/`).
