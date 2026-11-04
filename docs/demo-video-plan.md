# Demo video plan (target 2:40–2:50, hard cap < 3:00)

Record only genuine runs. Suggested shot list with narration cues:

| Time | Shot (screen capture) | Narration |
|---|---|---|
| 0:00–0:20 | Terminal: `genesis-rt plan` → validated IR (show `machine-ir.json`) | "Intent becomes a typed machine contract — invalid specs are rejected, never guessed." |
| 0:20–0:45 | Terminal: `generate` + `cat genesis_config_gen.h`; `diff` of two runs | "Deterministic codegen: same contract, byte-identical QNX build files." |
| 0:45–1:15 | QEMU/target terminal: `make qnx`, `./genesis_supervisor`, ALLOW log lines; `cat /dev/genesis/status` | "Native QNX 8.0: message-passing guard, controller, resource manager — on a real target." |
| 1:15–1:45 | Terminal: `faults` output 8/8; highlight one DENY + safe-stop + recovery | "We break it on purpose: stale sensor, over-limit command — the guard denies and recovers." |
| 1:45–2:15 | `scripts/replay.py` output + `ui/dashboard.html` with passport loaded | "Every claim links to a hash-chained evidence passport. Tamper with it and the gate fails." |
| 2:15–2:40 | Break-then-fix: sabotaged run FAIL → fixed run PASS (acceptance test) | "A bad revision cannot ship. The fixed one proves it. Specify, compile, run, break, prove." |

Rules: public YouTube upload, no copyrighted audio, no mockups — if a step
is not yet recorded on target, show the host run and label it honestly.
