#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Create a build set (provenance v2) for an on-target verification campaign.

Each --entry attributes one staged secondary executable to the build that
produced it, read from that build's evidence passport (chain verified):

    python scripts/build_set.py create -o artifacts/build-set.json \\
      --entry genesis_guard_conv=genesis_guard:artifacts/runs/run-CONV/passport.json \\
      --entry genesis_guard_v2=genesis_guard:artifacts/runs/run-AMRV2/passport.json

Then: scripts/qnx_target.py verify --ir ... --build-set artifacts/build-set.json
(and the same --build-set for `perf`).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "host"))

from genesis_rt import buildset  # noqa: E402
from genesis_rt.evidence import load_passport  # noqa: E402


def _parse_entry(spec: str) -> tuple[str, str, str]:
    try:
        staged, rest = spec.split("=", 1)
        source, passport = rest.split(":", 1)
    except ValueError:
        raise SystemExit(f"bad --entry {spec!r}: want STAGED=SOURCE_BINARY:PASSPORT")
    if not staged.startswith("genesis_") or not source.startswith("genesis_"):
        raise SystemExit(f"bad --entry {spec!r}: binary names start with genesis_")
    return staged, source, passport


def cmd_create(args: argparse.Namespace) -> int:
    entries = []
    for spec in args.entry:
        staged, source, passport = _parse_entry(spec)
        try:
            entries.append(buildset.entry_from_passport(
                load_passport(passport), source_binary=source, staged_name=staged))
        except (OSError, ValueError) as exc:
            print(f"build-set: REFUSED {staged}: {exc}")
            return 2
    try:
        bs = buildset.make_build_set(entries)
    except ValueError as exc:
        print(f"build-set: REFUSED: {exc}")
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for e in entries:
        print(f"{e['staged_name']}: {e['machine_id']} ({e['machine_kind']}, "
              f"schema v{e['schema_version']}) build {e['build_id'][:12]} "
              f"from {e['source_run_id']}")
    print(f"build set -> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create")
    c.add_argument("--entry", action="append", required=True,
                   help="STAGED=SOURCE_BINARY:PATH/TO/passport.json")
    c.add_argument("-o", "--out", required=True)
    c.set_defaults(func=cmd_create)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
