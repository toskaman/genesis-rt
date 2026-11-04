# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX build adapter: environment probe + honest build invocation.

Never reports success without a real compiler exit code 0 AND the
expected artifact on disk. Without an SDK it returns a structured
"blocked" record instead of failing or faking a build.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_BINS = ("genesis_guard", "genesis_controller", "genesis_device",
                 "genesis_status", "genesis_supervisor")


def _run(argv: list[str], cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=str(cwd) if cwd else None, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "",
                "stderr": f"timeout after {timeout}s: {' '.join(argv)}"}
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}


def probe() -> dict[str, Any]:
    """Inspect the host for a usable QNX SDP 8.0 toolchain."""
    qnx_host = os.environ.get("QNX_HOST")
    qnx_target = os.environ.get("QNX_TARGET")
    qcc = shutil.which("qcc") or (f"{qnx_host}/usr/bin/qcc" if qnx_host else None)
    qcc_present = bool(qcc and Path(qcc).exists()) if qcc else False
    result: dict[str, Any] = {
        "sdk_present": bool(qcc_present and qnx_target and Path(str(qnx_target)).exists()),
        "qnx_host": qnx_host, "qnx_target": qnx_target,
        "qcc": qcc if qcc_present else None, "qcc_version": None,
    }
    if qcc_present and qcc:
        ver = _run([qcc, "-V"], timeout=30)
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
    res = _run(["make", "-f", makefile, "qnx"], cwd=bdir, timeout=timeout)
    missing = [b for b in EXPECTED_BINS if not (bdir / b).exists() and not (bdir / f"{b}.exe").exists()]
    ok = bool(res["ok"]) and not missing
    return {"status": "ok" if ok else "error", "verified_on_target": False,
            "reason": None if ok else f"build failed or missing artifacts: {missing}",
            "returncode": res["returncode"], "stdout": res["stdout"],
            "stderr": res["stderr"], "environment": env,
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
