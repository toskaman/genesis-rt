# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: provenance primitives (cksum, distribution, matrix pin)."""
import importlib.util
import shutil
import subprocess

import pytest

from genesis_rt import provenance


def test_cksum_empty_stream_is_all_ones():
    # Universal POSIX vector: no input folds nothing, complement of zero.
    assert provenance.cksum_posix(b"") == (4294967295, 0)


def test_cksum_pinned_vector():
    # Observed from the reference `cksum` binary (QNX host tools):
    #   printf 'GENESIS-RT-provenance-v1' | cksum  ->  3104056534 24
    assert provenance.cksum_posix(b"GENESIS-RT-provenance-v1") == (3104056534, 24)


def test_cksum_single_byte_changes_everything():
    a, sa = provenance.cksum_posix(b"A")
    b, sb = provenance.cksum_posix(b"B")
    assert sa == sb == 1
    assert a != b


def test_cksum_matches_reference_binary_when_present(repo_root):
    ref = shutil.which("cksum")
    if ref is None:
        pytest.skip("no reference cksum binary on PATH")
    blob = (repo_root / "README.md").read_bytes()
    mine, size = provenance.cksum_posix(blob)
    out = subprocess.run([ref, str(repo_root / "README.md")],
                         capture_output=True, check=True, timeout=60)
    want_ck, want_size, _name = out.stdout.decode().split()
    assert (mine, size) == (int(want_ck), int(want_size))


def test_expected_matrix_matches_target_script(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_sync", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    live = [name for name, _ in mod.TARGET_MATRIX]
    assert live == list(provenance.EXPECTED_TARGET_CHECKS)


def test_perf_distribution_matches_legacy_shape():
    d = provenance.perf_distribution([float(i) for i in range(1, 101)])
    assert d["count"] == 100
    assert d["unit"] == "microseconds"
    assert (d["min"], d["max"]) == (1.0, 100.0)
    assert d["p50"] == 50.0  # nearest-rank, no interpolation


def test_ir_binding_matches_pipeline_manifest(amr_ir_path, tmp_path,
                                              repo_root):
    # Regression: verify --ir digested the raw file while the pipeline
    # digests the validated IR — every bound run failed closed as stale.
    # Both must use the pipeline loader.
    from genesis_rt import codegen
    from genesis_rt.ir import load_ir_file
    spec = importlib.util.spec_from_file_location(
        "qnx_target_bind", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ir = load_ir_file(amr_ir_path)
    binding = mod._ir_binding(str(amr_ir_path))
    manifest = codegen.generate(ir, tmp_path / "gen-bind")
    assert binding["ir_sha256"] == manifest["ir_sha256"]
    assert binding["machine_id"] == ir["machine"]["id"]
    assert provenance.perf_distribution([5.0])["p99"] == 5.0


def test_ir_binding_v2_matches_v2_manifest(tmp_path, repo_root):
    # Native 8-Nov finding: verify --ir used the v1 loader only, so a
    # v2 IR failed closed as "unknown top-level keys" and no v2 op
    # could attest. v2 binding must digest the v2 manifest form.
    from genesis_rt import codegen_v2
    from genesis_rt.ir_v2 import load_ir_v2_file
    spec = importlib.util.spec_from_file_location(
        "qnx_target_bind_v2", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    v2_path = repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
    ir = load_ir_v2_file(str(v2_path))
    binding = mod._ir_binding(str(v2_path))
    manifest = codegen_v2.generate_v2(ir, tmp_path / "gen-bind-v2")
    assert binding["ir_sha256"] == manifest["ir_sha256"]
    assert binding["machine_id"] == ir["machine"]["id"]
    assert binding["linear_limit_mps"] == float(
        ir["control"]["max_linear_speed_mps"])


def test_ir_binding_carries_schema_version(tmp_path, repo_root):
    # The estop/v2transitions parsers branch on the bound schema: v2
    # reset goes through the declared safe_stop->init transition and
    # v2 ops stage two v2 guards (SAME_BIN), unlike v1 (DIFF_BIN).
    spec = importlib.util.spec_from_file_location(
        "qnx_target_bind_ver", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    v1 = mod._ir_binding(str(repo_root / "examples" / "amr-demo"
                             / "machine-ir.json"))
    v2 = mod._ir_binding(str(repo_root / "examples" / "amr-demo"
                             / "machine-ir-v2.json"))
    assert v1["schema_version"] == 1
    assert v2["schema_version"] == 2
