# QNX 8.0 target components

Native multi-process control prototype. Shared policy in `common/`, transport
in per-process sources. QNX-only code is fenced with `#ifdef __QNXNTO__` so
host compilers verify the shared logic without pretending to test IPC.

| Process | Role | QNX APIs |
|---|---|---|
| `genesis_guard` | policy-enforcing command server (real sender `msglen`, stats endpoint) | `name_attach`, `MsgReceive`+`_msg_info`, `MsgReply` |
| `genesis_controller` | periodic client, never bypasses guard (2 s guard-call timeout) | `name_open`, `MsgSend`, `TimerTimeout`, `clock_nanosleep` |
| `genesis_device` | SIMULATED actuator/sensor endpoint (applies guard forwards; first-sender pid pinning rejects other senders with EPERM) | `name_attach`, `MsgReceive`, `MsgReply`, `MsgError` |
| `genesis_status` | live `/dev/genesis/status` (per-read IPC stats query) | resource manager (`resmgr_attach`), `MsgSend` |
| `genesis_supervisor` | spawn + bounded RESPAWN (×3, backoff) + GIVE_UP halt | `posix_spawn`, `wait` |
| `genesis_faultinject` | on-target guard verification client (9 checks, 2 s `TimerTimeout` per send) | `name_open`, `MsgSend`, `TimerTimeout` |

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
