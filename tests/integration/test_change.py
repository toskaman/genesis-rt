# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: K1 one-click BEFORE/AFTER change proof (verify-change).

Covers the thin orchestrator (host/genesis_rt/change.py) and the CLI
subcommand: golden verdict for the cell broken->fixed pair (mirrors the
Demo C expectations in docs/jury/DEMO_WALKTHROUGH.md), verdict.json
persistence, failure-leg behavior with manual-command fallback, and
change-id validation.
"""
import json

import pytest

from genesis_rt.change import (ChangeLegError, render_card_text, valid_change_id,
                               verify_change)
from genesis_rt.cli import main


def _cell_pair(repo_root):
    cell = repo_root / "examples" / "cell-demo"
    return cell / "cell-ir-broken.json", cell / "cell-ir.json"


def test_verify_change_cell_broken_to_fixed_golden(repo_root, tmp_path):
    """Demo C as one call: knob table, fixed list, gate verdicts."""
    before_ir, after_ir = _cell_pair(repo_root)
    verdict = verify_change(before_ir, after_ir, tmp_path / "runs",
                            tmp_path / "change", change_id="chg-golden")
    assert verdict["change_id"] == "chg-golden"
    assert verdict["before"]["verdict"] == "FAIL"
    assert verdict["after"]["verdict"] == "PASS"
    assert verdict["verdict"] == "PASS"  # after-leg gate decides the banner
    assert verdict["compare"]["contract"]["limits_changed"] == {
        "max_linear_speed_mps": [0.3, 1.2]}
    assert verdict["compare"]["scenarios"]["fixed"] == [
        "cell_nominal_transfer", "cell_stale_presence", "cell_transfer_jam"]
    assert verdict["compare"]["scenarios"]["broken"] == []
    assert verdict["compare"]["verdict"]["changed"] is True
    assert verdict["chains_valid"] == {"before": True, "after": True}


def test_verify_change_writes_verdict_json(repo_root, tmp_path):
    before_ir, after_ir = _cell_pair(repo_root)
    verdict = verify_change(before_ir, after_ir, tmp_path / "runs",
                            tmp_path / "change", change_id="chg-persist")
    path = tmp_path / "change" / "chg-persist" / "verdict.json"
    assert path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["change_id"] == "chg-persist"
    assert stored["before"]["run_id"] == "chg-persist-before"
    assert stored["after"]["run_id"] == "chg-persist-after"
    assert verdict["verdict_path"] == str(path)
    for leg in ("before", "after"):
        assert stored[leg]["passport"].endswith("passport.json")
        assert "level" in stored[leg] and "release_eligible" in stored[leg]


def test_verify_change_card_text(repo_root, tmp_path):
    before_ir, after_ir = _cell_pair(repo_root)
    verdict = verify_change(before_ir, after_ir, tmp_path / "runs",
                            tmp_path / "change", change_id="chg-card")
    card = render_card_text(verdict)
    assert "max_linear_speed_mps: 0.3 -> 1.2" in card
    assert "cell_nominal_transfer" in card
    assert "verdict: PASS" in card
    assert "chains: before=valid after=valid" in card


def test_verify_change_bad_before_leg_fails_loudly(repo_root, tmp_path):
    """A leg that cannot run raises with the manual-command fallback."""
    _, after_ir = _cell_pair(repo_root)
    bogus = tmp_path / "not-an-ir.json"
    bogus.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(ChangeLegError) as exc:
        verify_change(bogus, after_ir, tmp_path / "runs",
                      tmp_path / "change", change_id="chg-badleg")
    assert "before" in str(exc.value)
    assert "genesis-rt demo --ir" in str(exc.value)
    assert "genesis-rt compare" in str(exc.value)
    assert not (tmp_path / "change" / "chg-badleg" / "verdict.json").exists()


def test_verify_change_rejects_bad_change_id(repo_root, tmp_path):
    before_ir, after_ir = _cell_pair(repo_root)
    assert valid_change_id("chg-ok_1") is True
    assert valid_change_id("../escape") is False
    with pytest.raises(ValueError, match="invalid change_id"):
        verify_change(before_ir, after_ir, tmp_path / "runs",
                      tmp_path / "change", change_id="../escape")


def test_cli_verify_change_golden(repo_root, tmp_path, capsys):
    before_ir, after_ir = _cell_pair(repo_root)
    rc = main(["verify-change", "--before", str(before_ir),
               "--after", str(after_ir),
               "--artifacts-dir", str(tmp_path / "runs"),
               "--id", "chg-cli"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "verdict: PASS" in out
    assert "max_linear_speed_mps: 0.3 -> 1.2" in out
    assert (tmp_path / "change" / "chg-cli" / "verdict.json").is_file()


def test_cli_verify_change_json_flag(repo_root, tmp_path, capsys):
    before_ir, after_ir = _cell_pair(repo_root)
    rc = main(["verify-change", "--before", str(before_ir),
               "--after", str(after_ir),
               "--artifacts-dir", str(tmp_path / "runs"),
               "--id", "chg-clijson", "--json"])
    assert rc == 0
    body = json.loads(capsys.readouterr().out)
    assert body["change_id"] == "chg-clijson"
    assert body["verdict"] == "PASS"


def test_cli_verify_change_bad_leg_exit2(repo_root, tmp_path, capsys):
    _, after_ir = _cell_pair(repo_root)
    rc = main(["verify-change", "--before", str(tmp_path / "missing.json"),
               "--after", str(after_ir),
               "--artifacts-dir", str(tmp_path / "runs")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ChangeLegError" in err
    assert "genesis-rt demo --ir" in err
