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
import functools
import hashlib
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt import buildset, codegen, native_oracle, provenance  # noqa: E402
from genesis_rt.ir import load_ir_file  # noqa: E402
from genesis_rt.ir_v2 import load_ir_v2_file  # noqa: E402
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


class TargetBusy(Exception):
    """Another native campaign owns the target staging area."""


DEFAULT_TARGET_LOCK = REPO_ROOT / "artifacts" / ".target.lock"


class TargetLock:
    """Cross-process single-owner campaign lock (Windows-safe, no fcntl).

    The lock file holds ``{"owner": ..., "pid": ...}``. Creation is atomic
    (O_EXCL); a lock whose pid is dead is reclaimed as stale. Only the
    owning pid may release. Guarantees §14: no two target-touching
    invocations (boot/run/stop/put/verify/perf/sched/identity/probe)
    run concurrently — a rival either waits for release or fails
    loudly with TargetBusy, never interleaves. Only probe-image
    (local) and wait-ssh (TCP wait) run unlocked by design.
    ``GENESIS_TARGET_LOCK`` overrides the lock path (tests, ops).
    """

    def __init__(self, path: Path | None = None, owner: str = "") -> None:
        if path is None:
            path = Path(os.environ.get("GENESIS_TARGET_LOCK",
                                       str(DEFAULT_TARGET_LOCK)))
        self.path = Path(path)
        self.owner = owner or f"pid={os.getpid()}"

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        # No os.kill() probe: the holder is usually our own pid and
        # self-signaling kills the tree under sandboxed Windows runners.
        # _pid_is_gone() observes liveness without signaling (a zombie
        # holder counts as dead, so its lock is reclaimable).
        return not _pid_is_gone(pid)

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"owner": self.owner, "pid": os.getpid(),
                              "since": time.time()})
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            return
        # Lock file exists: live owner blocks, stale lock is reclaimed.
        try:
            holder = json.loads(self.path.read_text(encoding="utf-8"))
            holder_pid = int(holder.get("pid", -1))
        except (OSError, ValueError):
            holder_pid = -1
            holder = {}
        if holder_pid > 0 and self._pid_alive(holder_pid):
            raise TargetBusy(f"held by {holder.get('owner', '?')} "
                             f"(pid {holder_pid})")
        try:
            self.path.unlink()
        except OSError:
            pass  # lost the race; the open below refuses us
        try:
            fd = os.open(str(self.path),
                         os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise TargetBusy("lost the stale-lock race; retry the "
                             "command")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except BaseException:
            try:
                self.path.unlink()
            except OSError:
                pass
            raise

    def release(self) -> None:
        try:
            holder = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if int(holder.get("pid", -1)) == os.getpid():
            try:
                self.path.unlink()
            except OSError:
                pass

    def __enter__(self) -> "TargetLock":
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


def _with_target_lock(func):
    """Refuse (exit 2) when another native campaign owns the target."""
    @functools.wraps(func)
    def wrapper(args):
        try:
            with TargetLock(owner=f"{func.__name__} pid={os.getpid()}"):
                return func(args)
        except TargetBusy as exc:
            print(f"target: {exc}; one native campaign at a time "
                  f"(see `lock-status`)")
            return 2
    return wrapper


def _stage_entries(files: list[Path]) -> dict:
    """Per-file sha256 + POSIX cksum + size, keyed by basename."""
    entries = {}
    for src in files:
        blob = Path(src).read_bytes()
        crc, size = provenance.cksum_posix(blob)
        entries[Path(src).name] = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "cksum": crc,
            "size": size,
        }
    return entries


def write_stage_manifest(path: str | Path, dest: str,
                         files: list[Path]) -> dict:
    """Record what `put` staged: sha256 + POSIX cksum + size per file.

    Written atomically (tmp + os.replace) after ALL uploads succeed, so
    an interrupted staging never leaves a manifest claiming more than
    reached the target.
    """
    manifest = {"dest": dest, "created_utc": _utcnow(),
                "files": _stage_entries(files)}
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, out)
    return manifest


