# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""External build-manifest checks (BYOQNX minimal adapter, Titan W6).

Lets an EXISTING QNX project use one GENESIS capability without
rewriting anything in Machine IR: stale-artifact detection. The team
writes a small manifest of the binaries their own build produced
(name -> sha256); this module re-hashes a workspace directory and
reports per-binary MATCH / MISMATCH / ABSENT.

Hard trust boundary, enforced by construction:

- Only digest consistency is checked. Toolchain strings are recorded,
  never verified.
- ``test_claims`` from the manifest are counted and labelled
  UNVERIFIED_CLAIM. They are never evaluated, never trusted, and never
  touch the release gate: there is no code path from this module to
  ``gate.evaluate``.
- ``release_eligible`` is always False in every report this module
  emits. A consistent external workspace is "not stale", never
  "verified".

Manifest schema v1 (JSON, unknown keys rejected)::

    {"external_manifest_version": 1,
     "project": "my-controller",
     "toolchain": "qcc 12.2.0 gcc_ntox86_64 (recorded, not verified)",
     "binaries": {"guard": {"sha256": "<64 hex>", "size": 14432}},
     "test_claims": [{"name": "smoke", "verdict": "pass"}]}
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXTERNAL_MANIFEST_VERSION = 1
_HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")
_TOP_KEYS = frozenset({"external_manifest_version", "project",
                       "toolchain", "binaries", "test_claims"})
_BIN_KEYS = frozenset({"sha256", "size"})
_CLAIM_KEYS = frozenset({"name", "verdict", "detail"})

SCOPE_NOTE = ("digest consistency only: no QNX execution was supervised "
              "and nothing here grants release eligibility")


