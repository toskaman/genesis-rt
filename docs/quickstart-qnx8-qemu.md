# QNX 8.0 + QEMU quickstart

> Nothing here redistributes QNX software. You install the SDK yourself
> from official sources under their license; this repo only probes for it
> and invokes its toolchain.

## 0. Status on this machine (verified 4 Nov 2026)

- QEMU 11.1.0 at `E:\VMs\qemu\qemu-system-x86_64.exe` — satisfies the
  official "upgrade to QEMU 10" recommendation. Override with `GENESIS_QEMU`.
- QNX SDP 8.0.0 at `E:\qnx800` (Education licence activated) + QSTI
  `com.qnx.qnx800.quickstart.qemu` 0.5.0 unpacked. Auto-detected even
  without environment variables.
- Proven boot: `--boot disk` with `-cpu host` (WHPX), or
  `--accel tcg --cpu max` (the default `qemu64` CPU stalls the v1.2d
  loader with the guest RIP frozen — QMP-proven; `-cpu max` boots).
  Direct `-kernel` stalls the loader. Both `output/disk-qemu`
  (via `--disk-name disk-qemu`) and the default `output/disk-qemu.vmdk`
  boot to a login prompt.
- Target: `QNX qnxqemu 8.0.0 x86_64`, SSH `qnxuser` (password = the
  image-default username; never committed, pass via `GENESIS_TARGET_PASSWORD`).
- Verified 4 Nov 2026: `qcc` builds 7 binaries with 0 warnings;
  on-target matrix 11/11 PASS (`qnx_verified: true`, replay valid).

## 1. Get the SDK lawfully (your 10 minutes, cannot be automated)

QNX downloads require a myQNX account; there is no legitimate unattended path.

1. Create a myQNX account: https://www.qnx.com/account/login.html
2. Request the free non-commercial SDP 8.0 licence: https://www.qnx.com/getqnx
3. In the [myQNX License Manager](https://www.qnx.com/account/dashboard),
   accept the licence and deploy it to yourself as a user.
4. Download + install the QNX Software Center (QSC):
   https://www.qnx.com/download/group.html?programid=29178
5. In QSC, install **QNX Software Development Platform 8.0** and the
   **com.qnx.qnx800.quickstart.qemu** package (QSTI image for QEMU).
6. Unpack the image per the official guide (in the SDP install, under
   `images/qemu`, run `unpack_qemu_image.sh`) so you get the `qemu/`
   folder with `output/ifs.bin` + the disk image.

**License caution:** QNX Everywhere covers eligible non-commercial and some
OSS-interoperability uses; commercial product development may need
commercial terms. The hackathon excludes projects with preferential or
financial sponsor support — do not seek commercial/sponsored licensing
during the entry period without written eligibility clarification.

Official references:

- https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.quickstart/topic/install_host.html
- https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/about.html
- https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/getting_started.html
- https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/additional_specs.html

## 2. Verify the toolchain

```sh
python scripts/qnx_env_check.py  # expect sdk_present=true + qemu.present=true
```

On Linux/macOS-style shells source the SDP env first
(`source ~/qnx800/qnxsdp-env.sh`); on Windows use the SDP command prompt
(or set `QNX_HOST`/`QNX_TARGET` + `PATH` to include the toolchain).

## 3. Build the generated target

```sh
genesis-rt generate examples/amr-demo/machine-ir.json --out /tmp/genesis-qnx
make -C /tmp/genesis-qnx -f genesis_build_gen.mk qnx
ls /tmp/genesis-qnx/genesis_guard  # + controller/device/status/supervisor/faultinject
```

## 4. Boot the QSTI under QEMU (scripted)

```sh
python scripts/qnx_target.py probe-image ~/qnx800/images/qemu/qemu
python scripts/qnx_target.py boot ~/qnx800/images/qemu/qemu --out artifacts/qemu-boot
```

The boot flags follow the official `additional_specs` template
(`-kernel output/ifs.bin`, IDE disk, serial console, virtio-net), adapted
for the host: KVM on Linux, WHPX/TCG on Windows (`--accel`), user-mode
networking by default. The console transcript + exact command line land in
the output dir; boot markers are reported as seen/not-seen, never assumed.

## 5. Run genesis on target

Scripted path (needs `paramiko` + SSH reachable, e.g. `--ssh-port 2222`
at boot; password via `GENESIS_TARGET_PASSWORD`, never on the command line):

```sh
python scripts/qnx_target.py put /tmp/genesis-qnx/genesis_* --dest /tmp/genesis
python scripts/qnx_target.py verify --out artifacts/qemu-boot/target-record.json
# expect: 11/11 PASS — target_info, faultinject (9/9), status_live,
# limits_differ (probe 1.5: AMR DENY vs conveyor ALLOW + 9/9 vs conv),
# device_chain (guard→device→status, APPLIES≥20, NONGUARD=0),
# conv_chain (conv guard→belt device, BELT≥20, belt moved),
# estop_target (probe estop → DENY ESTOP + state=3 latch),
# target_perf (bench 200 shape), controller_flow,
# supervisor_respawn, supervisor_giveup
python scripts/qnx_target.py perf --samples 1000 --out artifacts/qnx-perf
# expect: PASS 1000/1000, p50 ~0.3 ms under TCG (see docs/perf-baseline.md);
# feed the record to `genesis-rt demo --perf-record` for the top gate tier
# NOTE: build BOTH machines (amr + conveyor) and upload the conveyor
# guard as genesis_guard_conv, or limits_differ fails MISSING_CONV_GUARD.
```

SSH discipline (measured): the guest sshd (OpenSSH >= 9.8) enforces
`PerSourcePenalties`, and the SLIRP/WHPX path drops occasional
handshakes. Run ONE ssh command at a time, never probe right before
the real command, and let failures cool down instead of hammering:
rapid retries reliably produce `Not allowed at this time` bans of
several minutes. The scripted client already spaces attempts (4 x 45 s
+ 300 s penalty cooldown) and reports every attempt.

Manual fallback: transfer the six binaries to the running target (shared
folder/`scp` per your setup), then on target:

```sh
./genesis_supervisor   # spawns guard/controller/device, bounded RESPAWN then GIVE_UP halt
./genesis_status &     # serves /dev/genesis/status (live telemetry)
cat /dev/genesis/status
```

Observe `ALLOW`/`DENY` lines from the guard log, then replay fault
scenarios by driving the controller inputs per `docs/codelab/`.
Capture raw transcripts: they are the QNX evidence the passport references.

## 6. Record the evidence honestly

- Save compiler stdout/stderr, `qcc -V` output, target `uname -a`, the QEMU
  transcript + command line next to the passport.
- Only runs executed on the real target may set `verified_on_target=true`
  (via `qnx_target.py verify`, which writes `qnx-target-record.json` plus
  per-step transcripts); host runs always keep `false`. Feed the record to
  `genesis-rt demo --target-record <record>` for a target-qualified passport.