def load_stage_manifest(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError("not a stage manifest")
    return data


def check_staged_against_manifest(staged: dict | None,
                                  manifest: dict) -> list[str]:
    """Errors when on-target binaries differ from the staging manifest.

    Missing binaries and cksum/size mismatches are hard errors (stale or
    foreign binary ran). Extra on-target files are NOT flagged here —
    secondary executables are attributed by the build set instead.
    """
    errors: list[str] = []
    if staged is None:
        return ["on-target cksum inventory unavailable"]
    for name, want in manifest.get("files", {}).items():
        got = staged.get(name)
        if got is None:
            errors.append(f"staged binary missing on target: {name}")
        elif (got.get("cksum") != want.get("cksum")
              or got.get("size") != want.get("size")):
            errors.append(f"staged binary differs from manifest: {name} "
                          f"(target cksum={got.get('cksum')} "
                          f"size={got.get('size')}, manifest "
                          f"cksum={want.get('cksum')} size={want.get('size')})")
    return errors


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
    # Pin unambiguous formats explicitly: QEMU's probe mis-opens a damaged
    # .vmdk descriptor as raw (guest then sees descriptor bytes as its disk
    # and every mount fails). Observed 2026-11-05: a torn descriptor (truncated
    # extent line) probed as raw and silently broke boots until repaired.
    fmt = {".vmdk": ",format=vmdk", ".qcow2": ",format=qcow2",
           "": ",format=raw"}.get(disk.suffix, "")
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


@_with_target_lock
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


def _qemu_pidfile(image_dir: Path) -> Path:
    """Pidfile written by `boot` via QEMU `-pidfile` (mirrors build_qemu_argv)."""
    out = image_dir / "output" if (image_dir / "output").is_dir() else image_dir
    return out / "qemu.pid"


def _pid_is_qemu(pid: int) -> bool:
    """True only when pid exists and its image looks like a QEMU system process.

    PID-reuse guard: never signal a pid that is not QEMU. Windows uses
    tasklist image-name matching (no new dependency); POSIX reads /proc.
    Deliberately no os.kill() probe: the image check answers existence
    by itself, and signaling must never touch our own pid.
    """
    if platform.system() == "Windows":
        try:
            # errors="replace": console tools emit OEM bytes (observed: fr
            # tasklist NBSP before ':' arrives as cp850 0xFF, fatal to a
            # UTF-8-forced reader thread, leaving stdout None).
            proc = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                                  capture_output=True, text=True, timeout=15,
                                  errors="replace")
        except OSError:
            return False
        return "qemu-system-" in (proc.stdout or "").lower()
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace")
    except OSError:
        return False
    return "qemu-system-" in cmdline


def _win_pid_listed(pid: int) -> bool:
    """True when tasklist still lists pid (Windows liveness oracle).

    os.kill(pid, 0) is not usable here: on Windows it succeeds while
    any handle to the process is open, so a terminated-but-unreaped
    process (e.g. a Popen child the caller has not wait()ed yet) is
    wrongly reported alive. tasklist only lists live processes.
    """
    try:
        proc = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                              capture_output=True, text=True, timeout=15,
                              errors="replace")
    except (OSError, subprocess.SubprocessError):
        return True  # unknown: keep waiting (safe direction, still bounded)
    if proc.stdout is None:
        return True  # decode death: unknown, same safe direction
    return f'"{pid}"' in proc.stdout


def _pid_is_gone(pid: int) -> bool:
    """True when pid has terminated, including terminated-but-unreaped.

    A zombie still owns its pid (POSIX) or kernel object (Windows)
    while the spawner has not reaped it, but the process itself is
    dead: for a stop-waiter that counts as gone.
    """
    if platform.system() == "Windows":
        return not _win_pid_listed(pid)
    if Path("/proc").is_dir():
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        except OSError:
            return True
        state = stat.rsplit(")", 1)[1].split()[0] if ")" in stat else ""
        return state in ("Z", "X", "x")
    try:
        os.kill(pid, 0)
    except OSError:
        return True
    return False


def _wait_pid_gone(pid: int, budget_s: float) -> bool:
    deadline = time.monotonic() + budget_s
    while time.monotonic() < deadline:
        if _pid_is_gone(pid):
            return True
        time.sleep(1)
    return _pid_is_gone(pid)


