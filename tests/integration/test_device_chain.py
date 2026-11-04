# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""P0 #4: guarded virtual device path.

- The pure device kinematics (shared by the QNX server) integrates pose
  from arrival-time dt, ignores stale/duplicate seq, clamps dt, and the
  actuator watchdog zeroes velocity after 500 ms of silence.
- No-bypass audit: the controller source must never reference the device
  channel; only the guard forwards to it.
"""
import shutil
import subprocess
from pathlib import Path

import pytest


def _build_harness(repo_root: Path, tmp_path: Path) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no host C compiler available")
    src = repo_root / "target" / "qnx8"
    out = tmp_path / ("device_vector.exe" if cc.lower().endswith(".exe") else "device_vector")
    cmd = [cc, "-O1", "-Wall", "-Wextra", f"-I{src / 'include'}",
           f"-I{src / 'common'}", "-o", str(out),
           str(src / "common" / "device_model.c"),
           str(src / "host_tests" / "device_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"C build failed:\n{proc.stderr}"
    return out


def _run(binary: Path, script: str):
    proc = subprocess.run([str(binary)], input=script, capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    rows = []
    for line in proc.stdout.splitlines():
        row = {}
        for tok in line.split():
            k, _, v = tok.partition("=")
            row[k] = v
        rows.append(row)
    return rows


def test_device_integrates_and_counts(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "APPLY 1.0 0.0 1 1000\nAPPLY 1.0 0.0 2 1100\n")
    assert rows[0]["APPLIED"] == "1" and float(rows[0]["X"]) == 0.0  # dt=0 first
    assert rows[1]["APPLIED"] == "1" and rows[1]["N"] == "2"
    assert abs(float(rows[1]["X"]) - 0.1) < 1e-9  # 1.0 m/s * 0.1 s


def test_device_ignores_stale_seq(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "APPLY 1.0 0.0 5 1000\nAPPLY 9.0 0.0 5 1100\n"
                        "APPLY 9.0 0.0 3 1200\n")
    assert [r["APPLIED"] for r in rows] == ["1", "0", "0"]
    assert rows[2]["N"] == "1" and float(rows[2]["V"]) == 1.0


def test_device_dt_clamped(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "APPLY 2.0 0.0 1 1000\nAPPLY 0.0 0.0 2 60000\n")
    assert abs(float(rows[1]["X"]) - 2.0) < 1e-9  # 59 s clamped to 1 s


def test_device_watchdog_zeroes_velocity(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "APPLY 1.0 0.5 1 1000\nTICK 1400\nTICK 1600\n")
    assert float(rows[1]["V"]) == 1.0   # 400 ms: still live
    assert float(rows[2]["V"]) == 0.0 and float(rows[2]["W"]) == 0.0  # 600 ms: cut
    assert float(rows[2]["X"]) == 0.0  # watchdog never integrates pose


def test_no_controller_bypass_path(repo_root):
    """The controller must not reference the device channel at all; the
    guard is the only forwarder. Source-level, checkable, no trust."""
    qnx8 = repo_root / "target" / "qnx8"
    controller = (qnx8 / "controller" / "genesis_controller.c").read_text()
    assert "genesis_device" not in controller
    assert "GENESIS_FWD_MAGIC" not in controller
    guard = (qnx8 / "guard" / "genesis_guard.c").read_text()
    assert "GENESIS_DEVICE_ATTACH_NAME" in guard  # the one forwarder
    device = (qnx8 / "device" / "genesis_device.c").read_text()
    assert "GENESIS_FWD_MAGIC" in device  # only accepts forwarded frames
