# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: deterministic hypothesis ranking + elimination (no LLM)."""

from genesis_rt.causal import (
    HYPOTHESES,
    rank_hypotheses,
    scenario_for,
    verdict_for,
)


def _estop_incident() -> dict:
    return {
        "schema_version": 1,
        "incident_id": "inc-estop-01",
        "title": "cell halts mid-transfer, status ESTOP",
        "machine_ir": "examples/cell-demo/cell-ir.json",
        "observed": [
            {"kind": "symptom", "detail": "transfer halted",
             "source": "operator report"},
            {"kind": "transcript_ref",
             "detail": "target-estop_target.log:3 DENY ESTOP state=3",
             "source": "omega2-before pack"},
        ],
    }


def test_hypothesis_table_bounded_with_falsifiers():
    assert 4 <= len(HYPOTHESES) <= 8
    for h in HYPOTHESES:
        assert h["falsifier"] and h["signals"] and h["mechanism"]


def test_estop_incident_ranks_estop_first():
    ranked = rank_hypotheses(_estop_incident())
    assert ranked[0]["id"] == "H-estop"
    assert "estop" in ranked[0]["matched_signals"]
    assert ranked[0]["rank"] == 1


def test_ranking_deterministic_tiebreak_by_table_order():
    assert ([h["id"] for h in rank_hypotheses(_estop_incident())]
            == [h["id"] for h in rank_hypotheses(_estop_incident())])


def test_cell_kind_selects_cell_scenario():
    assert scenario_for("H-estop", "industrial_cell") == \
        "cell_estop_during_transfer"


def test_base_kind_selects_base_scenario():
    assert scenario_for("H-estop", "differential_drive_robot") == \
        "estop_pressed"


def test_cell_crash_has_no_host_scenario():
    # No cell crash-injection scenario exists: host cannot test it.
    assert scenario_for("H-crash", "industrial_cell") is None
    assert scenario_for("H-seq", "industrial_cell") is None


def test_pass_matching_signature_supports():
    assert verdict_for("H-estop", {"status": "pass"},
                       _estop_incident()) == "SUPPORTED"


def test_pass_other_signature_inconclusive():
    assert verdict_for("H-jam", {"status": "pass"},
                       _estop_incident()) == "INCONCLUSIVE"


def test_fail_matching_signature_inconclusive():
    # Testbed contradicts the field observation: investigate, don't claim.
    assert verdict_for("H-estop", {"status": "fail"},
                       _estop_incident()) == "INCONCLUSIVE"


def test_fail_other_signature_refutes():
    assert verdict_for("H-jam", {"status": "fail"},
                       _estop_incident()) == "REFUTED"


def test_unsupported_experiment_not_testable():
    assert verdict_for("H-jam", {"status": "unsupported"},
                       _estop_incident()) == "NOT_TESTABLE"


def test_missing_experiment_inconclusive():
    assert verdict_for("H-estop", {"status": "missing"},
                       _estop_incident()) == "INCONCLUSIVE"
    assert verdict_for("H-estop", None, _estop_incident()) == \
        "INCONCLUSIVE"


def test_no_incident_text_fails_closed():
    assert verdict_for("H-estop", {"status": "pass"}) == \
        "INCONCLUSIVE"
    assert verdict_for("H-estop", {"status": "fail"}) == "INCONCLUSIVE"
