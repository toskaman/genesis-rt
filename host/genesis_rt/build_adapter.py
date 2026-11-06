# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX build adapter: environment probe + honest build invocation.

Never reports success without a real compiler exit code 0 AND the
expected artifact on disk. Without an SDK it returns a structured
"blocked" record instead of failing or faking a build.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from . import provenance

EXPECTED_BINS = ("genesis_guard", "genesis_controller", "genesis_device",
                 "genesis_status", "genesis_supervisor", "genesis_faultinject")


def _run(argv: list[str], cwd: Path | None = None, timeout: int = 120,
         env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              errors="replace",
                              cwd=str(cwd) if cwd else None, timeout=timeout,
                              check=False, env=env)
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "",
                "stderr": f"timeout after {timeout}s: {' '.join(argv)}"}
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}


def probe_qemu() -> dict[str, Any]:
    """Inspect the host for a usable QEMU system emulator."""
    candidates = [
        shutil.which("qemu-system-x86_64"),
        os.environ.get("GENESIS_QEMU"),
        r"E:\VMs\qemu\qemu-system-x86_64.exe",
        r"C:\Program Files\qemu\qemu-system-x86_64.exe",
    ]
    path = next((c for c in candidates if c and Path(c).exists()), None)
    result: dict[str, Any] = {"present": bool(path), "path": path, "version": None}
    if path:
        ver = _run([path, "--version"], timeout=30)
        first = ((ver["stdout"] or ver["stderr"]).strip().splitlines() or [None])[0]
        result["version"] = (first or "")[:200] or None
    return result


def _sdk_candidates() -> list[tuple[str, str]]:
    """Well-known SDP install layouts, used when env vars are unset."""
    host_dir = "host/win64/x86_64" if os.name == "nt" else "host/linux/x86_64"
    bases = ["E:/qnx800", "C:/qnx800",
             str(Path.home() / "qnx800").replace("\\", "/"), "/opt/qnx800"]
    return [(f"{b}/{host_dir}", f"{b}/target/qnx") for b in bases]


def _child_env(qnx_host: str, qnx_target: str) -> dict[str, str]:
    env = dict(os.environ)
    env["QNX_HOST"] = qnx_host
    env["QNX_TARGET"] = qnx_target
    base = qnx_host.rsplit("/host/", 1)[0]
    extra = os.pathsep.join([f"{qnx_host}/usr/bin", f"{base}/host/common/bin"])
    env["PATH"] = extra + os.pathsep + env.get("PATH", "")
    return env


def probe() -> dict[str, Any]:
    """Inspect the host for a usable QNX SDP 8.0 toolchain (plus QEMU)."""
    qnx_host = os.environ.get("QNX_HOST")
    qnx_target = os.environ.get("QNX_TARGET")
    if not (qnx_host and qnx_target):
        for host_cand, target_cand in _sdk_candidates():
            qcc_cand = Path(f"{host_cand}/usr/bin/qcc.exe" if os.name == "nt"
                            else f"{host_cand}/usr/bin/qcc")
            if qcc_cand.exists() and Path(target_cand).exists():
                qnx_host, qnx_target = host_cand, target_cand
                break
    qcc = shutil.which("qcc")
    if not qcc and qnx_host:
        for name in ("qcc.exe", "qcc") if os.name == "nt" else ("qcc",):
            cand = str(Path(qnx_host) / "usr" / "bin" / name)
            if Path(cand).exists():
                qcc = cand
                break
    qcc_present = bool(qcc and Path(qcc).exists())
    result: dict[str, Any] = {
        "sdk_present": bool(qcc_present and qnx_target and Path(str(qnx_target)).exists()),
        "qnx_host": qnx_host, "qnx_target": qnx_target,
        "qcc": qcc if qcc_present else None, "qcc_version": None,
        "qemu": probe_qemu(),
    }
    if qcc_present and qcc:
        ver = _run([qcc, "-V"], timeout=30,
                   env=_child_env(str(qnx_host), str(qnx_target)))
        result["qcc_version"] = (ver["stdout"] or ver["stderr"])[:500] or None
    return result


def build_qnx(build_dir: str | Path, makefile: str = "genesis_build_gen.mk",
              timeout: int = 600) -> dict[str, Any]:
    """Run a real `make qnx` build. Honest record, never a fake pass."""
    env = probe()
    bdir = Path(build_dir)
    if not env["sdk_present"]:
        return {"status": "blocked", "verified_on_target": False,
                "reason": "QNX SDP 8.0 SDK/toolchain not installed; "
                          "see docs/quickstart-qnx8-qemu.md",
                "environment": env}
    mk = bdir / makefile
    if not mk.exists():
        return {"status": "error", "verified_on_target": False,
                "reason": f"missing build file: {mk}", "environment": env}
    child = _child_env(str(env["qnx_host"]), str(env["qnx_target"]))
    make = shutil.which("make", path=child["PATH"]) or "make"
    res = _run([make, "-f", makefile, "qnx"], cwd=bdir, timeout=timeout, env=child)
    missing = [b for b in EXPECTED_BINS if not (bdir / b).exists() and not (bdir / f"{b}.exe").exists()]
    ok = bool(res["ok"]) and not missing
    binaries: dict[str, Any] = {}
    if ok:
        # Provenance anchor (§6): digest every output so the gate can
        # prove the staged target binaries ARE this build's outputs.
        # Per-machine extras (e.g. genesis_cellcheck, built only by cell
        # gen dirs) are digested too: otherwise the gate would not bind
        # them and a swapped staged extra would pass silently.
        names = list(EXPECTED_BINS)
        for p in sorted(bdir.iterdir(), key=lambda q: q.name):
            if (p.is_file() and p.name.startswith("genesis_")
                    and "." not in p.name and p.name not in names):
                names.append(p.name)
        for name in names:
            artifact = bdir / name
            if not artifact.exists():
                artifact = bdir / f"{name}.exe"
            raw = artifact.read_bytes()
            ck, size = provenance.cksum_posix(raw)
            binaries[name] = {"sha256": hashlib.sha256(raw).hexdigest(),
                              "cksum": ck, "size": size}
    return {"status": "ok" if ok else "error", "verified_on_target": False,
            "reason": None if ok else f"build failed or missing artifacts: {missing}",
            "returncode": res["returncode"], "stdout": res["stdout"],
            "stderr": res["stderr"], "environment": env,
            "built_utc": datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds"),
            "binaries": binaries,
            "note": "compile-only; on-target execution is recorded separately"}


def check_host_cc(build_dir: str | Path, genesis_src: str | Path,
                  timeout: int = 180) -> dict[str, Any]:
    """Compile the shared policy + vector harness with the host C compiler."""
    bdir = Path(build_dir)
    src = Path(genesis_src)
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        return {"status": "blocked", "reason": "no host C compiler found"}
    out = bdir / "guard_vector_check"
    res = _run([cc, "-O1", "-Wall", "-Wextra", f"-I{src / 'include'}",
                f"-I{src / 'common'}", f"-I{bdir}", "-o", str(out),
                str(src / "common" / "guard_policy.c"),
                str(src / "host_tests" / "guard_vector.c")],
               cwd=bdir, timeout=timeout)
    # Windows toolchains append .exe even when -o names no suffix.
    artifact = out if out.exists() else out.with_name(out.name + ".exe")
    ok = bool(res["ok"]) and artifact.exists()
    return {"status": "ok" if ok else "error",
            "reason": None if ok else "host policy compile failed",
            "returncode": res["returncode"],
            "stdout": res["stdout"][-2000:], "stderr": res["stderr"][-2000:]}
