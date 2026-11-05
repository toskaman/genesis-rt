# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 6 A1: simulate/faults route v1 and v2 IR through the strict loaders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from genesis_rt.cli import main

EX = Path(__file__).resolve().parents[2] / "examples"
CASES = [
    ("amr-demo/machine-ir.json", "v1", "nominal_navigation", 8),
    ("amr-demo/machine-ir-v2.json", "v2", "nominal_navigation", 8),
    ("conveyor-demo/machine-ir.json", "v1", "nominal_navigation", 5),
    ("conveyor-demo/machine-ir-v2.json", "v2", "nominal_navigation", 5),
    ("cell-demo/cell-ir.json", "v1", "cell_nominal_transfer", 4),
]


@pytest.mark.parametrize("rel,ver,nominal,n", CASES)
def test_simulate_uses_kind_nominal(rel, ver, nominal, n, capsys):
    assert main(["simulate", str(EX / rel)]) == 0
    out = capsys.readouterr().out
    assert f"schema {ver}" in out and f"{nominal}: pass" in out


@pytest.mark.parametrize("rel,ver,nominal,n", CASES)
def test_faults_all_pass(rel, ver, nominal, n, capsys):
    assert main(["faults", str(EX / rel)]) == 0
    out = capsys.readouterr().out
    assert f"schema {ver}" in out and f"{n}/{n} scenarios passed" in out


def test_broken_cell_simulate_fails_not_silently(capsys):
    assert main(["simulate", str(EX / "cell-demo/cell-ir-broken.json")]) == 1
    assert "cell_nominal_transfer: fail" in capsys.readouterr().out


def test_undeclared_scenario_rejected(capsys):
    assert main(["simulate", str(EX / "amr-demo/machine-ir.json"),
                 "--scenario", "belt_jam"]) == 2
    assert "not declared" in capsys.readouterr().err


def test_wrong_kind_scenario_rejected(capsys):
    assert main(["simulate", str(EX / "cell-demo/cell-ir.json"),
                 "--scenario", "nominal_navigation"]) == 2
    assert "not declared" in capsys.readouterr().err


@pytest.mark.parametrize("cmd", ["simulate", "faults", "validate"])
@pytest.mark.parametrize("bad", [3, None, "2"])
def test_invalid_schema_version(cmd, bad, tmp_path, capsys):
    doc = json.loads((EX / "amr-demo/machine-ir-v2.json").read_text())
    doc["schema_version"] = bad
    p = tmp_path / "ir.json"
    p.write_text(json.dumps(doc))
    assert main([cmd, str(p)]) == 2
    assert "unsupported schema_version" in capsys.readouterr().err


def test_v2_not_reinterpreted_as_v1(tmp_path, capsys):
    """A v2 body labelled v1 must fail the strict v1 loader, not be coerced."""
    doc = json.loads((EX / "amr-demo/machine-ir-v2.json").read_text())
    doc["schema_version"] = 1
    p = tmp_path / "ir.json"
    p.write_text(json.dumps(doc))
    assert main(["simulate", str(p)]) == 2
