# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M1 (§5.2): user-facing numerical claims stay mutually consistent
and pinned to measured code facts. Fast checks only (no full-suite recount;
absolute totals come from measured runs + CI and are updated with them)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from genesis_rt.provenance import EXPECTED_TARGET_CHECKS

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _one(pat: str, text: str, label: str) -> tuple[str, ...]:
    m = re.search(pat, text)
    assert m is not None, f"claim pattern missing: {label}"
    return m.groups()


def test_suite_total_agrees_across_docs():
    a = _one(r"(\d+) host tests", _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard total")
    b = _one(r"(\d+) tests w/ SDK", _read("docs/jury/REPRODUCE.md"), "reproduce total")
    c = _one(r"Expect green \((\d+) with SDK", _read("docs/jury/START_HERE.md"), "start-here total")
    d = _one(r"~(\d+)-test host suite", _read("docs/business/COMMERCIAL_VISION.md"), "commercial total")
    assert a == b == c == d, (a, b, c, d)


def test_sdk_free_counts_agree_across_docs():
    a = _one(r"SDK-free: (\d+) \+ (\d+) honest skips", _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard sdk-free")
    b = _one(r"else (\d+) \+ (\d+) honest skips", _read("docs/jury/REPRODUCE.md"), "reproduce sdk-free")
    c = _one(r"SDK-free: (\d+) passed \+ (\d+) honest skips", _read("docs/jury/START_HERE.md"), "start-here sdk-free")
    d = _one(r"SDK-free (\d+) passed \+ (\d+) honest skips", _read("docs/business/COMMERCIAL_VISION.md"), "commercial sdk-free")
    assert a == b == c == d, (a, b, c, d)


def test_matrix_claim_matches_provenance_pin():
    assert len(EXPECTED_TARGET_CHECKS) == 16
    for rel in ("README.md", "docs/jury/JUDGE_SCORECARD.md", "docs/limitations-and-safety.md"):
        assert "16/16" in _read(rel) or "16-step" in _read(rel), rel


def test_fault_campaign_counts_match_examples():
    claimed = _one(r"\(AMR (\d+), conveyor (\d+), cell (\d+)\)", _read("README.md"), "readme campaign")
    got = []
    for rel in ("examples/amr-demo/machine-ir.json",
                "examples/conveyor-demo/machine-ir.json",
                "examples/cell-demo/cell-ir.json"):
        doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        got.append(str(len(doc["verification"]["scenarios"])))
    assert tuple(got) == claimed, (got, claimed)


def test_planning_eval_count_matches_dataset():
    claimed = _one(r"(\d+)-case planning eval at (\d+)/(\d+)",
                   _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard eval")
    cases = json.loads((ROOT / "evals" / "planning_eval.json").read_text(encoding="utf-8"))["cases"]
    assert claimed == (str(len(cases)),) * 3 == ("28", "28", "28"), (claimed, len(cases))


def test_adversarial_count_matches_collected():
    claimed = _one(r"(\d+)-test adversarial", _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard adversarial")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_passport_adversarial.py",
         "-o", "addopts=", "--collect-only", "-q", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=120)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    assert (m.group(1),) == claimed, (m.group(1), claimed)
