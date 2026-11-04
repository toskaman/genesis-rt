# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX target test: generated v2 machine module builds natively with qcc.

Runs ONLY with a real SDK; otherwise an explicit skip (never a pass).
Asserts status ok AND zero warnings, and that the v2 makefile links the
machine module into genesis_guard.
"""
import pytest

from genesis_rt import codegen_v2
from genesis_rt.build_adapter import build_qnx, probe
from genesis_rt.ir_v2 import load_ir_v2_file


@pytest.fixture()
def qnx_env():
    env = probe()
    if not env["sdk_present"]:
        pytest.skip("QNX SDP 8.0 SDK not installed (honest skip, not a pass)")
    return env


@pytest.mark.parametrize("example", ["amr-demo", "conveyor-demo"])
def test_qnx_native_build_v2(qnx_env, repo_root, tmp_path, example):
    del qnx_env
    v2 = load_ir_v2_file(
        repo_root / "examples" / example / "machine-ir-v2.json")
    src = str((repo_root / "target" / "qnx8").as_posix())
    gen = tmp_path / "gen"
    codegen_v2.generate_v2(v2, gen, genesis_src=src)
    mk = (gen / "genesis_build_gen.mk").read_text(encoding="utf-8")
    assert "./genesis_machine_gen.c" in mk
    record = build_qnx(gen)
    assert record["status"] == "ok", record
    assert record["verified_on_target"] is False  # compile-only here
    output = (record.get("stdout", "") + record.get("stderr", "")).lower()
    assert "warning" not in output, output
