# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: productivity benchmark schema + counts (never timings)."""
import json
import subprocess
import sys

import pytest

from genesis_rt.bench_productivity import (TASK_IDS, TASKS, BenchError,
                                           run_all, run_task)

QUICK = ["validate", "generate"]


def test_registry_complete():
    assert tuple(TASK_IDS) == ("validate", "generate", "campaign",
                               "evidence", "compare", "regression")
    assert set(TASKS) == set(TASK_IDS)
    assert all(callable(fn) for fn in TASKS.values())


def test_quick_run_schema(tmp_path):
    report = run_all(tmp_path / "run", QUICK, reproduce=True)
    assert report["bench_version"] == 1
    assert report["env"]["python"]
    assert [t["id"] for t in report["tasks"]] == QUICK
    for task in report["tasks"]:
        for lane in ("genesis", "ref"):
            side = task[lane]
            assert side["n_cmds"] == len(side["cmds"]) >= 1
            assert side["wall_s"] >= 0.0
            assert isinstance(side["artifacts"], list)
            assert isinstance(side["summary"], dict)
        assert isinstance(task["ref"]["manual_steps"], list)
        assert task["ref"]["manual_steps"], "reference must name manual work"
        assert isinstance(task["reproducible"], bool)
    assert (tmp_path / "run" / "REPORT.json").is_file()


def test_quick_counts_deterministic_and_honest(tmp_path):
    first = run_all(tmp_path / "a", QUICK, reproduce=True)
    second = run_all(tmp_path / "b", QUICK, reproduce=True)
    for task_a, task_b in zip(first["tasks"], second["tasks"]):
        assert task_a["genesis"]["n_cmds"] == task_b["genesis"]["n_cmds"]
        assert task_a["ref"]["n_cmds"] == task_b["ref"]["n_cmds"]
        assert (task_a["ref"]["manual_steps"]
                == task_b["ref"]["manual_steps"])
        assert task_a["fault"] == task_b["fault"]
    validate = first["tasks"][0]
    assert validate["genesis"]["n_cmds"] == 1
    assert validate["fault"] == {
        "case": "unknown top-level key 'turbo'",
        "genesis_detected": True, "ref_detected": False}
    generate = first["tasks"][1]
    assert generate["genesis"]["n_cmds"] == 1
    assert generate["genesis"]["summary"]["files"], "no artifacts recorded"
    assert generate["fault"]["genesis_detected"] is True
    assert generate["fault"]["ref_detected"] is False


def test_unknown_task_rejected(tmp_path):
    with pytest.raises(BenchError):
        run_task("spaceship", tmp_path)
    with pytest.raises(BenchError):
        run_all(tmp_path, ["validate", "spaceship"])


def _ref(name, *args):
    from genesis_rt.bench_productivity import REPO_ROOT
    script = REPO_ROOT / "scripts" / "bench_ref" / name
    assert script.is_file(), f"reference script missing: {name}"
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True)


def test_ref_checker_honest_limits(amr_ir_path, tmp_path):
    good = _ref("check_limits.py", str(amr_ir_path))
    assert good.returncode == 0, good.stderr
    bad_number = json.loads(amr_ir_path.read_text(encoding="utf-8"))
    bad_number["control"]["max_linear_speed_mps"] = "fast"
    p1 = tmp_path / "badnum.json"
    p1.write_text(json.dumps(bad_number), encoding="utf-8")
    assert _ref("check_limits.py", str(p1)).returncode == 1
    unknown = json.loads(amr_ir_path.read_text(encoding="utf-8"))
    unknown["turbo"] = True
    p2 = tmp_path / "unknown.json"
    p2.write_text(json.dumps(unknown), encoding="utf-8")
    assert _ref("check_limits.py", str(p2)).returncode == 0, \
        "naive checker must MISS unknown keys (documented drift)"


def test_ref_render_and_collect(amr_ir_path, tmp_path):
    out = tmp_path / "refgen"
    assert _ref("render_guard.py", str(amr_ir_path),
                "--out", str(out)).returncode == 0
    header = out / "guard_stunt.h"
    assert header.is_file() and "STUNT_MAX_V" in header.read_text(
        encoding="utf-8")
    log = tmp_path / "run.log"
    log.write_text("8/8 scenarios passed\n", encoding="utf-8")
    pkg = tmp_path / "pkg"
    proc = _ref("collect_package.py", str(log), "--out", str(pkg))
    assert proc.returncode == 0, proc.stderr
    assert "MISSING" in proc.stdout, "absent CHECKS.md must be reported"
    assert "NOT bound" in proc.stdout
    assert (pkg / "MANIFEST.sha256").is_file()


def test_cli_bench_quick(tmp_path, capsys):
    from genesis_rt.cli import main
    assert main(["bench", "--tasks", "validate",
                 "--out", str(tmp_path / "cli")]) == 0
    assert "validate" in capsys.readouterr().out
