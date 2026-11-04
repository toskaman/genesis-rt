#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX target helper: probe a QSTI image dir and boot it under QEMU.

Boot flags follow the official QSTI-for-QEMU guide (additional_specs),
adapted for the host: KVM only on Linux, WHPX/TCG on Windows, user-mode
networking by default. Never claims success without observed output:
the transcript markers are reported as seen/not-seen.

Requires (user-provided, login-walled): SDP 8.0 + com.qnx.qnx800.quickstart.qemu
package installed via QNX Software Center, unpacked with unpack_qemu_image.sh.
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.build_adapter import probe_qemu  # noqa: E402

BOOT_MARKERS = ("QNX", "Neutrino", "qnx", "login:", "Welcome")


def probe_image(image_dir: Path) -> dict:
    """Inventory an unpacked QSTI image dir (presence only, no claims)."""
    files = {p.name: p.stat().st_size for p in sorted(image_dir.glob("*")) if p.is_file()}
    out = image_dir / "output"
    if out.is_dir():
        for p in sorted(out.glob("*")):
            if p.is_file():
                files[f"output/{p.name}"] = p.stat().st_size
    has_ifs = any(n.endswith("ifs.bin") for n in files)
    has_disk = any(n.endswith((".vmdk", ".qcow2", ".img")) for n in files)
    return {"dir": str(image_dir), "files": files,
            "has_ifs_bin": has_ifs, "has_disk_image": has_disk,
            "bootable_layout": bool(has_ifs and has_disk)}


def build_qemu_argv(qemu: str, image_dir: Path, memory: str = "4G",
                    accel: str = "auto", extra: list[str] | None = None) -> list[str]:
    out = image_dir / "output" if (image_dir / "output").is_dir() else image_dir
    ifs = next((p for p in sorted(out.glob("*")) if p.name.endswith("ifs.bin")), None)
    disk = next((p for p in sorted(out.glob("*"))
                 if p.suffix in (".vmdk", ".qcow2", ".img")), None)
    if ifs is None or disk is None:
        raise FileNotFoundError(f"need ifs.bin + disk image under {image_dir}")
    argv = [qemu, "-m", memory, "-smp", "4",
           "-drive", f"file={disk},if=ide,id=drv0",
           "-kernel", str(ifs),
           "-serial", "mon:stdio", "-nographic",
           "-netdev", "user,id=net0",
           "-device", "virtio-net-pci,netdev=net0"]
    system = platform.system()
    if accel == "auto":
        accel = "kvm" if system == "Linux" else ("whpx" if system == "Windows" else "tcg")
    if accel == "kvm":
        argv += ["--enable-kvm", "-cpu", "host"]
    elif accel == "whpx":
        argv += ["-accel", "whpx"]
    argv += ["-pidfile", str(out / "qemu.pid")]
    if extra:
        argv += extra
    return argv


def cmd_probe_image(args: argparse.Namespace) -> int:
    inv = probe_image(Path(args.image_dir))
    print(f"dir: {inv['dir']}")
    for name, size in inv["files"].items():
        print(f"  {name}  ({size} bytes)")
    print(f"has_ifs_bin={inv['has_ifs_bin']} has_disk_image={inv['has_disk_image']} "
          f"bootable_layout={inv['bootable_layout']}")
    return 0 if inv["bootable_layout"] else 1


def cmd_boot(args: argparse.Namespace) -> int:
    qemu = probe_qemu()
    if not qemu["present"]:
        print("error: QEMU not found (set GENESIS_QEMU or install QEMU)", file=sys.stderr)
        return 2
    image_dir = Path(args.image_dir)
    try:
        argv = build_qemu_argv(qemu["path"], image_dir, memory=args.memory,
                              accel=args.accel, extra=args.qemu_arg)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript = out_dir / "qemu-console.log"
    print(f"qemu: {qemu['version']}")
    print(f"cmd: {' '.join(argv)}")
    print(f"transcript: {transcript}  (timeout {args.timeout}s)")
    (out_dir / "qemu-cmdline.txt").write_text(" ".join(argv) + "\n", encoding="utf-8")
    t0 = time.monotonic()
    try:
        with open(transcript, "wb") as fh:
            proc = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=fh,
                                  stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
    except subprocess.TimeoutExpired:
        print("note: timeout reached; QEMU keeps no state (see transcript)")
        rc = None
    else:
        rc = proc.returncode
    elapsed = round(time.monotonic() - t0, 1)
    text = transcript.read_bytes()[:200000].decode("utf-8", "replace")
    seen = sorted({m for m in BOOT_MARKERS if m in text})
    print(f"elapsed_s={elapsed} returncode={rc} bytes={transcript.stat().st_size}")
    print(f"markers_seen={seen if seen else 'NONE'}")
    if not seen:
        print("result: INCONCLUSIVE — no boot markers observed (inspect transcript)")
        return 3
    print("result: BOOT MARKERS OBSERVED — on-target genesis runs are the next step")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="QNX QSTI image probe + QEMU boot")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe-image", help="inventory an unpacked QSTI dir")
    p.add_argument("image_dir"); p.set_defaults(func=cmd_probe_image)
    b = sub.add_parser("boot", help="boot the image under QEMU, capture transcript")
    b.add_argument("image_dir")
    b.add_argument("--memory", default="4G")
    b.add_argument("--accel", default="auto", choices=["auto", "kvm", "whpx", "tcg"])
    b.add_argument("--timeout", type=int, default=180)
    b.add_argument("--out", default="artifacts/qemu-boot")
    b.add_argument("--qemu-arg", action="append", default=[])
    b.set_defaults(func=cmd_boot)
    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
