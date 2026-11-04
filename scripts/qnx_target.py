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
import json
import os
import platform
import re
import socket
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


def _default_cpu() -> str:
    """Host CPU model (QNX startup needs real CPUID; see options guidance)."""
    ident = os.environ.get("PROCESSOR_IDENTIFIER", "")
    if "intel" in ident.lower():
        return "host"
    if "amd" in ident.lower():
        return "host,host-phys-bits-limit=40"
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
        if "AuthenticAMD" in cpuinfo:
            return "host,host-phys-bits-limit=40"
        if "GenuineIntel" in cpuinfo:
            return "host"
    except OSError:
        pass
    return "default"


def build_qemu_argv(qemu: str, image_dir: Path, memory: str = "4G",
                    accel: str = "auto", boot: str = "kernel",
                    disk_name: str | None = None, ssh_port: int = 0,
                    cpu: str = "auto",
                    extra: list[str] | None = None) -> list[str]:
    out = image_dir / "output" if (image_dir / "output").is_dir() else image_dir
    ifs = next((p for p in sorted(out.glob("*")) if p.name.endswith("ifs.bin")), None)
    if disk_name:
        disk = out / disk_name
        disk = disk if disk.exists() else None
    else:
        disk = next((p for p in sorted(out.glob("*"))
                     if p.suffix in (".vmdk", ".qcow2", ".img")), None)
    if ifs is None or disk is None:
        raise FileNotFoundError(f"need ifs.bin + disk image under {image_dir}")
    fmt = ",format=raw" if disk.suffix == "" else ""
    netdev = "user,id=net0"
    if ssh_port:
        netdev += f",hostfwd=tcp:127.0.0.1:{ssh_port}-:22"
    argv = [qemu, "-m", memory, "-smp", "4",
           "-drive", f"file={disk},if=ide,id=drv0{fmt}",
           "-serial", "mon:stdio", "-nographic",
           "-netdev", netdev,
           "-device", "virtio-net-pci,netdev=net0"]
    if boot == "kernel":
        argv += ["-kernel", str(ifs)]
    else:
        argv += ["-boot", "order=c,menu=off"]
    system = platform.system()
    if accel == "auto":
        accel = "kvm" if system == "Linux" else ("whpx" if system == "Windows" else "tcg")
    if cpu == "auto":
        cpu = _default_cpu()
    if accel == "kvm":
        argv += ["--enable-kvm"]
    elif accel == "whpx":
        argv += ["-accel", "whpx"]
    if cpu != "default":
        argv += ["-cpu", cpu]
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


def _qmp_screendump(port: int, path: Path) -> str:
    """Grab the emulated VGA framebuffer over QMP. Returns status string."""
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=15)
    except OSError as exc:
        return f"qmp-connect-failed: {exc}"
    try:
        fh = sock.makefile("r", encoding="utf-8")
        fh.readline()  # greeting
        sock.sendall(b'{"execute": "qmp_capabilities"}\n')
        fh.readline()  # ack
        cmd = {"execute": "screendump",
               "arguments": {"filename": str(path), "format": "png"}}
        sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
        resp = fh.readline()
        return f"qmp-response: {resp.strip()[:200]}"
    except OSError as exc:
        return f"qmp-error: {exc}"
    finally:
        sock.close()


def cmd_boot(args: argparse.Namespace) -> int:
    qemu = probe_qemu()
    if not qemu["present"]:
        print("error: QEMU not found (set GENESIS_QEMU or install QEMU)", file=sys.stderr)
        return 2
    image_dir = Path(args.image_dir)
    try:
        argv = build_qemu_argv(qemu["path"], image_dir, memory=args.memory,
                              accel=args.accel, boot=args.boot,
                              disk_name=args.disk_name, ssh_port=args.ssh_port,
                              cpu=args.cpu, extra=args.qemu_arg)
        if args.qmp_port:
            argv = argv + ["-qmp", f"tcp:127.0.0.1:{args.qmp_port},server=on,wait=off"]
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
    shot_status = "no-qmp"
    if args.qmp_port and args.shot_at:
        with open(transcript, "wb") as fh:
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=fh,
                                    stderr=subprocess.STDOUT)
            try:
                deadline = t0 + args.timeout
                shot_done = False
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        break
                    if not shot_done and time.monotonic() - t0 >= args.shot_at:
                        shot_status = _qmp_screendump(
                            args.qmp_port, out_dir / "vga-shot.png")
                        shot_done = True
                    time.sleep(2)
                else:
                    print("note: timeout reached; QEMU keeps no state (see transcript)")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            rc = proc.returncode
        print(f"screenshot: {shot_status}")
    else:
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


