# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""C-conformance replay for §9 explorer findings.

Re-runs a finding's recorded guard-command vectors through the compiled
``guard_vector`` harness (the same C ``guard_policy.c`` the QNX target
uses) and compares every decision. A finding earns
``c-conformance-reproduced`` only when ALL recorded decisions match;
any divergence is reported with the first mismatching tick (a finding
about host/C precision or behavior, never a silent pass).

Honest skips: no host C compiler, or a harness build/run failure,
yields ``supported: false`` with a reason — never a fake tier.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def find_host_cc() -> str | None:
    """Locate a host C compiler, if any."""
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def build_harness(repo_root: str | Path, workdir: str | Path,
                  timeout: int = 120) -> Path:
    """Compile guard_vector into workdir. Raises RuntimeError on failure."""
    cc = find_host_cc()
    if not cc:
        raise RuntimeError("no host C compiler available")
    src = Path(repo_root) / "target" / "qnx8"
    out = Path(workdir) / ("guard_vector.exe"
                           if cc.lower().endswith(".exe") else "guard_vector")
    cmd = [cc, "-O1", "-Wall", "-Wextra", f"-I{src / 'include'}",
           f"-I{src / 'common'}", "-o", str(out),
           str(src / "common" / "guard_policy.c"),
           str(src / "host_tests" / "guard_vector.c")]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"C harness build failed:\n{proc.stderr}")
    return out


def vector_line(vector: dict[str, Any]) -> str:
    """Format one recorded vector as guard_vector input (SEQ + vector)."""
    cmd = vector["cmd"]
    estop = int(cmd.get("estop_engaged", 0))
    size_ok = 1 if cmd.get("size_ok", True) else 0
    vec = (f"{int(cmd['magic']):X} {int(cmd['version'])} {size_ok} "
           f"{int(cmd['seq'])} {int(cmd['now_ms'])} "
           f"{int(cmd['deadline_ms'])} {float(cmd['linear_mps'])!r} "
           f"{float(cmd['angular_radps'])!r} {int(cmd['req_state'])} "
           f"{int(cmd['sensor_age_ms'])} "
           f"{1 if cmd.get('sim_connected') else 0} "
           f"{1 if vector.get('reset_armed') else 0} "
           f"{int(vector['state_in'])} {estop}")
    return f"SEQ {int(vector['last_seq_in'])}\n{vec}"


def replay_conformance(record: dict[str, Any], limits: dict[str, Any],
                       repo_root: str | Path,
                       timeout: int = 120) -> dict[str, Any]:
    """Replay a finding's vectors through the C guard.

    Returns supported/tier/matches/total/first_divergence. ``limits``
    are the guard limits of the IR the finding ran on (freshness +
    speed bounds drive C decisions).
    """
    vectors = record.get("vectors", [])
    if not vectors:
        return {"supported": False,
                "reason": "record carries no replay vectors"}
    cc = find_host_cc()
    if not cc:
        return {"supported": False,
                "reason": "no host C compiler available"}
    lines = [f"LIMITS {float(limits['max_linear_speed_mps'])!r} "
             f"{float(limits['max_angular_speed_radps'])!r} "
             f"{int(limits['freshness_limit_ms'])}"]
    for vector in vectors:
        lines.append(vector_line(vector))
    try:
        with tempfile.TemporaryDirectory(
                prefix="genesis_conformance_") as tmp:
            binary = build_harness(repo_root, tmp, timeout=timeout)
            proc = subprocess.run(
                [str(binary)], input="\n".join(lines) + "\n",
                capture_output=True, text=True, timeout=timeout)
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        return {"supported": False, "reason": str(exc)[:300]}
    if proc.returncode != 0:
        return {"supported": False,
                "reason": f"harness exited {proc.returncode}: "
                          f"{proc.stderr[:300]}"}
    outputs = [ln for ln in proc.stdout.splitlines()
               if not ln.startswith("SEQ-ARMED")]
    if len(outputs) != len(vectors):
        return {"supported": False,
                "reason": f"harness returned {len(outputs)} verdicts for "
                          f"{len(vectors)} vectors"}
    matches = 0
    first_divergence: dict[str, Any] | None = None
    for vector, line in zip(vectors, outputs):
        parts = line.split()
        if len(parts) != 3:
            return {"supported": False,
                    "reason": f"malformed harness line: {line[:100]!r}"}
        decision, reason, state_out = parts[0], parts[1], int(parts[2])
        expected = (vector["decision"], vector["reason"],
                    vector["state_out"])
        if (decision, reason, state_out) == expected:
            matches += 1
        elif first_divergence is None:
            first_divergence = {
                "tick": vector.get("tick"),
                "expected": {"decision": expected[0],
                             "reason": expected[1],
                             "state_out": expected[2]},
                "observed": {"decision": decision, "reason": reason,
                             "state_out": state_out},
            }
    tier = "c-conformance-reproduced" if matches == len(vectors) \
        else "c-divergent"
    return {"supported": True, "tier": tier, "matches": matches,
            "total": len(vectors), "first_divergence": first_divergence}
