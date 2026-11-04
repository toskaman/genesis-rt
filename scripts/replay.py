#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Re-verify a passport: chain integrity + gate re-evaluation.

Usage: python scripts/replay.py <passport.json> [--required a b c]
Exit 0 only if the chain is valid AND the gate passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt import gate  # noqa: E402
from genesis_rt.evidence import load_passport, verify_chain  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay-verify an evidence passport")
    ap.add_argument("passport")
    ap.add_argument("--required", nargs="*", default=None)
    args = ap.parse_args()
    passport = load_passport(args.passport)
    errors = verify_chain(passport)
    print(f"chain: {'valid' if not errors else 'INVALID'}")
    for e in errors:
        print(f"  {e}")
    if args.required is None:
        ir_rec = next((r for r in passport["chain"] if r["kind"] == "ir"), None)
        required = ir_rec["body"]["scenarios"] if ir_rec else []
    else:
        required = args.required
    verdict = gate.evaluate(passport, required)
    print(f"gate: {verdict['verdict']} (qnx_verified={verdict['qnx_verified']})")
    for r in verdict["reasons"]:
        print(f"  {r}")
    return 0 if (not errors and verdict["verdict"] == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