def _ssh_client(port: int, user: str, password: str, timeout: int = 30,
                retries: int = 4):
    """Connect with bounded, PATIENT retries. Two stacked hazards were
    observed against QEMU SLIRP/WHPX + guest OpenSSH >= 9.8:

    1. Transient mid-handshake failures (pre-existing environmental flap):
       an isolated attempt can die with AuthenticationException even with
       correct credentials; the next attempt minutes later succeeds.
    2. PerSourcePenalties: a burst of rapid reconnects gets the source
       penalised and every new connection is answered "Not allowed at
       this time" until the penalty decays -- and each new probe during
       the penalty extends it.

    A tight retry loop turns hazard 1 into hazard 2 (measured 3/3: a
    success immediately followed by rapid retries produced 8/8 fails +
    penalty box). So attempts are spaced 45 s apart (max ~4 min per
    command), a banner/penalty failure triggers one long 300 s cooldown
    instead of hammering, and giving up still fails loudly, never
    silently. Operational rule: run ONE ssh command at a time and never
    probe right before the real command -- the command itself is the
    probe."""
    import paramiko  # noqa: PLC0415
    last: Exception | None = None
    cooled_down = False
    for attempt in range(1, retries + 1):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect("127.0.0.1", port=port, username=user,
                           password=password, timeout=timeout,
                           banner_timeout=timeout, auth_timeout=timeout,
                           look_for_keys=False, allow_agent=False)
            return client
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"ssh: attempt {attempt}/{retries} failed: "
                  f"{type(exc).__name__}: {exc}")
            if attempt >= retries:
                break
            # Penalty-box signature: no SSH banner at all (sshd answered
            # "Not allowed at this time" and closed). Hammering extends the
            # ban, so back off hard once, then resume normal spacing.
            if not cooled_down and "banner" in str(exc).lower():
                print("ssh: penalty-box suspected (no banner); "
                      "cooling down 300 s before retrying")
                time.sleep(300)
                cooled_down = True
            else:
                time.sleep(45)
    raise last if last else RuntimeError("ssh connect failed")


def cmd_wait_ssh(args: argparse.Namespace) -> int:
    deadline = time.monotonic() + args.wait
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection(("127.0.0.1", args.ssh_port), timeout=5)
            sock.close()
            print(f"ssh: port {args.ssh_port} open")
            return 0
        except OSError:
            time.sleep(5)
    print(f"ssh: port {args.ssh_port} never opened after {args.wait}s")
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    rc_all = 0
    out_lines: list[str] = []
    try:
        for command in args.command:
            header = f"$ {command}"
            print(header)
            out_lines.append(header)
            _stdin, stdout, stderr = client.exec_command(command, timeout=args.timeout)
            deadline = time.monotonic() + args.timeout
            while not stdout.channel.exit_status_ready():
                if time.monotonic() > deadline:
                    out_lines.append(f"[TIMEOUT after {args.timeout}s]")
                    print(f"[TIMEOUT after {args.timeout}s]")
                    return 3
                time.sleep(0.5)
            status = stdout.channel.recv_exit_status()
            body = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            print(body, end="" if body.endswith("\n") else "\n")
            if err.strip():
                print(f"[stderr] {err}", end="" if err.endswith("\n") else "\n")
            print(f"[exit={status}]")
            out_lines += [body, f"[exit={status}]"]
            rc_all = rc_all or (0 if status == 0 else 1)
    finally:
        client.close()
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        print(f"transcript: {out_path}")
    return rc_all


