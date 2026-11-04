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


def test_belt_integrates_and_counts(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "BELT_APPLY 1.0 1 1000\nBELT_APPLY 1.0 2 1100\n")
    assert rows[0]["APPLIED"] == "1" and float(rows[0]["POS"]) == 0.0
    assert rows[1]["APPLIED"] == "1" and rows[1]["N"] == "2"
    assert abs(float(rows[1]["POS"]) - 0.1) < 1e-9  # prev setpoint * 0.1 s
    assert float(rows[1]["SPEED"]) == 1.0


def test_belt_ignores_stale_seq(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "BELT_APPLY 1.0 5 1000\nBELT_APPLY 9.0 5 1100\n"
                        "BELT_APPLY 9.0 3 1200\n")
    assert [r["APPLIED"] for r in rows] == ["1", "0", "0"]
    assert rows[2]["N"] == "1" and float(rows[2]["SPEED"]) == 1.0


def test_belt_dt_clamped(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "BELT_APPLY 2.0 1 1000\nBELT_APPLY 0.0 2 60000\n")
    assert abs(float(rows[1]["POS"]) - 2.0) < 1e-9  # 59 s clamped to 1 s


def test_belt_watchdog_zeroes_speed(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary, "BELT_APPLY 1.0 1 1000\nBELT_TICK 1400\nBELT_TICK 1600\n")
    assert float(rows[1]["SPEED"]) == 1.0   # 400 ms: still live
    assert float(rows[2]["SPEED"]) == 0.0   # 600 ms: cut
    assert float(rows[2]["POS"]) == 0.0     # watchdog never moves the belt


def test_belt_jam_freezes_and_decays(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary,
                "BELT_APPLY 2.0 1 1000\nBELT_APPLY 2.0 2 1100\n"
                "BELT_JAM 1\n"
                "BELT_APPLY 2.0 3 1200\nBELT_APPLY 2.0 4 1300\n"
                "BELT_APPLY 2.0 5 1400\n")
    pos_at_jam = float(rows[2]["POS"])
    assert float(rows[1]["POS"]) == pos_at_jam  # JAM line itself moves nothing
    speeds = [float(rows[3]["SPEED"]), float(rows[4]["SPEED"]),
              float(rows[5]["SPEED"])]
    assert speeds == [1.0, 0.5, 0.25]  # *=0.5 per command while jammed
    assert all(float(rows[i]["POS"]) == pos_at_jam for i in (3, 4, 5))
    assert all(rows[i]["JAMMED"] == "1" for i in range(2, 6))


def test_belt_jam_release_resumes(repo_root, tmp_path):
    binary = _build_harness(repo_root, tmp_path)
    rows = _run(binary,
                "BELT_APPLY 1.0 1 1000\nBELT_JAM 1\n"
                "BELT_APPLY 1.0 2 1100\nBELT_JAM 0\n"
                "BELT_APPLY 1.0 3 1200\nBELT_APPLY 1.0 4 1300\n")
    assert float(rows[2]["POS"]) == 0.0      # frozen while jammed
    assert float(rows[2]["SPEED"]) == 0.5    # decayed once
    assert float(rows[4]["POS"]) == 0.05     # 0.5 m/s * 0.1 s after release
    assert float(rows[4]["SPEED"]) == 1.0    # new setpoint latched
    assert float(rows[5]["POS"]) == 0.15     # 1.0 m/s * 0.1 s


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
