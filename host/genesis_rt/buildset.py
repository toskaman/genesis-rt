# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Multi-build provenance: the build set of a verification campaign (§6).

The on-target matrix runs several machine-specific executables that are
NOT produced by the pipeline under test (the conveyor guard, the AMR v2
guard). Provenance v1 let such "extra" staged binaries through without
any origin. A build set closes that gap: every staged executable must be
attributable to exactly one build, and every secondary build is described
by an entry derived from the evidence passport of the run that built it.

Entry (one per staged secondary executable)::

    {
      "staged_name":    "genesis_guard_conv",   # name on the target
      "source_binary":  "genesis_guard",        # name in its own build
      "machine_id":     "conveyor-demo-01",
      "machine_kind":   "conveyor",
      "schema_version": 1,
      "ir_sha256":      "<64 hex>",
      "generator_version": "0.1.0",
      "toolchain":      "<qcc -V excerpt>",
      "built_utc":      "<iso>",
      "build_id":       "<64 hex: digest of the source build record>",
      "sha256": "<64 hex>", "cksum": <int>, "size": <int>,
      "source_run_id":  "run-...",
      "source_passport_head": "<64 hex: last chain hash of that passport>"
    }

What this binds: the staged bytes (cksum+size against the target, sha256
on the host) to one specific build of one specific IR/machine, and that
build to a passport whose chain can be replayed independently
(``scripts/replay.py --build-set ... --source-passport ...``).
What it does not bind: a local operator who forges a whole source
passport (threat model A3/A4, docs/passport-threat-model.md).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .codegen import canonical_json
from .evidence import load_passport, verify_chain

BUILD_SET_VERSION = 1

# Secondary executables the current matrix runs, with the origin each one
# MUST have. A conveyor guard staged from an AMR build is rejected here.
REQUIRED_SECONDARIES: dict[str, dict[str, Any]] = {
    "genesis_guard_conv": {"machine_kind": "conveyor",
                           "source_binary": "genesis_guard",
                           "steps": ("limits_differ", "conv_chain")},
    "genesis_guard_v2": {"machine_kind": "differential_drive_robot",
                         "schema_version": 2,
                         "source_binary": "genesis_guard",
                         "steps": ("v2_transitions",)},
}

_ENTRY_FIELDS = ("staged_name", "source_binary", "machine_id", "machine_kind",
                 "schema_version", "ir_sha256", "generator_version",
                 "built_utc", "build_id", "sha256", "cksum", "size",
                 "source_run_id", "source_passport_head")


