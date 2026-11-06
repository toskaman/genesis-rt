#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""CI adoption bridge (Wave 11 §11, hardened Wave 12 §7): validate
changed Machine IRs + report impact.

Designed for a CI step on pull requests / pushes: given the IR files a
change touches, every file is validated and diffed against its base
revision. Output is a machine-readable JSON verdict plus, on GitHub
Actions, a step-summary table for the code-review workflow.

This is validation + change-impact only. It is NOT release eligibility:
release stays with the full gate over every declared scenario
(``gate.evaluate`` refuses reduced coverage), and native QNX evidence
still needs an authorized target runner.

Change semantics:
- modified / added: validated, diffed against the base blob when present;
- renamed: diffed against the OLD base path (``-M`` rename detection);
- deleted with a valid base revision: reported ``deleted``, verdict-neutral
  (nothing left to validate; removal impact is recorded, not failed);
- deleted with no (or an invalid) base revision: invalid, fail-closed;
- valid JSON that was never an IR (no schema markers here or at base):
  ``not an IR (skipped)``, verdict-neutral; a file that LOSES its IR
  markers is invalid, fail-closed;
- absolute paths and ``..`` escapes are rejected without touching disk.

Exit codes: 0 = all given IRs valid (or nothing to check);
2 = an IR is invalid, unreadable, or the base revision is unusable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.impact import analyze_impact  # noqa: E402
from genesis_rt.ir import IRValidationError  # noqa: E402
from genesis_rt.projects import validate_any  # noqa: E402
from genesis_rt.proofos import build_plan  # noqa: E402

IR_GLOBS = ("examples/**/*.json", "projects/**/*.json")

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _clean(value: object) -> str:
    """Strip control characters before interpolating into summaries."""
    return _CTRL_RE.sub("?", str(value))


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, timeout=60)


def _git_bytes(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          timeout=60)


