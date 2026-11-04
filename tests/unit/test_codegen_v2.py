# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: v2 machine-specific C generation (snapshot + differentiation)."""
import copy
import json

import pytest

from genesis_rt.codegen_v2 import c_ident, generate_v2
from genesis_rt.ir import canonical_json
from genesis_rt.ir_v2 import load_ir_v2_file, validate_v2

SNAP_DIR = "tests/snapshots/codegen_v2"


@pytest.fixture()
def amr_v2(repo_root):
    return load_ir_v2_file(repo_root / "examples" / "amr-demo" / "machine-ir-v2.json")


@pytest.fixture()
def conv_v2(repo_root):
    return load_ir_v2_file(repo_root / "examples" / "conveyor-demo" / "machine-ir-v2.json")


def _gen_files(v2, tmp_path):
    generate_v2(v2, tmp_path)
    return {p.name: (tmp_path / p.name).read_text(encoding="utf-8")
            for p in tmp_path.iterdir()}


def test_deterministic_across_dirs(amr_v2, tmp_path):
    a = _gen_files(amr_v2, tmp_path / "a")
    b = _gen_files(copy.deepcopy(amr_v2), tmp_path / "b")
    assert set(a) == {"genesis_machine_gen.h", "genesis_machine_gen.c",
                      "genesis_config_gen.h", "genesis_build_gen.mk"}
    assert a == b


def test_snapshot_amr(amr_v2, repo_root, tmp_path):
    files = _gen_files(amr_v2, tmp_path)
    for name in ("genesis_machine_gen.h", "genesis_machine_gen.c"):
        expected = (repo_root / SNAP_DIR / "amr" / name).read_text(encoding="utf-8")
        assert files[name] == expected, name


def test_snapshot_conveyor(conv_v2, repo_root, tmp_path):
    files = _gen_files(conv_v2, tmp_path)
    for name in ("genesis_machine_gen.h", "genesis_machine_gen.c"):
        expected = (repo_root / SNAP_DIR / "conv" / name).read_text(encoding="utf-8")
        assert files[name] == expected, name


def test_machines_differ_structurally(amr_v2, conv_v2, tmp_path):
    a = _gen_files(amr_v2, tmp_path / "a")["genesis_machine_gen.c"]
    b = _gen_files(conv_v2, tmp_path / "b")["genesis_machine_gen.c"]
    assert a != b
    # AMR-specific content
    assert "GENESIS_M_CMD_LEFT_MOTOR_CMD" in a
    assert "GENESIS_M_CMD_RIGHT_MOTOR_CMD" in a
    assert "*min_out = -1.2; *max_out = 1.2;" in a
    assert "GENESIS_M_SENS_PROXIMITY" in a
    # conveyor-specific content
    assert "GENESIS_M_CMD_BELT_CMD" in b
    assert "*min_out = -2.0; *max_out = 2.0;" in b
    assert "GENESIS_M_SENS_ESTOP" in b
    # structural difference: 2 command cases vs 1
    assert a.count("case GENESIS_M_CMD_") == 4  # count + bounds switches
    assert b.count("case GENESIS_M_CMD_") == 2
    # cross-absence: neither machine leaks the other's actuators
    assert "LEFT_MOTOR" not in b and "BELT_CMD" not in a


def test_manifest_provenance(amr_v2, tmp_path):
    import hashlib
    manifest = generate_v2(amr_v2, tmp_path)
    assert manifest["schema_version"] == 2
    assert manifest["machine_template_version"] == "2.1"
    assert set(manifest["templates"]) == {
        "genesis_config_gen.h.tmpl", "genesis_build_gen.mk.tmpl",
        "genesis_machine_gen.h.tmpl", "genesis_machine_gen.c.tmpl"}
    assert manifest["ir_sha256"] == hashlib.sha256(
        canonical_json(amr_v2).encode("utf-8")).hexdigest()
    for name, digest in manifest["files"].items():
        content = (tmp_path / name).read_text(encoding="utf-8")
        assert hashlib.sha256(content.encode("utf-8")).hexdigest() == digest


def test_c_ident_collision_fails_loud(amr_v2, tmp_path):
    bad = copy.deepcopy(amr_v2)
    bad["states"] = [
        {"id": "a-b", "safe": False, "initial": True},
        {"id": "a_b", "safe": True, "initial": False},
    ]
    bad["transitions"] = []
    for a in bad["actuators"]:
        a["fault_response"] = "a_b"
    for f in bad["fault_responses"]:
        f["enter_state"] = "a_b"
    validate_v2(bad)  # distinct v2 ids: the IR itself is legal
    with pytest.raises(ValueError, match="C-identifier collision"):
        generate_v2(bad, tmp_path)


