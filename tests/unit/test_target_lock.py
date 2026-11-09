# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Omega2 §3.1: one native campaign at a time, enforced and testable.

Host-side adversarial tests for the target campaign lock: mutual
exclusion, stale-lock reclaim (incl. the reclaim race), decorator
coverage over every SSH/QEMU-touching command, the non-destructive
`probe`, `lock-status`, and put read-back verification. No target,
no network: all SSH is faked or never reached.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import qnx_target as qt  # noqa: E402


@pytest.fixture
def lock_path(tmp_path, monkeypatch):
    """Point the campaign lock at a tmp file (never the repo one)."""
    p = tmp_path / "locks" / ".target.lock"
    monkeypatch.setenv("GENESIS_TARGET_LOCK", str(p))
    return p


def test_lock_acquire_release_roundtrip(lock_path):
    with qt.TargetLock():
        assert lock_path.is_file()
        holder = json.loads(lock_path.read_text(encoding="utf-8"))
        assert holder["pid"] == os.getpid()
    assert not lock_path.exists()


def test_second_contender_gets_busy_not_traceback(lock_path):
    with qt.TargetLock(owner="first"):
        with pytest.raises(qt.TargetBusy, match="held by first"):
            qt.TargetLock(owner="second").acquire()


def test_stale_lock_reclaimed(lock_path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"owner": "dead", "pid": 999999999}),
                         encoding="utf-8")
    with qt.TargetLock(owner="reclaimer"):
        holder = json.loads(lock_path.read_text(encoding="utf-8"))
        assert holder["owner"] == "reclaimer"
        assert holder["pid"] == os.getpid()


def test_stale_reclaim_race_never_tracebacks(lock_path):
    """8 racers on one stale lock: every outcome is acquire or
    TargetBusy, never a raw FileExistsError (H2 regression). Only
    the no-traceback and >=1-winner asserts are deterministic: a
    racer that reads the file mid-write sees a partial payload,
    treats it as stale, and unlink-steals the winner's file, so
    the loser count is timing-dependent (OMEGA6 A1: the old
    busy>=1 assert flaked). Mutual exclusion across real
    (multi-process, seconds-apart) campaigns is what the lock
    guarantees — see the SECURITY audit residual."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"owner": "dead", "pid": 999999999}),
                         encoding="utf-8")
    barrier = threading.Barrier(8)
    outcomes: list[str] = []
    errors: list[BaseException] = []

    def racer(n):
        try:
            barrier.wait(timeout=30)
            qt.TargetLock(owner=f"racer-{n}").acquire()
            outcomes.append("won")
        except qt.TargetBusy:
            outcomes.append("busy")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=racer, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors
    assert outcomes.count("won") >= 1
    assert lock_path.is_file()
    qt.TargetLock().release()


def test_lost_reclaim_race_raises_busy(lock_path, monkeypatch):
    """Deterministic H2: when the stale file survives our unlink
    (a rival reclaimed first), the second O_EXCL surfaces as
    TargetBusy, never FileExistsError."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"owner": "dead", "pid": 999999999}),
                         encoding="utf-8")
    monkeypatch.setattr(Path, "unlink", lambda self,
                        _missing_ok=False: None)
    with pytest.raises(qt.TargetBusy, match="stale-lock race"):
        qt.TargetLock(owner="loser").acquire()


def test_lock_env_override_respected(tmp_path, monkeypatch):
    p = tmp_path / "custom.lock"
    monkeypatch.setenv("GENESIS_TARGET_LOCK", str(p))
    assert qt.TargetLock().path == p


HELD_CMDS = ("cmd_boot", "cmd_stop", "cmd_run", "cmd_put", "cmd_verify",
             "cmd_perf", "cmd_sched", "cmd_identity", "cmd_probe")