def _is_safe_rel(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    if re.match(r"^[a-zA-Z]:", norm) or norm.startswith("//"):
        return False  # Windows drive-absolute or UNC path
    pure = PurePosixPath(norm)
    return (not pure.is_absolute() and ".." not in pure.parts
            and norm == pure.as_posix() and bool(pure.parts))


def _looks_like_ir(doc: object) -> bool:
    return (isinstance(doc, dict)
            and doc.get("schema_version") in (1, 2))


def changed_ir_files(base: str) -> tuple[list[tuple[str, str | None, str]] | None, str]:
    """(new, old, kind) IR changes between base and HEAD.

    ``(None, reason)`` when the base is unusable: callers then fall
    back to validating every IR. Rename detection (``-M``) maps the
    new path back to its old base path so the diff stays meaningful.
    NUL-separated output keeps hostile filenames parseable.
    """
    probe = _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    if probe.returncode != 0:
        return None, f"base ref {base!r} does not resolve"
    diff = _git_bytes(["diff", "-M", "--name-status", "-z",
                       f"{base}...HEAD", "--", *IR_GLOBS])
    if diff.returncode != 0:
        err = diff.stderr.decode("utf-8", "replace").strip()[:200]
        return None, f"git diff failed: {err}"
    records = diff.stdout.decode("utf-8", "replace").split("\x00")
    out: list[tuple[str, str | None, str]] = []
    i = 0
    while i < len(records):
        status = records[i]
        i += 1
        if not status:
            continue
        kind = status[0]
        if kind in ("R", "C"):
            if i + 1 >= len(records):
                break
            old, new = records[i], records[i + 1]
            i += 2
            out.append((new, old, "renamed" if kind == "R" else "copied"))
        else:
            if i >= len(records):
                break
            path = records[i]
            i += 1
            out.append((path, None,
                        {"A": "added", "D": "deleted", "M": "modified",
                         "T": "modified"}.get(kind, "modified")))
    return out, ""


def all_ir_files() -> list[str]:
    found: list[str] = []
    for pattern in IR_GLOBS:
        found.extend(sorted(str(p.relative_to(REPO_ROOT)).replace("\\", "/")
                            for p in REPO_ROOT.glob(pattern) if p.is_file()))
    return found


def _read_json(path: Path) -> tuple[object, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, "file not found"
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc}"
    except OSError as exc:
        return None, f"unreadable: {exc}"


def _base_blob(rel: str, base: str) -> tuple[object | None, bool]:
    """(parsed base blob or None, whether the blob exists)."""
    show = _git(["show", f"{base}:{rel}"])
    if show.returncode != 0:
        return None, False
    try:
        return json.loads(show.stdout), True
    except json.JSONDecodeError:
        return None, True


def check_file(rel: str, base: str | None,
               old_rel: str | None = None) -> dict:
    """Validate one IR + diff it against base (when available)."""
    rel = rel.replace("\\", "/")
    entry: dict = {"path": rel, "valid": False, "error": "",
                   "status": "unchecked", "retest": [],
                   "limits_changed": False, "requirements_changed": 0,
                   "renamed_from": old_rel, "ir_sha256_before": None,
                   "ir_sha256_after": None}
    if not _is_safe_rel(rel) or (old_rel is not None
                                 and not _is_safe_rel(old_rel)):
        entry["error"] = "unsafe path rejected (absolute or '..' escape)"
        return entry
    doc, err = _read_json(REPO_ROOT / rel)
    base_doc: object | None = None
    base_exists = False
    if base is not None:
        base_doc, base_exists = _base_blob(old_rel or rel, base)
    if err:  # missing from the worktree: deletion or never-existed
        if err == "file not found" and base_exists and isinstance(
                base_doc, dict):
            try:
                validate_any(base_doc)
            except (IRValidationError, ValueError, TypeError, KeyError) as exc:
                entry["error"] = (f"deleted but base revision was "
                                  f"invalid: {exc}")
                return entry
            entry["valid"] = True
            entry["status"] = "deleted"
            return entry
        entry["error"] = err
        return entry
    if not _looks_like_ir(doc):
        if base_doc is None or not _looks_like_ir(base_doc):
            entry["valid"] = True  # data file, never an IR: ignore
            entry["status"] = "not an IR (skipped)"
            return entry
        entry["error"] = ("IR markers lost: valid IR at base, "
                          "unrecognisable document now")
        return entry
    try:
        _version, _ir = validate_any(doc)
    except (IRValidationError, ValueError, TypeError, KeyError) as exc:
        entry["error"] = f"IR validation failed: {exc}"
        return entry
    entry["valid"] = True
    if base is None:
        entry["status"] = "valid (no base diff)"
        return entry
    if not base_exists:
        entry["status"] = "added (no base revision)"
        return entry
    if not isinstance(base_doc, dict):
        entry["status"] = "valid (base not JSON, no diff)"
        return entry
    diff_entry(entry, base_doc, doc)
    if old_rel is not None and entry["status"] in ("changed", "unchanged"):
        entry["status"] = (f"renamed from {old_rel} "
                           f"({entry['status']})")
    return entry


def diff_entry(entry: dict, before: object, doc: object) -> None:
    """Fill status/retest by diffing two validated IR docs (pure part)."""
    try:
        report = analyze_impact(before, doc)
    except (IRValidationError, ValueError, TypeError, KeyError) as exc:
        entry["status"] = f"valid (base uncomparable: {exc})"
        return
    entry["ir_sha256_before"] = report["before"]["ir_sha256"]
    entry["ir_sha256_after"] = report["after"]["ir_sha256"]
    changed = entry["ir_sha256_before"] != entry["ir_sha256_after"]
    entry["status"] = "changed" if changed else "unchanged"
    if changed:
        entry["retest"] = report["retest"]
        entry["limits_changed"] = bool(report["limits"].get("changed"))
        reqs = report["requirements"]
        entry["requirements_changed"] = len(reqs["added"]) + len(
            reqs["removed"]) + len(reqs["changed"])


def render_summary(report: dict) -> str:
    lines = ["### GENESIS IR check", ""]
    if not report["files"]:
        lines.append("No Machine IR files to check.")
        return "\n".join(lines) + "\n"
    lines += ["| IR | status | retest |",
              "| --- | --- | --- |"]
    for entry in report["files"]:
        retest = ("`" + "`, `".join(_clean(r) for r in entry["retest"])
                  + "`" if entry["retest"] else "—")
        detail = _clean(entry["status"]) + (
            f": {_clean(entry['error'])}" if entry["error"] else "")
        lines.append(f"| `{_clean(entry['path'])}` | {detail} | {retest} |")
    lines += ["",
              f"Verdict: **{report['verdict']}** "
              "(validation + change impact only; release eligibility "
              "needs the full gate and, for QNX claims, a target run)."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate changed Machine IRs and report retest impact.")
    parser.add_argument("paths", nargs="*",
                        help="IR files to check (default: from git diff)")
    parser.add_argument("--base", default=None,
                        help="base git ref for the diff "
                             "(default: $GENESIS_CI_BASE or detect)")
    parser.add_argument("--out", default="ir-ci-report.json",
                        help="JSON report path (default: ir-ci-report.json)")
    parser.add_argument("--plan-out", default=None,
                        help="optional ProofOS verification-plan JSON path")
    args = parser.parse_args(argv)

    base = args.base or os.environ.get("GENESIS_CI_BASE", "")
    changes: list[tuple[str, str | None, str]] = []
    fallback_note = ""
    if not args.paths:
        if not base:
            base = "HEAD~1"
        found, reason = changed_ir_files(base)
        if found is None:  # unusable base: validate everything instead
            fallback_note = (f"{reason}; falling back to all IRs under "
                             "examples/ and projects/")
            changes = [(p, None, "full-scan") for p in all_ir_files()]
            base = None
        else:
            changes = found
    else:
        changes = [(p, None, "explicit") for p in args.paths]
    if base is not None and args.paths:
        probe = _git(["rev-parse", "--verify", "--quiet",
                      f"{base}^{{commit}}"])
        if probe.returncode != 0:
            base = None  # explicit paths + bad base: validate only

    report = {"verdict": "PASS", "base": base, "files": [],
              "fallback_note": fallback_note}
    for rel, old_rel, _kind in changes:
        entry = check_file(rel.replace("\\", "/"), base,
                           old_rel.replace("\\", "/")
                           if old_rel else None)
        report["files"].append(entry)
        if not entry["valid"]:
            report["verdict"] = "FAIL"
    out_path = Path(args.out)
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out_path.write_text(report_text, encoding="utf-8")

    if args.plan_out:
        import hashlib

        def _sha(ref: str) -> str | None:
            probe = _git(["rev-parse", "--verify", "--quiet",
                          f"{ref}^{{commit}}"])
            return probe.stdout.strip() or None \
                if probe.returncode == 0 else None

        plan = build_plan(
            source_commit=_sha("HEAD"),
            base_commit=_sha(base) if base else None,
            changes=report["files"],
            report_sha256=hashlib.sha256(
                report_text.encode("utf-8")).hexdigest())
        plan_path = Path(args.plan_out)
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True)
                             + "\n", encoding="utf-8")
        print(f"plan: {plan_path} stage={plan['stage']} "
              f"id={plan['plan_id'][:12]}")

    summary = render_summary(report)
    step_file = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if step_file:
        try:
            with open(step_file, "a", encoding="utf-8") as fh:
                fh.write(summary)
        except OSError as exc:
            print(f"warning: cannot write step summary: {exc}")
    print(summary)
    print(f"report: {out_path} verdict={report['verdict']} "
          f"files={len(report['files'])}")
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
