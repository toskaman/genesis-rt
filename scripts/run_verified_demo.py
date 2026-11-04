#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Single-click verified demo: pipeline + sample passport copy.

Usage: python scripts/run_verified_demo.py [--ir examples/amr-demo/machine-ir.json]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.orchestrator import run_pipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the GENESIS RT verified demo")
    ap.add_argument("--ir", default=str(REPO_ROOT / "examples" / "amr-demo" / "machine-ir.json"))
    ap.add_argument("--copy-sample", action="store_true",
                    help="also copy the passport to artifacts/samples/")
    args = ap.parse_args()
    summary = run_pipeline(args.ir, REPO_ROOT / "artifacts" / "runs")
    print(json.dumps({k: summary[k] for k, v in summary.items()
                      if k in ("run_id", "verdict", "qnx_verified",
                               "elapsed_s", "passport")}, indent=2))
    if args.copy_sample and summary["verdict"] == "PASS":
        dest = REPO_ROOT / "artifacts" / "samples" / "golden_demo_passport.example.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(summary["passport"], dest)
        print(f"sample copied: {dest}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
