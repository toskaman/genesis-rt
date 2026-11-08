# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: full pipeline + planner + CLI surface."""
import subprocess
import sys

from genesis_rt import evidence, gate
from genesis_rt.orchestrator import run_pipeline
from genesis_rt.planner import PlannerRejection, propose


def test_pipeline_pass_host(amr_ir_path, tmp_path):
    from genesis_rt.build_adapter import probe
    summary = run_pipeline(amr_ir_path, tmp_path)
    assert summary["verdict"] == "PASS"
    assert summary["qnx_verified"] is False
    # A real build error must fail the test, never hide behind the PASS path.
    expected = "ok" if probe()["sdk_present"] else "blocked"
    actual = summary["steps"]["qnx_build"]["status"]
    assert actual == expected, summary["steps"]["qnx_build"].get("reason")
    passport = evidence.load_passport(summary["passport"])
    assert evidence.verify_chain(passport) == []
    assert summary["steps"]["host_cc_check"]["status"] in ("ok", "blocked")


def test_pipeline_all_scenarios_present(amr_ir, amr_ir_path, tmp_path):
    summary = run_pipeline(amr_ir_path, tmp_path)
    got = set(summary["steps"]["verification"]["scenarios"])
    assert got == set(amr_ir["verification"]["scenarios"])


def test_planner_accepts_robot_rejects_gibberish():
    ir = propose("differential drive robot, 10ms period, max 1.2 m/s")
    assert ir["machine"]["kind"] == "differential_drive_robot"
    assert ir["control"]["period_ms"] == 10
    try:
        propose("make me something cool")
    except PlannerRejection:
        pass
    else:
        raise AssertionError("planner must reject unbounded requests")


def test_cli_validate_and_faults(amr_ir_path, repo_root):
    repo = repo_root
    env = {"PYTHONPATH": str(repo / "host")}
    import os
    merged = dict(os.environ, **env)
    r = subprocess.run([sys.executable, "-m", "genesis_rt.cli", "validate", str(amr_ir_path)],
                       capture_output=True, text=True, timeout=60, env=merged)
    assert r.returncode == 0 and "valid:" in r.stdout
    r = subprocess.run([sys.executable, "-m", "genesis_rt.cli", "faults", str(amr_ir_path)],
                       capture_output=True, text=True, timeout=120, env=merged)
    assert r.returncode == 0 and "8/8 scenarios passed" in r.stdout


def test_cli_generate_src_points_at_target(amr_ir_path, repo_root, tmp_path):
    """`generate --out <anywhere>` must emit a GENESIS_SRC that resolves
    to this checkout's target/qnx8 (regression: one-level out dirs like
    the codelab's lab-build got a broken ../../ default)."""
    import os
    merged = dict(os.environ, PYTHONPATH=str(repo_root / "host"))
    for out in (tmp_path / "shallow", tmp_path / "deep" / "nested" / "dir"):
        r = subprocess.run(
            [sys.executable, "-m", "genesis_rt.cli", "generate",
             str(amr_ir_path), "--out", str(out)],
            capture_output=True, text=True, timeout=60, env=merged)
        assert r.returncode == 0, r.stderr
        (mk,) = [ln for ln in (out / "genesis_build_gen.mk"
                               ).read_text(encoding="utf-8").splitlines()
                 if ln.startswith("GENESIS_SRC")]
        src = mk.split("?=", 1)[1].strip()
        resolved = (out / src).resolve()
        assert (resolved / "guard" / "genesis_guard.c").is_file(), mk
        assert resolved == (repo_root / "target" / "qnx8").resolve()


def test_cli_generate_v2_produces_machine_module(repo_root, tmp_path):
    import os
    merged = dict(os.environ, PYTHONPATH=str(repo_root / "host"))
    out = tmp_path / "v2gen"
    r = subprocess.run(
        [sys.executable, "-m", "genesis_rt.cli", "generate",
         str(repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"),
         "--out", str(out)],
        capture_output=True, text=True, timeout=60, env=merged)
    assert r.returncode == 0, r.stderr
    assert (out / "genesis_machine_gen.c").exists()
    assert (out / "genesis_machine_gen.h").exists()
    mk = (out / "genesis_build_gen.mk").read_text(encoding="utf-8")
    assert "-DGENESIS_MACHINE_V2" in mk
    assert "schema v2" in r.stdout


def test_pipeline_pass_host_v2(repo_root, tmp_path):
    from genesis_rt.build_adapter import probe
    v2_path = repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
    summary = run_pipeline(v2_path, tmp_path)
    assert summary["verdict"] == "PASS"
    passport = evidence.load_passport(summary["passport"])
    assert evidence.verify_chain(passport) == []
    ir_record = next(e for e in passport["chain"] if e["kind"] == "ir")
    assert ir_record["body"]["schema_version"] == 2
    expected = "ok" if probe()["sdk_present"] else "blocked"
    assert summary["steps"]["qnx_build"]["status"] == expected


def test_gate_blocks_known_bad_revision(amr_ir, tmp_path):
    """Deliberately break a revision: gate must refuse release."""
    from genesis_rt import codegen, faultlab
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    results = faultlab.run_all(amr_ir)
    idx = next(i for i, r in enumerate(results) if r["scenario"] == "nominal_navigation")
    results[idx] = dict(results[idx], status="fail",
                        checks=[{"name": "sabotaged", "passed": False, "detail": "injected"}])
    passport = evidence.build_passport("run-bad", amr_ir, manifest, results,
                                       {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, amr_ir["verification"]["scenarios"])
    assert verdict["verdict"] == "FAIL"
    assert any("nominal_navigation=fail" in f for f in verdict["failed"])
