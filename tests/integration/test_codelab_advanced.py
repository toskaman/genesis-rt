# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Anti-rot harness: executes every runnable block of the advanced QNX codelab.

Conventions in docs/codelab/ADVANCED-QNX.md:
  ```sh-harness      run always (POSIX sh, repo root, CODELAB_TMP set)
  ```sh-harness-sdk  run only when the QNX SDK probes present
  ```sh-target       on-target over SSH: executed by the author during
                     writing (transcripts in Lab 6), never here
  ```sh / powershell / text = display only.
Blocks self-assert (`grep -q`, `test`, python asserts); the harness
only requires exit 0 per block, in document order.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOC = REPO_ROOT / "docs" / "codelab" / "ADVANCED-QNX.md"

sh = pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh missing")


def _blocks(kind: str) -> list[str]:
    text = DOC.read_text(encoding="utf-8")
    return re.findall(r"```" + kind + r"\n(.*?)```", text, re.DOTALL)


def _run_block(shell: str, block: str, repo: Path, tmp: Path, tag: str,
               sdk_env: dict[str, str] | None = None) -> None:
    import sys
    env = dict(sdk_env or os.environ, CODELAB_TMP=str(tmp),
               PYTHONPATH=str(repo / "host"))
    # `python` must resolve to this interpreter (QNX sh on Windows
    # otherwise hits the Store stub): interpreter dir first on PATH.
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
def test_codelab_host_blocks_all_green(tmp_path):
    shell = shutil.which("sh")
    assert shell
    blocks = _blocks("sh-harness")
    assert len(blocks) >= 6, "each host lab must ship runnable blocks"
    for i, block in enumerate(blocks):
        _run_block(shell, block, REPO_ROOT, tmp_path, f"sh-harness#{i}")


@sh
def test_codelab_sdk_blocks_green_or_skipped(tmp_path):
    from genesis_rt.build_adapter import _child_env, probe
    blocks = _blocks("sh-harness-sdk")
    assert len(blocks) >= 1, "Lab 5 must ship an SDK block"
    found = probe()
    if not found["sdk_present"]:
        pytest.skip("QNX SDK not installed (honest skip, not a pass)")
    shell = shutil.which("sh")
    assert shell
    sdk_env = _child_env(str(found["qnx_host"]), str(found["qnx_target"]))
    for i, block in enumerate(blocks):
        _run_block(shell, block, REPO_ROOT, tmp_path,
                   f"sh-harness-sdk#{i}", sdk_env)


def test_codelab_lab_coverage_and_target_presence():
    text = DOC.read_text(encoding="utf-8")
    labs = re.split(r"^## Lab ", text, flags=re.MULTILINE)[1:]
    assert len(labs) == 6, f"advanced codelab must have 6 labs, found {len(labs)}"
    for n, lab in enumerate(labs, start=1):
        if n <= 5:
            assert "sh-harness" in lab, f"Lab {n} ships no runnable block"
        else:
            assert "sh-target" in lab, "Lab 6 must show target commands"
            assert "GENESIS_TARGET_PASSWORD" in lab, \
                "Lab 6 must route the password via env"
