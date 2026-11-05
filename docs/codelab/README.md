# Codelab: from a typed machine contract to a QNX 8.0 native IPC controller in QEMU

> Authored during the hackathon entry period. Follows the bonus-prize shape
> (task on/for QNX 8.0); usable with or without the GENESIS entry itself.
> Every command below was executed against commit `db32221` on 2026-11-05
> (Windows 11 host + QNX 8.0 QEMU target); expected outputs are real.
>
> Final URL for the Devpost bonus box:
> `https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/README.md`

## Goal

In ~45 minutes you will: write a Machine IR contract, generate a QNX build,
compile it with `qcc`, run guard + controller on a QNX 8.0 QEMU target, watch
the guard deny an invalid command over native message passing, and inspect
the evidence passport that ties every claim to an execution.

## Architecture (what you will run)

```text
my-robot.json (Machine IR contract)
      |  validate -> generate
      v
genesis_config_gen.h + genesis_build_gen.mk   (hashed provenance header)
      |  make qnx  (qcc, 0 warnings)
      v
  genesis_controller  --MsgSend-->  genesis_guard  --forward-->  genesis_device
        (client)                   (policy: ALLOW/DENY)            (virtual robot)
                                          |
                                          +--> genesis_status (/dev/genesis/status telemetry)
                                          +--> genesis_supervisor (respawns dead children)
```

The guard is the authority: nothing reaches the device except through it.
Every denial carries a machine-readable reason (`SPEED_OVER_LIMIT`,
`STALE_SEQ`, `ESTOP`, ...).

## Prerequisites

- This repo cloned; Python ≥3.12. A host C compiler (`gcc` or `clang`)
  for step 3 — verify with `gcc --version`.
- For steps 4–6: QNX SDP 8.0 installed and a QEMU x86_64 target image
  (see `docs/quickstart-qnx8-qemu.md`). Steps 1–3 need no SDK.
- Shells: Linux/macOS use `sh`; Windows uses PowerShell. Both variants
  are given; run host commands from the repo root.

## Step 1 — Write the contract (5 min, no SDK)

Copy the AMR example and edit two fields — `machine.id` and
`control.max_linear_speed_mps`:

```sh
cp examples/amr-demo/machine-ir.json my-robot.json
PYTHONPATH=host python -m genesis_rt.cli validate my-robot.json
# expect: valid: schema v1 amr-demo-01 (differential_drive_robot) scenarios=8
# (your id replaces amr-demo-01 once edited)
```

```powershell
Copy-Item examples/amr-demo/machine-ir.json my-robot.json
$env:PYTHONPATH='host'; python -m genesis_rt.cli validate my-robot.json
```

Break it on purpose (set `control.max_linear_speed_mps` to `99`) and
re-run: the validator rejects it with the exact reason and exit code 2.
Restore the valid value.

```text
error: IRValidationError: control.max_linear_speed_mps must be a number in (0, 10.0] (bool rejected)
```

## Step 2 — Generate the target build (5 min, no SDK)

```sh
PYTHONPATH=host python -m genesis_rt.cli generate my-robot.json --out lab-build
cat lab-build/genesis_config_gen.h   # your limits, hashed provenance header
```

```powershell
$env:PYTHONPATH='host'; python -m genesis_rt.cli generate my-robot.json --out lab-build
Get-Content lab-build/genesis_config_gen.h
```

Expect two files plus their sha256 lines:

```text
generated: .../lab-build (schema v1)
  genesis_build_gen.mk  sha256:bfaa3718c096885a...
  genesis_config_gen.h  sha256:cd74fc72635d736c...
```

Re-run into a second directory and `diff -r` (Linux) or
`Compare-Object (Get-Content ...)` (PowerShell): byte-identical output.
Deterministic generation is what makes the evidence reproducible.

## Step 3 — See the guard think (10 min, no SDK)

Run the host fault campaign — 8 scenarios, each must pass:

```sh
PYTHONPATH=host python -m genesis_rt.cli faults examples/amr-demo/machine-ir.json
# expect: 8/8 scenarios passed (e.g. speed_command_over_limit: pass (allows=297 denies=3))
```

