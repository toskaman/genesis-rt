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

from genesis_rt import buildset, codegen, provenance  # noqa: E402
from genesis_rt.ir import load_ir_file  # noqa: E402
from genesis_rt.build_adapter import probe_qemu  # noqa: E402

BOOT_MARKERS = ("QNX", "Neutrino", "qnx", "login:", "Welcome")

# SSH retry policy (regression-pinned, see tests/unit/test_ssh_policy.py).
# Root cause: guest OpenSSH PerSourcePenalties bans rapid reconnect bursts
# ("Not allowed at this time"); each probe during the ban extends it.
_SSH_MAX_ATTEMPTS = 4
_SSH_ATTEMPT_GAP_S = 45
_SSH_PENALTY_COOLDOWN_S = 300


def _ssh_is_penalty_box_signature(exc: Exception) -> bool:
    """True when an SSH failure looks like a server-side penalty ban.

    Two observed surface forms: paramiko failing to read the SSH banner
    (sshd closed the connection instead of greeting), and sshd's explicit
    "Not allowed at this time" refusal. Both must trigger the long
    cooldown, never the short gap: retrying fast extends the ban.
    """
    text = str(exc).lower()
    return "banner" in text or "not allowed at this time" in text


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
        # QNX 8 startup spins forever on default qemu64 under TCG (guest
        # RIP frozen, 2 cores burned, zero progress); -cpu max boots.
        # -cpu host is invalid without a hardware accelerator.
        cpu = "max" if accel == "tcg" else _default_cpu()
    if accel == "tcg" and cpu.split(",")[0].strip() == "host":
        raise ValueError("cpu 'host' needs a hardware accelerator (kvm/whpx), not tcg")
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
                retries: int = _SSH_MAX_ATTEMPTS):
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
            # Penalty-box signature (banner missing or explicit refusal).
            # Hammering extends the ban, so back off hard once, then resume
            # normal spacing.
            if not cooled_down and _ssh_is_penalty_box_signature(exc):
                print("ssh: penalty-box suspected; "
                      f"cooling down {_SSH_PENALTY_COOLDOWN_S} s before retrying")
                time.sleep(_SSH_PENALTY_COOLDOWN_S)
                cooled_down = True
            else:
                time.sleep(_SSH_ATTEMPT_GAP_S)
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
     # NOTE: genesis_status runs under sudo -n like status_live:
     # resmgr_attach() at an absolute path requires root (qnxuser gets
     # EPERM "Operation not permitted" and the node never appears).
     # Cleanup slays it with sudo too, or a stale root process would
     # pollute the supervisor steps' pidin counts.
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; sudo -n slay genesis_status 2>/dev/null; sleep 1;"
     " rm -f device.log guard-dc.log ctrl-dc.log;"
     " ./genesis_device > device.log 2>&1 &"
     " ./genesis_guard > guard-dc.log 2>&1 & GUARDPID=$!; sleep 2;"
     " sudo -n ./genesis_status /tmp/genesis-status-node > status-dc.log 2>&1 & sleep 1;"
     " ./genesis_controller 50 > ctrl-dc.log 2>&1 & sleep 4;"
     " echo ---CHAIN-STATUS---; cat /tmp/genesis-status-node; echo STATUS_EXIT=$?;"
     " echo ---STATUS-DC-LOG---; cat status-dc.log;"
     " echo ---GUARD-DC-HEAD---; head -6 guard-dc.log;"
     " slay genesis_controller; sleep 1;"
     " echo APPLIES=$(grep -c APPLY device.log);"
     " echo APPLY-SAMPLE=$(head -2 device.log | tr '\n' '|');"
     " echo NONGUARD=$(grep APPLY device.log | grep -vc \"from_pid=$GUARDPID \");"
     " echo GUARDPID=$GUARDPID;"
     " slay genesis_guard; slay genesis_device; sudo -n slay genesis_status"),
    ("conv_chain",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; sudo -n slay genesis_status 2>/dev/null; sleep 1;"
     " rm -f device-conv.log guard-cc.log ctrl-cc.log;"
     " test -x ./genesis_guard_conv || { echo MISSING_CONV_GUARD; exit 3; };"
     " ./genesis_device belt > device-conv.log 2>&1 &"
     " ./genesis_guard_conv > guard-cc.log 2>&1 & GUARDPID=$!; sleep 2;"
     " sudo -n ./genesis_status /tmp/genesis-status-node > status-cc.log 2>&1 & sleep 1;"
     " ./genesis_controller 50 > ctrl-cc.log 2>&1 & sleep 4;"
     " echo ---CHAIN-STATUS---; cat /tmp/genesis-status-node; echo STATUS_EXIT=$?;"
     " echo ---DEVICE-CONV-HEAD---; head -3 device-conv.log;"
     " slay genesis_controller; sleep 1;"
     " echo APPLIES=$(grep -c APPLY device-conv.log);"
     " echo APPLY-SAMPLE=$(head -2 device-conv.log | tr '\\n' '|');"
     " echo NONGUARD=$(grep APPLY device-conv.log | grep -vc \"from_pid=$GUARDPID \");"
     " echo BELT=$(grep -c belt_pos device-conv.log);"
     " echo GUARDPID=$GUARDPID;"
     " slay genesis_guard_conv; slay genesis_device; sudo -n slay genesis_status"),
    ("estop_target",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " sudo -n slay genesis_status 2>/dev/null; sleep 1;"
     " rm -f guard-estop.log;"
     " ./genesis_guard > guard-estop.log 2>&1 & sleep 2;"
     " sudo -n ./genesis_status /tmp/genesis-status-node > status-estop.log 2>&1 & sleep 1;"
     " echo ---ESTOP-PROBE---; ./genesis_faultinject probe estop;"
     " echo ---STATUS-ESTOP---; cat /tmp/genesis-status-node; echo STATUS_EXIT=$?;"
     " slay genesis_guard; sudo -n slay genesis_status"),
    ("target_perf",
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard > guard-perf.log 2>&1 & sleep 2;"
     " ./genesis_faultinject bench 200;"
     " echo BENCH_EXIT=$?; slay genesis_guard"),
    ("controller_flow",
     "cd /tmp/genesis; rm -f guard.log ctrl.log;"
     " ./genesis_guard > guard.log 2>&1 & sleep 2;"
     " ./genesis_controller 100 > ctrl.log 2>&1 & sleep 6;"
     " slay genesis_controller; slay genesis_guard;"
     " grep -c ALLOW guard.log; grep -c DENY guard.log || true"),
    ("supervisor_respawn",
     "cd /tmp/genesis; slay genesis_supervisor 2>/dev/null;"
     " slay genesis_guard 2>/dev/null; slay genesis_controller 2>/dev/null;"
     " slay genesis_device 2>/dev/null; rm -f sup.log sup-*.log; sleep 1;"
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
     " slay genesis_device 2>/dev/null; rm -f sup2.log sup-*.log; sleep 1;"
     " ./genesis_supervisor > sup2.log 2>&1 & sleep 4;"
     " for i in 1 2 3 4; do slay genesis_guard; sleep 6; done; sleep 2;"
     " pidin -F %n 2>/dev/null | grep -c genesis || true;"
     " grep -c GIVE_UP sup2.log;"
     " slay genesis_supervisor 2>/dev/null; slay genesis_guard 2>/dev/null;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; true"),
    ("v2_transitions",
     # §5 native proof: same cruise magnitude, only req_state varies, one
     # fresh guard per probe (guard ctx persists across probes). The v1
     # binary holds the fixed table, genesis_guard_v2 the table generated
     # from the AMR IR v2 (build the v2 dir, copy its genesis_guard aside
     # as genesis_guard_v2 -- same bytes, staged name -- then put it).
     # Bidirectional contrast: v1 ALLOWs state 2 where v2 DENYs it (C),
     # v2 ALLOWs state 3 where v1 DENYs it (B). Suite/limit/estop pin
     # F-on-v2-binary, A and D natively.
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_v2 2>/dev/null; sleep 1;"
     " test -x ./genesis_guard_v2 || { echo MISSING_V2_GUARD; exit 3; };"
     " cmp -s ./genesis_guard ./genesis_guard_v2 && echo SAME_BIN || echo DIFF_BIN;"
     " ./genesis_guard > guard-v1s2.log 2>&1 & sleep 2;"
     " echo ---V1-STATE2---; ./genesis_faultinject probe state 2;"
     " slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard > guard-v1s3.log 2>&1 & sleep 2;"
     " echo ---V1-STATE3---; ./genesis_faultinject probe state 3;"
     " slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard_v2 > guard-v2s2.log 2>&1 & sleep 2;"
     " echo ---V2-STATE2---; ./genesis_faultinject probe state 2;"
     " slay genesis_guard_v2 2>/dev/null; slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard_v2 > guard-v2s3.log 2>&1 & sleep 2;"
     " echo ---V2-STATE3---; ./genesis_faultinject probe state 3;"
     " slay genesis_guard_v2 2>/dev/null; slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard_v2 > guard-v2fi.log 2>&1 & sleep 2;"
     " echo ---V2-SUITE---; ./genesis_faultinject; echo FI_V2_EXIT=$?;"
     " slay genesis_guard_v2 2>/dev/null; slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard_v2 > guard-v2lim.log 2>&1 & sleep 2;"
     " echo ---V2-LIMIT---; ./genesis_faultinject probe 1.5;"
     " slay genesis_guard_v2 2>/dev/null; slay genesis_guard 2>/dev/null; sleep 1;"
     " ./genesis_guard_v2 > guard-v2est.log 2>&1 & sleep 2;"
     " echo ---V2-ESTOP---; ./genesis_faultinject probe estop;"
     " slay genesis_guard_v2 2>/dev/null; slay genesis_guard 2>/dev/null; true"),
    ("controller_crash",
     # Fault containment: SIGKILL the controller mid-chain. The device
     # must freeze (<=3 in-flight applies may still land), the guard
     # log must freeze too (no phantom traffic once the source is
     # gone), every apply must come from the guard pid (no bypass),
     # the controller must be gone from pidin, and the guard must
     # survive. NOTE: pidin -F %n shows `./genesis_*` with padding,
     # so exact ^...$ matches never fire; plain substring counts are
     # used (conv/v2 guards are slain at step start, so no
     # cross-match is possible).
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_guard_v2 2>/dev/null;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; sleep 1;"
     " rm -f device-ccx.log guard-ccx.log ctrl-ccx.log;"
     " ./genesis_device > device-ccx.log 2>&1 &"
     " ./genesis_guard > guard-ccx.log 2>&1 & GPID=$!; sleep 2;"
     " ./genesis_controller 50 > ctrl-ccx.log 2>&1 & sleep 4;"
     " echo BEFORE=$(grep -c APPLY device-ccx.log);"
     " echo GBEFORE=$(grep -c decision guard-ccx.log);"
     " slay -9 genesis_controller; sleep 3;"
     " echo AFTER=$(grep -c APPLY device-ccx.log);"
     " echo GAFTER=$(grep -c decision guard-ccx.log);"
     " echo NONGUARD=$(grep APPLY device-ccx.log | grep -vc \"from_pid=$GPID \");"
     " echo CALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_controller);"
     " echo GALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_guard);"
     " slay genesis_guard 2>/dev/null; slay genesis_device 2>/dev/null; true"),
    ("device_crash",
     # Fault containment: SIGKILL the device mid-chain. The device
     # log must freeze (<=3 in-flight applies), the guard must KEEP
     # deciding (source + policy path alive despite the dead sink),
     # every apply must come from the guard pid, the device must be
     # gone from pidin, and controller + guard must survive.
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_guard_v2 2>/dev/null;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; sleep 1;"
     " rm -f device-dcx.log guard-dcx.log ctrl-dcx.log;"
     " ./genesis_device > device-dcx.log 2>&1 &"
     " ./genesis_guard > guard-dcx.log 2>&1 & GPID=$!; sleep 2;"
     " ./genesis_controller 50 > ctrl-dcx.log 2>&1 & sleep 4;"
     " echo BEFORE=$(grep -c APPLY device-dcx.log);"
     " echo GBEFORE=$(grep -c decision guard-dcx.log);"
     " slay -9 genesis_device; sleep 3;"
     " echo AFTER=$(grep -c APPLY device-dcx.log);"
     " echo GAFTER=$(grep -c decision guard-dcx.log);"
     " echo NONGUARD=$(grep APPLY device-dcx.log | grep -vc \"from_pid=$GPID \");"
     " echo DALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_device);"
     " echo CALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_controller);"
     " echo GALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_guard);"
     " slay genesis_controller 2>/dev/null; slay genesis_guard 2>/dev/null; true"),
    ("guard_crash",
     # Fault containment: SIGKILL the guard mid-chain. The device must
     # freeze (<=3 in-flight applies may still land), every apply must
     # come from the dead guard pid (no bypass), the guard must be gone
     # from pidin, and the orphaned controller must observe MsgSend
     # failures instead of silently succeeding.
     "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
     " slay genesis_guard_conv 2>/dev/null; slay genesis_guard_v2 2>/dev/null;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; sleep 1;"
     " rm -f device-gc.log guard-gc.log ctrl-gc.log;"
     " ./genesis_device > device-gc.log 2>&1 &"
     " ./genesis_guard > guard-gc.log 2>&1 & GPID=$!; sleep 2;"
     " ./genesis_controller 50 > ctrl-gc.log 2>&1 & sleep 4;"
     " echo BEFORE=$(grep -c APPLY device-gc.log);"
     " slay -9 genesis_guard; sleep 3;"
     " echo AFTER=$(grep -c APPLY device-gc.log);"
     " echo NONGUARD=$(grep APPLY device-gc.log | grep -vc \"from_pid=$GPID \");"
     " echo ALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_guard);"
     " echo ---CTRL-GC-TAIL---; tail -5 ctrl-gc.log;"
     " slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null; true"),
    ("cell_policy",
     "cd /tmp/genesis;"
     " test -x ./genesis_cellcheck || { echo MISSING_CELLCHECK; exit 3; };"
     " ./genesis_cellcheck selftest; echo CELL_EXIT=$?"),
]


