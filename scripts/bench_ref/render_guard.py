#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""SYNTHETIC REFERENCE WORKFLOW for the §12 productivity benchmark.

A stunt "generator": stamps the v1 control limits into a C header with
string formatting and no schema validation, no provenance, no
determinism contract. It must be adapted by hand for every new machine
kind or field — the manual step the benchmark counts. Never used by
the product itself.

Usage: python scripts/bench_ref/render_guard.py <ir.json> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ir")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        doc = json.loads(Path(args.ir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable IR: {exc}", file=sys.stderr)
        return 1
    control = doc.get("control", {})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    header = (
        "/* stunt header: hand-stamped limits, no provenance */\n"
        "#pragma once\n"
        f"#define STUNT_PERIOD_MS ({control.get('period_ms', '?')})\n"
        f"#define STUNT_MAX_V ({control.get('max_linear_speed_mps', '?')})\n"
        f"#define STUNT_MAX_W ({control.get('max_angular_speed_radps', '?')})\n"
    )
    (out / "guard_stunt.h").write_text(header, encoding="utf-8")
    print(f"stunt header written to {out / 'guard_stunt.h'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
