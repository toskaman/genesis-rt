# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: deterministic codegen (byte-identical, hash-linked)."""
from genesis_rt import codegen
from genesis_rt.ir import canonical_json


def test_generate_deterministic_bytes(amr_ir, tmp_path):
    m1 = codegen.generate(amr_ir, tmp_path / "a")
    m2 = codegen.generate(amr_ir, tmp_path / "b")
    assert m1 == m2
    for name in m1["files"]:
        a = (tmp_path / "a" / name).read_bytes()
        b = (tmp_path / "b" / name).read_bytes()
        assert a == b and len(a) > 0


def test_generated_header_records_provenance(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path)
    header = (tmp_path / "genesis_config_gen.h").read_text(encoding="utf-8")
    assert manifest["ir_sha256"] in header
    assert codegen.TEMPLATE_VERSION in header
    assert "amr-demo-01" in header
    assert "1.2" in header  # max linear speed from IR
    assert "100" in header  # freshness limit from IR


def test_different_ir_different_hash(amr_ir, tmp_path):
    import copy
    m1 = codegen.generate(amr_ir, tmp_path / "a")
    other = copy.deepcopy(amr_ir)
    other["control"]["max_linear_speed_mps"] = 0.8
    m2 = codegen.generate(other, tmp_path / "b")
    assert m1["ir_sha256"] != m2["ir_sha256"]
    assert m1["files"] != m2["files"]


def test_makefile_covers_all_include_dirs(amr_ir, tmp_path):
    codegen.generate(amr_ir, tmp_path)
    mk = (tmp_path / "genesis_build_gen.mk").read_text(encoding="utf-8")
    # qcc flags must find genesis_ipc.h (include/) and guard_policy.h (common/)
    assert "-I$(GENESIS_SRC)/include" in mk
    assert "-I$(GENESIS_SRC)/common" in mk
    assert mk.count("-I$(GENESIS_SRC)/common") >= 2  # qnx flags + host target


def test_no_timestamps_in_output(amr_ir, tmp_path):
    import datetime
    codegen.generate(amr_ir, tmp_path)
    blob = "".join(p.read_text(encoding="utf-8") for p in tmp_path.iterdir())
    year = str(datetime.datetime.now().year)
    assert year not in blob  # would break byte determinism
    assert canonical_json(amr_ir)  # canonical form exists for hashing


def test_manifest_records_full_provenance(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path, genesis_src="/opt/src")
    assert manifest["genesis_src"] == "/opt/src"
    assert set(manifest["templates"]) == {
        "genesis_config_gen.h.tmpl", "genesis_build_gen.mk.tmpl"}
    for digest in manifest["templates"].values():
        assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    other = codegen.generate(amr_ir, tmp_path / "b", genesis_src="/other/src")
    assert other["genesis_src"] != manifest["genesis_src"]
    assert other["files"] != manifest["files"]  # bytes differ, manifest must say so


def test_genesis_src_injection_rejected(amr_ir, tmp_path):
    import pytest
    for evil in ("a\nMALICIOUS: all\n\trm -rf /", "a\rb", "a\x00b", "", "a\x7fb",
                 "$(shell touch pwned)", "${GENESIS_SRC}", "$$HOME",
                 "a#b", "a;b", "a b", "a`b`", "a&b", "a|b", "a>b",
                 "a'b", 'a"b', "a*b", "a?b", "a(b)", "a[b]", "a{b}",
                 "a=b", "a!b", "a%b", "a@b", "a^b", "a~b",
                 "caf\xc3\xa9"):
        with pytest.raises(ValueError):
            codegen.generate(amr_ir, tmp_path / "evil", genesis_src=evil)


def test_cell_generates_policy_header(cell_ir, tmp_path):
    manifest = codegen.generate(cell_ir, tmp_path / "cell")
    assert "genesis_cell_policy.h" in manifest["files"]
    header = (tmp_path / "cell" / "genesis_cell_policy.h"
              ).read_text(encoding="utf-8")
    assert manifest["ir_sha256"] in header
    assert "GENESIS_CELL_STATION_X_M 6.0" in header
    assert "GENESIS_CELL_TRANSFER_TICKS 50" in header
    assert 'GENESIS_CELL_PRESENCE_ID "station-presence"' in header
    assert 'GENESIS_CELL_AMR_ACTUATOR "amr-drive"' in header
    assert 'GENESIS_CELL_BELT_ACTUATOR "belt-drive"' in header
    assert "genesis_cell_transfer_allowed" in header


def test_cell_makefile_compiles_cellcheck(cell_ir, tmp_path):
    codegen.generate(cell_ir, tmp_path / "cell")
    mk = (tmp_path / "cell" / "genesis_build_gen.mk"
          ).read_text(encoding="utf-8")
    assert "-o genesis_cellcheck $(GENESIS_SRC)/cell/genesis_cellcheck.c" in mk


def test_non_cell_build_has_no_cell_artifacts(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path / "amr")
    assert "genesis_cell_policy.h" not in manifest["files"]
    mk = (tmp_path / "amr" / "genesis_build_gen.mk"
          ).read_text(encoding="utf-8")
    assert "genesis_cellcheck" not in mk
    assert "cell_station" not in mk


def test_cell_generation_deterministic_bytes(cell_ir, tmp_path):
    m1 = codegen.generate(cell_ir, tmp_path / "a")
    m2 = codegen.generate(cell_ir, tmp_path / "b")
    assert m1 == m2
    for name in m1["files"]:
        assert (tmp_path / "a" / name).read_bytes() == (
            tmp_path / "b" / name).read_bytes()


def test_cell_policy_follows_ir(cell_ir, tmp_path):
    import copy
    other = copy.deepcopy(cell_ir)
    other["cell"]["station_x_m"] = 4.0
    other["cell"]["transfer_ticks"] = 25
    codegen.generate(cell_ir, tmp_path / "a")
    codegen.generate(other, tmp_path / "b")
    ha = (tmp_path / "a" / "genesis_cell_policy.h").read_text()
    hb = (tmp_path / "b" / "genesis_cell_policy.h").read_text()
    assert "GENESIS_CELL_STATION_X_M 4.0" in hb
    assert "GENESIS_CELL_TRANSFER_TICKS 25" in hb
    assert ha != hb
