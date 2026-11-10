# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""W1: one-shot stale-refusal moment (seal -> mutate -> STALE in seconds).

Pure, UI-free core behind `genesis-rt demo-break`, POST /demo/break and
the Studio "Break it" button. Host digest-level refusal only: the native
behavioral refusal stays an archived, explicitly labeled pointer (see the
Omega2 packs), never presented as live.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .external import check_workspace, write_manifest

BUDGET_S = 30.0
_BINARIES = (("genesis_guard", b"guard-binary-v1"),
             ("genesis_controller", b"controller-binary-v1"))
_MUTATION = b"+hotfix"


def run_break_demo(workspace: str | Path) -> dict[str, Any]:
    """Seal a workspace, verify CONSISTENT, mutate one binary, refuse STALE.

    Returns a JSON-serializable report; raises AssertionError if the
    refusal does not reproduce (fail-loud demo, never a faked verdict).
    """
    t0 = time.monotonic()
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in _BINARIES:
        (root / name).write_bytes(payload)
    manifest = write_manifest(root, "demo-break", "qcc 12.2.0")
    man_path = root / "external-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=1, sort_keys=True),
                        encoding="utf-8")
    fresh = check_workspace(man_path, root)
    assert fresh["verdict"] == "CONSISTENT", fresh
    with (root / "genesis_guard").open("ab") as fh:
        fh.write(_MUTATION)
    stale = check_workspace(man_path, root)
    assert stale["verdict"] == "STALE", stale
    assert stale["stale_binaries"] == ["genesis_guard"], stale
    elapsed = time.monotonic() - t0
    return {
        "fresh": {"verdict": fresh["verdict"]},
        "stale": {"verdict": stale["verdict"],
                  "stale_binaries": list(stale["stale_binaries"])},
        "binaries": sorted(name for name, _ in _BINARIES),
        "elapsed_s": round(elapsed, 3),
        "budget_s": BUDGET_S,
        "level": "host-digest",
        "native_pointer": ("archived: v2 contract + v1 binary fails 14/16 on"
                           " estop_target + v2_transitions; replay offline"
                           " via evidence/qnx8-x86_64-omega2-after/verify.py"),
    }
