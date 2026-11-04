# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: SSH retry policy vs the guest penalty box (no network).

Regression for the PerSourcePenalties incident: rapid reconnect bursts got
the source banned ("Not allowed at this time"), and every probe during the
ban extended it. Paramiko and time.sleep are faked; no socket is opened.
"""
import importlib.util
import sys
import types

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


def test_policy_constants_pinned(qt):
    assert qt._SSH_MAX_ATTEMPTS == 4
    assert qt._SSH_ATTEMPT_GAP_S == 45
    assert qt._SSH_PENALTY_COOLDOWN_S == 300


@pytest.mark.parametrize("text,expected", [
    ("Error reading SSH protocol banner", True),
    ("No banner received", True),
    ("BANNER negotiation failed", True),
    ("Not allowed at this time", True),
    ("ssh: Not allowed at this time (penalty)", True),
    ("Authentication failed", False),
    ("AuthenticationException: auth error", False),
    ("Connection refused", False),
    ("timed out", False),
    ("", False),
])
def test_penalty_box_signature(qt, text, expected):
    assert qt._ssh_is_penalty_box_signature(RuntimeError(text)) is expected


class _FakeClient:
    instances = []

    def __init__(self, script):
        self._script = script
        _FakeClient.instances.append(self)

    def set_missing_host_key_policy(self, _policy):
        pass

    def connect(self, *args, **kwargs):
        if not self._script:
            return  # success once the failure script is exhausted
        raise self._script.pop(0)


@pytest.fixture()
def fake_ssh(monkeypatch):
    """Install fake paramiko + recording sleep. Returns (script, sleeps)."""
    script = []
    sleeps = []
    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.SSHClient = lambda: _FakeClient(script)
    fake_paramiko.AutoAddPolicy = lambda: object()
    monkeypatch.setitem(sys.modules, "paramiko", fake_paramiko)
    monkeypatch.setattr("time.sleep", sleeps.append)
    _FakeClient.instances.clear()
    return script, sleeps


def test_first_try_success_no_sleep(qt, fake_ssh):
    script, sleeps = fake_ssh
    client = qt._ssh_client(2222, "qnxuser", "pw")
    assert isinstance(client, _FakeClient)
    assert sleeps == []


def test_auth_flap_retries_with_patient_gap_then_raises(qt, fake_ssh):
    script, sleeps = fake_ssh
    script.extend(RuntimeError("Authentication failed") for _ in range(4))
    with pytest.raises(RuntimeError, match="Authentication failed"):
        qt._ssh_client(2222, "qnxuser", "pw")
    assert len(_FakeClient.instances) == 4
    assert sleeps == [45, 45, 45]


def test_banner_failure_triggers_single_long_cooldown(qt, fake_ssh):
    script, sleeps = fake_ssh
    script.append(RuntimeError("Error reading SSH protocol banner"))
    client = qt._ssh_client(2222, "qnxuser", "pw")
    assert isinstance(client, _FakeClient)
    assert sleeps == [300]


def test_explicit_refusal_triggers_cooldown_not_gap(qt, fake_ssh):
    script, sleeps = fake_ssh
    script.append(RuntimeError("Not allowed at this time"))
    qt._ssh_client(2222, "qnxuser", "pw")
    assert sleeps == [300]


def test_cooldown_only_once_then_normal_gap(qt, fake_ssh):
    script, sleeps = fake_ssh
    script.extend([
        RuntimeError("Error reading SSH protocol banner"),
        RuntimeError("Error reading SSH protocol banner"),
        RuntimeError("Authentication failed"),
        RuntimeError("Authentication failed"),
    ])
    with pytest.raises(RuntimeError):
        qt._ssh_client(2222, "qnxuser", "pw")
    assert sleeps == [300, 45, 45]


def test_flap_then_success(qt, fake_ssh):
    """Transient mid-handshake failure, then success: one gap, no cooldown."""
    script, sleeps = fake_ssh
    script.append(RuntimeError("Authentication failed"))
    client = qt._ssh_client(2222, "qnxuser", "pw")
    assert isinstance(client, _FakeClient)
    assert sleeps == [45]
