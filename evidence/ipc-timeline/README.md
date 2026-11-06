# Native IPC execution timeline — captured evidence (Wave 11 §12)

One focused native run (NOT a matrix campaign: no passport, no gate
verdict): `genesis_guard` + `genesis_faultinject bench 5` with
`GENESIS_IPC_TRACE=1` on QNX 8.0 x86_64 under QEMU (tcg, 4 vCPU).

- `bench-stdout.log` — raw capture: the exact SSH command (`$` line),
  client SEND/DONE stamps, bench SAMPLE deltas, guard RECV/REPLY
  stamps. All stamps are the target's CLOCK_MONOTONIC in nanoseconds.
- `timeline.json` / `timeline.txt` — parser output
  (`genesis_rt.ipc_timeline`): per-probe SEND→RECV→REPLY→DONE join
  plus an ASCII waterfall in microseconds.
- `run-meta.json` — staged binary sha256 digests (qcc build, 0
  warnings) and parser result (5 trips, 0 errors).
- `qemu-cmdline.txt`, `qemu-console.log`, `stage-manifest.json` —
  target identity and staging provenance.

Observed (QEMU timings — regression aids, not hardware guarantees):

| probe | round trip | guard span | decision |
| ----- | ---------- | ---------- | -------- |
| 1 | 1292.211 µs | 520.292 µs | ALLOW |
| 2 | 392.869 µs | 123.575 µs | ALLOW |
| 3 | 981.641 µs | 205.878 µs | ALLOW |
| 4 | 641.882 µs | 192.832 µs | ALLOW |
| 5 | 872.675 µs | 211.911 µs | ALLOW |

Consistency: each bench SAMPLE delta equals the parser's DONE−SEND
for the same seq (independent computation, same clock). Probe 1 is
slower (cold IPC path under emulation).

Reproduce: build amr-demo with qcc, boot the QSTI image with SSH
forwarding, stage guard+faultinject, run the `$` command from
`bench-stdout.log`, parse with
`PYTHONPATH=host python -c "from genesis_rt.ipc_timeline import ..."`.
Device-forward events are not timestamped (shown as unknown, never
invented).