TARGET_MATRIX = [
    ("target_info", "uname -a; echo ---; pidin -F %n 2>/dev/null | head -5"),
    ("faultinject",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null; rm -f guard.log;"
     " ./genesis_guard > guard.log 2>&1 & sleep 3; ./genesis_faultinject;"
     " echo FI_EXIT=$?; sleep 1; echo ---GUARD-LOG---; cat guard.log;"
     " slay genesis_guard"),
    ("status_live",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " sudo -n slay genesis_status 2>/dev/null; rm -f guard.log;"
     " ./genesis_guard > guard.log 2>&1 & sleep 2;"
     " sudo -n ./genesis_status > status-root.log 2>&1 & sleep 2;"
     " echo ---STATUS-BEFORE---; cat /dev/genesis/status;"
     " ./genesis_faultinject > fi-status.log 2>&1; echo FI_EXIT=$?;"
     " echo ---STATUS-AFTER---; cat /dev/genesis/status; echo STATUS_CAT_EXIT=$?;"
     " slay genesis_guard; sudo -n slay genesis_status"),
    ("limits_differ",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; sleep 1;"
     " test -x ./genesis_guard_conv || { echo MISSING_CONV_GUARD; exit 3; };"
     " ./genesis_guard > guard-amr.log 2>&1 & sleep 2;"
     " echo ---PROBE-AMR---; ./genesis_faultinject probe 1.5;"
     " slay genesis_guard; slay genesis_guard_conv 2>/dev/null; sleep 1;"
     " ./genesis_guard_conv > guard-conv.log 2>&1 & sleep 2;"
     " echo ---PROBE-CONV---; ./genesis_faultinject probe 1.5;"
     " slay genesis_guard_conv; sleep 1;"
     " ./genesis_guard_conv > guard-conv.log 2>&1 & sleep 2;"
     " echo ---FI-VS-CONV---; ./genesis_faultinject; echo FI_CONV_EXIT=$?;"
     " slay genesis_guard; slay genesis_guard_conv 2>/dev/null;"
     " echo ---GUARD-HEADERS---;"
     " grep -h machine guard-amr.log guard-conv.log"),
    ("device_chain",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; slay genesis_status 2>/dev/null; sleep 1;"
     " rm -f device.log guard-dc.log ctrl-dc.log;"
     " ./genesis_device > device.log 2>&1 &"
     " ./genesis_guard > guard-dc.log 2>&1 & GUARDPID=$!; sleep 2;"
     " ./genesis_status /tmp/genesis-status-node > status-dc.log 2>&1 & sleep 1;"
     " ./genesis_controller 50 > ctrl-dc.log 2>&1 & sleep 4;"
     " echo ---CHAIN-STATUS---; cat /tmp/genesis-status-node; echo STATUS_EXIT=$?;"
     " echo ---STATUS-DC-LOG---; cat status-dc.log;"
     " echo ---GUARD-DC-HEAD---; head -6 guard-dc.log;"
     " slay genesis_controller; sleep 1;"
     " echo APPLIES=$(grep -c APPLY device.log);"
     " echo APPLY-SAMPLE=$(head -2 device.log | tr '\n' '|');"
     " echo NONGUARD=$(grep APPLY device.log | grep -vc \"from_pid=$GUARDPID \");"
     " echo GUARDPID=$GUARDPID;"
     " slay genesis_guard; slay genesis_device; slay genesis_status"),
    ("controller_flow",
     "cd /tmp/genesis; rm -f guard.log ctrl.log;"
     " ./genesis_guard > guard.log 2>&1 & sleep 2;"
     " ./genesis_controller 100 > ctrl.log 2>&1 & sleep 6;"
     " slay genesis_controller; slay genesis_guard;"
     " grep -c ALLOW guard.log; grep -c DENY guard.log || true"),
    ("supervisor_respawn",
     "cd /tmp/genesis; slay genesis_supervisor 2>/dev/null;"
     " slay genesis_guard 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; rm -f sup.log; sleep 1;"
     " ./genesis_supervisor > sup.log 2>&1 & sleep 4;"
     " slay genesis_device; sleep 6;"
     " pidin -F %n 2>/dev/null | grep -c genesis;"
     " grep -c RESPAWN sup.log;"
     " echo ---SUP-LOG---; cat sup.log;"
     " slay genesis_supervisor; slay genesis_guard;"
     " slay genesis_controller; slay genesis_device"),
    ("supervisor_giveup",
     "cd /tmp/genesis; slay genesis_supervisor 2>/dev/null;"
     " slay genesis_guard 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; rm -f sup2.log; sleep 1;"
     " ./genesis_supervisor > sup2.log 2>&1 & sleep 4;"
     " for i in 1 2 3 4; do slay genesis_guard; sleep 6; done; sleep 2;"
     " pidin -F %n 2>/dev/null | grep -c genesis || true;"
     " grep -c GIVE_UP sup2.log;"
     " slay genesis_supervisor 2>/dev/null; slay genesis_guard 2>/dev/null;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; true"),
]


