#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""COMPETENT REFERENCE WORKFLOW for the productivity benchmark.

Validates a Machine IR JSON file with the stock `jsonschema` engine
against a hand-maintained schema (`amr.schema.json`). This is what a
diligent team does without GENESIS RT: real detection power, but the
schema itself is hand-authored and must be extended by hand for every
new IR rule, machine kind, and schema version — that maintenance cost
is the benchmark's honest differentiator (see `manual_steps`).

Not covered: cross-field semantics (limit vs nominal), transition
tables, v2 constructs. Never used by the product itself.

Usage: python scripts/bench_ref/validate_schema.py <ir.json>
Exit 0 valid, 1 invalid, 2 usage/IO error, 3 jsonschema missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = Path(__file__).with_name("amr.schema.json")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_schema.py <ir.json>", file=sys.stderr)
        return 2
    try:
        import jsonschema
    except ImportError:
        print("BLOCKED: python package 'jsonschema' not installed",
              file=sys.stderr)
        return 3
    try:
        doc = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable IR: {exc}", file=sys.stderr)
        return 2
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable schema: {exc}", file=sys.stderr)
        return 2
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        print(f"invalid: {exc.message}", file=sys.stderr)
        return 1
    print("schema validation passed (stock jsonschema engine)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
