#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""SYNTHETIC REFERENCE WORKFLOW for the §12 productivity benchmark.

A naive hand-maintained contract checker: loads a Machine IR JSON file
and sanity-checks the v1 control block (required keys present, numeric,
positive). It deliberately does NOT enforce the strict schema (unknown
keys pass, transitions unchecked, v2 unsupported) — exactly the drift a
hand-rolled checker accumulates. Never used by the product itself.

Usage: python scripts/bench_ref/check_limits.py <ir.json>
Exit 0 when the naive checks pass, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = ("period_ms", "max_linear_speed_mps",
            "max_angular_speed_radps")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_limits.py <ir.json>", file=sys.stderr)
        return 2
    try:
        doc = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable IR: {exc}", file=sys.stderr)
        return 1
    control = doc.get("control")
    if not isinstance(control, dict):
        print("missing control block", file=sys.stderr)
        return 1
    for key in REQUIRED:
        value = control.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            print(f"bad {key}: {value!r} (not a number)", file=sys.stderr)
            return 1
        if value <= 0:
            print(f"bad {key}: {value!r} (not positive)", file=sys.stderr)
            return 1
    for sensor in doc.get("sensors", []):
        fresh = sensor.get("freshness_limit_ms")
        if isinstance(fresh, bool) or not isinstance(fresh, int):
            print(f"bad freshness_limit_ms: {fresh!r} (not an int)",
                  file=sys.stderr)
            return 1
        if not 1 <= fresh <= 60000:
            print(f"bad freshness_limit_ms: {fresh!r} (not 1..60000)",
                  file=sys.stderr)
            return 1
    print(f"naive check passed ({len(REQUIRED)} keys present and positive)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
