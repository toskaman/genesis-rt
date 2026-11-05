#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""SYNTHETIC REFERENCE WORKFLOW for the §12 productivity benchmark.

Packs loose log files into a directory with a sha256 manifest. It
cannot bind a verdict (no gate ran over the inputs) and it cannot
confirm the packer wrote an honest summary: CHECKS.md is expected to
be written BY HAND (the manual step the benchmark counts) and is
reported missing when absent. Never used by the product itself.

Usage: python scripts/bench_ref/collect_package.py <log...> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest: list[str] = []
    for name in args.logs:
        src = Path(name)
        if not src.is_file():
            print(f"missing log: {name}", file=sys.stderr)
            return 1
        data = src.read_bytes()
        shutil.copyfile(src, out / src.name)
        manifest.append(
            f"{hashlib.sha256(data).hexdigest()}  {src.name}")
    checks = out / "CHECKS.md"
    if checks.is_file():
        manifest.append(
            f"{hashlib.sha256(checks.read_bytes()).hexdigest()}  CHECKS.md")
        print("CHECKS.md present (hand-written verdict summary)")
    else:
        print("CHECKS.md MISSING: no hand-written verdict summary")
    (out / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n",
                                         encoding="utf-8")
    print(f"package: {len(manifest)} files, manifest written, "
          "verdict NOT bound (no gate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
