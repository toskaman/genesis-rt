# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Generated-machine behavior: host-compiled queries match their IR.

Builds the generated genesis_machine_gen.c + machine_vector harness with
the host C compiler (-Wall -Wextra, warnings fail) and drives every query
with vectors derived FROM the v2 IR under test. Skips only when no host
C compiler exists (explicit skip, never a silent pass).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis_rt.codegen_v2 import generate_v2
from genesis_rt.ir_v2 import load_ir_v2_file


def _generate(repo_root: Path, tmp_path: Path, example: str):
    v2 = load_ir_v2_file(
        repo_root / "examples" / example / "machine-ir-v2.json")
    gen = tmp_path / "gen"
    generate_v2(v2, gen)
    return v2, gen


def _build(repo_root: Path, gen: Path, tmp_path: Path) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no host C compiler available")
    out = tmp_path / ("machine_vector.exe" if cc.lower().endswith(".exe")
                      else "machine_vector")
    cmd = [cc, "-O1", "-Wall", "-Wextra", f"-I{gen}", "-o", str(out),
           str(gen / "genesis_machine_gen.c"),
           str(repo_root / "target" / "qnx8" / "host_tests" / "machine_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"C build failed:\n{proc.stderr}"
    assert "warning" not in proc.stderr.lower(), proc.stderr
    return out


def _query(binary: Path, lines: list[str]) -> list[str]:
    proc = subprocess.run([str(binary)], input="\n".join(lines) + "\n",
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.splitlines()


def _indexes(v2) -> dict:
    states = [s["id"] for s in v2["states"]]
    events = list(dict.fromkeys(t["event"] for t in v2["transitions"]))
    return {
        "state": {s: i for i, s in enumerate(states)},
        "event": {e: i for i, e in enumerate(events)},
        "cmd": {c["id"]: i for i, c in enumerate(v2["commands"])},
        "fault": {f: i for i, f in
                  enumerate(dict.fromkeys(fr["fault"] for fr in v2["fault_responses"]))},
        "action": {a: i for i, a in
                   enumerate(dict.fromkeys(fr["action"] for fr in v2["fault_responses"]))},
        "act": {a["id"]: i for i, a in enumerate(v2["actuators"])},
        "sens": {s["id"]: i for i, s in enumerate(v2["sensors"])},
        "tm": {t["id"]: i for i, t in enumerate(v2["telemetry"])},
        "n_state": len(states),
        "n_event": len(events),
    }


@pytest.mark.parametrize("example", ["amr-demo", "conveyor-demo"])
def test_generated_module_matches_ir(repo_root, tmp_path, example):
    v2, gen = _generate(repo_root, tmp_path, example)
    binary = _build(repo_root, gen, tmp_path)
    idx = _indexes(v2)

    lines, expected = [], []
    declared = {(t["from"], t["to"], t["event"]) for t in v2["transitions"]}
    for (src, dst, ev) in sorted(declared):
        lines.append(f"T {idx['state'][src]} {idx['state'][dst]} {idx['event'][ev]}")
        expected.append("1")
    # reversed transitions are illegal unless also declared
    for (src, dst, ev) in sorted(declared):
        if (dst, src, ev) not in declared:
            lines.append(f"T {idx['state'][dst]} {idx['state'][src]} {idx['event'][ev]}")
            expected.append("0")
    # unknown ids fail closed
    lines.append(f"T {idx['n_state']} 0 0")
    expected.append("0")

    for c in v2["commands"]:
        ci = idx["cmd"][c["id"]]
        for j, f in enumerate(c["fields"]):
            lines.append(f"C {ci} {j}")
            expected.append(f"{float(f['min'])} {float(f['max'])}")
        lines.append(f"C {ci} {len(c['fields'])}")
        expected.append("ERR")
    lines.append(f"C {len(v2['commands'])} 0")
    expected.append("ERR")

    first: dict[str, dict] = {}
    for fr in v2["fault_responses"]:
        first.setdefault(fr["fault"], fr)
    for fault, fr in first.items():
        lines.append(f"F {idx['fault'][fault]}")
        expected.append(f"{idx['state'][fr['enter_state']]} {idx['action'][fr['action']]}")
    lines.append(f"F {len(first)}")
    expected.append("ERR")

    for a in v2["actuators"]:
        lines.append(f"A {idx['act'][a['id']]}")
        expected.append(f"{float(a['bounds']['min'])} {float(a['bounds']['max'])}")

    for s in v2["sensors"]:
        lines.append(f"S {idx['sens'][s['id']]}")
        if "range" in s:
            expected.append(f"{float(s['freshness_limit_ms'])} "
                            f"{float(s['range']['min'])} {float(s['range']['max'])}")
        else:
            expected.append(f"{float(s['freshness_limit_ms'])} NONE NONE")

    for t in v2["telemetry"]:
        lines.append(f"M {idx['tm'][t['id']]}")
        expected.append(f"{float(t['rate_hz'])} {t['id']} {t['source']}")
    lines.append(f"M {len(v2['telemetry'])}")
    expected.append("ERR")

    got = _query(binary, lines)
    assert len(got) == len(expected), (got, expected)
    for g, e in zip(got, expected):
        gt, et = g.split(), e.split()
        assert len(gt) == len(et), (g, e)
        for a, b in zip(gt, et):
            try:
                assert float(a) == float(b), (g, e)
            except ValueError:
                assert a == b, (g, e)
