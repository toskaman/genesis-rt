#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Rebuild a native evidence pack's binaries from source; compare digests.

  python scripts/qnx_rebuild_check.py evidence/qnx8-x86_64-w11-after

Reads the pack's manifest (repo commit) and qnx-build-record.json (exact
qcc commands + published sha256), checks out that commit into a fresh
git worktree in a temp dir (so the source path differs from the original
build), regenerates the config header from the pack's ir.json, replays
each recorded qcc command with paths rewritten to the worktree, and
compares sha256. Exit 0 only if every binary matches.

Needs the QNX SDK (qcc on PATH or QNX_HOST set). Never modifies the pack.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _qcc() -> str:
    found = shutil.which("qcc")
    if found:
        return found
    host = os.environ.get("QNX_HOST", "")
    for name in ("qcc.exe", "qcc"):
        p = Path(host) / "usr" / "bin" / name
        if p.is_file():
            return str(p)
    sys.exit("qcc not found: source the QNX SDP environment first")


def main() -> int:
    pack = Path(sys.argv[1]).resolve()
    rec = json.loads((pack / "qnx-build-record.json").read_text(encoding="utf-8"))
    commit = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))["commit"]
    cmds = [ln for ln in rec["stdout"].splitlines() if ln.startswith("qcc ")]
    qcc = _qcc()
    ok = True
    with tempfile.TemporaryDirectory(prefix="genesis-rebuild-") as tmp:
        wt = Path(tmp) / "src"
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach",
                        str(wt), commit], check=True, capture_output=True)
        try:
            build = Path(tmp) / "build"
            build.mkdir()
            env = dict(os.environ, PYTHONPATH=str(wt / "host"))
            subprocess.run([sys.executable, "-m", "genesis_rt.cli", "generate",
                            str(pack / "ir.json"), "--out", str(build)],
                           check=True, capture_output=True, env=env, cwd=wt)
            for cmd in cmds:
                # Original absolute source root -> this worktree.
                m = re.search(r"-I(\S+?)[\\/]include", cmd)
                old_root = m.group(1)
                new = cmd.replace(old_root, str(wt / "target" / "qnx8"))
                argv = [qcc] + new.split()[1:]
                subprocess.run(argv, check=True, cwd=build, capture_output=True)
                name = new.split(" -o ")[1].split()[0]
                got = hashlib.sha256((build / name).read_bytes()).hexdigest()
                want = rec["binaries"][name]["sha256"]
                ok &= got == want
                print(f"{name:<22} {'MATCH' if got == want else 'DIFF '} "
                      f"{got[:16]} (published {want[:16]})")
        finally:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove",
                            "--force", str(wt)], capture_output=True)
    print(f"commit {commit}: {'ALL BINARIES REPRODUCED' if ok else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
