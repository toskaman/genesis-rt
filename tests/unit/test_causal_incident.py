# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: causal incident intake (schema + fail-closed validation)."""

import json

import pytest

from genesis_rt.incident import (
    IncidentError,
    incident_digest,
    load_incident,
    validate_incident,
)


def _good() -> dict:
    return {
        "schema_version": "incident/1",
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


def test_valid_incident_loads(tmp_path):
    p = tmp_path / "inc.json"
    p.write_text(json.dumps(_good()), encoding="utf-8")
    assert validate_incident(load_incident(p)) == []


def test_missing_observed_rejected():
    bad = _good()
    bad.pop("observed")
    assert validate_incident(bad)


def test_load_rejects_bad_json_with_incident_error(tmp_path):
    p = tmp_path / "inc.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(IncidentError):
        load_incident(p)


def test_unknown_observed_kind_rejected_fail_closed():
    bad = _good()
    bad["observed"] = [{"kind": "telepathy", "detail": "x",
                        "source": "y"}]
    errs = validate_incident(bad)
    assert errs and any("telepathy" in e for e in errs)


def test_bad_incident_id_rejected():
    bad = _good()
    bad["incident_id"] = "../escape"
    assert validate_incident(bad)


def test_digest_stable_and_canonical(tmp_path):
    p = tmp_path / "inc.json"
    p.write_text(json.dumps(_good()), encoding="utf-8")
    d1 = incident_digest(load_incident(p))
    p.write_text(json.dumps(_good(), indent=2, sort_keys=True),
                 encoding="utf-8")
    assert incident_digest(load_incident(p)) == d1
    assert len(d1) == 64


def test_incident_marker_not_ir_version():
    # ci_ir_check keys on schema_version in (1, 2): a colliding
    # incident marker would fail CI IR validation (PR #19 lesson).
    from genesis_rt.incident import INCIDENT_SCHEMA_VERSION
    assert INCIDENT_SCHEMA_VERSION not in (1, 2)
    assert isinstance(INCIDENT_SCHEMA_VERSION, str)
