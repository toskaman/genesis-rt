# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""The rebuild checker must never pass vacuously (independent review)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pack(tmp_path, stdout):
    p = tmp_path / "pack"
    p.mkdir()
    (p / "manifest.json").write_text(json.dumps({"commit": "HEAD"}))
    (p / "qnx-build-record.json").write_text(json.dumps(
        {"stdout": stdout, "binaries": {"genesis_guard": {"sha256": "0" * 64}}}))
    return p


def test_no_qcc_commands_fails(tmp_path):
    p = _pack(tmp_path, "make: nothing to do\n")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "qnx_rebuild_check.py"), str(p)],
                       capture_output=True, text=True, env={"PATH": "", "QNX_HOST": str(tmp_path)})
    assert r.returncode != 0
    assert "no qcc command" in r.stdout
