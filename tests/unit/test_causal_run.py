# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: causal run — plans, outcome mapping, seal/verify (pure)."""

import copy
from pathlib import Path

import pytest

from genesis_rt.causal import rank_hypotheses
from genesis_rt.causal_run import (
    DOSSIER_VERSION,
    outcome_status,
    plan_experiments,
    seal_dossier,
    verify_dossier,
)


def _estop_incident() -> dict:
    return {
        "schema_version": "incident/1",
        "incident_id": "inc-estop-01",
        "title": "cell halts mid-transfer, status ESTOP",
        "machine_ir": "examples/cell-demo/cell-ir.json",
        "observed": [
            {"kind": "symptom", "detail": "transfer halted",
             "source": "operator report"},
        ],
    }


def _bare_dossier() -> dict:
    return {
        "dossier_version": DOSSIER_VERSION,
        "incident": {"incident_id": "inc-estop-01",
                     "digest": "abc123"},
        "hypotheses": [{"id": "H-estop", "verdict": "SUPPORTED"}],
        "experiments": [],
        "causality": {"winning_hypothesis": "H-estop"},
    }


def test_plan_orders_by_rank_with_kind_scenarios():
    plans = plan_experiments(rank_hypotheses(_estop_incident()),
                             "industrial_cell")
    assert [p["order"] for p in plans] == list(range(1, len(plans) + 1))
    assert plans[0]["hypothesis_id"] == "H-estop"
    assert plans[0]["scenario"] == "cell_estop_during_transfer"


def test_plan_stalebin_has_no_scenario_manifest_kind():
    plans = plan_experiments(rank_hypotheses(_estop_incident()),
                             "industrial_cell")
    stalebin = [p for p in plans
                if p["hypothesis_id"] == "H-stalebin"][0]
    assert stalebin["scenario"] is None
    assert stalebin["experiment_kind"] == "manifest"


def test_outcome_fail_reproduces():
    assert outcome_status("fail") == "fail"


def test_outcome_pass_refutes():
    assert outcome_status("pass") == "pass"


def test_outcome_crash_is_unsupported_not_support():
    # Kind-mismatch crashes must never read as reproduced failures.
    assert outcome_status("crash") == "unsupported"


def test_outcome_unknown_fails_closed_to_missing():
    assert outcome_status("bogus") == "missing"
    assert outcome_status(None) == "missing"


def test_seal_verify_roundtrip_valid(tmp_path):
    d = seal_dossier(_bare_dossier())
    assert verify_dossier(d)["valid"] is True
    p = tmp_path / "dossier.json"
    import json
    p.write_text(json.dumps(d), encoding="utf-8")
    assert verify_dossier(p)["valid"] is True


def test_seal_over_seal_refused():
    with pytest.raises(ValueError):
        seal_dossier(seal_dossier(_bare_dossier()))


def test_tampered_verdict_invalidates():
    d = seal_dossier(_bare_dossier())
    tampered = copy.deepcopy(d)
    tampered["hypotheses"][0]["verdict"] = "REFUTED"
    result = verify_dossier(tampered)
    assert result["valid"] is False
    assert result["errors"]


class _FakeRunner:
    """Scripted TargetRunner double (no QEMU): states served in order."""

    def __init__(self, states, artifacts=None):
        self._states = list(states)
        self._n = 0
        self.cancelled = []
        self.started = []
        self._artifacts = artifacts or {}

    def start(self, workflow, params):
        self.started.append((workflow, params))
        return {"op_id": "op-fake", "state": "PENDING"}

    def get(self, op_id):
        idx = min(self._n, len(self._states) - 1)
        self._n += 1
        return {"op_id": op_id, "state": self._states[idx],
                "artifacts": dict(self._artifacts)}

    def cancel(self, op_id):
        self.cancelled.append(op_id)
        return {"op_id": op_id, "state": "CANCELLED"}


def _live_dossier(tmp_path, repo_root, runner, only=("H-stalebin",), **kw):
    import json as _json
    from genesis_rt.causal_run import reproduce
    inc = tmp_path / "inc.json"
    inc.write_text(_json.dumps(_estop_incident()), encoding="utf-8")
    ir = (repo_root / "examples" / "cell-demo" / "cell-ir.json")
    return reproduce(inc, tmp_path / "runs", tmp_path / "dossiers",
                     target="live", machine_ir=ir,
                     only=list(only) if only is not None else None,
                     runner_factory=lambda: runner, **kw)


def _fake_target_dir(tmp_path, checks):
    """A target dir shaped like qnx_target.py output (record + logs)."""
    import json as _json
    tdir = tmp_path / "op-target"
    tdir.mkdir()
    rec = {"checks": [{"name": n, "passed": ok, "detail": "d"}
                      for n, ok in checks.items()],
           "verified_on_target": True}
    (tdir / "qnx-target-record.json").write_text(_json.dumps(rec),
                                                 encoding="utf-8")
    for name in checks:
        (tdir / f"target-{name}.log").write_text(
            f"native transcript for {name}\n", encoding="utf-8")
    return tdir