def _matrix_check(name: str, body: str, status: int,
                  bound: dict | None = None) -> dict:
    """Parse one matrix step into a pass/fail check (strict assertions).

    bound is the _ir_binding() dict when verify ran with --ir: the
    limits_differ step pins the slot-1 guard banner to the bound IR
    instead of the legacy AMR machine."""
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
        # Same probe (1.5 mps) must DENY on the slot-1 guard and ALLOW on
        # the conveyor guard (limit 2.0): generated limits drive runtime
        # behavior. Guard banners pin which binary answered; the slot-1
        # banner must match the --ir-bound machine (legacy AMR when
        # unattested). Geometry is enforced: a bound limit >= the probe
        # would make the DENY expectation meaningless, so it fails
        # closed instead of weakening the assertion.
        parts = body.split("---PROBE-CONV---")
        conv_pin = "machine=conveyor-demo-01 limits linear=2.000"
        if bound is None:
            slot1_pin: str | None = "machine=amr-demo-01 limits linear=1.200"
            geometry_ok = True
        else:
            try:
                mid = str(bound["machine_id"])
                lim = float(bound["linear_limit_mps"])
            except (KeyError, TypeError, ValueError):
                mid, lim = "", float("nan")
            slot1_pin = (f"machine={mid} limits linear={lim:.3f}"
                         if mid and lim == lim else None)
            geometry_ok = (slot1_pin is not None
                           and mid != "conveyor-demo-01"
                           and 0.0 < lim < 1.5 < 2.0)
        ok = (len(parts) == 2
              and "decision=DENY reason=SPEED_OVER_LIMIT" in parts[0]
              and "decision=ALLOW reason=OK" in parts[1]
              and "ALL 9 CHECKS PASS" in parts[1]
              and "FI_CONV_EXIT=0" in parts[1]
              and slot1_pin is not None and slot1_pin in body
              and conv_pin in body
              and geometry_ok
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
    elif name == "conv_chain":
        # Conveyor twin of device_chain: conv guard -> belt device ->
        # status. The BELT counter ties every APPLY to a belt_pos audit
        # line, and the banner pins belt mode (pose lines would fail).
        def _num(pat, cast=float, default=None):
            m = re.search(pat, body)
            return cast(m.group(1)) if m else default
        ok = ("STATUS_EXIT=0" in body
              and "MISSING_CONV_GUARD" not in body
              and "belt mode" in body
              and (_num(r"dev_applied=(\d+)", int, 0) or 0) >= 20
              and (_num(r"dev_x=([\d.]+)", float, 0.0) or 0.0) > 0.2
              and (_num(r"dev_v=([\d.]+)", float, 0.0) or 0.0) > 0.3
              and (_num(r"fwd_ok=(\d+)", int, 0) or 0) >= 20
              and _num(r"fwd_fail=(\d+)", int, -1) == 0
              and _num(r"APPLIES=(\d+)", int, 0) >= 20
              and (_num(r"BELT=(\d+)", int, 0) or 0) >= 20
              and _num(r"NONGUARD=(\d+)", int, -1) == 0)
    elif name == "estop_target":
        # Guard-level estop observed natively: the probe verdict plus
        # the latched safe-stop state in live telemetry.
        ok = ("STATUS_EXIT=0" in body
              and "decision=DENY reason=ESTOP" in body
              and "estop=1" in body
              and "state=3 " in body
              and "last_reason=ESTOP" in body)
    elif name == "target_perf":
        # Bench shape only (no timing thresholds: informational tier).
        # Full distributions come from `perf --samples N`.
        samples, done = _parse_bench(body)
        ok = (done == 200 and len(samples) == 200
              and all(s == s and s != float("inf") and s >= 0
                      for s in samples))
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
    elif name == "v2_transitions":
        # Bidirectional v1-vs-v2 contrast plus v2 A/B/C/D/F, all native.
        # Markers must appear in order; each section holds its verdict.
        tags = ["---V1-STATE2---", "---V1-STATE3---", "---V2-STATE2---",
                "---V2-STATE3---", "---V2-SUITE---", "---V2-LIMIT---",
                "---V2-ESTOP---"]
        wants = ["PROBE state=2 decision=ALLOW",
                 "PROBE state=3 decision=DENY reason=BAD_TRANSITION",
                 "PROBE state=2 decision=DENY reason=BAD_TRANSITION",
                 "PROBE state=3 decision=ALLOW",
                 "ALL 9 CHECKS PASS",
                 "decision=DENY reason=SPEED_OVER_LIMIT",
                 "decision=DENY reason=ESTOP"]
        idx = [body.find(t) for t in tags]
        ordered = all(a != -1 and a < b for a, b in zip(idx, idx[1:]))
        secs = [body[i:j] for i, j in zip(idx, idx[1:] + [len(body)])]
        ok = (ordered and "DIFF_BIN" in body and "SAME_BIN" not in body
              and "MISSING_V2_GUARD" not in body and "FI_V2_EXIT=0" in body
              and secs[4].count("PASS ") >= 9
              and all(w in s for w, s in zip(wants, secs)))
    elif name == "controller_crash":
        # Containment: a live chain (BEFORE>=20) loses its
        # controller; the device must freeze (<=3 in-flight
        # applies), the guard log must freeze too (no phantom
        # traffic), nothing may bypass the guard pid, pidin must
        # show no controller left, and the guard must survive.
        def _num(pat, cast=float, default=None):
            m = re.search(pat, body)
            return cast(m.group(1)) if m else default
        before = _num(r"BEFORE=(\d+)", int, -1)
        after = _num(r"AFTER=(\d+)", int, -1)
        gbefore = _num(r"GBEFORE=(\d+)", int, -1)
        gafter = _num(r"GAFTER=(\d+)", int, -1)
        ok = (before >= 20 and 0 <= after - before <= 3
              and gbefore >= 20 and 0 <= gafter - gbefore <= 3
              and _num(r"NONGUARD=(\d+)", int, -1) == 0
              and _num(r"CALIVE=(\d+)", int, -1) == 0
              and _num(r"GALIVE=(\d+)", int, -1) == 1)
    elif name == "device_crash":
        # Containment: a live chain (BEFORE>=20) loses its device;
        # the device log must freeze (<=3 in-flight applies) while
        # the guard KEEPS deciding (source + policy path alive),
        # nothing may bypass the guard pid, pidin must show no
        # device left, and controller + guard must survive.
        def _num(pat, cast=float, default=None):
            m = re.search(pat, body)
            return cast(m.group(1)) if m else default
        before = _num(r"BEFORE=(\d+)", int, -1)
        after = _num(r"AFTER=(\d+)", int, -1)
        gbefore = _num(r"GBEFORE=(\d+)", int, -1)
        gafter = _num(r"GAFTER=(\d+)", int, -1)
        ok = (before >= 20 and 0 <= after - before <= 3
              and gafter - gbefore >= 20
              and _num(r"NONGUARD=(\d+)", int, -1) == 0
              and _num(r"DALIVE=(\d+)", int, -1) == 0
              and _num(r"CALIVE=(\d+)", int, -1) == 1
              and _num(r"GALIVE=(\d+)", int, -1) == 1)
    elif name == "guard_crash":
        # Containment: a live chain (BEFORE>=20) is SIGKILLed; the
        # device must freeze (<=3 in-flight applies), nothing may
        # bypass the dead guard pid, pidin must show no guard left,
        # and the orphaned controller must report MsgSend failures.
        def _num(pat, cast=float, default=None):
            m = re.search(pat, body)
            return cast(m.group(1)) if m else default
        before = _num(r"BEFORE=(\d+)", int, -1)
        after = _num(r"AFTER=(\d+)", int, -1)
        ok = (before >= 20 and 0 <= after - before <= 3
              and _num(r"NONGUARD=(\d+)", int, -1) == 0
              and _num(r"ALIVE=(\d+)", int, -1) == 0
              and "MsgSend failed" in body)
    elif name == "cell_policy":
        # Cell interlock selftest, native: 9 truth-table vectors + 3
        # policy bound checks from the generated cell header.
        m = re.search(r"CELL_POLICY: (PASS|FAIL) (\d+)/(\d+)", body)
        ok = ("MISSING_CELLCHECK" not in body and "CELL_EXIT=0" in body
              and m is not None and m.group(1) == "PASS"
              and m.group(2) == m.group(3) == "12"
              and body.count("CELLCHECK") == 12)
    else:
        ok = False
    return {"name": name, "passed": ok, "detail": body[-500:].strip().replace("\n", " | ")}


def _perf_distribution(samples: list[float]) -> dict:
    # Single implementation lives in genesis_rt.provenance so the gate
    # recomputes bit-identical distributions when binding perf records.
    return provenance.perf_distribution(list(samples))


def _parse_bench(body: str) -> tuple[list[float], int | None]:
    """Parse bench output: raw samples + the PERF_DONE count (if any)."""
    samples = [float(m.group(1)) for m in
               re.finditer(r"^SAMPLE ([0-9]+(?:\.[0-9]+)?)$", body, re.M)]
    done = re.search(r"^PERF_DONE n=(\d+)$", body, re.M)
    return samples, int(done.group(1)) if done else None


def _utcnow() -> str:
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")


def _exec_wait(client, command: str, timeout: int) -> tuple[int, str]:
    """Run one command on an open SSH client; raise TimeoutError on stall."""
    _stdin, stdout, _stderr = client.exec_command(command, timeout=timeout)
    deadline = time.monotonic() + timeout
    while not stdout.channel.exit_status_ready():
        if time.monotonic() > deadline:
            raise TimeoutError(command)
        time.sleep(1)
    return (stdout.channel.recv_exit_status(),
            stdout.read().decode("utf-8", "replace"))


def _fetch_uname(client) -> tuple[str | None, str | None]:
    """Target identity line, or (None, reason). One exec, same connection."""
    try:
        status, body = _exec_wait(client, "uname -a", 60)
    except Exception as exc:
        return None, f"uname failed: {type(exc).__name__}: {exc}"
    line = body.strip().splitlines()[0] if body.strip() else ""
    if status != 0 or not line:
        return None, f"uname exit={status} empty={not line}"
    return line, None


def _fetch_staged(client, dest: str = "/tmp/genesis") -> tuple[dict | None, str | None]:
    """cksum+size of every staged genesis_* binary, or (None, reason).

    POSIX cksum is the portable rendezvous: the build side computes the
    same CRC over the same bytes (genesis_rt.provenance.cksum_posix),
    so the gate can prove WHAT ran is WHAT was built.
    """
    try:
        status, body = _exec_wait(
            client, f"cd {dest} && cksum genesis_*", 60)
    except Exception as exc:
        return None, f"cksum failed: {type(exc).__name__}: {exc}"
    if status != 0:
        return None, f"cksum exit={status}: {body.strip()[:200]}"
    staged: dict = {}
    for line in body.splitlines():
        parts = line.split()
        # QNX/GNU format: "<cksum> <size> <name>"
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            return None, f"unparsable cksum line: {line!r}"
        staged[parts[2]] = {"cksum": int(parts[0]), "size": int(parts[1])}
    if not staged:
        return None, "cksum returned no binaries"
    return staged, None


def _ir_binding(ir_path: str | None) -> dict | None:
    """{machine_id, ir_sha256} the operator binds this run to, or None
    when unattested (the gate then caps the tier — never silently)."""
    if not ir_path:
        return None
    # Same loader as the pipeline (validate+normalize): the digest must
    # match the codegen manifest, not the raw file bytes.
    data = load_ir_file(ir_path)
    return {"machine_id": data["machine"]["id"],
            "ir_sha256": codegen.ir_sha256(data),
            "linear_limit_mps": float(
                data["control"]["max_linear_speed_mps"])}


def _load_build_set(path: str | None) -> tuple[dict | None, str | None]:
    """Build set attributing the secondary staged executables (§6 v2).
    Absent/invalid => recorded as a provenance error (the gate then caps
    the tier); never silently treated as attributed."""
    if not path:
        return None, ("no --build-set given: secondary staged executables "
                      "are unattributed (gate will cap the tier)")
    try:
        return buildset.load_build_set(path), None
    except (OSError, ValueError) as exc:
        return None, f"build set unusable: {exc}"


def _target_identity_block(uname: str | None) -> dict:
    return {"platform": provenance.TARGET_PLATFORM, "uname": uname or ""}


SCHED_CONFIGS = (
    # (name, guard_spec, bench_spec) for `on -p`. None = default
    # inheritance (observed 10r on the QSTI image as qnxuser).
    ("baseline", None, None),
    ("fifo_guard", "20f", None),
    ("fifo_both", "20f", "20f"),
    ("rr_both", "20r", "20r"),
)


def _sched_command(guard_spec: str | None, bench_spec: str | None,
                   samples: int) -> str:
    """One scheduling-config campaign step (informational, no thresholds)."""
    guard_launch = ("./genesis_guard" if guard_spec is None
                    else f"on -p {guard_spec} ./genesis_guard")
    bench_launch = ("./genesis_faultinject" if bench_spec is None
                    else f"on -p {bench_spec} ./genesis_faultinject")
    return ("cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
            " slay genesis_guard_conv 2>/dev/null;"
            " slay genesis_guard_v2 2>/dev/null; sleep 1;"
            f" {guard_launch} > guard-sched.log 2>&1 & sleep 2;"
            " echo ---SCHED-PIDIN---;"
            " pidin 2>/dev/null | grep genesis_guard | head -3;"
            f" {bench_launch} bench {samples};"
            " echo BENCH_EXIT=$?; slay genesis_guard")


def _parse_sched_observed(body: str) -> str | None:
    """Applied guard policy from the pidin line (`20f`, `10r`, ...).

    Anchored on `./genesis_guard` + whitespace so secondary guards
    (`./genesis_guard_conv`, ...) never match."""
    m = re.search(r"\./genesis_guard\s+(\d+[rfo])\b", body)
    return m.group(1) if m else None


def cmd_sched(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    started = _utcnow()
    prov_errors: list[str] = []
    try:
        try:
            _st, ncpu_body = _exec_wait(client, "nproc", 30)
        except TimeoutError:
            ncpu_body = ""
        ncpu_m = re.search(r"(\d+)", ncpu_body)
        ncpu = int(ncpu_m.group(1)) if ncpu_m else None
        if ncpu is None:
            prov_errors.append("nproc unreadable")
        uname, uname_err = _fetch_uname(client)
        if uname_err:
            prov_errors.append(uname_err)
        staged, staged_err = _fetch_staged(client)
        if staged_err:
            prov_errors.append(staged_err)
        configs: dict = {}
        all_ok = True
        for name, guard_spec, bench_spec in SCHED_CONFIGS:
            command = _sched_command(guard_spec, bench_spec, args.samples)
            try:
                _status, body = _exec_wait(client, command, 300)
            except TimeoutError:
                configs[name] = {"status": "timeout"}
                all_ok = False
                continue
            samples, done = _parse_bench(body)
            observed = _parse_sched_observed(body)
            bench_ok = (done == args.samples
                        and len(samples) == args.samples
                        and all(s == s and s != float("inf") for s in samples))
            # Setup assertion only: the requested policy must be the
            # observed one (no timing thresholds — TCG is noisy).
            setup_ok = (observed is not None
                        and (guard_spec is None or observed == guard_spec))
            ok = bench_ok and setup_ok
            all_ok = all_ok and ok
            entry: dict = {
                "status": "ok" if ok else "fail",
                "guard_spec": guard_spec, "bench_spec": bench_spec,
                "observed_guard": observed,
                "command": command, "transcript_tail": body[-800:],
                "raw_samples_us": samples if bench_ok else [],
            }
            if bench_ok:
                entry["distribution_us"] = _perf_distribution(samples)
            configs[name] = entry
            dist = entry.get("distribution_us", {})
            print(f"sched {name}: {'ok' if ok else 'FAIL'} "
                  f"(guard {guard_spec or 'default'}->{observed}, "
                  f"bench {bench_spec or 'default'}, "
                  f"n={len(samples)}/{args.samples}"
                  + (f", p50={dist['p50']:.1f} p99={dist['p99']:.1f} us"
                     if dist else "") + ")")
    finally:
        client.close()
    finished = _utcnow()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "status": "ok" if all_ok else "fail",
        "verified_on_target": bool(all_ok and not prov_errors),
        "provenance_version": provenance.PROVENANCE_VERSION,
        "provenance_error": ("; ".join(prov_errors)
                             if prov_errors else None),
        "started_utc": started, "finished_utc": finished,
        "target": _target_identity_block(uname),
        "ncpu": ncpu, "staged": staged,
        "method": {"probe": "genesis_faultinject bench (sequential nominal "
                            "MsgSend round trips, fresh seq each)",
                   "clock": "CLOCK_MONOTONIC on target (nanoseconds)",
                   "percentile": "nearest-rank on sorted samples",
                   "launch": "`on -p <prio>[r|f|o]` per config; guard "
                             "policy verified post-launch via pidin",
                   "target": "QNX 8.0 QEMU x86_64 (TCG); scheduling "
                             "contrast only, not a hardware timing guarantee"},
        "note": ("sender-observed IPC round trip incl. guard decision; "
                 "informational campaign, no gate tier attached; "
                 "host and target numbers must never be mixed"),
        "configs": configs,
    }
    (out_dir / "qnx-sched-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"sched campaign: {'PASS' if all_ok else 'FAIL'} -> {out_dir}")
    return 0 if all_ok else 1


def cmd_perf(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    command = ("cd /tmp/genesis; slay genesis_guard 2>/dev/null; sleep 1;"
               " ./genesis_guard > guard-perf.log 2>&1 & sleep 2;"
               f" ./genesis_faultinject bench {args.samples};"
               " echo BENCH_EXIT=$?; slay genesis_guard")
    started = _utcnow()
    prov_errors: list[str] = []
    build_set, bs_err = _load_build_set(getattr(args, "build_set", None))
    if bs_err:
        prov_errors.append(bs_err)
    try:
        try:
            _status, body = _exec_wait(client, command, 300)
        except TimeoutError:
            print("perf: TIMEOUT waiting for target bench")
            return 3
        uname, uname_err = _fetch_uname(client)
        if uname_err:
            prov_errors.append(uname_err)
        staged, staged_err = _fetch_staged(client)
        if staged_err:
            prov_errors.append(staged_err)
    finally:
        client.close()
    finished = _utcnow()
    samples, done = _parse_bench(body)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "target-perf.log").write_text(
        f"$ {command}\n{body}\n", encoding="utf-8")
    ok = (done == args.samples and len(samples) == args.samples
          and all(s == s and s != float("inf") for s in samples))
    bound = ok and not prov_errors
    record: dict = {
        "status": "ok" if ok else "fail",
        "verified_on_target": bool(bound),
        "provenance_version": provenance.PROVENANCE_VERSION,
        "provenance_error": "; ".join(prov_errors) if prov_errors else None,
        "started_utc": started,
        "finished_utc": finished,
        "target": _target_identity_block(uname),
        "staged": staged,
        "build_set": build_set,
        "method": {"probe": "genesis_faultinject bench (sequential nominal "
                            "MsgSend round trips, fresh seq each)",
                   "clock": "CLOCK_MONOTONIC on target (nanoseconds)",
                   "percentile": "nearest-rank on sorted samples",
                   "target": "QNX 8.0 QEMU x86_64 (TCG); reproducibility only, "
                             "not a hardware timing guarantee"},
        "measurements": {},
        "raw_samples_us": samples if ok else [],
        "note": ("sender-observed IPC round trip incl. guard decision; "
                 "host and target numbers must never be mixed") if ok
                else f"bench incomplete: {len(samples)}/{args.samples} samples",
    }
    if ok:
        record["measurements"] = {
            "ipc_roundtrip_us": _perf_distribution(samples)}
    (out_dir / "qnx-perf-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"target perf: {'PASS' if ok else 'FAIL'} "
          f"({len(samples)}/{args.samples} samples) -> {out_dir}")
    if ok:
        d = record["measurements"]["ipc_roundtrip_us"]
        print(f"  p50={d['p50']:.1f} p95={d['p95']:.1f} "
              f"p99={d['p99']:.1f} max={d['max']:.1f} us (n={d['count']})")
    return 0 if ok else 1


def cmd_verify(args: argparse.Namespace) -> int:
    import hashlib
    import os
    live = [n for n, _ in TARGET_MATRIX]
    if live != list(provenance.EXPECTED_TARGET_CHECKS):
        print("verify: REFUSED — TARGET_MATRIX drifted from "
              f"genesis_rt.provenance.EXPECTED_TARGET_CHECKS: {live}")
        return 2
    try:
        ir_binding = _ir_binding(getattr(args, "ir", None))
    except (OSError, ValueError, KeyError) as exc:
        print(f"verify: REFUSED — cannot bind --ir: {exc}")
        return 2
    build_set, bs_err = _load_build_set(getattr(args, "build_set", None))
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
    started = _utcnow()
    prov_errors: list[str] = []
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
                check = _matrix_check(name, body, status, ir_binding)
                results.append(check)
                all_ok = all_ok and check["passed"]
                print(f"target:{name}: {'PASS' if check['passed'] else 'FAIL'}")
        uname, uname_err = _fetch_uname(client)
        if uname_err:
            prov_errors.append(uname_err)
        staged, staged_err = _fetch_staged(client)
        if staged_err:
            prov_errors.append(staged_err)
    finally:
        client.close()
    finished = _utcnow()
    if bs_err:
        prov_errors.append(bs_err)
    transcripts = {}
    for name, _command in TARGET_MATRIX:
        log = out_dir / f"target-{name}.log"
        # Missing log (timeout/abort): None digest → the gate refuses
        # binding loudly instead of crashing here.
        transcripts[name] = (hashlib.sha256(log.read_bytes()).hexdigest()
                             if log.exists() else None)
    verified = all_ok and not prov_errors and ir_binding is not None
    if getattr(args, "ir", None) is None:
        prov_errors.append("no --ir given: run unattested "
                           "(gate will cap the tier)")
    record = {"status": "ok" if all_ok else "fail",
              "verified_on_target": verified,
              "provenance_version": provenance.PROVENANCE_VERSION,
              "provenance_error": "; ".join(prov_errors) if prov_errors else None,
              "user": args.user,
              "matrix": live,
              "checks": results,
              "started_utc": started,
              "finished_utc": finished,
              "target": _target_identity_block(uname),
              "ir": ir_binding,
              "staged": staged,
              "build_set": build_set,
              "transcripts": transcripts,
              "note": "executed on QNX 8.0 QEMU target over SSH; transcripts beside record"}
    (out_dir / "qnx-target-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"target verification: {'PASS' if all_ok else 'FAIL'} -> {out_dir}")
    if prov_errors:
        print(f"provenance: {'BOUND' if verified else 'UNBOUND'} "
              f"({'; '.join(prov_errors)})")
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
    v.add_argument("--build-set", default=None,
                   help="build set JSON attributing secondary staged "
                        "executables (scripts/build_set.py); required for "
                        "provenance v2 behavior tiers")
    v.add_argument("--ir", default=None,
                   help="machine IR JSON this run is bound to "
                        "(machine id + digest embedded; required for "
                        "QNX_BEHAVIOR_VERIFIED and above)")
    v.set_defaults(func=cmd_verify)
    f = sub.add_parser("perf", help="measure target IPC round-trip latency over SSH")
    f.add_argument("--ssh-port", type=int, default=2222)
    f.add_argument("--user", default="qnxuser")
    f.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    f.add_argument("--samples", type=int, default=1000)
    f.add_argument("--build-set", default=None,
                   help="same build set as the verify run")
    f.add_argument("--out", default="artifacts/runs/qnx-perf")
    f.set_defaults(func=cmd_perf)
    s = sub.add_parser("sched", help="compare IPC latency across QNX "
                                     "scheduling configs over SSH")
    s.add_argument("--ssh-port", type=int, default=2222)
    s.add_argument("--user", default="qnxuser")
    s.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    s.add_argument("--samples", type=int, default=200)
    s.add_argument("--out", default="artifacts/runs/qnx-sched")
    s.set_defaults(func=cmd_sched)
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
