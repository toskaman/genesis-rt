# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §8: `serve` binds loopback, single worker (trust boundary pin)."""
import argparse
import sys
import types

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")

from genesis_rt import cli as cli_mod


def test_serve_binds_loopback_single_worker(monkeypatch, tmp_path):
    captured: dict = {}
    fake = types.ModuleType("uvicorn")
    fake.run = lambda app, **kw: captured.update(kw)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "uvicorn", fake)
    # Never touch the real store: building the app runs crash recovery,
    # which reaped a live campaign op on 2026-11-05.
    monkeypatch.setattr("genesis_rt.api.ARTIFACTS", tmp_path / "artifacts")
    rc = cli_mod._cmd_serve(argparse.Namespace(port=8077))
    assert rc == 0
    assert captured == {"host": "127.0.0.1", "port": 8077, "workers": 1}


def test_serve_without_api_extra_is_actionable(monkeypatch, capsys):
    """Wave 10 Sprint D4 (§20): a missing fastapi/uvicorn fails with
    an actionable message and exit 2, not a raw traceback."""
    monkeypatch.setitem(sys.modules, "fastapi", None)
    monkeypatch.setitem(sys.modules, "uvicorn", None)
    monkeypatch.delitem(sys.modules, "genesis_rt.api", raising=False)
    rc = cli_mod._cmd_serve(argparse.Namespace(port=8077))
    assert rc == 2
    assert "pip install -e '.[api]'" in capsys.readouterr().err
