# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: provider-independent planning interface + published eval set."""
import copy
import json

import pytest

from genesis_rt.planner import PlannerRejection
from genesis_rt.planning import OfflineProvider, plan_machine


def _eval_cases(repo_root):
    path = repo_root / "evals" / "planning_eval.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def test_published_eval_offline_scores_100(repo_root):
    """The deterministic provider must satisfy every published case."""
    passed, total = 0, 0
    failures = []
    for case in _eval_cases(repo_root):
        total += 1
        try:
            if "expect" in case:
                ir = plan_machine(case["request"],
                                  machine_id=f"eval-{case['id']}")
                exp = case["expect"]
                assert ir["machine"]["kind"] == exp["kind"], case["id"]
                assert ir["control"]["period_ms"] == exp["period_ms"], case["id"]
                assert ir["control"]["max_linear_speed_mps"] == pytest.approx(
                    exp["max_linear_speed_mps"]), case["id"]
            else:
                with pytest.raises(PlannerRejection) as ei:
                    plan_machine(case["request"])
                assert case["match"] in str(ei.value).lower(), case["id"]
            passed += 1
        except (AssertionError, PlannerRejection) as exc:
            failures.append((case["id"], str(exc)[:160]))
    assert failures == [], f"{passed}/{total} passed: {failures}"
    assert total >= 15 and passed == total


def test_unknown_provider_lists_available():
    with pytest.raises(PlannerRejection, match="available.*offline"):
        plan_machine("a robot", provider="gpt-99")


def test_explicit_provider_instance_accepted():
    ir = plan_machine("a conveyor", provider=OfflineProvider())
    assert ir["machine"]["kind"] == "conveyor"


class _GarbageProvider:
    name = "garbage"

    def propose_raw(self, request, machine_id):
        return "not-an-ir"


class _InvalidProvider:
    name = "invalid"

    def propose_raw(self, request, machine_id):
        return {"schema_version": 1, "zzz_unknown": True}


class _BoomProvider:
    name = "boom"

    def propose_raw(self, request, machine_id):
        raise RuntimeError("model exploded")


def test_non_object_proposal_rejected():
    with pytest.raises(PlannerRejection, match="non-object"):
        plan_machine("a robot", provider=_GarbageProvider())


def test_invalid_proposal_rejected_by_gate():
    with pytest.raises(PlannerRejection, match="IR validation"):
        plan_machine("a robot", provider=_InvalidProvider())


def test_provider_crash_wrapped():
    with pytest.raises(PlannerRejection, match="provider 'boom' failed"):
        plan_machine("a robot", provider=_BoomProvider())


def test_unsafe_scan_runs_before_provider_call():
    calls = []

    class _Spy:
        name = "spy"

        def propose_raw(self, request, machine_id):
            calls.append(request)
            return copy.deepcopy(OfflineProvider().propose_raw(
                "a robot", machine_id))

    with pytest.raises(PlannerRejection, match="unsafe or unsupported"):
        plan_machine("robot with the guard disabled", provider=_Spy())
    assert calls == []


def test_offline_rejections_pass_through_unchanged():
    with pytest.raises(PlannerRejection, match="unknown machine kind"):
        plan_machine("toaster that makes breakfast")
