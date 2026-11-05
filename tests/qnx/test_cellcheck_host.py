# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Host C check: genesis_cellcheck compiles warning-free and selftests.

Portable C (no QNX headers): the same selftest binary logic runs on the
host toolchain here and on the QNX target in the cell_policy matrix
step. Skips honestly when no host C compiler is available.
"""
import shutil
import subprocess

import pytest

from genesis_rt import codegen


@pytest.fixture()
def cc():
    exe = shutil.which("cc") or shutil.which("gcc")
    if exe is None:
        pytest.skip("no host C compiler (honest skip, not a pass)")
    return exe


def _build_cellcheck(cc, repo_root, tmp_path, cell_ir):
    gen = tmp_path / "gen-cell"
    codegen.generate(cell_ir, gen)
    src = repo_root / "target" / "qnx8" / "cell" / "genesis_cellcheck.c"
    exe = tmp_path / ("cellcheck.exe" if cc.endswith(".exe") else "cellcheck")
    build = subprocess.run(
        [cc, "-O1", "-Wall", "-Wextra", f"-I{gen}", "-o", str(exe),
         str(src)],
        capture_output=True, text=True, timeout=120)
    return exe, build


def test_cellcheck_compiles_warning_free_and_selftests(cc, cell_ir, tmp_path,
                                                       repo_root):
    exe, build = _build_cellcheck(cc, repo_root, tmp_path, cell_ir)
    assert build.returncode == 0, build.stderr
    assert "warning" not in build.stderr.lower(), build.stderr
    run = subprocess.run([str(exe), "selftest"], capture_output=True,
                         text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "CELL_POLICY: PASS 12/12" in run.stdout
    assert run.stdout.count("CELLCHECK") == 12


def test_cellcheck_rejects_tampered_policy(cc, cell_ir, tmp_path, repo_root):
    gen = tmp_path / "gen-evil"
    codegen.generate(cell_ir, gen)
    header = gen / "genesis_cell_policy.h"
    text = header.read_text(encoding="utf-8")
    header.write_text(text.replace(
        "GENESIS_CELL_STATION_X_M 6.0", "GENESIS_CELL_STATION_X_M 99.0"),
        encoding="utf-8")
    src = repo_root / "target" / "qnx8" / "cell" / "genesis_cellcheck.c"
    exe = tmp_path / "cellcheck-evil"
    build = subprocess.run(
        [cc, "-O1", f"-I{gen}", "-o", str(exe), str(src)],
        capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe), "selftest"], capture_output=True,
                         text=True, timeout=60)
    assert run.returncode == 1
    assert "CELL_POLICY: FAIL" in run.stdout


def test_cellcheck_rejects_bad_usage(cc, cell_ir, tmp_path, repo_root):
    exe, build = _build_cellcheck(cc, repo_root, tmp_path, cell_ir)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True,
                         timeout=60)
    assert run.returncode == 2
    assert "usage:" in run.stderr
