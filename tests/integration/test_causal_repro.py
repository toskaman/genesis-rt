# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: causal reproduce + fix over real pipelines (integration)."""

import json
from pathlib import Path

from genesis_rt.causal_run import reproduce, verify_dossier, verify_fix


def _paths(repo_root: Path, tmp_path: Path):
    incident = (repo_root / "incidents"
                / "estop-cell-transfer.json")
    return (incident, tmp_path / "runs", tmp_path / "dossiers",
            tmp_path / "change")


def test_reproduce_estop_supports_winner(repo_root, tmp_path):
    incident, runs, dossiers, _change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers,
                        only=["H-estop", "H-jam"])
    assert dossier["causality"]["winning_hypothesis"] == "H-estop"
    by_id = {h["id"]: h for h in dossier["hypotheses"]}
    assert by_id["H-estop"]["verdict"] == "SUPPORTED"
    # Jam mechanism healthy but signature differs from the incident.
    assert by_id["H-jam"]["verdict"] == "INCONCLUSIVE"
    exp = dossier["experiments"][0]
    assert Path(exp["passport"]).exists()
    assert verify_dossier(dossier)["valid"] is True


def test_reproduce_records_archived_native_grounding(repo_root,
                                                     tmp_path):
    incident, runs, dossiers, _change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers, only=["H-estop"])
    ground = dossier["experiments"][0]["native_grounding"]
    assert ground["mode"] == "archived"
    assert ground["status"] == "present"
    assert len(ground["transcript_sha256"]) == 64


def test_reproduce_seals_dossier_dir(repo_root, tmp_path):
    incident, runs, dossiers, _change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers, only=["H-estop"])
    dpath = Path(dossier["dossier_path"])
    assert (dpath / "dossier.json").exists()
    assert verify_dossier(dpath / "dossier.json")["valid"] is True


def test_verify_fix_appends_k1_proof_and_reseals(repo_root, tmp_path):
    incident, runs, dossiers, change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers, only=["H-estop"])
    dpath = Path(dossier["dossier_path"])
    old_seal = dossier["seal"]
    after_ir = repo_root / "examples" / "cell-demo" / "cell-ir.json"
    fixed = verify_fix(dpath, after_ir, runs, change)
    assert fixed["fix"]["change_id"].startswith("inc-estop-cell-01")
    assert Path(fixed["fix"]["verdict_path"]).exists()
    assert fixed["seal"] != old_seal
    assert fixed["supersedes"] == old_seal
    assert verify_dossier(fixed)["valid"] is True


def test_dossier_self_contained_before_ir(repo_root, tmp_path):
    incident, runs, dossiers, _change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers, only=["H-estop"])
    dpath = Path(dossier["dossier_path"])
    assert Path(dossier["machine"]["ir"]) == dpath / "before-ir.json"
    (dpath / "before-ir.json").unlink()
    assert verify_dossier(dossier)["valid"] is False


def test_verify_fix_refuses_tampered_dossier(repo_root, tmp_path):
    incident, runs, dossiers, change = _paths(repo_root, tmp_path)
    dossier = reproduce(incident, runs, dossiers, only=["H-estop"])
    dpath = Path(dossier["dossier_path"])
    raw = json.loads((dpath / "dossier.json").read_text(encoding="utf-8"))
    raw["hypotheses"][0]["verdict"] = "REFUTED"
    (dpath / "dossier.json").write_text(json.dumps(raw), encoding="utf-8")
    after_ir = repo_root / "examples" / "cell-demo" / "cell-ir.json"
    import pytest
    from genesis_rt.causal_run import DossierError
    with pytest.raises(DossierError):
        verify_fix(dpath, after_ir, runs, change)