Read one denial: `speed_command_over_limit` shows the guard rejecting an
over-limit command while the run continues. These host results are the
**Python mirror** of the policy. The C implementation is proven identical
by a conformance harness — build it and feed it vectors by hand:

Linux/macOS:

```sh
cc -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common \
  -o /tmp/guard_vector target/qnx8/common/guard_policy.c target/qnx8/host_tests/guard_vector.c
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 5.0 0.0 1 0 1 0 1\n' | /tmp/guard_vector
# expect: DENY SPEED_OVER_LIMIT 1
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 0.5 0.0 1 0 1 0 1 1\n' | /tmp/guard_vector
# expect: DENY ESTOP 3 (14th field = estop wire; state latched to SAFE_STOP)
```

Windows (PowerShell — there is no `printf`; use files):

```powershell
gcc -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common `
  -o $env:TEMP/guard_vector target/qnx8/common/guard_policy.c target/qnx8/host_tests/guard_vector.c
@'
LIMITS 1.2 1.0 100
47454E31 1 1 1 0 50 5.0 0.0 1 0 1 0 1
'@ | Set-Content $env:TEMP/vec1.txt
Get-Content $env:TEMP/vec1.txt | & $env:TEMP/guard_vector.exe
# expect: DENY SPEED_OVER_LIMIT 1
```

The first vector sends 5.0 m/s against a 1.2 limit (3× over → deny,
stay in state 1). The second asserts the estop wire (deny, latch to
state 3 = SAFE_STOP). Same C file ships on the target in step 4.

## Step 4 — Compile natively with qcc (5 min, needs SDK)

Linux/macOS:

```sh
source ~/qnx800/qnxsdp-env.sh
make -C lab-build -f genesis_build_gen.mk qnx
ls lab-build/genesis_guard lab-build/genesis_controller
```

Windows (adjust the SDK path to your install):

```powershell
cmd /c "call E:\qnx800\qnxsdp-env.bat >NUL 2>&1 && make -C lab-build -f genesis_build_gen.mk qnx"
ls lab-build/genesis_guard, lab-build/genesis_controller
```

Expect 6 `genesis_*` binaries (guard, controller, device, status,
supervisor, faultinject) with **0 warnings** — save the compiler
output, it is evidence, not decoration. (The industrial-cell build adds
`genesis_cellcheck` for 7; the full on-target matrix stages 9 files:
those 7 plus the conveyor and v2 guards under distinct names.)

## Step 5 — Run on QEMU (10 min, needs target)

Copy the binaries to the target (from the host):

```sh
python scripts/qnx_target.py put lab-build/genesis_* --dest /tmp/genesis
```

Then SSH to the target (`ssh qnxuser@localhost -p 2222` per the
quickstart) and start the chain by hand — device first, then guard,
then the controller in the **foreground** so you watch the decisions:

```sh
cd /tmp/genesis
./genesis_device > dev.log 2>&1 &
./genesis_guard > guard.log 2>&1 &
sleep 2
./genesis_controller 50
```

Expect a stream of allows (period = 50 ms, Ctrl-C to stop):

```text
controller: machine=amr-demo-01 connected to 'genesis_guard', period=50ms cruise=0.480
controller: seq=1 decision=ALLOW reason=0 state=1
controller: seq=2 decision=ALLOW reason=0 state=1
```

Now the guard's other half: in a second SSH session, start the
supervisor (it runs its own guard + controller + device and respawns
dead children) and the status resource manager, then read the live
telemetry node:

```sh
./genesis_supervisor > sup.log 2>&1 &
sudo -n ./genesis_status > status.log 2>&1 &
sleep 3
cat /dev/genesis/status
# expect: state=1 allows=<n> denies=<m> last_reason=... fwd_ok=... dev_x=...
slay genesis_controller; sleep 2; grep RESPAWN sup.log
# expect: supervisor: RESPAWN ./genesis_controller deaths=1 ...
```

`status` needs `sudo -n`: attaching a resource manager at an absolute
path requires root (otherwise `EPERM` and no `/dev/genesis/status`
node). Do **not** run your manual controller while the supervisor is
up: two sequence counters share one guard and the second one eats
`STALE_SEQ` denies — the guard doing its job (verified live).

Cleanup when done (both sessions):

```sh
slay genesis_controller; slay genesis_supervisor; slay genesis_guard
slay genesis_device; sudo -n slay genesis_status
```

## Step 6 — Break it, prove it (5 min, no SDK)

On the host, run the verified demo pipeline and open the passport in
`ui/dashboard.html` (open the file in a browser, then load the
passport JSON it prints):

```sh
PYTHONPATH=host python scripts/run_verified_demo.py
# expect: "verdict": "PASS" ("qnx_verified": false without target records —
# honest: host-only evidence is labeled as such)
```

Compare: same scenario IDs, same oracles, host mirror vs your target
log from step 5. Then tamper-check the chain — flip one byte in a copy
of the passport and re-run the replay verifier:

```sh
PYTHONPATH=host python scripts/replay.py artifacts/runs/<run-id>/passport.json
# expect: chain: valid ... gate: PASS (qnx_verified=False)
```

Going further (the automated version of step 5): `python
scripts/qnx_target.py verify` runs the 16-step on-target matrix —
fault injection, supervision, IR-bound limits, crash containment of
controller/device/guard, and the cell interlock selftest — and binds
the transcripts into a `QNX_PERFORMANCE_MEASURED` passport. See
`docs/jury/REPRODUCE.md` for the one-page recipe.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `error: IRValidationError: ... (0, 10.0]` | Limit outside the schema envelope | Keep linear ≤ 10.0 m/s (edit `control.*`) |
| `qcc: not found` / `make: qcc: No such file` | SDK env not sourced | `source ~/qnx800/qnxsdp-env.sh` (Linux) or `call E:\qnx800\qnxsdp-env.bat` (Windows) in the **same** shell |
| `status: EPERM`, no `/dev/genesis/status` | Resource manager needs root | `sudo -n ./genesis_status` (needs NOPASSWD sudo, as on the QSTI image) |
| Manual controller eats `STALE_SEQ` denies | Supervisor already runs a controller on the same guard | `slay genesis_supervisor` first, or watch the supervisor's chain instead |
| `MsgSend failed` in controller log | Guard died (or was never started) | Start `./genesis_guard` before the controller |
| `slay: Unable to find process` | Already dead / never started | Harmless — check with `pidin \| grep genesis` |
| `printf: command not found` (Windows) | PowerShell has no `printf` | Use the file-based vector variant from step 3 |
| `verify: REFUSED — TARGET_MATRIX drifted` | Script/provenance version skew | Re-pull; never hand-edit one side of the pin |
| Stale `qnx_verified: true` after rebuild | Records bound to older binaries | Re-run `put` + `verify`; the gate refuses recycled evidence |

## Cleanup

```sh
# on the target:
slay genesis_controller; slay genesis_supervisor; slay genesis_guard
slay genesis_device; sudo -n slay genesis_status
rm -f /tmp/genesis/codelab-*.log /tmp/genesis/*.log
# on the host:
rm -rf lab-build lab-build2 my-robot.json
```

## Safety and scope limitations

- **Simulation only.** The device is a virtual robot (`dev_x` is a
  float in a log). Nothing here may drive physical hardware; the IR
  schema carries a `simulation_only` gate for that reason.
- **Prototype, not certified.** No functional-safety qualification
  (see `docs/jury/KNOWN_LIMITATIONS.md` and
  `docs/limitations-and-safety.md`, which govern).
- **QEMU timing is not real-time evidence.** Latency numbers in
  `docs/perf-baseline.md` are regression aids; determinism on
  hardware needs hardware measurement.
- Host fault results are simulated; the C policy is proven identical
  by conformance vectors, and on-target runs are labeled with an
  explicit `qnx_verified` flag — never trust a passport without
  reading it.

## Takeaway

A typed contract, a native IPC controller, and evidence that ties every
claim to an execution. That loop — specify → compile → run → break →
prove — is the whole GENESIS RT idea.
