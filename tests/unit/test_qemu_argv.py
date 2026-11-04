# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: QEMU argv construction (accel/cpu defaults that boot QNX)."""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_argv", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


@pytest.fixture()
def image_dir(tmp_path):
    out = tmp_path / "img" / "output"
    out.mkdir(parents=True)
    (out / "ifs.bin").write_bytes(b"ifs")
    (out / "disk-qemu.vmdk").write_bytes(b"disk")
    return tmp_path / "img"


def _cpu_of(argv):
    assert "-cpu" in argv
    return argv[argv.index("-cpu") + 1]


def test_tcg_defaults_to_cpu_max(qt, image_dir):
    """QNX spins on default qemu64 under TCG (proven stuck guest); max boots."""
    argv = qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk")
    assert _cpu_of(argv) == "max"
    assert "-accel" not in argv  # tcg is QEMU's default backend


def test_tcg_rejects_host_cpu(qt, image_dir):
    with pytest.raises(ValueError, match="hardware accelerator"):
        qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk",
                           cpu="host")


def test_tcg_honors_explicit_cpu(qt, image_dir):
    argv = qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk",
                             cpu="Haswell")
    assert _cpu_of(argv) == "Haswell"


def test_whpx_keeps_host_passthrough(qt, image_dir, monkeypatch):
    monkeypatch.setenv("PROCESSOR_IDENTIFIER", "Intel64 Family 6")
    argv = qt.build_qemu_argv("qemu", image_dir, accel="whpx", boot="disk")
    assert _cpu_of(argv) == "host"
    assert argv[argv.index("-accel") + 1] == "whpx"


def test_device_chain_status_runs_as_root(qt):
    """resmgr_attach() needs root: the device_chain status leg must start
    and be cleaned up via sudo, or the node never appears (EPERM)."""
    body = dict(qt.TARGET_MATRIX)["device_chain"]
    assert "sudo -n ./genesis_status /tmp/genesis-status-node" in body
    assert body.count("sudo -n slay genesis_status") >= 2  # setup + cleanup
