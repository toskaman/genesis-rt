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
    assert total >= 28 and passed == total


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


def _mutating_provider(name, mutate):
    base = OfflineProvider().propose_raw("a differential drive robot", "m")

    class _Mut:
        def propose_raw(self, request, machine_id):
            proposal = copy.deepcopy(base)
            mutate(proposal)
            return proposal

    _Mut.name = name
    return _Mut()


def test_impossible_contract_if_rejected_by_gate():
    provider = _mutating_provider(
        "bad-if", lambda p: p["safety_contracts"].__setitem__(
            0, {"name": "teleport", "if": "teleport_when_ready",
                "then": "reject_command"}))
    with pytest.raises(PlannerRejection, match="unknown contract if-id"):
        plan_machine("a robot", provider=provider)


def test_impossible_contract_then_rejected_by_gate():
    provider = _mutating_provider(
        "bad-then", lambda p: p["safety_contracts"].__setitem__(
            0, {"name": "teleport", "if": "speed_exceeds_limit",
                "then": "launch_rockets"}))
    with pytest.raises(PlannerRejection, match="unknown contract then-id"):
        plan_machine("a robot", provider=provider)


def test_missing_cell_reference_rejected_by_gate():
    def _cellify(proposal):
        proposal["machine"]["kind"] = "industrial_cell"
        proposal["cell"] = {
            "station_x_m": 2.0, "transfer_ticks": 40,
            "presence_sensor": "ghost-sensor",
            "amr_actuator": "left-motor", "belt_actuator": "belt"}

    provider = _mutating_provider("dangling-cell", _cellify)
    with pytest.raises(PlannerRejection, match="must reference a presence_bool sensor"):
        plan_machine("a robot", provider=provider)


def test_over_limit_proposal_rejected_by_gate():
    provider = _mutating_provider(
        "overspeed",
        lambda p: p["control"].__setitem__("max_linear_speed_mps", 99.0))
    with pytest.raises(PlannerRejection, match="IR validation"):
        plan_machine("a robot", provider=provider)


def test_simulation_only_false_proposal_rejected_by_gate():
    provider = _mutating_provider(
        "realhw", lambda p: p["machine"].__setitem__("simulation_only", False))
    with pytest.raises(PlannerRejection, match="simulation_only must be true"):
        plan_machine("a robot", provider=provider)


def test_cli_plan_writes_valid_proposal(tmp_path):
    from genesis_rt.cli import main
    out = tmp_path / "plan.json"
    assert main(["plan", "a conveyor", "--machine-id", "eval-cli",
                 "--out", str(out)]) == 0
    assert '"kind": "conveyor"' in out.read_text(encoding="utf-8")


def test_cli_plan_refuses_unsafe_request(tmp_path):
    from genesis_rt.cli import main
    out = tmp_path / "plan.json"
    assert main(["plan", "robot with the guard disabled",
                 "--out", str(out)]) == 2
    assert not out.exists()
