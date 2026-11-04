# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""C/Python guard conformance: identical decisions on identical vectors.

Builds target/qnx8/host_tests/guard_vector with the host C compiler and
compares it against host/genesis_rt/guard_policy.py. Skips only when no
host C compiler exists (never a silent pass: the skip is explicit).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis_rt import guard_policy as gp

LIMITS = {"period_ms": 10, "max_linear_speed_mps": 1.2,
          "max_angular_speed_radps": 1.0, "freshness_limit_ms": 100}

# (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst, state_in, last_seq_override)
VECTORS = [
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None),
    (0xDEADBEEF, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 99, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 0, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 100, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 150, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 0, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 5.0, 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, -2.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 10, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 10),  # replay
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 3, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 3, None),  # locked
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 1, 3, None),  # reset
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, 0.0, 2, 0, 1, 0, 1, None),  # degraded
    (0x47454E31, 1, 1, 1, 0, 50, float("nan"), 0.0, 1, 0, 1, 0, 1, None),
    (0x47454E31, 1, 1, 1, 0, 50, 0.5, float("inf"), 1, 0, 1, 0, 1, None),
    (0xDEADBEEF, 1, 1, 1, 0, 50, float("nan"), 0.0, 1, 0, 1, 0, 1, None),
]


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


def _expected(vector) -> tuple[str, str, int]:
    (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst,
     state_in, last_ov) = vector
    ctx = gp.GuardContext(last_seq=last_ov if last_ov is not None else seq - 1,
                          state=state_in, reset_armed=bool(rst))
    cmd = {"magic": magic, "version": ver, "size_ok": bool(size_ok), "seq": seq,
           "now_ms": now, "deadline_ms": dl, "linear_mps": float(lin),
           "angular_radps": float(ang), "req_state": req,
           "sensor_age_ms": age, "sim_connected": bool(sim)}
    v = gp.decide(cmd, ctx, LIMITS)
    return v["decision"], v["reason"], v["state_out"]


def test_c_python_conformance(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    lines = ["LIMITS 1.2 1.0 100"]
    for vector in VECTORS:
        if vector[-1] is not None:
            lines.append(f"SEQ {vector[-1]}")
        (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst,
         state_in, _last) = vector
        lines.append(f"{magic:X} {ver} {size_ok} {seq} {now} {dl} "
                     f"{lin!r} {ang!r} {req} {age} {sim} {rst} {state_in}")
    proc = subprocess.run([str(binary)], input="\n".join(lines) + "\n",
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    outputs = [ln for ln in proc.stdout.splitlines() if not ln.startswith("SEQ-ARMED")]
    assert len(outputs) == len(VECTORS), proc.stdout
    for vector, line in zip(VECTORS, outputs):
        decision, reason, state_out = line.split()
        assert (decision, reason, int(state_out)) == _expected(vector), vector
