# QNX 8.0 + QEMU quickstart

> Nothing here redistributes QNX software. You install the SDK yourself
> from official sources under their license; this repo only probes for it
> and invokes its toolchain.

## 0. Status on this machine (verified 4 Nov 2026)

- QEMU 11.1.0 at `E:\VMs\qemu\qemu-system-x86_64.exe` — satisfies the
  official "upgrade to QEMU 10" recommendation. Override with `GENESIS_QEMU`.
- QNX SDP 8.0.0 at `E:\qnx800` (licence Education activée) + QSTI
  `com.qnx.qnx800.quickstart.qemu` 0.5.0 déballé. Auto-détecté même sans
  variables d'environnement.
- Boot prouvé : `--boot disk --disk-name disk-qemu` avec `-cpu host`
  (WHPX) ; `-kernel` direct et CPU émulé stallent le loader v1.2d.
- Cible : `QNX qnxqemu 8.0.0 x86_64`, SSH `qnxuser` (mot de passe =
  nom d'utilisateur par défaut de l'image).

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
ls /tmp/genesis-qnx/genesis_guard  # + controller/device/status/supervisor
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

Transfer the five binaries to the running target (shared folder/`scp` per
your setup), then on target:

```sh
./genesis_supervisor   # spawns guard/controller/device, monitors health
./genesis_status &     # serves /dev/genesis/status (read-only telemetry)
cat /dev/genesis/status
```

Observe `ALLOW`/`DENY` lines from the guard log, then replay fault
scenarios by driving the controller inputs per `docs/codelab/`.
Capture raw transcripts: they are the QNX evidence the passport references.

## 6. Record the evidence honestly

- Save compiler stdout/stderr, `qcc -V` output, target `uname -a`, the QEMU
  transcript + command line next to the passport.
- Only runs executed on the real target may set `verified_on_target=true`
  (via the target-side runner, roadmap); host runs always keep `false`.
