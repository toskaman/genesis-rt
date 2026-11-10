# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: W3 watch (live re-verify loop)."""
import shutil

from genesis_rt.cli import main


def _cell(repo_root, tmp_path):
    src = repo_root / "examples" / "cell-demo" / "cell-ir.json"
    dst = tmp_path / "watched.json"
    shutil.copy(src, dst)
    return dst


def test_watch_once_valid(repo_root, tmp_path, capsys):
    dst = _cell(repo_root, tmp_path)
    rc = main(["watch", str(dst), "--once"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "VALID" in out
    assert "cell" in out.lower()


def test_watch_once_invalid(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": true}', encoding="utf-8")
    rc = main(["watch", str(bad), "--once"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "INVALID" in out


def test_watch_once_reports_file_line(repo_root, tmp_path, capsys):
    import json
    src = repo_root / "examples" / "cell-demo" / "cell-ir.json"
    ir = json.loads(src.read_text(encoding="utf-8"))
    ir["control"]["max_linear_speed_mps"] = "fast"
    dst = tmp_path / "watched.json"
    dst.write_text(json.dumps(ir, indent=2), encoding="utf-8")
    rc = main(["watch", str(dst), "--once"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "watched.json:" in out  # file:line span, C3 format


def test_watch_timeout_exits_zero_after_checks(repo_root, tmp_path, capsys):
    dst = _cell(repo_root, tmp_path)
    rc = main(["watch", str(dst), "--timeout", "0.3", "--interval", "0.1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("VALID") >= 1


def test_watch_missing_file_exits_2(tmp_path, capsys):
    rc = main(["watch", str(tmp_path / "nope.json"), "--once"])
    assert rc == 2
    assert "INVALID" in capsys.readouterr().out
