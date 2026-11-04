# QNX 8.0 + QEMU quickstart

> Nothing here redistributes QNX software. You install the SDK yourself
> from official sources under their license; this repo only probes for it
> and invokes its toolchain.

## 1. Get the SDK lawfully

1. Request QNX SDP 8.0 access via https://www.qnx.com/getqnx (QNX Everywhere
   for eligible non-commercial use) and accept the license in your browser.
2. Install per the official host docs:
   https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.quickstart/topic/install_host.html
3. Install a supported QEMU x86_64 target image per:
   https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/about.html

**License caution:** QNX Everywhere covers eligible non-commercial and some
OSS-interoperability uses; commercial product development may need
commercial terms. The hackathon excludes projects with preferential or
financial sponsor support — do not seek commercial/sponsored licensing
during the entry period without written eligibility clarification.

## 2. Verify the toolchain

```sh
source ~/qnx800/qnxsdp-env.sh   # path varies by install; do not assume
python scripts/qnx_env_check.py  # expect sdk_present=true
```

## 3. Build the generated target

```sh
genesis-rt generate examples/amr-demo/machine-ir.json --out /tmp/genesis-qnx
make -C /tmp/genesis-qnx -f genesis_build_gen.mk qnx
ls /tmp/genesis-qnx/genesis_guard  # + controller/device/status/supervisor
```

## 4. Run on QEMU

Transfer the five binaries to the QEMU target (shared folder or `scp` per
your target setup), then on target:

```sh
./genesis_supervisor   # spawns guard/controller/device, monitors health
./genesis_status &     # serves /dev/genesis/status (read-only telemetry)
cat /dev/genesis/status
```

Observe `ALLOW`/`DENY` lines from the guard log, then replay fault
scenarios by driving the controller inputs per `docs/codelab/`.
Capture raw transcripts: they are the QNX evidence the passport references.

## 5. Record the evidence honestly

- Save compiler stdout/stderr, `qcc -V` output, target `uname -a` and the
  QEMU invocation line next to the passport.
- Only runs executed on the real target may set `verified_on_target=true`
  (via the target-side runner, roadmap); host runs always keep `false`.
