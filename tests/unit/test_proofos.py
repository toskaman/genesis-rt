# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 12 §6: ProofOS verification-plan schema, derivation and stages."""
from __future__ import annotations

import pytest

from genesis_rt.proofos import (EXPECTED_TARGET_CHECKS, advance, build_plan,
                                validate_plan)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _change(path="examples/amr-demo/machine-ir.json", status="changed",
            valid=True, before=DIGEST_A, after=DIGEST_B):
    return {"path": path, "status": status, "valid": valid,
            "renamed_from": None, "ir_sha256_before": before,
            "ir_sha256_after": after, "limits_changed": True,
            "requirements_changed": 1, "retest": ["nominal_navigation"]}


def test_invalid_change_yields_invalid_stage():
    plan = build_plan(source_commit="s", base_commit="b",
                      changes=[_change(valid=False)])
    assert plan["stage"] == "INVALID"
    assert plan["release_status"]["eligible"] is False
    assert any("invalid IR" in r
               for r in plan["release_status"]["reasons"])
    assert validate_plan(plan) == []


def test_changed_ir_requires_full_native_matrix():
    plan = build_plan(source_commit="s", base_commit="b",
                      changes=[_change()])
    assert plan["stage"] == "IMPACT_ANALYZED"
    assert [c["name"] for c in plan["required_native_checks"]] == \
        list(EXPECTED_TARGET_CHECKS)
    assert plan["target_requirements"]["needed"] is True
    assert plan["target_requirements"]["platform"]
    assert plan["required_host_tests"][0] == "tests/ (full host suite)"
    assert any("nominal_navigation" in t
               for t in plan["required_host_tests"][1:])
    assert plan["release_status"]["eligible"] is False


def test_unchanged_ir_needs_no_native_run():
    entry = _change(status="unchanged", before=DIGEST_A, after=DIGEST_A)
    entry["retest"] = []
    plan = build_plan(source_commit="s", base_commit="b", changes=[entry])
    assert plan["required_native_checks"] == []
    assert plan["target_requirements"]["needed"] is False
    assert plan["release_status"]["eligible"] is False


def test_plan_id_deterministic_and_sensitive():
    a = build_plan(source_commit="s", base_commit="b",
                   changes=[_change()])
    b = build_plan(source_commit="s", base_commit="b",
                   changes=[_change()])
    assert a["plan_id"] == b["plan_id"]
    c = build_plan(source_commit="s", base_commit="b",
                   changes=[_change(after="c" * 64)])
    assert c["plan_id"] != a["plan_id"]


def test_validate_plan_rejects_bad_shapes():
    good = build_plan(source_commit="s", base_commit="b",
                      changes=[_change()])
    assert validate_plan("nope") != []
    bad = dict(good, plan_version=99)
    assert validate_plan(bad) != []
    bad = dict(good, plan_id="zzz")
    assert validate_plan(bad) != []
    bad = dict(good, stage="NOPE")
    assert validate_plan(bad) != []
    bad = dict(good, release_status={"eligible": True, "reasons": []})
    assert validate_plan(bad) != []
    bad_change = dict(good["changes"][0], ir_sha256_after="zzz")
    bad = dict(good, changes=[bad_change])
    assert validate_plan(bad) != []


def test_advance_happy_path_and_terminal_guard():
    plan = build_plan(source_commit="s", base_commit="b",
                      changes=[_change()])
    assert plan["stage"] == "IMPACT_ANALYZED"
    plan = advance(plan, "HOST_VERIFIED", note="suite green")
    plan = advance(plan, "NATIVE_PENDING")
    plan = advance(plan, "TARGET_VERIFIED")
    plan = advance(plan, "EVIDENCE_SEALED")
    assert plan["stage"] == "EVIDENCE_SEALED"
    assert len(plan["stage_history"]) == 5
    with pytest.raises(ValueError):
        advance(plan, "REVIEW_READY")  # needs the release pipeline
    with pytest.raises(ValueError):
        advance(plan, "CHANGE_DETECTED")  # illegal jump back


def test_advance_terminal_and_blocked_recovery():
    bad = build_plan(source_commit="s", base_commit="b",
                     changes=[_change(valid=False)])
    with pytest.raises(ValueError):
        advance(bad, "IMPACT_ANALYZED")
    plan = build_plan(source_commit="s", base_commit="b",
                      changes=[_change()])
    plan = advance(plan, "BLOCKED", note="target busy")
    plan = advance(plan, "IMPACT_ANALYZED", note="target back")
    assert plan["stage"] == "IMPACT_ANALYZED"
