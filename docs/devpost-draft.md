# Devpost submission draft (fill in video URL, then paste)

Category: **Developer Tooling & Host Tools**.
Video: `<paste public YouTube URL, < 3:00>` — record per `docs/demo-video-plan.md`.
Repo: https://github.com/toskaman/genesis-rt

## Title

GENESIS RT — The Physical World Compiler

## Tagline

From human intent to tested QNX-native machine software, with proof.

## Description (paste-ready)

Embedded control prototypes are slow to build, and their test evidence is
usually folklore. GENESIS RT is a host toolchain that turns a constrained
machine description into a typed, inspectable specification (Machine IR),
generates a native QNX 8.0 multi-process controller, runs it, breaks it on
purpose with seeded fault injection, and produces a hash-linked evidence
passport where every green verdict links to a real execution trace.

What it does:

- **Specify** — constrained intent becomes a strictly validated Machine IR
  contract (fixed kinds, units, safety-contract whitelist; unknown input is
  rejected, never guessed).
- **Compile** — deterministic codegen emits QNX C build files: identical
  input always yields byte-identical output with hashed provenance.
- **Run natively** — six QNX processes: a policy-enforcing guard server
  (native `MsgReceive`/`MsgReply`, live stats endpoint), a periodic
  controller (`MsgSend`, no bypass path, 2 s guard-call timeout), a
  simulated device endpoint, a live `/dev/genesis/status` resource
  manager, a supervisor (bounded RESPAWN, then GIVE_UP halt), and an
  on-target 9-check fault-injection client.
- **Break** — an 8-scenario fault lab (stale sensor, over-limit command,
  planner crash, delayed/dropped/corrupted messages, disconnect) with
  explicit oracles and recorded seeds.
- **Prove** — a hash-chained evidence passport plus a fail-closed release
  gate: missing, skipped, crashed or tampered evidence always yields FAIL,
  and a sabotaged revision is proven blocked before the fix passes.

QNX-specific substance: synchronous native message passing with a fixed
versioned protocol (magic/version/monotonic sequence/deadlines), a
read-only resource manager, monotonic-clock periodic control, and
process supervision (with QNX HAM documented as a deployment complement).
The guard policy is implemented once in C and mirrored in Python, with a
compiled conformance harness proving identical decisions on every vector.

Honest scope: host fault results are simulated; on-target QNX 8.0/QEMU
execution is verified (11/11 matrix, 9/9 IPC checks, `qcc` 0 warnings),
and passports always report `qnx_verified` explicitly. Simulation-only,
prototype-grade, no safety certification claimed. Judges start at
`docs/jury/START_HERE.md`.

## How we use QNX (paste-ready)

The generated controller is QNX-native C: guard + controller communicate
over Neutrino synchronous message passing (`name_attach`/`name_open`,
`MsgSend`/`MsgReceive`/`MsgReply`), telemetry is served by a resource
manager at `/dev/genesis/status`, control timing uses `CLOCK_MONOTONIC`,
and the supervisor owns process health plus safe-state reset authority.
Target: QNX SDP 8.0, `qcc -Vgcc_ntox86_64`, x86_64 QEMU. Key files:
`target/qnx8/include/genesis_ipc.h`, `target/qnx8/guard/`,
`target/qnx8/controller/`, `target/qnx8/status/`,
`target/qnx8/supervisor/`, `target/qnx8/common/guard_policy.c`.

## Testing instructions (paste-ready)

Without a QNX SDK (2 minutes):

```sh
git clone https://github.com/toskaman/genesis-rt.git && cd genesis-rt
pip install pytest pyyaml
PYTHONPATH=host python scripts/run_verified_demo.py
PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json
python -m pytest tests/ -q   # green, 129 tests (QNX build runs w/ SDK, else honest skip)
```

Open `ui/dashboard.html` and load the passport to inspect every verdict.
With an SDK: `python scripts/qnx_env_check.py`, then follow
`docs/quickstart-qnx8-qemu.md` to build (`make -f genesis_build_gen.mk qnx`)
and run on QEMU.