def _matrix_check(name: str, body: str, status: int) -> dict:
    """Parse one matrix step into a pass/fail check (strict assertions)."""
    if name == "target_info":
        ok = status == 0 and "QNX" in body and "x86_64" in body
    elif name == "faultinject":
        # compound exit code is slay's (1 even on success); FI_EXIT is authoritative
        ok = ("ALL 9 CHECKS PASS" in body and "FI_EXIT=0" in body
              and body.count("PASS ") >= 9)
    elif name == "status_live":
        # Live telemetry: counters must move with real guard traffic and the
        # SAFE_STOP latch (left by faultinject) must be visible as state=3.
        allows = [int(n) for n in re.findall(r"allows=(\d+)", body)]
        denies = [int(n) for n in re.findall(r"denies=(\d+)", body)]
        ok = ("STATUS_CAT_EXIT=0" in body and "FI_EXIT=0" in body
              and "last_reason=BAD_TRANSITION" in body
              and allows == [0, 1] and denies == [0, 8]
              and "state=1 " in body.split("---STATUS-AFTER---")[0]
              and body.rsplit("state=", 1)[1].startswith("3 "))
    elif name == "limits_differ":
        # Same probe (1.5 mps) must DENY on the AMR guard (limit 1.2) and
        # ALLOW on the conveyor guard (limit 2.0): generated limits drive
        # runtime behavior. Guard banners pin which binary answered.
        parts = body.split("---PROBE-CONV---")
        ok = (len(parts) == 2
              and "decision=DENY reason=SPEED_OVER_LIMIT" in parts[0]
              and "decision=ALLOW reason=OK" in parts[1]
              and "ALL 9 CHECKS PASS" in parts[1]
              and "FI_CONV_EXIT=0" in parts[1]
              and "machine=amr-demo-01 limits linear=1.200" in body
              and "machine=conveyor-demo-01 limits linear=2.000" in body
              and "MISSING_CONV_GUARD" not in body)
    elif name == "device_chain":
        # Full actuation chain: controller -> guard -> device -> status.
        # The virtual robot must have MOVED (dev_x > 0), every applied
        # command must come from the guard pid (no bypass), and no
        # forward may have failed while the device was up.
        def _num(pat, cast=float, default=None):
            m = re.search(pat, body)
            return cast(m.group(1)) if m else default
        ok = ("STATUS_EXIT=0" in body
              and (_num(r"dev_applied=(\d+)", int, 0) or 0) >= 20
              and (_num(r"dev_x=([\d.]+)", float, 0.0) or 0.0) > 0.2
              and (_num(r"dev_v=([\d.]+)", float, 0.0) or 0.0) > 0.3
              and (_num(r"fwd_ok=(\d+)", int, 0) or 0) >= 20
              and _num(r"fwd_fail=(\d+)", int, -1) == 0
              and _num(r"APPLIES=(\d+)", int, 0) >= 20
              and _num(r"NONGUARD=(\d+)", int, -1) == 0)
    elif name == "controller_flow":
        ok = False
        for line in body.splitlines():
            line = line.strip()
            if line.isdigit() and int(line) >= 50:
                ok = True  # >=50 ALLOW lines in 6 s at 100 ms
    elif name == "supervisor_respawn":
        digits = [line.strip() for line in body.splitlines() if line.strip().isdigit()]
        # set back to 4 after respawn, >=1 RESPAWN marker in sup.log
        ok = len(digits) >= 2 and digits[0] == "4" and int(digits[1]) >= 1
    elif name == "supervisor_giveup":
        digits = [line.strip() for line in body.splitlines() if line.strip().isdigit()]
        # set halted (0 genesis processes), >=1 GIVE_UP marker in sup2.log
        ok = len(digits) >= 2 and digits[0] == "0" and int(digits[1]) >= 1
    else:
        ok = False
    return {"name": name, "passed": ok, "detail": body[-500:].strip().replace("\n", " | ")}


