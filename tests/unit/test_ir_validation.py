# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: strict Machine IR validation."""
import copy
import json

import pytest

from genesis_rt.ir import (IRValidationError, SCENARIO_IDS, guard_limits,
                           load_ir_file, validate_ir)


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


def test_schema_scenario_enum_matches_registry(repo_root):
    """The published v1 schema must accept every registered scenario id:
    adding a scenario without updating the schema breaks the contract."""
    schema = json.loads((repo_root / "schemas" / "machine-ir-v1.schema.json"
                         ).read_text(encoding="utf-8"))
    enum = schema["properties"]["verification"]["properties"][
        "scenarios"]["items"]["enum"]
    assert set(enum) == set(SCENARIO_IDS), (
        set(SCENARIO_IDS) ^ set(enum))


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


def _mutate(amr_ir_dict, path, value):
    bad = copy.deepcopy(amr_ir_dict)
    node = bad
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return bad


@pytest.mark.parametrize("path,value", [
    (["schema_version"], True),
    (["schema_version"], 1.0),
    (["schema_version"], "1"),
    (["control", "period_ms"], True),
    (["control", "max_linear_speed_mps"], True),
    (["control", "max_angular_speed_radps"], False),
    (["sensors", 0, "freshness_limit_ms"], True),
    (["control", "max_linear_speed_mps"], float("nan")),
    (["control", "max_linear_speed_mps"], float("inf")),
])
def test_rejects_bool_and_non_numeric_limits(amr_ir_dict, path, value):
    """True==1 must not smuggle bools past strict numeric validation."""
    with pytest.raises(IRValidationError):
        validate_ir(_mutate(amr_ir_dict, path, value))


def _cell_doc(repo_root):
    return json.loads((repo_root / "examples" / "cell-demo" / "cell-ir.json"
                       ).read_text(encoding="utf-8"))


def test_cell_example_valid(repo_root):
    c = load_ir_file(repo_root / "examples" / "cell-demo" / "cell-ir.json")
    assert c["machine"]["kind"] == "industrial_cell"
    assert c["cell"]["presence_sensor"] == "station-presence"
    assert "cell_nominal_transfer" in c["verification"]["scenarios"]


def test_cell_block_required_for_cell_kind(repo_root):
    bad = _cell_doc(repo_root)
    del bad["cell"]
    with pytest.raises(IRValidationError):
        validate_ir(bad)


def test_cell_block_forbidden_for_other_kinds(amr_ir_dict):
    bad = copy.deepcopy(amr_ir_dict)
    bad["cell"] = {"station_x_m": 6.0, "transfer_ticks": 50,
                   "presence_sensor": "x", "amr_actuator": "y",
                   "belt_actuator": "z"}
    with pytest.raises(IRValidationError):
        validate_ir(bad)


@pytest.mark.parametrize("path,value", [
    (["cell", "station_x_m"], 0.0),
    (["cell", "station_x_m"], 13.0),
    (["cell", "station_x_m"], True),
    (["cell", "station_x_m"], float("nan")),
    (["cell", "transfer_ticks"], 0),
    (["cell", "transfer_ticks"], 601),
    (["cell", "transfer_ticks"], True),
    (["cell", "presence_sensor"], "amr-odometry"),  # wrong sensor type
    (["cell", "presence_sensor"], "no-such-sensor"),
    (["cell", "amr_actuator"], "belt-drive"),  # wrong actuator type
    (["cell", "belt_actuator"], "amr-drive"),  # wrong actuator type
    (["cell", "belt_actuator"], "no-such-actuator"),
])
def test_cell_block_rejects_bad_values(repo_root, path, value):
    with pytest.raises(IRValidationError):
        validate_ir(_mutate(_cell_doc(repo_root), path, value))
