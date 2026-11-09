#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""OMEGA6 B2: scripted 30-second stale-refusal demo (host, no QNX needed).

Beat 1 (live): seal a build workspace with `external-write-manifest`,
check it -> CONSISTENT. Beat 2 (live): change one binary without
re-sealing (the requirement moved, the build did not), check again ->
STALE naming the binary: the wrong binary cannot pass. Beat 3
(archived, labeled): the native behavioral refusal (v2 contract +
v1 binary fails 14/16 exactly on estop_target + v2_transitions)
lives in the committed Omega2 packs, not in this host run.

Usage: python scripts/demo_stale_refusal.py [--workspace DIR]
Exit 0 when the STALE refusal is demonstrated end to end.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.external import (check_workspace, render_text,  # noqa: E402
                                 write_manifest)

BUDGET_S = 30.0


def _beat(title: str) -> None:
    print(f"\n== {title}")


def run_demo(workspace: Path) -> dict:
    """Seal, verify, mutate, refuse. Returns the STALE report."""
    t0 = time.monotonic()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "genesis_guard").write_bytes(b"guard-binary-v1")
    (workspace / "genesis_controller").write_bytes(b"controller-binary-v1")
    _beat("beat 1/3: seal the build (live)")
    manifest = write_manifest(workspace, "demo-stale-refusal", "qcc 12.2.0")
    man_path = workspace / "external-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=1, sort_keys=True),
                        encoding="utf-8")
    print(f"sealed {len(manifest['binaries'])} binaries -> {man_path.name}")
    fresh = check_workspace(man_path, workspace)
    print(render_text(fresh), end="")
    assert fresh["verdict"] == "CONSISTENT", fresh
    _beat("beat 2/3: the binary moved without a re-seal (live)")
    with (workspace / "genesis_guard").open("ab") as fh:
        fh.write(b"+hotfix")
    stale = check_workspace(man_path, workspace)
    print(render_text(stale), end="")
    assert stale["verdict"] == "STALE", stale
    assert stale["stale_binaries"] == ["genesis_guard"], stale
    _beat("beat 3/3: the native refusal (archived, not live)")
    print("On target this refusal is behavioral: v2 contract + v1 binary "
          "fails 14/16, exactly on estop_target + v2_transitions "
          "(operator-recorded, prose-grade). Replay it offline:\n"
          "  python evidence/qnx8-x86_64-omega2-after/verify.py "
          "evidence/qnx8-x86_64-omega2-after")
    elapsed = time.monotonic() - t0
    print(f"\nstale-refusal demo: STALE in {elapsed:.1f}s "
          f"(budget {BUDGET_S:.0f}s) — the wrong binary cannot pass.")
    return stale


def main() -> int:
    ap = argparse.ArgumentParser(description="30-second stale-refusal demo")
    ap.add_argument("--workspace", default=None,
                    help="keep the demo workspace here (default: temp dir)")
    args = ap.parse_args()
    t0 = time.monotonic()
    if args.workspace:
        run_demo(Path(args.workspace))
    else:
        with tempfile.TemporaryDirectory(prefix="genesis-stale-demo-") as tmp:
            run_demo(Path(tmp))
    if time.monotonic() - t0 > BUDGET_S:
        print(f"OVER BUDGET: demo exceeded {BUDGET_S:.0f}s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
