# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: Machine IR v2 validation, v1 migration, CLI dispatch."""
import copy
import json

import pytest

from genesis_rt import ir_v2
from genesis_rt.cli import main
from genesis_rt.ir import (
    IF_IDS as V1_IF_IDS,
    IRValidationError,
    load_ir_file,
)
from genesis_rt.ir_v2 import (
    MIGRATED_ORIGIN,
    V1_IF_FAULT_MAP,
    canonical_json,
    load_ir_v2_file,
    migrate_v1_to_v2,
    validate_v2,
)


@pytest.fixture()
def amr_v2_path(repo_root):
    return repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"


@pytest.fixture()
def amr_v2_dict(amr_v2_path):
    return json.loads(amr_v2_path.read_text(encoding="utf-8"))


@pytest.fixture()
def conveyor_v2_path(repo_root):
    return repo_root / "examples" / "conveyor-demo" / "machine-ir-v2.json"


def _mutate(base, fn):
    doc = copy.deepcopy(base)
    fn(doc)
    return doc


def test_valid_amr_v2(amr_v2_dict):
    out = validate_v2(amr_v2_dict)
    assert out["machine"]["id"] == "amr-demo-01"
    assert len(out["fault_responses"]) == 3


def test_valid_conveyor_v2(conveyor_v2_path):
    out = load_ir_v2_file(conveyor_v2_path)
    assert out["machine"]["kind"] == "conveyor"


def test_canonical_stable(amr_v2_dict):
    assert canonical_json(amr_v2_dict) == canonical_json(
        json.loads(json.dumps(amr_v2_dict))
    )


# --- rejection matrix: each mutation must raise IRValidationError ---

def _set_version(doc):
    doc["schema_version"] = 1


def _unknown_top(doc):
    doc["zzz"] = 1


def _drop_top(doc):
    del doc["simulation"]


def _bad_kind(doc):
    doc["machine"]["kind"] = "starship"


def _bad_target(doc):
    doc["machine"]["execution_target"] = "linux_x86_64_sim"


def _bad_arch(doc):
    doc["machine"]["arch"] = "aarch64"


def _bad_machine_id(doc):
    doc["machine"]["id"] = "AMR!"


def _empty_actuators(doc):
    doc["actuators"] = []


def _dup_actuator(doc):
    doc["actuators"].append(copy.deepcopy(doc["actuators"][0]))


def _overlap_ids(doc):
    doc["sensors"][0]["id"] = doc["actuators"][0]["id"]


def _bad_unit(doc):
    doc["actuators"][0]["unit"] = "rad"


def _bad_bounds(doc):
    doc["actuators"][0]["bounds"] = {"min": 1.0, "max": -1.0}


def _bad_rate(doc):
    doc["actuators"][0]["rate_limit"] = 0.0


def _bad_fresh(doc):
    doc["sensors"][0]["freshness_limit_ms"] = 0


def _bad_range(doc):
    doc["sensors"][0]["range"] = {"min": 5.0, "max": 5.0}


def _bad_fault_ref(doc):
    doc["actuators"][0]["fault_response"] = "running"


def _unknown_fault_ref(doc):
    doc["actuators"][0]["fault_response"] = "nope"


def _bad_period(doc):
    doc["control"]["period_ms"] = 0


def _bad_deadline(doc):
    doc["control"]["deadline_ms"] = -1


def _bad_speed(doc):
    doc["control"]["max_linear_speed_mps"] = 0


def _bad_policy(doc):
    doc["control"]["scheduling"]["policy"] = "round-robin"


def _bad_prio(doc):
    doc["control"]["scheduling"]["priority"] = 256


def _unguarded(doc):
    doc["control"]["guarded_state_transitions"] = False


def _two_initial(doc):
    doc["states"][1]["initial"] = True


def _no_safe(doc):
    for s in doc["states"]:
        s["safe"] = False


def _bad_transition_state(doc):
    doc["transitions"][0]["to"] = "nowhere"


def _self_transition(doc):
    doc["transitions"][0]["to"] = doc["transitions"][0]["from"]


def _bad_event(doc):
    doc["transitions"][0]["event"] = "explode"


def _dup_transition(doc):
    doc["transitions"].append(copy.deepcopy(doc["transitions"][0]))


def _bad_command_act(doc):
    doc["commands"][0]["actuator"] = "ghost"


def _bad_command_dl(doc):
    doc["commands"][0]["deadline_ms"] = 0


def _empty_fields(doc):
    doc["commands"][0]["fields"] = []


def _bad_field_unit(doc):
    doc["commands"][0]["fields"][0]["unit"] = "furlong"


def _bad_field_bounds(doc):
    doc["commands"][0]["fields"][0]["min"] = 9.0
    doc["commands"][0]["fields"][0]["max"] = -9.0


def _bad_tm_source(doc):
    doc["telemetry"][0]["source"] = "ghost"


def _dup_tm_id(doc):
    doc["telemetry"][0]["id"] = doc["commands"][0]["id"]


def _bad_tm_rate(doc):
    doc["telemetry"][0]["rate_hz"] = 0


def _empty_contracts(doc):
    doc["safety_contracts"] = []


def _bad_if(doc):
    doc["safety_contracts"][0]["if"] = "vibes_bad"


def _bad_then(doc):
    doc["safety_contracts"][0]["then"] = "panic"


def _empty_faults(doc):
    doc["fault_responses"] = []


def _bad_fault(doc):
    doc["fault_responses"][0]["fault"] = "gremlins"


def _nonsafe_enter(doc):
    doc["fault_responses"][0]["enter_state"] = "running"


def _unknown_enter(doc):
    doc["fault_responses"][0]["enter_state"] = "nowhere"