def cmd_verify(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    all_ok = True
    try:
        for name, command in TARGET_MATRIX:
            _stdin, stdout, stderr = client.exec_command(command, timeout=180)
            deadline = time.monotonic() + 180
            while not stdout.channel.exit_status_ready():
                if time.monotonic() > deadline:
                    results.append({"name": name, "passed": False, "detail": "TIMEOUT"})
                    all_ok = False
                    break
                time.sleep(1)
            else:
                status = stdout.channel.recv_exit_status()
                body = stdout.read().decode("utf-8", "replace")
                (out_dir / f"target-{name}.log").write_text(
                    f"$ {command}\n{body}\n[exit={status}]\n", encoding="utf-8")
                check = _matrix_check(name, body, status)
                results.append(check)
                all_ok = all_ok and check["passed"]
                print(f"target:{name}: {'PASS' if check['passed'] else 'FAIL'}")
    finally:
        client.close()
    record = {"status": "ok" if all_ok else "fail",
              "verified_on_target": all_ok,
              "user": args.user, "checks": results,
              "note": "executed on QNX 8.0 QEMU target over SSH; transcripts beside record"}
    (out_dir / "qnx-target-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"target verification: {'PASS' if all_ok else 'FAIL'} -> {out_dir}")
    return 0 if all_ok else 1


def cmd_put(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    try:
        sftp = client.open_sftp()
        try:
            sftp.mkdir(args.dest)
        except OSError:
            pass  # exists
        for src in args.src:
            name = Path(src).name
            dst = f"{args.dest}/{name}"
            sftp.put(src, dst)
            sftp.chmod(dst, 0o755)
            print(f"put: {src} -> {dst}")
        return 0
    finally:
        client.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="QNX QSTI image probe + QEMU boot")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe-image", help="inventory an unpacked QSTI dir")
    p.add_argument("image_dir"); p.set_defaults(func=cmd_probe_image)
    b = sub.add_parser("boot", help="boot the image under QEMU, capture transcript")
    b.add_argument("image_dir")
    b.add_argument("--memory", default="4G")
    b.add_argument("--accel", default="auto", choices=["auto", "kvm", "whpx", "tcg"])
    b.add_argument("--boot", default="kernel", choices=["kernel", "disk"])
    b.add_argument("--disk-name", default=None,
                   help="disk file inside output/ (default: first .vmdk/.qcow2/.img)")
    b.add_argument("--ssh-port", type=int, default=0,
                   help="forward host port to target sshd (0 = off)")
    b.add_argument("--cpu", default="auto",
                   help="QEMU -cpu model (auto = host passthrough when detected)")
    w = sub.add_parser("wait-ssh", help="wait until the forwarded sshd port opens")
    w.add_argument("--ssh-port", type=int, default=2222)
    w.add_argument("--wait", type=int, default=300)
    w.set_defaults(func=cmd_wait_ssh)
    r = sub.add_parser("run", help="run commands on target over SSH (paramiko)")
    r.add_argument("--ssh-port", type=int, default=2222)
    r.add_argument("--user", default="root")
    r.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    r.add_argument("--timeout", type=int, default=120)
    r.add_argument("--out", default=None)
    r.add_argument("command", nargs="+")
    r.set_defaults(func=cmd_run)
    t = sub.add_parser("put", help="upload files to target over SFTP (+x)")
    t.add_argument("--ssh-port", type=int, default=2222)
    t.add_argument("--user", default="qnxuser")
    t.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    t.add_argument("--dest", default="/tmp/genesis")
    t.add_argument("src", nargs="+")
    t.set_defaults(func=cmd_put)
    v = sub.add_parser("verify", help="run the on-target verification matrix over SSH")
    v.add_argument("--ssh-port", type=int, default=2222)
    v.add_argument("--user", default="qnxuser")
    v.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    v.add_argument("--out", default="artifacts/runs/qnx-target")
    v.set_defaults(func=cmd_verify)
    b.add_argument("--timeout", type=int, default=180)
    b.add_argument("--qmp-port", type=int, default=0)
    b.add_argument("--shot-at", type=int, default=0,
                   help="seconds after boot to capture VGA via QMP (needs --qmp-port)")
    b.add_argument("--out", default="artifacts/qemu-boot")
    b.add_argument("--qemu-arg", action="append", default=[])
    b.set_defaults(func=cmd_boot)
    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
