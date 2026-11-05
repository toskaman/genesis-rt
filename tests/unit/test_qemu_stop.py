# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: `qnx_target.py stop` (no network, no target, no real QEMU).

Pidfile resolution, stale-pidfile clearing, PID-reuse refusal (a live
non-QEMU pid must never be signalled), and the SIGTERM path against a
short-lived child process with the QEMU-identity check stubbed.
"""
import argparse
import importlib.util
import os
import subprocess
import sys

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_under_test", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


def _args(image_dir):
    return argparse.Namespace(image_dir=str(image_dir))


def test_pidfile_prefers_output_subdir(qt, tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    assert qt._qemu_pidfile(tmp_path) == out / "qemu.pid"


def test_pidfile_falls_back_to_image_dir(qt, tmp_path):
    assert qt._qemu_pidfile(tmp_path) == tmp_path / "qemu.pid"


def test_stop_missing_pidfile_is_already_stopped(qt, tmp_path, capsys):
    assert qt.cmd_stop(_args(tmp_path)) == 0
    assert "nothing running" in capsys.readouterr().out


def test_stop_garbage_pidfile_is_already_stopped(qt, tmp_path, capsys):
    (tmp_path / "qemu.pid").write_text("not-a-pid", encoding="utf-8")
    assert qt.cmd_stop(_args(tmp_path)) == 0
    assert "nothing running" in capsys.readouterr().out


def test_stop_dead_pid_clears_stale_pidfile(qt, tmp_path, capsys):
    pidfile = tmp_path / "qemu.pid"
    pidfile.write_text("2147483647", encoding="utf-8")  # cannot be a live pid
    assert qt._pid_is_qemu(2147483647) is False
    assert qt.cmd_stop(_args(tmp_path)) == 0
    assert not pidfile.exists()
    assert "stale" in capsys.readouterr().out


def test_live_non_qemu_pid_is_never_qemu(qt):
    assert qt._pid_is_qemu(os.getpid()) is False


def test_stop_live_non_qemu_pid_refuses_and_clears(qt, tmp_path, capsys):
    pidfile = tmp_path / "qemu.pid"
    pidfile.write_text(str(os.getpid()), encoding="utf-8")
    assert qt.cmd_stop(_args(tmp_path)) == 0
    assert not pidfile.exists()
    assert "not a live QEMU process" in capsys.readouterr().out
    # self still alive: nothing was signalled (reaching this line proves
    # survival; never os.kill() our own pid: sandboxed Windows runners
    # treat self-signaling as hostile and kill the tree)
    assert os.getppid() > 0


def test_stop_terminates_verified_process(qt, tmp_path, monkeypatch):
    monkeypatch.setattr(qt, "_pid_is_qemu", lambda pid: True)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    try:
        (tmp_path / "qemu.pid").write_text(str(child.pid), encoding="utf-8")
        assert qt.cmd_stop(_args(tmp_path)) == 0
        assert child.wait(timeout=30) is not None
        assert not (tmp_path / "qemu.pid").exists()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_stop_refused_process_is_left_alive(qt, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(qt, "_pid_is_qemu", lambda pid: False)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    try:
        (tmp_path / "qemu.pid").write_text(str(child.pid), encoding="utf-8")
        assert qt.cmd_stop(_args(tmp_path)) == 0
        assert child.poll() is None  # untouched
    finally:
        child.kill()
        child.wait()
