# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: build adapter probes + qnx_target negative paths (no SDK needed)."""
import subprocess
import sys


def test_probe_qemu_shape():
    from genesis_rt.build_adapter import probe_qemu
    q = probe_qemu()
    assert set(q) == {"present", "path", "version"}
    assert isinstance(q["present"], bool)
    if q["present"]:
        assert q["path"] and q["version"]


def test_probe_includes_qemu():
    from genesis_rt.build_adapter import probe
    assert "qemu" in probe()
    assert set(probe()["qemu"]) == {"present", "path", "version"}


def test_qnx_target_probe_image_empty_dir(repo_root, tmp_path):
    script = repo_root / "scripts" / "qnx_target.py"
    r = subprocess.run([sys.executable, str(script), "probe-image", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 1
    assert "bootable_layout=False" in r.stdout


def test_qnx_target_probe_image_with_files(repo_root, tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "ifs.bin").write_bytes(b"fake-ifs")
    (tmp_path / "output" / "disk-qemu.vmdk").write_bytes(b"fake-disk")
    script = repo_root / "scripts" / "qnx_target.py"
    r = subprocess.run([sys.executable, str(script), "probe-image", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
    assert "bootable_layout=True" in r.stdout


def test_qnx_target_boot_refuses_without_image(repo_root, tmp_path):
    script = repo_root / "scripts" / "qnx_target.py"
    r = subprocess.run([sys.executable, str(script), "boot", str(tmp_path),
                        "--out", str(tmp_path / "o"), "--timeout", "5"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 2  # missing image files, QEMU never launched