@_with_target_lock
def cmd_stop(args: argparse.Namespace) -> int:
    """Stop the QEMU instance recorded in output/qemu.pid (bounded, verified).

    Refuses to signal a pid that is not a live QEMU process (PID reuse);
    a stale pidfile is cleared and reported as already-stopped. Exit 0
    when nothing is left running, 1 when the process survives SIGKILL.
    """
    pidfile = _qemu_pidfile(Path(args.image_dir))
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        print(f"stop: no pid recorded at {pidfile}; nothing running")
        return 0
    if not _pid_is_qemu(pid):
        print(f"stop: pid {pid} is not a live QEMU process; clearing stale {pidfile}")
        try:
            pidfile.unlink()
        except OSError:
            pass
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError as exc:
        print(f"stop: cannot signal pid {pid}: {exc}", file=sys.stderr)
        return 1
    if not _wait_pid_gone(pid, 20):
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=30)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        if not _wait_pid_gone(pid, 10):
            print(f"stop: pid {pid} still alive; {pidfile} kept", file=sys.stderr)
            return 1
    try:
        pidfile.unlink()
    except OSError:
        pass
    print(f"stop: QEMU pid {pid} stopped; {pidfile} cleared")
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
        # Titan F6: AutoAdd is scoped to loopback only (connect() pins
        # 127.0.0.1 below). Any off-loopback use MUST switch to a pinned
        # known_hosts policy first.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect("127.0.0.1", port=port, username=user,
                           password=password, timeout=timeout,
                           banner_timeout=timeout, auth_timeout=timeout,
                           look_for_keys=False, allow_agent=False)
            return client
        except Exception as exc:  # noqa: BLE001
            last = exc
            try:
                client.close()
            except Exception:
                pass  # M8: never leak a half-open transport on retry
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


@_with_target_lock
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
     " ./genesis_guard > guard-dc.log 2>&1 & GUARDPID=$!;"
     " ./genesis_device --guard-pid $GUARDPID > device.log 2>&1 & sleep 2;"
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
     " ./genesis_guard_conv > guard-cc.log 2>&1 & GUARDPID=$!;"
     " ./genesis_device belt --guard-pid $GUARDPID > device-conv.log 2>&1 & sleep 2;"
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
     " ./genesis_guard > guard-estop.log 2>&1 & GPID=$!; sleep 2;"
     " sudo -n ./genesis_status /tmp/genesis-status-node > status-estop.log 2>&1 & sleep 1;"
     " echo ---ESTOP-PROBE---; ./genesis_faultinject probe estop;"
     " echo ---STATUS-ESTOP---; cat /tmp/genesis-status-node; echo STATUS_EXIT=$?;"
     " echo ---OPERATOR-RESET---; kill -s USR1 $GPID; sleep 1;"
     " echo ---RESET-PROBE---; ./genesis_faultinject probe state 0 2;"
     " ./genesis_faultinject probe 0.4 3;"
     " grep 'operator reset armed' guard-estop.log;"
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
     " echo PRE_APPLIES=$(grep -c APPLY sup-device.log);"
     " slay genesis_guard; sleep 10;"
     " echo REBIND_COUNT=$(grep -c REBIND sup.log);"
     " echo POST_APPLIES=$(grep -c APPLY sup-device.log);"
     " echo SETTLED=$(pidin -F %n 2>/dev/null | grep -c genesis);"
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
     " slay genesis_guard_v1 2>/dev/null; slay genesis_guard_v2 2>/dev/null;"
     " sleep 1;"
     " test -x ./genesis_guard_v2 || { echo MISSING_V2_GUARD; exit 3; };"
     " cmp -s ./genesis_guard ./genesis_guard_v2 && echo SAME_BIN || echo DIFF_BIN;"
     " V1BIN=./genesis_guard; test -x ./genesis_guard_v1 && V1BIN=./genesis_guard_v1;"
     " $V1BIN > guard-v1s2.log 2>&1 & sleep 2;"
     " echo ---V1-STATE2---; ./genesis_faultinject probe state 2;"
     " slay genesis_guard 2>/dev/null; slay genesis_guard_v1 2>/dev/null; sleep 1;"
     " $V1BIN > guard-v1s3.log 2>&1 & sleep 2;"
     " echo ---V1-STATE3---; ./genesis_faultinject probe state 3;"
     " slay genesis_guard 2>/dev/null; slay genesis_guard_v1 2>/dev/null; sleep 1;"
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
     " ./genesis_guard > guard-ccx.log 2>&1 & GPID=$!;"
     " ./genesis_device --guard-pid $GPID > device-ccx.log 2>&1 & sleep 2;"
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
     " ./genesis_guard > guard-dcx.log 2>&1 & GPID=$!;"
     " ./genesis_device --guard-pid $GPID > device-dcx.log 2>&1 & sleep 2;"
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
     " ./genesis_guard > guard-gc.log 2>&1 & GPID=$!;"
     " ./genesis_device --guard-pid $GPID > device-gc.log 2>&1 & sleep 2;"
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


