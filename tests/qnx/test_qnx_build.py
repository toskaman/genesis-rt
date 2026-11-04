# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX target tests: run ONLY with a real SDK; otherwise explicit skip.

A skip here is never presented as QNX-tested: passports keep
qnx_verified=false and the gate reports the qnx_build record as
blocked. See docs/quickstart-qnx8-qemu.md for the SDK setup.
"""
import pytest

from genesis_rt.build_adapter import build_qnx, probe
from genesis_rt import codegen


@pytest.fixture()
def qnx_env():
    env = probe()
    if not env["sdk_present"]:
        pytest.skip("QNX SDP 8.0 SDK not installed (honest skip, not a pass)")
    return env


def test_qnx_native_build(qnx_env, amr_ir, tmp_path, repo_root):
    src = str((repo_root / "target" / "qnx8").as_posix())
    manifest = codegen.generate(amr_ir, tmp_path / "gen", genesis_src=src)
    assert manifest["files"]
    record = build_qnx(tmp_path / "gen")
    assert record["status"] == "ok", record
    assert record["verified_on_target"] is False  # compile-only here