class ExternalManifestError(ValueError):
    """Raised when a manifest is malformed or unsafe."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Parse and strictly validate an external manifest (fail-closed)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExternalManifestError(f"cannot read manifest: {exc}") from exc
    except ValueError as exc:
        raise ExternalManifestError(f"manifest is not JSON: {exc}") from exc
    return validate_manifest(raw)


def validate_manifest(raw: Any) -> dict[str, Any]:
    """Strictly validate an already-parsed manifest (fail-closed)."""
    if not isinstance(raw, dict):
        raise ExternalManifestError("manifest must be a JSON object")
    unknown = set(raw) - _TOP_KEYS
    if unknown:
        raise ExternalManifestError(
            f"unknown manifest keys {sorted(unknown)}; "
            f"external_manifest_version {EXTERNAL_MANIFEST_VERSION} "
            "accepts only " + ", ".join(sorted(_TOP_KEYS)))
    if raw.get("external_manifest_version") != EXTERNAL_MANIFEST_VERSION:
        raise ExternalManifestError(
            "external_manifest_version must be "
            f"{EXTERNAL_MANIFEST_VERSION}")
    project = raw.get("project")
    if not isinstance(project, str) or not project.strip():
        raise ExternalManifestError("project must be a non-empty string")
    toolchain = raw.get("toolchain")
    if not isinstance(toolchain, str) or not toolchain.strip():
        raise ExternalManifestError("toolchain must be a non-empty string")
    binaries = raw.get("binaries")
    if not isinstance(binaries, dict) or not binaries:
        raise ExternalManifestError("binaries must be a non-empty object")
    for name, entry in binaries.items():
        if not isinstance(name, str) or not name.strip():
            raise ExternalManifestError("binary names must be non-empty strings")
        if not isinstance(entry, dict):
            raise ExternalManifestError(f"binary {name!r} must be an object")
        unknown_b = set(entry) - _BIN_KEYS
        if unknown_b:
            raise ExternalManifestError(
                f"binary {name!r} has unknown keys {sorted(unknown_b)}")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not _HEX64.match(digest):
            raise ExternalManifestError(
                f"binary {name!r} sha256 must be 64 hex chars")
        size = entry.get("size")
        if size is not None and (isinstance(size, bool)
                                 or not isinstance(size, int) or size < 0):
            raise ExternalManifestError(
                f"binary {name!r} size must be a non-negative int")
    claims = raw.get("test_claims", [])
    if not isinstance(claims, list):
        raise ExternalManifestError("test_claims must be a list")
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ExternalManifestError(f"test_claims[{i}] must be an object")
        unknown_c = set(claim) - _CLAIM_KEYS
        if unknown_c:
            raise ExternalManifestError(
                f"test_claims[{i}] has unknown keys {sorted(unknown_c)}")
        if not isinstance(claim.get("name"), str) or not claim["name"].strip():
            raise ExternalManifestError(
                f"test_claims[{i}] name must be a non-empty string")
        if claim.get("verdict") not in ("pass", "fail"):
            raise ExternalManifestError(
                f"test_claims[{i}] verdict must be pass/fail")
        detail = claim.get("detail")
        if detail is not None and not isinstance(detail, str):
            raise ExternalManifestError(
                f"test_claims[{i}] detail must be a string")
    return {"external_manifest_version": EXTERNAL_MANIFEST_VERSION,
            "project": project.strip(), "toolchain": toolchain.strip(),
            "binaries": {n: {"sha256": e["sha256"].lower(),
                             "size": e.get("size")}
                         for n, e in binaries.items()},
            "test_claims": [{"name": c["name"].strip(),
                             "verdict": c["verdict"],
                             "detail": c.get("detail")}
                            for c in claims]}


def _confined(root: Path, name: str) -> Path:
    """Resolve a manifest binary name inside the workspace (fail-closed).

    Absolute paths, drive letters, and `..` escapes are refused before
    any read: a hostile manifest must not make the checker hash (or
    report on) files outside the workspace.

    The backslash / drive-letter / absolute-spelling rejects are
    lexical on purpose: on POSIX ``..\\x`` is a harmless literal
    filename and ``C:/x`` resolves inside the workspace, so a
    resolve-only check would pass names that escape on Windows.
    Manifests travel across platforms; the guard must not depend
    on the checker's OS.
    """
    if ("\\" in name or name.startswith("/") or name.startswith("~")
            or re.match(r"^[A-Za-z]:", name)):
        raise ExternalManifestError(
            f"binary {name!r} escapes the workspace; manifest names "
            "must be relative paths inside it (no backslashes, drive "
            "letters, or absolute spellings)")
    candidate = (root / name).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise ExternalManifestError(
            f"binary {name!r} escapes the workspace; manifest names "
            "must stay inside it")
    return candidate


def check_workspace(manifest: str | Path | dict[str, Any],
                    workspace: str | Path) -> dict[str, Any]:
    """Hash every manifest binary in the workspace; report consistency."""
    man = validate_manifest(manifest) if isinstance(manifest, dict) \
        else load_manifest(manifest)
    root = Path(workspace)
    if not root.is_dir():
        raise ExternalManifestError(f"workspace is not a directory: {root}")
    binaries: dict[str, Any] = {}
    for name, entry in man["binaries"].items():
        target = _confined(root, name)
        if not target.is_file():
            binaries[name] = {"status": "ABSENT",
                              "expected_sha256": entry["sha256"],
                              "observed_sha256": None}
            continue
        observed = hashlib.sha256(target.read_bytes()).hexdigest()
        size_ok = entry["size"] is None or target.stat().st_size == entry["size"]
        if observed == entry["sha256"] and size_ok:
            binaries[name] = {"status": "MATCH",
                              "expected_sha256": entry["sha256"],
                              "observed_sha256": observed}
        else:
            binaries[name] = {"status": "MISMATCH",
                              "expected_sha256": entry["sha256"],
                              "observed_sha256": observed}
    stale = [n for n, b in binaries.items() if b["status"] != "MATCH"]
    claims = man["test_claims"]
    return {"project": man["project"],
            "toolchain_recorded": man["toolchain"],
            "scope": SCOPE_NOTE,
            "binaries": binaries,
            "test_claims": {"total": len(claims),
                            "claimed_pass": sum(c["verdict"] == "pass"
                                                for c in claims),
                            "claimed_fail": sum(c["verdict"] == "fail"
                                                for c in claims),
                            "trust": "UNVERIFIED_CLAIM",
                            "note": ("verdicts are the manifest author's "
                                     "unverified assertion; they are counted, "
                                     "never evaluated")},
            "verdict": "STALE" if stale else "CONSISTENT",
            "stale_binaries": sorted(stale),
            "release_eligible": False}


def write_manifest(workspace: str | Path, project: str, toolchain: str,
                 names: list[str] | None = None) -> dict[str, Any]:
    """Build a v1 manifest by hashing binaries in a workspace directory.

    ``names`` selects which files to cover (default: every regular file
    directly inside the workspace, sorted). Names are confined exactly
    like check time: anything escaping the workspace is refused.
    """
    root = Path(workspace)
    if not root.is_dir():
        raise ExternalManifestError(f"workspace is not a directory: {root}")
    if not isinstance(project, str) or not project.strip():
        raise ExternalManifestError("project must be a non-empty string")
    if not isinstance(toolchain, str) or not toolchain.strip():
        raise ExternalManifestError("toolchain must be a non-empty string")
    if names is None:
        names = sorted(p.name for p in root.iterdir() if p.is_file())
    if not names:
        raise ExternalManifestError("workspace has no files to cover")
    binaries = {}
    for name in names:
        target = _confined(root, name)
        if not target.is_file():
            raise ExternalManifestError(
                f"binary {name!r} not found in the workspace")
        binaries[name] = {"sha256": hashlib.sha256(
            target.read_bytes()).hexdigest(),
            "size": target.stat().st_size}
    return validate_manifest(
        {"external_manifest_version": EXTERNAL_MANIFEST_VERSION,
         "project": project.strip(), "toolchain": toolchain.strip(),
         "binaries": binaries, "test_claims": []})


def render_text(report: dict[str, Any]) -> str:
    """One-screen human summary of a workspace check."""
    lines = [f"external manifest: {report['project']}",
             f"toolchain (recorded, not verified): {report['toolchain_recorded']}",
             f"scope: {report['scope']}"]
    for name in sorted(report["binaries"]):
        got = report["binaries"][name]
        if got["status"] == "MATCH":
            lines.append(f"  MATCH    {name}")
        elif got["status"] == "ABSENT":
            lines.append(f"  ABSENT   {name} (expected {got['expected_sha256'][:12]}…)")
        else:
            lines.append(f"  MISMATCH {name} (expected {got['expected_sha256'][:12]}…, "
                         f"observed {got['observed_sha256'][:12]}…)")
    claims = report["test_claims"]
    lines.append(f"test claims: {claims['claimed_pass']}/{claims['total']} claimed pass "
                 f"[{claims['trust']}]")
    lines.append(f"verdict: {report['verdict']}; release_eligible: False")
    return "\n".join(lines) + "\n"
