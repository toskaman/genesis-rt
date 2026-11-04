# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Deterministic code generator: Machine IR -> QNX C build directory.

Same validated IR + same template version => byte-identical output.
No timestamps, no randomness, no network, no shell interpolation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from string import Template
from typing import Any

from . import __version__ as GENERATOR_VERSION
from .ir import canonical_json, guard_limits

TEMPLATE_VERSION = "1.0"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

GENERATED_FILES = (
    ("genesis_config_gen.h.tmpl", "genesis_config_gen.h"),
    ("genesis_build_gen.mk.tmpl", "genesis_build_gen.mk"),
)


def ir_sha256(ir: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(ir).encode("utf-8")).hexdigest()


def template_sha256(name: str) -> str:
    return hashlib.sha256((TEMPLATES_DIR / name).read_bytes()).hexdigest()


def _check_genesis_src(genesis_src: str) -> None:
    """Fail closed on values that could inject make directives or paths."""
    if not isinstance(genesis_src, str) or not genesis_src:
        raise ValueError("genesis_src must be a non-empty string")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in genesis_src):
        raise ValueError("genesis_src must not contain control characters")


def _render(name: str, mapping: dict[str, str]) -> str:
    text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    return Template(text).substitute(mapping)


def generate(ir: dict[str, Any], out_dir: str | Path,
             genesis_src: str = "../../target/qnx8") -> dict[str, Any]:
    """Render the per-machine build directory. Returns the codegen manifest."""
    _check_genesis_src(genesis_src)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    limits = guard_limits(ir)
    digest = ir_sha256(ir)
    mapping = {
        "generator_version": GENERATOR_VERSION,
        "template_version": TEMPLATE_VERSION,
        "ir_sha256": digest,
        "machine_id": ir["machine"]["id"],
        "machine_kind": ir["machine"]["kind"],
        "period_ms": str(limits["period_ms"]),
        "max_linear": repr(limits["max_linear_speed_mps"]),
        "max_angular": repr(limits["max_angular_speed_radps"]),
        "freshness_limit": str(limits["freshness_limit_ms"]),
        "genesis_src": genesis_src,
    }
    files: dict[str, str] = {}
    for tmpl_name, out_name in GENERATED_FILES:
        rendered = _render(tmpl_name, mapping).replace("\r\n", "\n")
        if not rendered.endswith("\n"):
            rendered += "\n"
        (out / out_name).write_text(rendered, encoding="utf-8", newline="\n")
        files[out_name] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return {
        "generator_version": GENERATOR_VERSION,
        "template_version": TEMPLATE_VERSION,
        "templates": {tmpl: template_sha256(tmpl) for tmpl, _ in GENERATED_FILES},
        "genesis_src": genesis_src,
        "ir_sha256": digest,
        "files": files,
    }
