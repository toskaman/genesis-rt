# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 8 §8: `serve` binds loopback, single worker (trust boundary pin)."""
import argparse
import sys
import types

import pytest

pytest.importorskip("fastapi", reason="api extra not installed")

from genesis_rt import cli as cli_mod


def test_serve_binds_loopback_single_worker(monkeypatch):
    captured: dict = {}
    fake = types.ModuleType("uvicorn")
    fake.run = lambda app, **kw: captured.update(kw)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "uvicorn", fake)
    rc = cli_mod._cmd_serve(argparse.Namespace(port=8077))
    assert rc == 0
    assert captured == {"host": "127.0.0.1", "port": 8077, "workers": 1}
