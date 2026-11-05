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
  `pidin`): RT priorities at both ends cut p50 ~45% / p99 ~65% vs
  baseline on the author's QEMU target. Informational, no gate tier —
  TCG timing is a regression aid, not a guarantee.
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

## Bonus candidacy

Best Use of QNX-specific Technologies: message passing, resource
manager, monotonic timers + periodic scheduling, RT scheduling
experiments, supervision, and crash containment are all first-class,
measured, and replayable — see `TECHNICAL_EVIDENCE.md`.
