# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: build adapter probes + qnx_target negative paths (no SDK needed)."""
import subprocess
import sys

import pytest


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


def _fake_build_dir(tmp_path, extra=None):
    from genesis_rt.build_adapter import EXPECTED_BINS
    (tmp_path / "genesis_build_gen.mk").write_text("qnx:\n")
    for name in EXPECTED_BINS:
        (tmp_path / name).write_bytes(b"fake-" + name.encode())
    if extra:
        (tmp_path / extra).write_bytes(b"fake-" + extra.encode())
    # Generated sources must never be digested as binaries.
    (tmp_path / "genesis_config_gen.h").write_text("#define X 1\n")
    return tmp_path


@pytest.fixture()
def _fake_toolchain(monkeypatch):
    import genesis_rt.build_adapter as ba
    monkeypatch.setattr(ba, "probe", lambda: {
        "sdk_present": True, "qnx_host": "h", "qnx_target": "t"})
    monkeypatch.setattr(ba, "_child_env", lambda h, t: {"PATH": ""})
    monkeypatch.setattr(
        ba, "_run",
        lambda *a, **k: {"ok": True, "returncode": 0,
                               "stdout": "", "stderr": ""})


def test_build_qnx_digests_expected_only(tmp_path, _fake_toolchain):
    from genesis_rt.build_adapter import EXPECTED_BINS, build_qnx
    rec = build_qnx(_fake_build_dir(tmp_path))
    assert rec["status"] == "ok"
    assert set(rec["binaries"]) == set(EXPECTED_BINS)
    assert rec["binaries"]["genesis_guard"]["size"] == len(b"fake-genesis_guard")


def test_build_qnx_digests_cellcheck_extra(tmp_path, _fake_toolchain):
    from genesis_rt.build_adapter import EXPECTED_BINS, build_qnx
    rec = build_qnx(_fake_build_dir(tmp_path, extra="genesis_cellcheck"))
    assert rec["status"] == "ok"
    assert set(rec["binaries"]) == set(EXPECTED_BINS) | {"genesis_cellcheck"}
    assert rec["binaries"]["genesis_cellcheck"]["size"] == len(b"fake-genesis_cellcheck")


def test_build_qnx_ignores_generated_sources(tmp_path, _fake_toolchain):
    from genesis_rt.build_adapter import build_qnx
    rec = build_qnx(_fake_build_dir(tmp_path))
    assert "genesis_config_gen" not in "".join(rec["binaries"])