def _bad_scenario(doc):
    doc["verification"]["scenarios"][0] = "moon_landing"


def _bad_req_scenario(doc):
    doc["verification"]["requirements"][0]["scenario"] = "moon_landing"


def _long_claim(doc):
    doc["verification"]["requirements"][0]["claim"] = "x" * 257


def _bad_dt(doc):
    doc["simulation"]["dt_ms"] = 0


def _bad_duration(doc):
    doc["simulation"]["duration_ms"] = 700000


def _bad_seed(doc):
    doc["simulation"]["seed"] = -1


def _sim_not_only(doc):
    doc["machine"]["simulation_only"] = False


def _policy_beyond_capability(doc):
    # control policy allows 9.9 m/s but the mps actuators cap at 1.2
    doc["control"]["max_linear_speed_mps"] = 9.9


def _field_beyond_actuator(doc):
    doc["commands"][0]["fields"][0]["max"] = 9.9


def _field_unit_mismatch(doc):
    doc["commands"][0]["fields"][0]["unit"] = "rad"


@pytest.mark.parametrize("fn", [
    _set_version, _unknown_top, _drop_top, _bad_kind, _bad_target, _bad_arch,
    _bad_machine_id, _empty_actuators, _dup_actuator, _overlap_ids, _bad_unit,
    _bad_bounds, _bad_rate, _bad_fresh, _bad_range, _bad_fault_ref,
    _unknown_fault_ref, _bad_period, _bad_deadline, _bad_speed, _bad_policy,
    _bad_prio, _unguarded, _two_initial, _no_safe, _bad_transition_state,
    _self_transition, _bad_event, _dup_transition, _bad_command_act,
    _bad_command_dl, _empty_fields, _bad_field_unit, _bad_field_bounds,
    _bad_tm_source, _dup_tm_id, _bad_tm_rate, _empty_contracts, _bad_if,
    _bad_then, _empty_faults, _bad_fault, _nonsafe_enter, _unknown_enter,
    _bad_scenario, _bad_req_scenario, _long_claim, _bad_dt, _bad_duration,
    _bad_seed, _sim_not_only, _policy_beyond_capability,
    _field_beyond_actuator, _field_unit_mismatch,
])
def test_rejections(amr_v2_dict, fn):
    with pytest.raises(IRValidationError):
        validate_v2(_mutate(amr_v2_dict, fn))


def test_non_object_rejected():
    with pytest.raises(IRValidationError):
        validate_v2([1, 2])


def test_load_v2_rejects_v1_file(amr_ir_path):
    with pytest.raises(IRValidationError):
        load_ir_v2_file(amr_ir_path)


# --- migration ---

def test_migrate_amr(amr_ir):
    v2 = migrate_v1_to_v2(amr_ir)
    assert v2["machine"]["id"] == "amr-demo-01"
    assert v2["machine"]["kind"] == "differential_drive_robot"


def test_migrate_conveyor(repo_root):
    v1 = load_ir_file(repo_root / "examples" / "conveyor-demo" / "machine-ir.json")
    v2 = migrate_v1_to_v2(v1)
    assert v2["machine"]["kind"] == "conveyor"
    assert v2["actuators"][0]["bounds"] == {"min": -2.0, "max": 2.0}


def test_migrate_deterministic(amr_ir):
    assert canonical_json(migrate_v1_to_v2(amr_ir)) == canonical_json(
        migrate_v1_to_v2(copy.deepcopy(amr_ir))
    )


def test_migrate_tags_origins(amr_ir):
    v2 = migrate_v1_to_v2(amr_ir)
    tagged_sections = ["actuators", "sensors", "states", "transitions",
                       "commands", "telemetry", "safety_contracts", "fault_responses"]
    for section in tagged_sections:
        assert v2[section], section
        for entry in v2[section]:
            assert entry["origin"] == MIGRATED_ORIGIN, (section, entry)


def test_migrate_bounds_mirror_guard(amr_ir):
    v2 = migrate_v1_to_v2(amr_ir)
    for act in v2["actuators"]:
        assert act["bounds"] == {"min": -1.2, "max": 1.2}


def test_migrate_fault_map_total():
    assert set(V1_IF_FAULT_MAP) == set(V1_IF_IDS)
    assert set(V1_IF_FAULT_MAP.values()) <= set(ir_v2.FAULT_IDS)


def test_migrate_copies_contract_vocabulary(amr_ir):
    v2 = migrate_v1_to_v2(amr_ir)
    for src, dst in zip(amr_ir["safety_contracts"], v2["safety_contracts"]):
        assert (dst["name"], dst["if"], dst["then"]) == (src["name"], src["if"], src["then"])
    for src, dst in zip(amr_ir["safety_contracts"], v2["fault_responses"]):
        assert dst["fault"] == V1_IF_FAULT_MAP[src["if"]]
        assert dst["action"] == src["then"]


# --- CLI dispatch ---

def test_cli_validate_v1(amr_ir_path, capsys):
    assert main(["validate", str(amr_ir_path)]) == 0
    assert "schema v1" in capsys.readouterr().out


def test_cli_validate_v2(amr_v2_path, capsys):
    assert main(["validate", str(amr_v2_path)]) == 0
    assert "schema v2" in capsys.readouterr().out


def test_cli_validate_broken_v2(amr_v2_dict, tmp_path):
    bad = _mutate(amr_v2_dict, _bad_event)
    p = tmp_path / "bad-v2.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert main(["validate", str(p)]) != 0


def test_cli_validate_unknown_version(tmp_path):
    p = tmp_path / "v9.json"
    p.write_text(json.dumps({"schema_version": 9}), encoding="utf-8")
    assert main(["validate", str(p)]) != 0
