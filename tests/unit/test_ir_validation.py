# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: strict Machine IR validation."""
import copy

import pytest

from genesis_rt.ir import IRValidationError, guard_limits, load_ir_file, validate_ir


def test_amr_example_valid_json_and_yaml(repo_root):
    a = load_ir_file(repo_root / "examples" / "amr-demo" / "machine-ir.json")
    assert a["machine"]["id"] == "amr-demo-01"
    try:
        b = load_ir_file(repo_root / "examples" / "amr-demo" / "machine-ir.yaml")
    except IRValidationError as exc:
        pytest.skip(f"pyyaml missing: {exc}")
    assert b["machine"]["id"] == "amr-demo-01"
    assert a["verification"]["scenarios"] == b["verification"]["scenarios"]


def test_conveyor_example_valid(repo_root):
    c = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    assert c["machine"]["kind"] == "conveyor"


def test_rejects_unknown_top_level_key(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["surprise"] = 1
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_unknown_machine_kind(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["machine"]["kind"] = "starship"
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_simulation_false(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["machine"]["simulation_only"] = False
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_bad_contract_ids(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["safety_contracts"][0]["if"] = "eval(user_code())"
    with pytest.raises(IRValidationError):
        validate_ir(bad)
    bad = copy.deepcopy(amr_ir_dict)
    bad["safety_contracts"][0]["then"] = "launch_missiles"
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_out_of_range_limits(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["control"]["max_linear_speed_mps"] = 99.0
    with pytest.raises(IRValidationError):
        validate_ir(bad)
    bad = copy.deepcopy(amr_ir_dict)
    bad["control"]["period_ms"] = 0
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_duplicate_ids(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["actuators"].append({"id": "left-motor", "type": "velocity_command"})
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_rejects_unknown_scenario(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["verification"]["scenarios"].append("do_anything")
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_guard_limits_use_strictest_freshness(amr_ir):
    limits = guard_limits(amr_ir)
    assert limits["freshness_limit_ms"] == 100
    assert limits["max_linear_speed_mps"] == 1.2
    assert limits["period_ms"] == 10
