# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Anti-rot harness for the external-build codelab (Titan W7).

Same conventions as docs/codelab/ADVANCED-QNX.md (see
tests/integration/test_codelab_advanced.py): ```sh-harness blocks run
always, ```sh-harness-sdk blocks run only when the QNX SDK probes
present, everything else is display-only. Blocks self-assert; the
harness only requires exit 0 per block, in document order.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOC = REPO_ROOT / "docs" / "codelab" / "EXTERNAL-BUILD.md"

sh = pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh missing")


def _blocks(kind: str) -> list[str]:
    text = DOC.read_text(encoding="utf-8")
    return re.findall(r"```" + kind + r"\n(.*?)```", text, re.DOTALL)


def _run_block(shell: str, block: str, repo: Path, tmp: Path, tag: str,
               sdk_env: dict[str, str] | None = None) -> None:
    # Forward slashes: backslash tmp paths break sh globbing under the
    # QNX sh used on Windows (same directory, portable spelling).
    env = dict(sdk_env or os.environ, CODELAB_TMP=tmp.as_posix(),
               PYTHONPATH=str(repo / "host"))
    env["PATH"] = (str(Path(sys.executable).parent) + os.pathsep +
                   env.get("PATH", ""))
    proc = subprocess.run([shell, "-c", "set -e\n" + block], cwd=repo,
                          env=env, capture_output=True, text=True,
                          timeout=240)
    assert proc.returncode == 0, (
        f"codelab block {tag} failed (rc={proc.returncode}):\n"
        f"--- block ---\n{block[:800]}\n--- stderr ---\n"
        f"{proc.stderr[-2000:]}")


@sh
def test_external_codelab_host_blocks_all_green(tmp_path):
    shell = shutil.which("sh")
    assert shell
    blocks = _blocks("sh-harness")
    assert len(blocks) >= 3, "build, manifest+check, tamper blocks required"
    for i, block in enumerate(blocks):
        _run_block(shell, block, REPO_ROOT, tmp_path, f"sh-harness#{i}")


@sh
def test_external_codelab_sdk_blocks_green_or_skipped(tmp_path):
    from genesis_rt.build_adapter import _child_env, probe
    blocks = _blocks("sh-harness-sdk")
    assert len(blocks) >= 1, "the qcc lab must ship an SDK block"
    env = probe()
    if not env["sdk_present"]:
        pytest.skip("QNX SDK not installed (honest skip, not a pass)")
    sdk_env = _child_env(env["qnx_host"], env["qnx_target"])
    shell = shutil.which("sh")
    assert shell
    for i, block in enumerate(blocks):
        _run_block(shell, block, REPO_ROOT, tmp_path,
                   f"sh-harness-sdk#{i}", sdk_env)


def test_external_codelab_covers_trust_boundary():
    text = DOC.read_text(encoding="utf-8")
    for token in ("UNVERIFIED_CLAIM", "release_eligible",
                  "recorded, not verified", "## Troubleshooting",
                  "## Cleanup", "## Safety and scope limitations"):
        assert token in text, token
