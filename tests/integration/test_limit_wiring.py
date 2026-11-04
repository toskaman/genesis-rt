# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""P0 #3: generated limits must control runtime behavior.

Two machines with different IR limits must produce different generated
headers, and the shared C policy must render different decisions for an
identical command under each limit set. The on-target `limits_differ`
matrix step proves the compiled guard binaries embed their own headers.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis_rt import codegen
from genesis_rt.ir import guard_limits, load_ir_file

# Identical command vector: linear 1.5 mps sits between the AMR limit
# (1.2, must DENY) and the conveyor limit (2.0, must ALLOW).
# (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst, state)
PROBE_VECTOR = (0x47454E31, 1, 1, 1, 0, 50, 1.5, 0.0, 1, 0, 1, 0, 1)


def _load_both(repo_root: Path):
    amr = load_ir_file(repo_root / "examples" / "amr-demo" / "machine-ir.json")
    conv = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    return amr, conv


def test_generated_headers_differ_per_machine(repo_root, tmp_path):
    amr, conv = _load_both(repo_root)
    assert guard_limits(amr)["max_linear_speed_mps"] != \
        guard_limits(conv)["max_linear_speed_mps"]
    codegen.generate(amr, tmp_path / "amr")
    codegen.generate(conv, tmp_path / "conv")
    amr_h = (tmp_path / "amr" / "genesis_config_gen.h").read_text()
    conv_h = (tmp_path / "conv" / "genesis_config_gen.h").read_text()
    assert "#define GENESIS_MAX_LINEAR_MPS 1.2" in amr_h
    assert "#define GENESIS_MAX_LINEAR_MPS 2.0" in conv_h
    assert '#define GENESIS_MACHINE_ID "amr-demo-01"' in amr_h
    assert '#define GENESIS_MACHINE_ID "conveyor-demo-01"' in conv_h
    assert amr_h != conv_h


def _build_harness(repo_root: Path, tmp_path: Path) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no host C compiler available")
    src = repo_root / "target" / "qnx8"
    out = tmp_path / ("guard_vector.exe" if cc.lower().endswith(".exe") else "guard_vector")
    cmd = [cc, "-O1", "-Wall", "-Wextra", f"-I{src / 'include'}",
           f"-I{src / 'common'}", "-o", str(out),
           str(src / "common" / "guard_policy.c"),
           str(src / "host_tests" / "guard_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"C build failed:\n{proc.stderr}"
    return out


def _decide(binary: Path, limits_line: str) -> str:
    magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst, state = PROBE_VECTOR
    stdin = (f"{limits_line}\n{magic:X} {ver} {size_ok} {seq} {now} {dl} "
             f"{lin!r} {ang!r} {req} {age} {sim} {rst} {state}\n")
    proc = subprocess.run([str(binary)], input=stdin, capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.split()[0]


def test_identical_command_different_decisions(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    assert _decide(binary, "LIMITS 1.2 1.0 100") == "DENY"   # AMR header
    assert _decide(binary, "LIMITS 2.0 1.0 50") == "ALLOW"    # conveyor header
