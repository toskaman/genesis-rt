# Why QNX (judge copy)

GENESIS RT is not portable-middleware-that-happens-to-run-on-QNX. The
generated system is shaped by Neutrino primitives, and the evidence it
produces is about those primitives behaving.

## What the product uses, natively

- **Synchronous message passing** — guard (`name_attach`,
  `MsgReceive`/`MsgReply`), controller (`name_open`, `MsgSend`, 2 s
  guard-call timeout via `TimerTimeout`). Fixed versioned protocol
  (magic/version/monotonic sequence/deadlines) in
  `target/qnx8/include/genesis_ipc.h`. There is no bypass path:
  unguarded device writes are asserted absent (`NONGUARD=0`) in every
  matrix step.
- **Resource manager** — live telemetry at `/dev/genesis/status`
  (allows/denies/state, per-read IPC stats query). Needs root to
  attach; the matrix and codelab say so instead of hiding it.
- **Real-time scheduling** — `scripts/qnx_target.py sched` compares 4
  configurations (`on -p`, SCHED_FIFO/SCHED_RR, policy verified via
  `pidin`). Result inconclusive across runs: the 5 Nov campaign
  showed lower p50/p99 at RT priority on both ends, but the 8 Nov
  re-run on jury-fixed sources did not reproduce any speedup
  (baseline p50 227.4/p99 420.2 vs fifo_both 274.9/438.6,
  rr_both 264.6/462.9 µs;
  `docs/audits/CAMPAIGN_2026-11-08.md`) — no general
  RT-priority speedup is claimed. Informational, no gate tier:
  QEMU/TCG timing is a regression aid, not a guarantee.
- **Process supervision** — bounded RESPAWN (×3, then GIVE_UP halt)
  with reset authority, proven by dedicated matrix steps. QNX HAM is
  documented as a complementary deployment option; the QSTI image
  ships no `ham` binary, so we do not claim to use it.
- **Process isolation as a safety argument** — crash-containment
  steps kill controller/device/guard mid-stream and assert the blast
  radius: a dead controller freezes the chain (≤3 lines), a dead
  device leaves the guard deciding, a dead guard fails the client's
  `MsgSend` loudly. Microkernel isolation is what makes these claims
  small and checkable.

## Why not Linux + sockets

Sequence enforcement, fail-closed denies, and supervision could be
rebuilt anywhere — but the deterministic IPC semantics, the
resmgr telemetry node, and the RT scheduling classes are the reason
the guard's contract (`SPEED_OVER_LIMIT`, `STALE_SEQ`, `ESTOP`, …)
maps 1:1 onto observable kernel behavior. The C policy is proven
identical to its Python mirror by compiled conformance vectors, and
the 16-step on-target matrix executes the whole story on QNX 8.0
(QEMU x86_64, `qcc -Vgcc_ntox86_64`, 0 warnings).

## Native binary footprint

Measured 9 Nov 2026 (`qcc -Vgcc_ntox86_64 -O2 -Wall -Wextra`,
AMR v1 IR, `ntox86_64-size -B`; reproduce: `genesis-rt generate
examples/amr-demo/machine-ir.json --out <dir>` then `make -f
genesis_build_gen.mk qnx` + `ntox86_64-size -B genesis_*`):

| binary | text | data | bss | file bytes |
|---|---|---|---|---|
| genesis_guard | 6641 | 800 | 56 | 14592 |
| genesis_controller | 5363 | 704 | 8 | 14016 |
| genesis_device | 5898 | 696 | 16 | 14280 |
| genesis_status | 6554 | 1328 | 528 | 15144 |
| genesis_supervisor | 4954 | 780 | 24 | 14328 |
| genesis_faultinject | 8136 | 680 | 8 | 18152 |

RSS is NOT measured here — it needs a live QEMU boot with
`pidin` against these exact binaries, which no campaign has
recorded; the committed Omega2 packs carry v2-machine binaries
(different sizes, see `qnx-build-record.json`), not these AMR
v1 ones. No resident-set claim is made.

## Bonus candidacy

Best Use of QNX-specific Technologies: message passing, resource
manager, monotonic timers + periodic scheduling, RT scheduling
experiments, supervision, and crash containment are all first-class,
measured, and replayable — see `TECHNICAL_EVIDENCE.md`.
