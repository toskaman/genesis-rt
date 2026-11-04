# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.ir import load_ir_file  # noqa: E402


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def amr_ir_path(repo_root: Path) -> Path:
    return repo_root / "examples" / "amr-demo" / "machine-ir.json"


@pytest.fixture()
def amr_ir(amr_ir_path: Path) -> dict:
    return load_ir_file(amr_ir_path)


@pytest.fixture()
def amr_ir_dict(amr_ir_path: Path) -> dict:
    return json.loads(amr_ir_path.read_text(encoding="utf-8"))
