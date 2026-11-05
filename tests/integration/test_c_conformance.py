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

# (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst,
#  state_in, last_seq_override, estop)
E = 0x47454E31
VECTORS = [
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),
    (0xDEADBEEF, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 99, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 0, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 100, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 150, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 0, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 5.0, 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 0.5, -2.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 10, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 10, 0),  # replay
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 3, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 3, None, 0),  # locked
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 1, 3, None, 0),  # reset
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 2, 0, 1, 0, 1, None, 0),  # degraded
    (E, 1, 1, 1, 0, 50, float("nan"), 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 1, 0, 50, 0.5, float("inf"), 1, 0, 1, 0, 1, None, 0),
    (0xDEADBEEF, 1, 1, 1, 0, 50, float("nan"), 0.0, 1, 0, 1, 0, 1, None, 0),
    (E, 1, 1, 0, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 0xFFFFFFFF, 0),  # wrap
    (E, 1, 1, 50, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 100, 0),  # old replay
    (E, 1, 1, 100, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 100, 0),  # dup
    (E, 1, 1, 0x80000000, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, 0, 0),  # jump
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 1),  # estop
    (E, 1, 1, 1, 0, 50, 9.0, 0.0, 1, 0, 1, 0, 1, None, 1),  # estop>speed
    (0xDEADBEEF, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 1),  # magic>estop
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 1, None, 2),  # estop bad value
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 0, 3, None, 1),  # estop while locked
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 0, 1, 1, 3, None, 1),  # estop blocks reset
    # §16 deadline serial arithmetic (M = 2^32)
    (E, 1, 1, 1, 10, (1 << 32) - 5, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # overdue across wrap
    (E, 1, 1, 1, (1 << 32) - 10, 100, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # future across wrap
    (E, 1, 1, 1, (1 << 32) - 1, (1 << 32) - 1, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # equal at edge
    (E, 1, 1, 1, (1 << 31) - 1, 0, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # max overdue
    (E, 1, 1, 1, 1 << 31, 0, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # ambiguity reads future
    # Wave 10 E3: exact-limit boundaries (wire is float32, oracle float64)
    (E, 1, 1, 1, 0, 50, 1.2, 0.0, 1, 0, 1, 0, 1, None, 0),  # lin at limit
    (E, 1, 1, 1, 0, 50, 1.1999999, 0.0, 1, 0, 1, 0, 1, None, 0),  # just under
    (E, 1, 1, 1, 0, 50, -1.2, 0.0, 1, 0, 1, 0, 1, None, 0),  # neg at limit
    (E, 1, 1, 1, 0, 50, 0.5, 1.0, 1, 0, 1, 0, 1, None, 0),  # ang at limit
    (E, 1, 1, 1, 0, 50, 0.5, -1.0, 1, 0, 1, 0, 1, None, 0),  # ang neg at limit
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 100, 1, 0, 1, None, 0),  # age at limit
    (E, 1, 1, 1, 0, 50, 0.5, 0.0, 1, 101, 1, 0, 1, None, 0),  # age just over
    (E, 1, 1, 1, 1000, 1000, 0.5, 0.0, 1, 0, 1, 0, 1, None, 0),  # now == dl
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
     state_in, last_ov, estop) = vector
    ctx = gp.GuardContext(last_seq=last_ov if last_ov is not None else seq - 1,
                          state=state_in, reset_armed=bool(rst))
    cmd = {"magic": magic, "version": ver, "size_ok": bool(size_ok), "seq": seq,
           "now_ms": now, "deadline_ms": dl, "linear_mps": float(lin),
           "angular_radps": float(ang), "req_state": req,
           "sensor_age_ms": age, "sim_connected": bool(sim),
           "estop_engaged": estop}
    v = gp.decide(cmd, ctx, LIMITS)
    return v["decision"], v["reason"], v["state_out"]


def test_c_python_conformance(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    lines = ["LIMITS 1.2 1.0 100"]
    for vector in VECTORS:
        if vector[-2] is not None:
            lines.append(f"SEQ {vector[-2]}")
        (magic, ver, size_ok, seq, now, dl, lin, ang, req, age, sim, rst,
         state_in, _last, estop) = vector
        lines.append(f"{magic:X} {ver} {size_ok} {seq} {now} {dl} "
                     f"{lin!r} {ang!r} {req} {age} {sim} {rst} {state_in} "
                     f"{estop}")
    proc = subprocess.run([str(binary)], input="\n".join(lines) + "\n",
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    outputs = [ln for ln in proc.stdout.splitlines() if not ln.startswith("SEQ-ARMED")]
    assert len(outputs) == len(VECTORS), proc.stdout
    for vector, line in zip(VECTORS, outputs):
        decision, reason, state_out = line.split()
        assert (decision, reason, int(state_out)) == _expected(vector), vector