def test_live_completed_without_record_is_not_grounded(tmp_path, repo_root):
    """T10: a COMPLETED op with no target record no longer reads as
    grounded (the old slice reported bare 'completed')."""
    dossier = _live_dossier(tmp_path, repo_root,
                            _FakeRunner(["PENDING", "COMPLETED"]))
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["mode"] == "live"
    assert ground["status"] == "no-record"
    assert ground["op_id"] == "op-fake"
    assert "check_passed" not in ground


def test_live_present_when_check_passed_with_transcript(tmp_path, repo_root):
    from genesis_rt.causal_run import verify_dossier
    tdir = _fake_target_dir(tmp_path, {"v2_transitions": True,
                                       "estop_target": True})
    runner = _FakeRunner(["COMPLETED"], {"target_dir": str(tdir),
                                         "qnx_verified": True,
                                         "verdict": "PASS"})
    dossier = _live_dossier(tmp_path, repo_root, runner)
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["status"] == "present"
    assert ground["check_passed"] is True
    assert ground["native_check"] == "v2_transitions"
    assert len(ground["transcript_sha256"]) == 64
    assert dossier["native_op"]["qnx_verified"] is True
    assert "_record" not in dossier["native_op"]
    assert verify_dossier(Path(dossier["dossier_path"]) /
                          "dossier.json")["valid"] is True


def test_live_check_failed_is_reported(tmp_path, repo_root):
    tdir = _fake_target_dir(tmp_path, {"v2_transitions": False})
    runner = _FakeRunner(["COMPLETED"], {"target_dir": str(tdir)})
    ground = _live_dossier(tmp_path, repo_root,
                           runner)["experiments"][0]["native_grounding"]
    assert ground["status"] == "check-failed"
    assert ground["check_passed"] is False


def test_live_check_absent_from_matrix(tmp_path, repo_root):
    tdir = _fake_target_dir(tmp_path, {"estop_target": True})
    runner = _FakeRunner(["COMPLETED"], {"target_dir": str(tdir)})
    ground = _live_dossier(tmp_path, repo_root,
                           runner)["experiments"][0]["native_grounding"]
    assert ground["status"] == "absent"


def test_live_one_hermetic_op_for_all_hypotheses(tmp_path, repo_root):
    """One QEMU boot per incident, 'full' workflow (generate+build+stage
    this incident's own binaries), the incident IR passed as params."""
    import json as _json
    tdir = _fake_target_dir(tmp_path, {"estop_target": True,
                                       "v2_transitions": True,
                                       "controller_crash": True,
                                       "guard_crash": True,
                                       "limits_differ": True,
                                       "status_live": True})
    runner = _FakeRunner(["COMPLETED"], {"target_dir": str(tdir)})
    dossier = _live_dossier(tmp_path, repo_root, runner, only=None,
                            live_params={"image_dir": str(tmp_path)})
    assert len(runner.started) == 1
    workflow, params = runner.started[0]
    assert workflow == "full"
    ir = _json.loads((repo_root / "examples" / "cell-demo"
                      / "cell-ir.json").read_text(encoding="utf-8"))
    assert params["ir"] == ir
    assert params["image_dir"] == str(tmp_path)
    assert len(dossier["experiments"]) > 1


def test_live_tampered_transcript_fails_verify(tmp_path, repo_root):
    from genesis_rt.causal_run import verify_dossier
    tdir = _fake_target_dir(tmp_path, {"v2_transitions": True})
    runner = _FakeRunner(["COMPLETED"], {"target_dir": str(tdir)})
    dossier = _live_dossier(tmp_path, repo_root, runner)
    (tdir / "target-v2_transitions.log").write_text("forged\n",
                                                    encoding="utf-8")
    result = verify_dossier(Path(dossier["dossier_path"]) / "dossier.json")
    assert result["valid"] is False
    assert any("transcript hash mismatch" in e for e in result["errors"])


def test_live_failed_op_honest(tmp_path, repo_root):
    dossier = _live_dossier(tmp_path, repo_root,
                            _FakeRunner(["FAILED"]))
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["status"] == "op-failed"
    assert ground["state"] == "FAILED"


def test_live_timeout_cancels_and_reports(tmp_path, repo_root):
    runner = _FakeRunner(["RUNNING"])
    dossier = _live_dossier(tmp_path, repo_root, runner,
                            live_timeout_s=0.01)
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["status"] == "timeout"
    assert runner.cancelled == ["op-fake"]


def test_live_start_failure_reported(tmp_path, repo_root):
    class _Broken(_FakeRunner):
        def start(self, workflow, params):
            raise RuntimeError("no ssh")

    dossier = _live_dossier(tmp_path, repo_root, _Broken(["PENDING"]))
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["status"] == "start-failed"
    assert "no ssh" in ground["error"]
