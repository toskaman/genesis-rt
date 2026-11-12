# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""T10: why the native oracle may predict industrial_cell guard verdicts.

The oracle predicts probe verdicts from the shared guard speed rule.
That is only sound for a kind whose generated guard IS that rule. These
tests pin the structural facts the extension relies on, so a future
codegen change that gives the cell its own guard semantics turns this
red instead of silently keeping a now-vacuous prediction:

1. no QNX target source branches on the machine kind;
2. the cell config header differs from the AMR one only in the
   machine id / IR digest and numeric limit constants;
3. the cell makefile builds the same guard sources (plus cellcheck).
"""
import json
import re

from genesis_rt import codegen, native_oracle
from genesis_rt.ir import load_ir_file

_ALLOWED_DIFF_KEYS = {"GENESIS_MACHINE_ID", "GENESIS_PERIOD_MS",
                      "GENESIS_MAX_LINEAR_MPS", "GENESIS_MAX_ANGULAR_RADPS",
                      "GENESIS_FRESHNESS_LIMIT_MS"}


def _defines(text):
    return dict(re.findall(r"^#define (\w+) (.+)$", text, re.M))


def _gen(repo_root, rel, tmp_path, name):
    ir = load_ir_file(repo_root / rel)
    out = tmp_path / name
    codegen.generate(ir, out)
    return out


def test_cell_is_supported_and_arm_is_not():
    assert "industrial_cell" in native_oracle.SUPPORTED_MACHINE_KINDS
    assert "robotic_arm_virtual" not in native_oracle.SUPPORTED_MACHINE_KINDS


def test_target_sources_never_branch_on_machine_kind(repo_root):
    srcs = list((repo_root / "target" / "qnx8").rglob("*.[ch]"))
    assert srcs
    for src in srcs:
        text = src.read_text(encoding="utf-8", errors="replace")
        assert "industrial_cell" not in text, src
        assert "MACHINE_KIND" not in text, src


def test_cell_config_differs_from_amr_only_in_constants(repo_root, tmp_path):
    amr = _gen(repo_root, "examples/amr-demo/machine-ir.json", tmp_path, "amr")
    cell = _gen(repo_root, "examples/cell-demo/cell-ir.json", tmp_path, "cell")
    a = _defines((amr / "genesis_config_gen.h").read_text(encoding="utf-8"))
    c = _defines((cell / "genesis_config_gen.h").read_text(encoding="utf-8"))
    assert set(a) == set(c)
    differing = {k for k in a if a[k] != c[k]}
    assert differing <= _ALLOWED_DIFF_KEYS
    assert c["GENESIS_PROTOCOL_MAGIC"] == a["GENESIS_PROTOCOL_MAGIC"]
    assert c["GENESIS_PROTOCOL_VERSION"] == a["GENESIS_PROTOCOL_VERSION"]


def test_cell_build_uses_the_shared_guard_sources(repo_root, tmp_path):
    amr = _gen(repo_root, "examples/amr-demo/machine-ir.json", tmp_path, "amr")
    cell = _gen(repo_root, "examples/cell-demo/cell-ir.json", tmp_path, "cell")

    def guard_rule(mk):
        lines = mk.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if "-o genesis_guard " in ln]

    a = guard_rule(amr / "genesis_build_gen.mk")
    c = guard_rule(cell / "genesis_build_gen.mk")
    assert a and a == c
    assert "guard_policy.c" in a[0]


def test_cell_limit_predictions_follow_the_contract(repo_root):
    ir = json.loads((repo_root / "examples" / "cell-demo" / "cell-ir.json")
                    .read_text(encoding="utf-8"))
    lim = codegen.guard_limits(ir)["max_linear_speed_mps"]
    plan = native_oracle.plan_probes(lim)
    got = [(v, native_oracle.expect_linear_probe(
        machine_kind="industrial_cell", limit_mps=lim, probe_mps=v).decision)
        for v in plan]
    # 1.2 m/s cell: below ALLOW; at-limit DENY (float32 wire > 1.2);
    # reference 1.5 and above DENY. Matches the live QNX transcript of
    # op-c0da134ead07 (T10) probe-for-probe.
    assert got == [(0.6, "ALLOW"), (1.2, "DENY"), (1.5, "DENY"),
                   (1.7, "DENY")]
