# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""TDD red: causal-repro / causal-fix CLI plumbing + exit codes."""

import json
from pathlib import Path

from genesis_rt.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INCIDENT = (REPO_ROOT / "incidents"
            / "estop-cell-transfer.json")
CELL_IR = REPO_ROOT / "examples" / "cell-demo" / "cell-ir.json"


def _dirs(tmp_path):
    return ["--runs-dir", str(tmp_path / "runs"),
            "--dossiers-dir", str(tmp_path / "dossiers")]


def test_repro_conclusive_exits_zero(tmp_path, capsys):
    rc = main(["causal-repro", "--incident", str(INCIDENT),
               *_dirs(tmp_path), "--hypotheses", "H-estop",
               "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["causality"]["winning_hypothesis"] == "H-estop"


def test_repro_inconclusive_exits_one(tmp_path, capsys):
    rc = main(["causal-repro", "--incident", str(INCIDENT),
               *_dirs(tmp_path), "--hypotheses", "H-jam"])
    assert rc == 1


def test_repro_rejects_unknown_target(tmp_path):
    import pytest
    with pytest.raises(SystemExit) as exc:
        main(["causal-repro", "--incident", str(INCIDENT),
              *_dirs(tmp_path), "--target", "cloud"])
    assert exc.value.code == 2


def test_fix_mirrors_k1_verdict(tmp_path, capsys):
    assert main(["causal-repro", "--incident", str(INCIDENT),
                 *_dirs(tmp_path), "--hypotheses", "H-estop"]) == 0
    dossier = tmp_path / "dossiers" / "inc-estop-cell-01"
    capsys.readouterr()
    rc = main(["causal-fix", "--dossier", str(dossier),
               "--after-ir", str(CELL_IR),
               "--runs-dir", str(tmp_path / "runs"),
               "--changes-dir", str(tmp_path / "change"), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == (0 if out["fix"]["verdict"] == "PASS" else 1)
    assert out["fix"]["change_id"].startswith("inc-estop-cell-01-fix")
