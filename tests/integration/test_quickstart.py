# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: W2 quickstart (validate -> run -> card, one command)."""
import json

import pytest

from genesis_rt.cli import main


def test_quickstart_cell_passes(tmp_path, capsys):
    rc = main(["quickstart", "--runs-dir", str(tmp_path / "runs")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "valid:" in out
    assert "PASS" in out
    assert "passport:" in out
    assert "verify-change" in out  # next step printed


def test_quickstart_example_choice(tmp_path, capsys):
    rc = main(["quickstart", "--example", "conveyor",
               "--runs-dir", str(tmp_path / "runs")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in out


def test_quickstart_runs_dir_isolated(tmp_path):
    runs = tmp_path / "runs"
    rc = main(["quickstart", "--runs-dir", str(runs)])
    assert rc == 0
    assert sorted(p.name for p in runs.iterdir()) != []
    assert list((runs / sorted(p.name for p in runs.iterdir())[0]
                 ).glob("passport.json")) != []


def test_quickstart_unknown_example_exits_2():
    with pytest.raises(SystemExit) as exc:
        main(["quickstart", "--example", "nope"])
    assert exc.value.code == 2


def test_quickstart_invalid_ir_exits_2(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": true}', encoding="utf-8")
    rc = main(["quickstart", "--ir", str(bad)])
    assert rc == 2
    assert "invalid" in capsys.readouterr().out.lower()


def test_quickstart_json(tmp_path, capsys):
    rc = main(["quickstart", "--json",
               "--runs-dir", str(tmp_path / "runs")])
    out = capsys.readouterr().out
    assert rc == 0
    body = json.loads(out)
    assert body["verdict"] == "PASS"
    assert "passport" in body
