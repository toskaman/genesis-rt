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


def test_no_timestamps_in_output(amr_ir, tmp_path):
    import datetime
    codegen.generate(amr_ir, tmp_path)
    blob = "".join(p.read_text(encoding="utf-8") for p in tmp_path.iterdir())
    year = str(datetime.datetime.now().year)
    assert year not in blob  # would break byte determinism
    assert canonical_json(amr_ir)  # canonical form exists for hashing
