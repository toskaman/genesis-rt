# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: §14 native-campaign isolation (no network, no target).

Campaign lock (single owner, stale reclaim), staging-manifest
roundtrip + stale/missing detection, and target-identity fetchers
against a faked SSH client.
"""
import importlib.util
import json
import os

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


class _FakeChannel:
    def __init__(self, status):
        self._status = status

    def exit_status_ready(self):
        return True

    def recv_exit_status(self):
        return self._status


class _FakeStream:
    def __init__(self, status, body):
        self.channel = _FakeChannel(status)
        self._body = body.encode("utf-8")

    def read(self):
        return self._body


class _FakeClient:
    def __init__(self, status=0, body=""):
        self._status = status
        self._body = body
        self.commands = []

    def exec_command(self, command, timeout=None):
        self.commands.append(command)
        return (None, _FakeStream(self._status, self._body),
                _FakeStream(self._status, ""))

    def close(self):
        pass


# -- campaign lock ----------------------------------------------------

def test_lock_acquire_release_roundtrip(qt, tmp_path):
    lock = qt.TargetLock(tmp_path / "target.lock", owner="t1")
    lock.acquire()
    assert (tmp_path / "target.lock").exists()
    lock.release()
    assert not (tmp_path / "target.lock").exists()


def test_lock_second_acquire_refused_while_held(qt, tmp_path):
    first = qt.TargetLock(tmp_path / "target.lock", owner="first")
    first.acquire()
    try:
        with pytest.raises(qt.TargetBusy):
            qt.TargetLock(tmp_path / "target.lock",
                          owner="second").acquire()
    finally:
        first.release()


def test_lock_context_manager_releases(qt, tmp_path):
    with qt.TargetLock(tmp_path / "target.lock", owner="ctx"):
        assert (tmp_path / "target.lock").exists()
    assert not (tmp_path / "target.lock").exists()


def test_lock_stale_holder_reclaimed(qt, tmp_path, monkeypatch):
    (tmp_path / "target.lock").write_text(
        json.dumps({"owner": "dead", "pid": 424242}), encoding="utf-8")
    monkeypatch.setattr(qt.TargetLock, "_pid_alive",
                        staticmethod(lambda pid: False))
    qt.TargetLock(tmp_path / "target.lock", owner="new").acquire()
    holder = json.loads(
        (tmp_path / "target.lock").read_text(encoding="utf-8"))
    assert holder["owner"] == "new"
    assert holder["pid"] == os.getpid()


def test_lock_release_by_non_owner_keeps_lock(qt, tmp_path):
    (tmp_path / "target.lock").write_text(
        json.dumps({"owner": "someone-else", "pid": 424243}),
        encoding="utf-8")
    qt.TargetLock(tmp_path / "target.lock", owner="me").release()
    assert (tmp_path / "target.lock").exists()


def test_lock_decorator_refuses_busy_campaign(qt, tmp_path, monkeypatch,
                                              capsys):
    monkeypatch.setattr(qt, "DEFAULT_TARGET_LOCK",
                        tmp_path / "target.lock")
    held = qt.TargetLock(tmp_path / "target.lock", owner="other-campaign")
    held.acquire()
    try:
        @qt._with_target_lock
        def _campaign(args):
            raise AssertionError("must not run while busy")

        assert _campaign(object()) == 2
        assert "one native campaign at a time" in capsys.readouterr().out
    finally:
        held.release()


# -- staging manifest -------------------------------------------------

def _staged_from_manifest(manifest):
    return {name: {"cksum": e["cksum"], "size": e["size"]}
            for name, e in manifest["files"].items()}


def test_manifest_roundtrip_matches(qt, tmp_path):
    a = tmp_path / "genesis_guard"
    b = tmp_path / "genesis_faultinject"
    a.write_bytes(b"\x7fELF-guard-bytes")
    b.write_bytes(b"\x7fELF-fi-bytes")
    out = tmp_path / "stage.json"
    manifest = qt.write_stage_manifest(out, "/tmp/genesis", [a, b])
    assert qt.load_stage_manifest(out) == manifest
    assert qt.check_staged_against_manifest(
        _staged_from_manifest(manifest), manifest) == []
    # atomic write leaves no temp file behind
    assert list(tmp_path.glob("*.tmp")) == []


def test_manifest_mismatch_detected(qt, tmp_path):
    a = tmp_path / "genesis_guard"
    a.write_bytes(b"fresh-binary")
    manifest = qt.write_stage_manifest(tmp_path / "stage.json",
                                       "/tmp/genesis", [a])
    staged = _staged_from_manifest(manifest)
    staged["genesis_guard"] = {"cksum": 1, "size": 2}  # stale on target
    errors = qt.check_staged_against_manifest(staged, manifest)
    assert len(errors) == 1
    assert "genesis_guard" in errors[0]


def test_manifest_missing_binary_detected(qt, tmp_path):
    a = tmp_path / "genesis_guard"
    a.write_bytes(b"fresh-binary")
    manifest = qt.write_stage_manifest(tmp_path / "stage.json",
                                       "/tmp/genesis", [a])
    errors = qt.check_staged_against_manifest({}, manifest)
    assert len(errors) == 1
    assert "missing on target" in errors[0]


def test_manifest_extra_on_target_not_flagged(qt, tmp_path):
    a = tmp_path / "genesis_guard"
    a.write_bytes(b"fresh-binary")
    manifest = qt.write_stage_manifest(tmp_path / "stage.json",
                                       "/tmp/genesis", [a])
    staged = _staged_from_manifest(manifest)
    staged["genesis_extra"] = {"cksum": 9, "size": 9}
    assert qt.check_staged_against_manifest(staged, manifest) == []


def test_manifest_no_inventory_is_error(qt, tmp_path):
    a = tmp_path / "genesis_guard"
    a.write_bytes(b"fresh-binary")
    manifest = qt.write_stage_manifest(tmp_path / "stage.json",
                                       "/tmp/genesis", [a])
    assert qt.check_staged_against_manifest(None, manifest) != []


def test_manifest_invalid_file_rejected(qt, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": true}', encoding="utf-8")
    with pytest.raises(ValueError):
        qt.load_stage_manifest(bad)
    with pytest.raises(OSError):
        qt.load_stage_manifest(tmp_path / "absent.json")


# -- identity fetchers (faked SSH) ------------------------------------

def test_fetch_uname_ok(qt):
    client = _FakeClient(0, "QNX neutrino 8.0.0 x86_64\n")
    uname, err = qt._fetch_uname(client)
    assert err is None
    assert uname == "QNX neutrino 8.0.0 x86_64"
    assert client.commands == ["uname -a"]


def test_fetch_uname_empty_is_reason(qt):
    uname, err = qt._fetch_uname(_FakeClient(0, "\n"))
    assert uname is None
    assert err is not None


def test_fetch_staged_ok(qt):
    body = "1219131554 13 genesis_guard\n987654 7 genesis_faultinject\n"
    staged, err = qt._fetch_staged(_FakeClient(0, body))
    assert err is None
    assert staged == {"genesis_guard": {"cksum": 1219131554, "size": 13},
                      "genesis_faultinject": {"cksum": 987654, "size": 7}}


def test_fetch_staged_garbage_is_reason(qt):
    staged, err = qt._fetch_staged(_FakeClient(0, "total 3\n"))
    assert staged is None
    assert "unparsable" in err


def test_fetch_staged_nonzero_exit_is_reason(qt):
    staged, err = qt._fetch_staged(_FakeClient(1, "cksum: not found\n"))
    assert staged is None
    assert "exit=1" in err