# Conveyor slot contract (examples/conveyor-demo/machine-ir.json). The
# banner pin below independently verifies the staged binary matches
# this assumption — a rebuilt conv guard fails loudly, not silently.
CONV_MACHINE_ID = "conveyor-demo-01"
CONV_LIMIT_MPS = 2.0

_PROBE_LINE_RE = re.compile(
    r"PROBE linear=([0-9.]+) estop=(\d) decision=(ALLOW|DENY) "
    r"reason=([A-Z_]+) state=(\d+)")


def _limits_differ_legacy(body: str) -> bool:
    """Unattested fixed-probe assertions (pre-Wave-11 behavior)."""
    parts = body.split("---PROBE-CONV---")
    slot1_pin = "machine=amr-demo-01 limits linear=1.200"
    conv_pin = "machine=conveyor-demo-01 limits linear=2.000"
    return (len(parts) == 2
            and "decision=DENY reason=SPEED_OVER_LIMIT" in parts[0]
            and "decision=ALLOW reason=OK" in parts[1]
            and "ALL 9 CHECKS PASS" in parts[1]
            and "FI_CONV_EXIT=0" in parts[1]
            and slot1_pin in body
            and conv_pin in body
            and "MISSING_CONV_GUARD" not in body)


def _limits_differ_bound(body: str, bound: dict) -> bool:
    """Contract-aware verdicts: every probe line must match the oracle
    prediction for its slot contract. Anything unpredicted, missing,
    reordered or mismatched fails closed."""
    try:
        mid = str(bound["machine_id"])
        kind = str(bound["machine_kind"])
        lim = float(bound["linear_limit_mps"])
    except (KeyError, TypeError, ValueError):
        return False
    if "ORACLE_NO_PLAN_FOR_LIMIT" in body:
        return False
    plan = (native_oracle.plan_probes(lim)
            if kind in native_oracle.SUPPORTED_MACHINE_KINDS else None)
    if plan is None or mid == CONV_MACHINE_ID:
        return False
    parts = body.split("---PROBE-CONV---")
    if len(parts) != 2:
        return False
    want_echo = ["%.3f" % v for v in plan]
    slots = (((kind, lim), parts[0]),
             (("conveyor", CONV_LIMIT_MPS), parts[1]))
    for (skind, slim), section in slots:
        lines = _PROBE_LINE_RE.findall(section)
        if [echo for echo, _, _, _, _ in lines] != want_echo:
            return False
        for echo, estop, dec, reason, state in lines:
            want = native_oracle.expect_linear_probe(
                machine_kind=skind, limit_mps=slim,
                probe_mps=float(echo), estop=(estop == "1"))
            if want.decision is None:
                return False
            if (dec, reason, int(state)) != (want.decision, want.reason,
                                             want.state_out):
                return False
    slot1_pin = f"machine={mid} limits linear={lim:.3f}"
    conv_pin = f"machine={CONV_MACHINE_ID} limits linear={CONV_LIMIT_MPS:.3f}"
    return (slot1_pin in body
            and conv_pin in body
            and "ALL 9 CHECKS PASS" in parts[1]
            and "FI_CONV_EXIT=0" in parts[1]
            and "MISSING_CONV_GUARD" not in body)