def test_v2_makefile_links_machine_module(amr_v2, tmp_path):
    from genesis_rt import codegen as codegen_v1
    generate_v2(amr_v2, tmp_path / "v2")
    mk = (tmp_path / "v2" / "genesis_build_gen.mk").read_text(encoding="utf-8")
    assert "./genesis_machine_gen.c" in mk
    guard_rule = mk.split("./genesis_machine_gen.c")[0].splitlines()[-1]
    assert "genesis_guard" in guard_rule
    # the v2 tail of guard_policy.c compiles only under this flag, and
    # only the guard rule carries it (all other rules keep the v1 tail)
    assert "-DGENESIS_MACHINE_V2" in guard_rule
    flagged = [ln for ln in mk.splitlines()
               if ln.startswith("\t") and "-DGENESIS_MACHINE_V2" in ln]
    assert len(flagged) == 1


def test_v1_makefile_untouched(amr_ir, tmp_path):
    from genesis_rt import codegen as codegen_v1
    codegen_v1.generate(amr_ir, tmp_path)
    mk = (tmp_path / "genesis_build_gen.mk").read_text(encoding="utf-8")
    assert "genesis_machine_gen.c" not in mk
    assert "GENESIS_MACHINE_V2" not in mk


def test_c_ident_shape():
    assert c_ident("left-motor", "CMD") == "GENESIS_M_CMD_LEFT_MOTOR"
    assert c_ident("a_b", "STATE") == "GENESIS_M_STATE_A_B"


def test_rejects_unvalidated_input(tmp_path):
    with pytest.raises(Exception):
        generate_v2({"schema_version": 2}, tmp_path)


def _wire_map_of(v2, tmp_path):
    generate_v2(v2, tmp_path)
    return (tmp_path / "genesis_machine_gen.c").read_text(encoding="utf-8")


def test_wire_map_emitted(amr_v2, tmp_path):
    src = _wire_map_of(amr_v2, tmp_path)
    assert "genesis_machine_wire_of" in src
    # AMR: init -> wire 0, running -> wire 1, safe_stop -> wire 3
    assert "case GENESIS_M_STATE_INIT: return 0;" in src
    assert "case GENESIS_M_STATE_RUNNING: return 1;" in src
    assert "case GENESIS_M_STATE_SAFE_STOP: return 3;" in src


def test_wire_map_rejects_unmappable_states(amr_v2, tmp_path):
    bad = copy.deepcopy(amr_v2)
    bad["states"] = [
        {"id": "init", "safe": False, "initial": True},
        {"id": "mid1", "safe": False, "initial": False},
        {"id": "mid2", "safe": False, "initial": False},
        {"id": "mid3", "safe": False, "initial": False},
        {"id": "safe_stop", "safe": True, "initial": False},
    ]
    bad["transitions"] = []
    validate_v2(bad)  # the IR itself is legal: 3 middle states exist
    with pytest.raises(ValueError, match="wire"):
        generate_v2(bad, tmp_path)


def test_has_fault_macros_emitted(amr_v2, conv_v2, tmp_path):
    generate_v2(amr_v2, tmp_path / "a")
    ahead = (tmp_path / "a" / "genesis_machine_gen.h").read_text(encoding="utf-8")
    assert "#define GENESIS_M_HAS_FAULT_STALE_SENSOR 1" in ahead
    assert "#define GENESIS_M_HAS_FAULT_COMMAND_REJECTED 1" in ahead
    assert "#define GENESIS_M_HAS_FAULT_SIMULATOR_DISCONNECT 1" in ahead
    assert "#define GENESIS_M_HAS_ACTION_COMMAND_VIRTUAL_STOP 1" in ahead
    assert "#define GENESIS_M_HAS_ACTION_REJECT_COMMAND 1" in ahead
    generate_v2(conv_v2, tmp_path / "b")
    bhead = (tmp_path / "b" / "genesis_machine_gen.h").read_text(encoding="utf-8")
    # conveyor declares no stale_sensor: no macro, so the shared guard
    # source keeps compiling and falls back to the hardcoded latch
    assert "GENESIS_M_HAS_FAULT_STALE_SENSOR" not in bhead
    assert "#define GENESIS_M_HAS_FAULT_COMMAND_REJECTED 1" in bhead