@pytest.mark.parametrize("cmd", HELD_CMDS)
def test_mutating_commands_refuse_when_held(lock_path, capsys, cmd):
    """Every target-touching command fails loudly (rc 2) under a held
    lock — before any SSH/QEMU side effect."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"owner": "campaign-A",
                                     "pid": os.getpid()}), encoding="utf-8")
    rc = getattr(qt, cmd)(argparse.Namespace())
    assert rc == 2
    assert "one native campaign at a time" in capsys.readouterr().out


def test_lock_status_reports_free_held_stale(lock_path, capsys):
    rc = qt.cmd_lock_status(argparse.Namespace())
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["held"] is False
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"owner": "me", "pid": os.getpid()}),
                         encoding="utf-8")
    assert qt.cmd_lock_status(argparse.Namespace()) == 0
    info = json.loads(capsys.readouterr().out)
    assert (info["held"], info["pid_alive"], info["owner"]) == \
        (True, True, "me")
    lock_path.write_text(json.dumps({"owner": "dead", "pid": 999999999}),
                         encoding="utf-8")
    assert qt.cmd_lock_status(argparse.Namespace()) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["pid_alive"] is False and "stale" in info["note"]


class _FakeChannel:
    def __init__(self, status=0):
        self._status = status

    def exit_status_ready(self):
        return True

    def recv_exit_status(self):
        return self._status


class _FakeStdout:
    def __init__(self, body: bytes, status=0):
        self.channel = _FakeChannel(status)
        self._body = body

    def read(self):
        return self._body


class _FakeClient:
    """Records exec_command calls; canned cksum/uname output."""

    def __init__(self, cksum_body=b"", uname_body=b"QNX qnxqemu\n"):
        self.commands: list[str] = []
        self.cksum_body = cksum_body
        self.uname_body = uname_body
        self.closed = False
        self.puts: list[tuple[str, str]] = []

    def exec_command(self, command, timeout=None):
        self.commands.append(command)
        body = self.cksum_body if "cksum" in command else self.uname_body
        return None, _FakeStdout(body), None

    def open_sftp(self):
        outer = self

        class _Sftp:
            def mkdir(self, _path):
                pass

            def put(self, src, dst):
                outer.puts.append((src, dst))

            def chmod(self, _dst, _mode):
                pass

        return _Sftp()

    def close(self):
        self.closed = True


def test_probe_runs_fixed_uname_only(lock_path, monkeypatch, capsys):
    """`probe` executes exactly `uname -a` — the non-destructive
    auth check; `run` stays the (locked, explicit) escape hatch."""
    fake = _FakeClient()
    monkeypatch.setattr(qt, "_ssh_client", lambda *a, **k: fake)
    rc = qt.cmd_probe(argparse.Namespace(ssh_port=2222, user="qnxuser",
                                         password=None))
    assert rc == 0
    assert fake.commands == ["uname -a"]
    assert fake.closed
    assert "auth OK" in capsys.readouterr().out


def test_put_readback_refuses_mismatch(lock_path, tmp_path, monkeypatch,
                                       capsys):
    src = tmp_path / "genesis_guard"
    src.write_bytes(b"local-bytes-v2")
    man_out = tmp_path / "stage-manifest.json"
    fake = _FakeClient(cksum_body=b"1 5 genesis_guard\n")
    monkeypatch.setattr(qt, "_ssh_client", lambda *a, **k: fake)
    rc = qt.cmd_put(argparse.Namespace(ssh_port=2222, user="qnxuser",
                                       password=None, dest="/tmp/genesis",
                                       src=[str(src)],
                                       manifest_out=str(man_out)))
    assert rc == 2
    assert not man_out.exists()
    assert "no manifest written" in capsys.readouterr().out


def test_put_readback_accepts_match(lock_path, tmp_path, monkeypatch):
    from genesis_rt import provenance
    blob = b"local-bytes-v2"
    src = tmp_path / "genesis_guard"
    src.write_bytes(blob)
    man_out = tmp_path / "stage-manifest.json"
    crc, size = provenance.cksum_posix(blob)
    fake = _FakeClient(cksum_body=f"{crc} {size} genesis_guard\n".encode())
    monkeypatch.setattr(qt, "_ssh_client", lambda *a, **k: fake)
    rc = qt.cmd_put(argparse.Namespace(ssh_port=2222, user="qnxuser",
                                       password=None, dest="/tmp/genesis",
                                       src=[str(src)],
                                       manifest_out=str(man_out)))
    assert rc == 0
    assert man_out.is_file()


@pytest.mark.parametrize("sub", ["probe", "lock-status"])
def test_new_subcommands_registered(monkeypatch, sub):
    monkeypatch.setattr(sys, "argv", ["qnx_target.py", sub, "--help"])
    with pytest.raises(SystemExit) as exc:
        qt.main()
    assert exc.value.code == 0
