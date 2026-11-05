# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration: §9 explorer C-conformance replay tier."""
import pytest

from genesis_rt import explorer
from genesis_rt.explorer_conformance import (
    replay_conformance,
    vector_line,
)
from genesis_rt.ir import guard_limits


def test_vector_line_shape(amr_ir_dict):
    out = explorer.run_script(
        amr_ir_dict,
        {"ticks": 5, "seed": 1, "faults": [], "commands": []})
    line = vector_line(out["vectors"][0])
    seq_line, vec = line.split("\n")
    assert seq_line == "SEQ 0"
    parts = vec.split()
    assert len(parts) == 14
    assert parts[0] == "47454E31"  # magic hex
    assert parts[6] == "0.5"  # nominal linear


def test_strict_finding_reproduced_by_c_guard(amr_ir_dict, repo_root):
    report = explorer.explore(
        amr_ir_dict, invariant="no_over_limit_allow",
        params={"max_allow_linear": 0.9}, strategies=["boundary"],
        budgets={"max_scripts": 200, "max_findings": 1}, seed=7)
    assert report["findings"], "need a finding to replay"
    rec = report["findings"][0]
    result = replay_conformance(rec, guard_limits(amr_ir_dict),
                                repo_root)
    if not result["supported"]:
        pytest.skip(result["reason"])
    assert result["tier"] == "c-conformance-reproduced", result
    assert result["matches"] == result["total"]


def test_conformance_reports_divergence_honestly(amr_ir_dict, repo_root):
    report = explorer.explore(
        amr_ir_dict, invariant="no_over_limit_allow",
        params={"max_allow_linear": 0.9}, strategies=["boundary"],
        budgets={"max_scripts": 200, "max_findings": 1}, seed=7)
    rec = report["findings"][0]
    tampered = dict(rec)
    tampered["vectors"] = [dict(v) for v in rec["vectors"]]
    tampered["vectors"][0] = dict(tampered["vectors"][0])
    tampered["vectors"][0]["decision"] = "DENY"
    result = replay_conformance(tampered, guard_limits(amr_ir_dict),
                                repo_root)
    if not result["supported"]:
        pytest.skip(result["reason"])
    assert result["tier"] == "c-divergent"
    assert result["first_divergence"]["tick"] == 0
