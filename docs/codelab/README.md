# Codelab: from a typed machine contract to a QNX 8.0 native IPC controller in QEMU

> Authored during the hackathon entry period. Follows the bonus-prize shape
> (task on/for QNX 8.0); usable with or without the GENESIS entry itself.

## Goal

In ~30 minutes you will: write a Machine IR contract, generate a QNX build,
compile it with `qcc`, run guard + controller on a QNX 8.0 QEMU target, and
watch the guard deny an invalid command over native message passing.

## Prerequisites

- This repo cloned; Python ≥3.12.
- For steps 4–6: QNX SDP 8.0 installed (`qnxsdp-env.sh` sourced) and a QEMU
  x86_64 target image (see `docs/quickstart-qnx8-qemu.md`). Steps 1–3 need
  no SDK.

## Step 1 — Write the contract (5 min)

Create `my-robot.json` (or copy `examples/amr-demo/machine-ir.json` and edit
the `id` and `max_linear_speed_mps`). Validate it:

```sh
PYTHONPATH=host python -m genesis_rt.cli validate my-robot.json
```

Break it on purpose (e.g. set `max_linear_speed_mps: 99`) and re-run: the
validator rejects it with the exact reason. Restore the valid value.

## Step 2 — Generate the target build (5 min)

```sh
PYTHONPATH=host python -m genesis_rt.cli generate my-robot.json --out lab-build
cat lab-build/genesis_config_gen.h   # your limits, hashed provenance header
```

Re-run into a second directory and `diff -r`: byte-identical output.

## Step 3 — See the guard think (5 min, no SDK)

```sh
PYTHONPATH=host python -m genesis_rt.cli faults examples/amr-demo/machine-ir.json
```

Read one denial: `speed_command_over_limit` shows the guard rejecting a 3×
over-limit command while the run continues. Then build the C conformance
harness and feed it vectors by hand (`cc` may be `gcc` or `clang`):

```sh
cc -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common \
  -o /tmp/guard_vector target/qnx8/common/guard_policy.c target/qnx8/host_tests/guard_vector.c
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 5.0 0.0 1 0 1 0 1\n' | /tmp/guard_vector
# expect: DENY SPEED_OVER_LIMIT 1
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 0.5 0.0 1 0 1 0 1 1\n' | /tmp/guard_vector
# expect: DENY ESTOP 3 (14th field = estop wire; state latched to SAFE_STOP)
```

## Step 4 — Compile natively with qcc (5 min, needs SDK)

```sh
source ~/qnx800/qnxsdp-env.sh
make -C lab-build -f genesis_build_gen.mk qnx
ls lab-build/genesis_guard lab-build/genesis_controller
```

Save the compiler output: it is evidence, not decoration.

## Step 5 — Run on QEMU (5 min, needs target)

Copy the seven `genesis_*` binaries to the target (build both machines
and upload the conveyor guard as `genesis_guard_conv`) and run:

```sh
./genesis_supervisor &
sudo -n ./genesis_status &
./genesis_controller 10
```

`status` needs `sudo -n`: attaching a resource manager at an absolute
path requires root (otherwise `EPERM` and no `/dev/genesis/status`
node). `10` is the controller period in ms; it runs in the foreground
— watch `ALLOW` lines flow, then Ctrl-C it. `cat /dev/genesis/status`
shows the resource-manager telemetry.

Note: the supervisor already runs its own controller, so a second
manual one produces some `STALE_SEQ` denies (two seq counters share
one guard — the guard is doing its job). Cleanup when done:

```sh
slay genesis_controller; slay genesis_supervisor; slay genesis_guard
slay genesis_device; sudo -n slay genesis_status
```

## Step 6 — Break it, prove it (5 min)

On the host, re-run the fault campaign and open the passport in
`ui/dashboard.html`:

```sh
PYTHONPATH=host python scripts/run_verified_demo.py
```

Compare: same scenario IDs, same oracles, host mirror vs (your) target log.
The passport's `qnx_build` record is where your `qcc` transcript belongs.

## Takeaway

A typed contract, a native IPC controller, and evidence that ties every
claim to an execution. That loop — specify → compile → run → break → prove —
is the whole GENESIS RT idea.
