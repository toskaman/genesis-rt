# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""v2 guard decisions: the COMPILED C policy follows the generated machine.

Builds target/qnx8/common/guard_policy.c with -DGENESIS_MACHINE_V2 plus
the IR-generated genesis_machine_gen.c, then drives the shared
guard_vector harness. Vectors are derived FROM the v2 IR under test, so
a spec change that does not move a verdict fails loudly (spec A-H host
half; the target half runs the same verdicts through QNX IPC).

Skips only when no host C compiler exists (explicit skip, never a pass).
"""
import copy
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis_rt.codegen_v2 import generate_v2
from genesis_rt.ir_v2 import load_ir_v2_file, validate_v2

MAGIC = 0x47454E31

LIMITS = {
    "amr-demo": (1.2, 1.0, 100),
    "conveyor-demo": (2.0, 1.0, 50),
}


def _load(repo_root: Path, example: str):
    return load_ir_v2_file(
        repo_root / "examples" / example / "machine-ir-v2.json")


def _build(repo_root: Path, v2: dict, tmp_path: Path, tag: str) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no host C compiler available")
    gen = tmp_path / f"gen-{tag}"
    generate_v2(validate_v2(copy.deepcopy(v2)), gen)
    src = repo_root / "target" / "qnx8"
    out = tmp_path / (f"guard_v2_{tag}.exe" if cc.lower().endswith(".exe")
                      else f"guard_v2_{tag}")
    cmd = [cc, "-O1", "-Wall", "-Wextra", "-DGENESIS_MACHINE_V2",
           f"-I{gen}", f"-I{src / 'include'}", f"-I{src / 'common'}",
           "-o", str(out),
           str(src / "common" / "guard_policy.c"),
           str(gen / "genesis_machine_gen.c"),
           str(src / "host_tests" / "guard_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"C build failed:\n{proc.stderr}"
    assert "warning" not in proc.stderr.lower(), proc.stderr
    return out


def _decide(binary: Path, example: str, vectors: list[str],
            limits: tuple[float, float, int] | None = None) -> list[str]:
    lin, ang, fresh = limits or LIMITS[example]
    script = [f"LIMITS {lin} {ang} {fresh}"] + vectors
    proc = subprocess.run([str(binary)], input="\n".join(script) + "\n",
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def _vec(seq: int, req: int, state_in: int, linear: float = 0.5,
         angular: float = 0.0, age: int = 0, sim: int = 1,
         reset: int = 0, estop: int = 0) -> str:
    return (f"{MAGIC:X} 1 1 {seq} 0 50 {linear} {angular} {req} "
            f"{age} {sim} {reset} {state_in} {estop}")


def test_v2_nominal_allows(repo_root, tmp_path):
    binary = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    assert _decide(binary, "amr-demo", [_vec(1, 1, 1)]) == ["ALLOW OK 1"]


def test_a_limit_change_moves_the_native_verdict(repo_root, tmp_path):
    """Same command: ALLOW under the 1.2 policy, DENY under a 0.5 mutant."""
    base = _load(repo_root, "amr-demo")
    mutant = copy.deepcopy(base)
    mutant["control"]["max_linear_speed_mps"] = 0.5
    for a in mutant["actuators"]:
        a["bounds"] = {"min": -0.5, "max": 0.5}
    for c in mutant["commands"]:
        for f in c["fields"]:
            f["min"], f["max"] = -0.5, 0.5
    validate_v2(mutant)  # mutant stays a legal IR (policy within capability)
    gen_base, gen_mut = tmp_path / "gb", tmp_path / "gm"
    generate_v2(base, gen_base)
    generate_v2(mutant, gen_mut)
    h_base = (gen_base / "genesis_config_gen.h").read_text(encoding="utf-8")
    h_mut = (gen_mut / "genesis_config_gen.h").read_text(encoding="utf-8")
    assert "GENESIS_MAX_LINEAR_MPS 1.2" in h_base
    assert "GENESIS_MAX_LINEAR_MPS 0.5" in h_mut
    binary = _build(repo_root, base, tmp_path, "amr")
    vec = _vec(1, 1, 1, linear=0.8)
    assert _decide(binary, "amr-demo", [vec], limits=(1.2, 1.0, 100)) == [
        "ALLOW OK 1"]
    assert _decide(binary, "amr-demo", [vec], limits=(0.5, 1.0, 100)) == [
        "DENY SPEED_OVER_LIMIT 1"]


def test_a_machine_limits_differ_natively(repo_root, tmp_path):
    """1.5 m/s: AMR (1.2) denies, conveyor (2.0) allows. Spec E (limits)."""
    b_amr = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    b_conv = _build(repo_root, _load(repo_root, "conveyor-demo"), tmp_path, "c")
    vec = _vec(1, 1, 1, linear=1.5)
    assert _decide(b_amr, "amr-demo", [vec]) == ["DENY SPEED_OVER_LIMIT 1"]
    assert _decide(b_conv, "conveyor-demo", [vec]) == ["ALLOW OK 1"]


def test_b_transition_change_moves_the_automaton(repo_root, tmp_path):
    """Removing running->safe_stop flips 1->3 from ALLOW to DENY."""
    base = _load(repo_root, "amr-demo")
    cut = copy.deepcopy(base)
    cut["transitions"] = [t for t in cut["transitions"]
                          if not (t["from"] == "running"
                                  and t["to"] == "safe_stop")]
    assert len(cut["transitions"]) == 2  # only init->running, safe->init left
    validate_v2(cut)
    b_base = _build(repo_root, base, tmp_path, "amr")
    b_cut = _build(repo_root, cut, tmp_path, "cut")
    vec = _vec(1, 3, 1)
    assert _decide(b_base, "amr-demo", [vec]) == ["ALLOW OK 3"]
    assert _decide(b_cut, "amr-demo", [vec]) == ["DENY BAD_TRANSITION 1"]


def test_c_forbidden_transitions_rejected(repo_root, tmp_path):
    binary = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    vecs = [
        _vec(1, 2, 1),   # wire 2 (DEGRADED) maps to no AMR state
        _vec(2, 0, 1),   # running -> init is not declared
        _vec(3, 99, 1),  # unknown wire state
        _vec(4, 1, 2),   # from-state 2 has no v2 interpretation: deny
    ]
    assert _decide(binary, "amr-demo", vecs) == [
        "DENY BAD_TRANSITION 1",
        "DENY BAD_TRANSITION 1",
        "DENY BAD_TRANSITION 1",
        "DENY BAD_TRANSITION 2",
    ]


def test_c_v1_allows_what_v2_forbids(repo_root, tmp_path):
    """v1 guard ALLOWS 1->2 (fixed nominal/degraded rule); the v2 AMR
    guard DENYs it (no such transition). Proves the v2 tail, not v1."""
    src = repo_root / "target" / "qnx8"
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no host C compiler available")
    out = tmp_path / ("guard_v1.exe" if cc.lower().endswith(".exe")
                      else "guard_v1")
    cmd = [cc, "-O1", "-Wall", "-Wextra", f"-I{src / 'include'}",
           f"-I{src / 'common'}", "-o", str(out),
           str(src / "common" / "guard_policy.c"),
           str(src / "host_tests" / "guard_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    assert _decide(out, "amr-demo", [_vec(1, 2, 1)]) == ["ALLOW OK 2"]


def test_d_fault_latches_predicted_safe_state(repo_root, tmp_path):
    """Stale sensor / estop deny and latch wire 3 (safe_stop)."""
    binary = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    assert _decide(binary, "amr-demo", [_vec(1, 1, 1, age=150)]) == [
        "DENY STALE_SENSOR 3"]
    assert _decide(binary, "amr-demo", [_vec(1, 1, 1, estop=1)]) == [
        "DENY ESTOP 3"]


def test_d_reject_command_action_skips_the_latch(repo_root, tmp_path):
    """IR action reject_command on stale_sensor: deny, no latch, and the
    next nominal command is allowed without a supervisor reset."""
    v2 = _load(repo_root, "amr-demo")
    for fr in v2["fault_responses"]:
        if fr["fault"] == "stale_sensor":
            fr["action"] = "reject_command"
    validate_v2(v2)
    binary = _build(repo_root, v2, tmp_path, "amr-nl")
    assert _decide(binary, "amr-demo", [_vec(1, 1, 1, age=150)]) == [
        "DENY STALE_SENSOR 1"]
    assert _decide(binary, "amr-demo", [_vec(2, 1, 1)]) == ["ALLOW OK 1"]


def test_e_machines_behave_distinctly(repo_root, tmp_path):
    """Same sensor age 75 ms: AMR (freshness 100) allows, conveyor
    (strictest 50) denies. The IR, not the harness, decides."""
    b_amr = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    b_conv = _build(repo_root, _load(repo_root, "conveyor-demo"), tmp_path, "c")
    vec = _vec(1, 1, 1, age=75)
    assert _decide(b_amr, "amr-demo", [vec]) == ["ALLOW OK 1"]
    assert _decide(b_conv, "conveyor-demo", [vec]) == ["DENY STALE_SENSOR 3"]


def test_safe_stop_exit_needs_supervisor_reset(repo_root, tmp_path):
    """safe_stop -> init is declared, but leaving wire 3 still requires
    reset_armed (v1 reset authority preserved in v2)."""
    binary = _build(repo_root, _load(repo_root, "amr-demo"), tmp_path, "amr")
    assert _decide(binary, "amr-demo", [_vec(1, 0, 3)]) == [
        "DENY BAD_TRANSITION 3"]
    assert _decide(binary, "amr-demo", [_vec(1, 0, 3, reset=1)]) == [
        "ALLOW OK 0"]