def _hex64(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def build_id(build_body: dict[str, Any], ir_sha256: str) -> str:
    """Identity of one build: IR digest + build time + toolchain + every
    output digest. Two builds differ in id as soon as any of these does."""
    ident = {"ir_sha256": ir_sha256,
             "built_utc": build_body.get("built_utc"),
             "qcc_version": (build_body.get("environment") or {}).get("qcc_version"),
             "binaries": build_body.get("binaries") or {}}
    return hashlib.sha256(canonical_json(ident).encode("utf-8")).hexdigest()


def _records(passport: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rec in passport.get("chain", []):
        if isinstance(rec, dict) and isinstance(rec.get("kind"), str):
            out.setdefault(rec["kind"], rec.get("body") or {})
    return out


def entry_from_passport(passport: dict[str, Any], *, source_binary: str,
                        staged_name: str) -> dict[str, Any]:
    """Build-set entry for one binary of the build recorded in `passport`.

    Refuses (ValueError) anything that would make the entry unverifiable:
    broken chain, build not 'ok', binary absent from the build digests.
    """
    errors = verify_chain(passport)
    if errors:
        raise ValueError(f"source passport chain invalid: {errors[:3]}")
    recs = _records(passport)
    ir_body, build = recs.get("ir"), recs.get("qnx_build")
    if not ir_body or not isinstance(ir_body.get("machine"), dict):
        raise ValueError("source passport has no ir record")
    if not build or build.get("status") != "ok":
        raise ValueError(f"source build status is {build and build.get('status')!r}, "
                         "need 'ok' (a blocked/failed build has no outputs)")
    digest = (build.get("binaries") or {}).get(source_binary)
    if not isinstance(digest, dict):
        raise ValueError(f"{source_binary!r} not among the source build's "
                         f"digested binaries {sorted(build.get('binaries') or {})}")
    codegen = recs.get("codegen") or {}
    return {
        "staged_name": staged_name,
        "source_binary": source_binary,
        "machine_id": ir_body["machine"].get("id"),
        "machine_kind": ir_body["machine"].get("kind"),
        "schema_version": ir_body.get("schema_version", 1),
        "ir_sha256": ir_body.get("ir_sha256"),
        "generator_version": codegen.get("generator_version"),
        "toolchain": ((build.get("environment") or {}).get("qcc_version") or "")[:300],
        "built_utc": build.get("built_utc"),
        "build_id": build_id(build, ir_body.get("ir_sha256") or ""),
        "sha256": digest.get("sha256"),
        "cksum": digest.get("cksum"),
        "size": digest.get("size"),
        "source_run_id": passport.get("run_id"),
        "source_passport_head": passport["chain"][-1]["hash"],
    }


def make_build_set(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_name: dict[str, dict[str, Any]] = {}
    for e in entries:
        if e["staged_name"] in by_name:
            raise ValueError(f"duplicate staged name {e['staged_name']!r}")
        by_name[e["staged_name"]] = e
    return {"build_set_version": BUILD_SET_VERSION, "entries": by_name}


def load_build_set(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("build_set_version") != BUILD_SET_VERSION:
        raise ValueError(f"not a build set v{BUILD_SET_VERSION}: {path}")
    return data


def check_build_set(*, staged: Any, primary_binaries: Any,
                    primary_ir_sha256: Any, primary_build_id: str | None,
                    build_set: Any, matrix: Any) -> list[str]:
    """Reasons the staged executables are NOT all attributable ([] = ok).

    Rules (each one is a regression test in tests/unit/test_buildset.py):
      * every staged executable belongs to exactly one build: the primary
        build or one build-set entry (unregistered / ambiguous => refused);
      * an entry's cksum+size equal what the target observed;
      * an entry is well-formed (digests, machine, schema, build id);
      * required secondaries for the matrix steps are present and have the
        declared origin (machine kind, schema version, source binary);
      * no reused provenance: an entry cannot claim the primary build, and
        one build id cannot describe two different IRs or byte contents.
    """
    if not isinstance(staged, dict) or not staged:
        return ["staged binaries missing (no target-observed cksums)"]
    prim = primary_binaries if isinstance(primary_binaries, dict) else {}
    if not isinstance(build_set, dict) or build_set.get("build_set_version") != BUILD_SET_VERSION:
        return [f"build set missing or not v{BUILD_SET_VERSION} "
                f"(secondary executables cannot be attributed)"]
    entries = build_set.get("entries")
    if not isinstance(entries, dict):
        return ["build set has no entries map"]
    reasons: list[str] = []
    for name in sorted(staged):
        in_prim, in_set = name in prim, name in entries
        if in_prim and in_set:
            reasons.append(f"{name}: claimed by the primary build AND the build set (ambiguous)")
        elif not in_prim and not in_set:
            reasons.append(f"{name}: staged on target but registered in no build "
                           f"(unattributed executable)")
    seen_ids: dict[str, tuple[Any, Any]] = {}
    for name, e in sorted(entries.items()):
        if not isinstance(e, dict):
            reasons.append(f"{name}: build-set entry is not an object")
            continue
        missing = [f for f in _ENTRY_FIELDS if e.get(f) in (None, "")]
        if missing:
            reasons.append(f"{name}: build-set entry missing {missing}")
            continue
        if e["staged_name"] != name:
            reasons.append(f"{name}: entry declares staged_name {e['staged_name']!r}")
        for f in ("ir_sha256", "build_id", "sha256", "source_passport_head"):
            if not _hex64(e[f]):
                reasons.append(f"{name}: {f} is not a sha256 hex digest")
        obs = staged.get(name)
        if not isinstance(obs, dict):
            reasons.append(f"{name}: registered in the build set but not staged on target")
        elif obs.get("cksum") != e["cksum"] or obs.get("size") != e["size"]:
            reasons.append(f"{name}: staged bytes differ from its registered build "
                           f"(cksum {obs.get('cksum')}/{e['cksum']}, "
                           f"size {obs.get('size')}/{e['size']})")
        if primary_build_id and e["build_id"] == primary_build_id:
            reasons.append(f"{name}: entry reuses the primary build id")
        prev = seen_ids.get(e["build_id"])
        if prev is not None and prev[0] != e["ir_sha256"]:
            reasons.append(f"{name}: build id {e['build_id'][:12]} already describes "
                           f"another IR (reused provenance)")
        seen_ids.setdefault(e["build_id"], (e["ir_sha256"], e["sha256"]))
        rule = REQUIRED_SECONDARIES.get(name)
        if rule:
            for key in ("machine_kind", "schema_version", "source_binary"):
                if key in rule and e.get(key) != rule[key]:
                    reasons.append(f"{name}: wrong origin: {key}={e.get(key)!r} "
                                   f"(this matrix needs {rule[key]!r})")
            if (rule.get("machine_kind") and e.get("ir_sha256") == primary_ir_sha256):
                reasons.append(f"{name}: built from the primary IR, not a "
                               f"{rule['machine_kind']} IR")
    steps = set(matrix or [])
    for name, rule in REQUIRED_SECONDARIES.items():
        if steps & set(rule["steps"]) and name not in entries:
            reasons.append(f"{name}: required by matrix steps "
                           f"{sorted(steps & set(rule['steps']))} but absent from the build set")
    return reasons