def _limits_differ_command(bound: dict | None) -> str:
    """Bound runs probe below/at/above the IR limit on both slots (the
    guard restarts per probe: seq is single-use). Unattested runs keep
    the legacy fixed command."""
    legacy = next(c for n, c in TARGET_MATRIX if n == "limits_differ")
    if bound is None:
        return legacy
    try:
        lim = float(bound["linear_limit_mps"])
    except (KeyError, TypeError, ValueError):
        return "echo ORACLE_NO_PLAN_FOR_LIMIT; exit 3"
    plan = native_oracle.plan_probes(lim)
    if plan is None:
        return "echo ORACLE_NO_PLAN_FOR_LIMIT; exit 3"

    def _slot(binary: str, log: str) -> str:
        runs = ""
        for value in plan:
            runs += (f" ./{binary} > {log} 2>&1 & sleep 2;"
                     f" ./genesis_faultinject probe {value:.3f};"
                     f" slay {binary}; sleep 1;")
        return runs

    return (
        "cd /tmp/genesis; slay genesis_guard 2>/dev/null;"
        " slay genesis_guard_conv 2>/dev/null; sleep 1;"
        " test -x ./genesis_guard_conv"
        " || { echo MISSING_CONV_GUARD; exit 3; };"
        " echo ---PROBE-AMR---;" + _slot("genesis_guard", "guard-amr.log") +
        " echo ---PROBE-CONV---;"
        + _slot("genesis_guard_conv", "guard-conv.log") +
        " ./genesis_guard_conv > guard-conv.log 2>&1 & sleep 2;"
        " echo ---FI-VS-CONV---; ./genesis_faultinject;"
        " echo FI_CONV_EXIT=$?;"
        " slay genesis_guard; slay genesis_guard_conv 2>/dev/null;"
        " echo ---GUARD-HEADERS---;"
        " grep -h machine guard-amr.log guard-conv.log")


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
        # Wave 11 §5: bound runs use the contract-aware oracle (each
        # probe verdict predicted from the IR, then compared); the
        # legacy fixed-probe path stays for unattested runs.
        ok = (_limits_differ_bound(body, bound) if bound is not None
              else _limits_differ_legacy(body))
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
        # the latched safe-stop state in live telemetry, then the
        # operator-reset wire (SIGUSR1 arms the one-shot latch and a
        # fresh-seq nominal probe ALLOWs out of SAFE_STOP). v2 has no
        # safe_stop->running edge, so the reset must first take the
        # declared safe_stop->init transition (state=0 ALLOW).
        reset_tail = body.split("---RESET-PROBE---", 1)
        reset_ok = (len(reset_tail) == 2
                    and "decision=ALLOW reason=OK" in reset_tail[1])
        v2_reset_ok = (
            reset_ok and "PROBE state=0 decision=ALLOW reason=OK"
            in reset_tail[1])
        want_v2 = (bound is not None
                   and bound.get("schema_version") == 2)
        ok = ("STATUS_EXIT=0" in body
              and "decision=DENY reason=ESTOP" in body
              and "estop=1" in body
              and "state=3 " in body
              and "last_reason=ESTOP" in body
              and "operator reset armed (SIGUSR1)" in body
              and (v2_reset_ok if want_v2 else reset_ok))
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
        # guard kill then rebinds the device (REBIND>=1), the set
        # settles back to 4, and fresh applies land afterwards.
        m_pre = re.search(r"PRE_APPLIES=(\d+)", body)
        m_post = re.search(r"POST_APPLIES=(\d+)", body)
        m_rebind = re.search(r"REBIND_COUNT=(\d+)", body)
        m_settled = re.search(r"SETTLED=(\d+)", body)
        ok = ok and all((m_pre, m_post, m_rebind, m_settled)) \
            and int(m_rebind.group(1)) >= 1 \
            and m_settled.group(1) == "4" \
            and int(m_post.group(1)) > int(m_pre.group(1))
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
        # v1 ops stage v1+v2 (DIFF_BIN); v2 ops stage v2 twice with
        # the v1 guard aside (SAME_BIN) since slot-1 itself is v2.
        want_v2 = (bound is not None
                   and bound.get("schema_version") == 2)
        bins_ok = (("SAME_BIN" in body and "DIFF_BIN" not in body)
                   if want_v2 else
                   ("DIFF_BIN" in body and "SAME_BIN" not in body))
        ok = (ordered and bins_ok
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


def _verify_exit_code(all_ok: bool, fatal_errors: list) -> int:
    """Exit status for `verify`: 0 only when the matrix passed AND
    provenance is intact. Fatal errors (unknown identity, unreadable
    staging, unloadable build-set) fail the run even with a green
    matrix; absent --ir/--build-set only cap the tier (soft)."""
    return 0 if (all_ok and not fatal_errors) else 1


def _ir_binding(ir_path: str | None) -> dict | None:
    """{machine_id, ir_sha256} the operator binds this run to, or None
    when unattested (the gate then caps the tier — never silently)."""
    if not ir_path:
        return None
    # Same loader as the pipeline (validate+normalize): the digest must
    # match the codegen manifest, not the raw file bytes. v2 IRs carry
    # extra top-level keys the v1 loader rejects, so dispatch on the
    # declared schema version exactly like `genesis-rt generate`.
    version = None
    if Path(ir_path).suffix.lower() not in (".yaml", ".yml"):
        try:
            raw = json.loads(Path(ir_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = None
        if isinstance(raw, dict):
            version = raw.get("schema_version")
    data = (load_ir_v2_file(ir_path) if version == 2
            else load_ir_file(ir_path))
    return {"machine_id": data["machine"]["id"],
            "machine_kind": data["machine"]["kind"],
            "schema_version": version or data.get("schema_version") or 1,
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


@_with_target_lock
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


@_with_target_lock
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


@_with_target_lock
def cmd_verify(args: argparse.Namespace) -> int:
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
    manifest = None
    manifest_path = getattr(args, "require_manifest", None)
    if manifest_path:
        try:
            manifest = load_stage_manifest(manifest_path)
        except (OSError, ValueError) as exc:
            print(f"verify: REFUSED — --require-manifest unusable: {exc}")
            return 2
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
    fatal_errors: list[str] = []
    try:
        for name, command in TARGET_MATRIX:
            if name == "limits_differ":
                command = _limits_differ_command(ir_binding)
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
            fatal_errors.append(uname_err)
        staged, staged_err = _fetch_staged(client)
        if staged_err:
            prov_errors.append(staged_err)
            fatal_errors.append(staged_err)
        manifest_errors: list[str] = []
        if manifest is not None and not staged_err:
            manifest_errors = check_staged_against_manifest(staged, manifest)
            for problem in manifest_errors:
                print(f"verify: STALE/MISMATCHED — {problem}")
                prov_errors.append(problem)
                fatal_errors.append(problem)
            if manifest_errors:
                all_ok = False  # wrong binary ran: never a PASS
    finally:
        client.close()
    finished = _utcnow()
    if bs_err:
        prov_errors.append(bs_err)
        if getattr(args, "build_set", None):
            # Explicitly requested provenance that cannot load fails
            # the run; an absent --build-set only caps the tier.
            fatal_errors.append(bs_err)
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
              "stage_manifest": ({"path": manifest_path,
                                  "errors": manifest_errors or None}
                                 if manifest is not None else None),
              "transcripts": transcripts,
              "note": "executed on QNX 8.0 QEMU target over SSH; transcripts beside record"}
    (out_dir / "qnx-target-record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"target verification: {'PASS' if all_ok else 'FAIL'} -> {out_dir}")
    if prov_errors:
        print(f"provenance: {'BOUND' if verified else 'UNBOUND'} "
              f"({'; '.join(prov_errors)})")
    return _verify_exit_code(all_ok, fatal_errors)


@_with_target_lock
def cmd_put(args: argparse.Namespace) -> int:
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    if getattr(args, "manifest_out", None):
        for src in args.src:  # fail before touching the target
            if not Path(src).is_file():
                print(f"put: REFUSED — missing local file: {src}")
                return 2
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
        if getattr(args, "manifest_out", None):
            staged, staged_err = _fetch_staged(client, args.dest)
            if staged is None:
                print(f"put: REFUSED — cannot read back staging: "
                      f"{staged_err}; no manifest written")
                return 2
            errors = check_staged_against_manifest(
                staged, {"files": _stage_entries(
                    [Path(s) for s in args.src])})
            if errors:
                print("put: REFUSED — target staging differs from "
                      "local bytes; no manifest written:")
                for err in errors:
                    print(f"put:   {err}")
                return 2
            manifest = write_stage_manifest(
                args.manifest_out, args.dest, [Path(s) for s in args.src])
            print(f"put: manifest ({len(manifest['files'])} files, "
                  f"read-back verified) -> {args.manifest_out}")
        return 0
    finally:
        client.close()


@_with_target_lock
def cmd_identity(args: argparse.Namespace) -> int:
    """Inspect target identity: uname + staged-binary cksum inventory."""
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    try:
        uname, uname_err = _fetch_uname(client)
        staged, staged_err = _fetch_staged(client, args.dest)
    finally:
        client.close()
    info = {"target": _target_identity_block(uname),
            "dest": args.dest, "staged": staged,
            "error": uname_err or staged_err}
    print(json.dumps(info, indent=2, sort_keys=True))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"transcript: {out_path}")
    return 0 if uname else 1


@_with_target_lock
def cmd_probe(args: argparse.Namespace) -> int:
    """Non-destructive auth probe: connect + fixed `uname -a`, nothing else.

    THE command for "is the target reachable / are my credentials
    right". Unlike `run`, the remote command is fixed and read-only,
    so retry loops can never re-execute a destructive string (the
    8-Nov campaign wipe came from a retried `run 'rm -rf ...'`).
    """
    import os
    password = os.environ.get("GENESIS_TARGET_PASSWORD", args.password or "")
    try:
        client = _ssh_client(args.ssh_port, args.user, password)
    except Exception as exc:
        print(f"ssh: connect/auth failed: {type(exc).__name__}: {exc}")
        return 2
    try:
        uname, err = _fetch_uname(client)
    finally:
        client.close()
    if uname:
        print(f"probe: auth OK: {uname}")
        return 0
    print(f"probe: authenticated but uname failed: {err}")
    return 1


def cmd_lock_status(args: argparse.Namespace) -> int:
    """Inspect the campaign lock without acquiring it (never blocks)."""
    path = Path(os.environ.get("GENESIS_TARGET_LOCK",
                               str(DEFAULT_TARGET_LOCK)))
    info: dict = {"path": str(path), "held": False, "owner": None,
                  "pid": None, "pid_alive": False}
    try:
        holder = json.loads(path.read_text(encoding="utf-8"))
        pid = int(holder.get("pid", -1))
    except (OSError, ValueError):
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    info.update(held=True, owner=holder.get("owner"),
                pid=pid, pid_alive=TargetLock._pid_alive(pid))
    if pid > 0 and not info["pid_alive"]:
        info["note"] = ("stale (holder dead); next command reclaims it "
                        "automatically")
    print(json.dumps(info, indent=2, sort_keys=True))
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
    st = sub.add_parser("stop", help="stop the QEMU instance in output/qemu.pid")
    st.add_argument("image_dir")
    st.set_defaults(func=cmd_stop)
    r = sub.add_parser("run", help="run commands on target over SSH "
                                     "(paramiko; serialized by the "
                                     "campaign lock; retries re-execute — "
                                     "use `probe` for auth checks)")
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
    t.add_argument("--manifest-out", default=None,
                   help="write an atomic staging manifest (sha256+cksum) "
                        "after all uploads succeed")
    t.add_argument("src", nargs="+")
    t.set_defaults(func=cmd_put)
    i = sub.add_parser("identity", help="inspect target identity (uname + "
                                        "staged-binary inventory)")
    i.add_argument("--ssh-port", type=int, default=2222)
    i.add_argument("--user", default="qnxuser")
    i.add_argument("--password", default=None,
                   help="prefer GENESIS_TARGET_PASSWORD env var")
    i.add_argument("--dest", default="/tmp/genesis")
    i.add_argument("--out", default=None)
    i.set_defaults(func=cmd_identity)
    pb = sub.add_parser("probe", help="non-destructive auth probe "
                                      "(connect + fixed uname -a)")
    pb.add_argument("--ssh-port", type=int, default=2222)
    pb.add_argument("--user", default="qnxuser")
    pb.add_argument("--password", default=None,
                    help="prefer GENESIS_TARGET_PASSWORD env var")
    pb.set_defaults(func=cmd_probe)
    ls = sub.add_parser("lock-status", help="inspect the campaign lock "
                                            "without acquiring it")
    ls.set_defaults(func=cmd_lock_status)
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
    v.add_argument("--require-manifest", default=None,
                   help="staging manifest from `put --manifest-out`; "
                        "refuse when missing/invalid, FAIL when on-target "
                        "binaries differ (stale staging)")
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
