#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""CI adoption bridge (Wave 11 §11): validate changed Machine IRs + report impact.

Designed for a CI step on pull requests / pushes: given the IR files a
change touches, every file is validated and diffed against its base
revision. Output is a machine-readable JSON verdict plus, on GitHub
Actions, a step-summary table for the code-review workflow.

This is validation + change-impact only. It is NOT release eligibility:
release stays with the full gate over every declared scenario
(``gate.evaluate`` refuses reduced coverage), and native QNX evidence
still needs an authorized target runner.

Exit codes: 0 = all given IRs valid (or nothing to check);
2 = an IR is invalid, unreadable, or the base revision is unusable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt.impact import analyze_impact  # noqa: E402
from genesis_rt.ir import IRValidationError  # noqa: E402
from genesis_rt.projects import validate_any  # noqa: E402

IR_GLOBS = ("examples/*/*.json", "projects/*/*.json")


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, timeout=60)


def changed_ir_files(base: str) -> tuple[list[str] | None, str]:
    """IR paths changed between base and HEAD. (None, reason) when the
    base is unusable: callers then fall back to validating every IR."""
    probe = _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    if probe.returncode != 0:
        return None, f"base ref {base!r} does not resolve"
    diff = _git(["diff", "--name-only", f"{base}...HEAD", "--",
                 *IR_GLOBS])
    if diff.returncode != 0:
        return None, f"git diff failed: {diff.stderr.strip()[:200]}"
    paths = [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]
    return paths, ""


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


def check_file(rel: str, base: str | None) -> dict:
    """Validate one IR + diff it against base (when available)."""
    entry: dict = {"path": rel, "valid": False, "error": "",
                   "status": "unchecked", "retest": [],
                   "limits_changed": False, "requirements_changed": 0}
    doc, err = _read_json(REPO_ROOT / rel)
    if err:
        entry["error"] = err
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
    show = _git(["show", f"{base}:{rel}"])
    if show.returncode != 0:
        entry["status"] = "added (no base revision)"
        return entry
    try:
        before = json.loads(show.stdout)
    except json.JSONDecodeError:
        entry["status"] = "valid (base not JSON, no diff)"
        return entry
    diff_entry(entry, before, doc)
    return entry


def diff_entry(entry: dict, before: object, doc: object) -> None:
    """Fill status/retest by diffing two validated IR docs (pure part)."""
    try:
        report = analyze_impact(before, doc)
    except (IRValidationError, ValueError, TypeError, KeyError) as exc:
        entry["status"] = f"valid (base uncomparable: {exc})"
        return
    changed = report["before"]["ir_sha256"] != report["after"]["ir_sha256"]
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
        retest = ("`" + "`, `".join(entry["retest"]) + "`"
                  if entry["retest"] else "—")
        detail = entry["status"] + (f": {entry['error']}"
                                    if entry["error"] else "")
        lines.append(f"| `{entry['path']}` | {detail} | {retest} |")
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
    args = parser.parse_args(argv)

    base = args.base or os.environ.get("GENESIS_CI_BASE", "")
    paths = list(args.paths)
    fallback_note = ""
    if not paths:
        if not base:
            base = "HEAD~1"
        found, reason = changed_ir_files(base)
        if found is None:  # unusable base: validate everything instead
            fallback_note = (f"{reason}; falling back to all IRs under "
                             "examples/ and projects/")
            paths = all_ir_files()
            base = None
        else:
            paths = found
    if base is not None and args.paths:
        probe = _git(["rev-parse", "--verify", "--quiet",
                      f"{base}^{{commit}}"])
        if probe.returncode != 0:
            base = None  # explicit paths + bad base: validate only

    report = {"verdict": "PASS", "base": base, "files": [],
              "fallback_note": fallback_note}
    for rel in paths:
        entry = check_file(rel.replace("\\", "/"), base)
        report["files"].append(entry)
        if not entry["valid"]:
            report["verdict"] = "FAIL"
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

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
