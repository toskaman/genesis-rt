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


def test_limitations_match_judge_mode_implementation():
    """F4 anti-rot: limitations must not claim Judge Mode is missing while
    Studio ships a guided Judge tab (or vice versa)."""
    studio = _read("ui/studio.html")
    lim = _read("docs/jury/KNOWN_LIMITATIONS.md")
    score = _read("docs/jury/JUDGE_SCORECARD.md")
    assert "function judgeStages()" in studio
    assert "No guided Judge Mode yet" not in score
    assert "no guided Judge Mode yet" not in lim


def test_limitations_match_twin_ab_implementation():
    """F4 anti-rot: limitations must not claim A/B twin replay is missing
    while Studio paints two passport tracks on one cursor (or vice versa)."""
    studio = _read("ui/studio.html")
    lim = _read("docs/jury/KNOWN_LIMITATIONS.md")
    assert "twincv-b" in studio and "twinCompareTexts" in studio
    assert "no synchronized A/B twin replay" not in lim


def test_no_model_truncation_markers_in_shipped_docs():
    """Wave 10 Sprint D1: two docs were once committed carrying a pasted
    model-output truncation marker, silently dropping their tail
    sections. Fail if that marker shape ever recurs in shipped docs."""
    pat = re.compile(rb"\.\.\.\[truncated \d+ chars\]")
    hits = []
    targets = [ROOT / "README.md", ROOT / "ui" / "studio.html"]
    targets += sorted((ROOT / "docs").rglob("*.md"))
    for f in targets:
        if pat.search(f.read_bytes()):
            hits.append(str(f.relative_to(ROOT)))
    assert not hits, f"truncation marker in shipped docs: {hits}"


def test_competitive_landscape_grading_vocabulary():
    """F9 anti-rot: the competitive matrix must carry evidence grades
    (vendor-doc / assessment / hypothesis) and keep unmeasured
    comparisons out of matrix form."""
    text = _read("docs/business/COMPETITIVE_LANDSCAPE.md")
    for token in ("vendor-doc", "assessment", "hypothesis"):
        assert token in text, token
    assert "| Learning curve |" not in text
    assert "| Integration burden |" not in text
    assert "| Cost model |" not in text


def test_pilot_kit_covers_wave10_checklist():
    """Sprint D4 (§14): the pilot kit must ship the invitation, the
    reviewer checklist, and the anonymization protocol — not just
    the measurement templates."""
    text = _read("docs/business/pilot-study.md")
    for token in ("## 9. Technical invitation",
                  "zero invitations sent so far",
                  "## 10. Reviewer checklist",
                  "## 6. Privacy guidance + anonymization protocol"):
        assert token in text, token


def test_adversarial_count_matches_collected():
    claimed = _one(r"(\d+)-test adversarial", _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard adversarial")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_passport_adversarial.py",
         "-o", "addopts=", "--collect-only", "-q", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=120)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    assert (m.group(1),) == claimed, (m.group(1), claimed)


def test_docs_match_facts_source_of_truth():
    from genesis_rt import facts
    total = _one(r"(\d+) host tests", _read("docs/jury/JUDGE_SCORECARD.md"),
                 "scorecard total")
    assert total == (str(facts.TESTS_WITH_SDK),), total
    adv = _one(r"(\d+)-test adversarial",
               _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard adversarial")
    assert adv == (str(facts.ADVERSARIAL_TESTS),), adv
    free = _one(r"SDK-free: (\d+) \+ (\d+) honest skips",
                _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard sdk-free")
    assert free == (str(facts.TESTS_SDK_FREE_PASSED),
                    str(facts.TESTS_SDK_FREE_SKIPS)), free


def test_devpost_counts_match_facts():
    from genesis_rt import facts
    text = _read("docs/devpost-draft.md")
    m = re.search(r"# (\d+) pass, 0 skip .*SDK-less CI: (\d+) passed \+ "
                  r"(\d+) honest skips", text)
    assert m is not None, "devpost count line missing"
    assert (m.group(1), m.group(2), m.group(3)) == \
        (str(facts.TESTS_WITH_SDK), str(facts.TESTS_SDK_FREE_PASSED),
         str(facts.TESTS_SDK_FREE_SKIPS)), m.groups()


def test_limitations_e2e_wording_current():
    text = _read("docs/jury/KNOWN_LIMITATIONS.md")
    assert "browser E2E is pending" not in text
    assert "real-browser E2E runs in CI" in text
