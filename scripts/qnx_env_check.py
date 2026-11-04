#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX environment setup checker (cross-platform, stdlib-only).

Prints a structured report: SDK present/absent, qcc version, target dir.
Exit 0 always (absence is a report, not a crash); use the JSON to decide.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.build_adapter import probe  # noqa: E402


def main() -> int:
    report = probe()
    print(json.dumps(report, indent=2))
    if not report["sdk_present"]:
        print("\nQNX SDK not found. Follow docs/quickstart-qnx8-qemu.md, then re-run.")
        print("Host verification (pytest, guard_vector, demo) works without the SDK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
