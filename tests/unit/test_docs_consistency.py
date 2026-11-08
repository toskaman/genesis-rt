# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M1 (§5.2): user-facing numerical claims stay mutually consistent
and pinned to measured code facts. Fast checks only (no full-suite recount;
absolute totals come from measured runs + CI and are updated with them)."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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
    b = _one(r"green, (\d+) tests", _read("docs/jury/REPRODUCE.md"), "reproduce total")
    c = _one(r"Expect green \((\d+) tests", _read("docs/jury/START_HERE.md"), "start-here total")
    d = _one(r"(\d+)-test host suite", _read("docs/business/COMMERCIAL_VISION.md"), "commercial total")
    assert a == b == c == d, (a, b, c, d)


def test_sdk_free_counts_agree_across_docs():
    a = _one(r"SDK-free: (\d+) \+ (\d+) honest skips", _read("docs/jury/JUDGE_SCORECARD.md"), "scorecard sdk-free")
    b = _one(r"SDK-free [^:]*: (\d+) \+ (\d+) honest skips", _read("docs/jury/REPRODUCE.md"), "reproduce sdk-free")
    c = _one(r"SDK-free[^:]*: (\d+) passed \+ (\d+) honest skips", _read("docs/jury/START_HERE.md"), "start-here sdk-free")
    d = _one(r"SDK-free: (\d+) passed \+ (\d+) honest skips", _read("docs/business/COMMERCIAL_VISION.md"), "commercial sdk-free")
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
                  "## 6. Privacy guidance + anonymization protocol",
                  "pilot-onboarding.md",
                  "--plan"):
        assert token in text, token
    onboarding = _read("docs/business/pilot-onboarding.md")
    for token in ("Recording procedure", "lane order", "anonymization",
                  "consent"):
        assert token in onboarding, token


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
    # Collected totals are never reported as pass counts (CLAIMS.md):
    # the devpost line states the collected total, the per-machine SDK
    # caveat, and the measured SDK-less outcome.
    m = re.search(r"# (\d+) collected; .*SDK-less CI: (\d+) passed \+ "
                  r"(\d+) honest skips", text)
    assert m is not None, "devpost count line missing"
    assert (m.group(1), m.group(2), m.group(3)) == \
        (str(facts.TESTS_WITH_SDK), str(facts.TESTS_SDK_FREE_PASSED),
         str(facts.TESTS_SDK_FREE_SKIPS)), m.groups()
    assert f"# {facts.TESTS_WITH_SDK} pass, 0 skip" not in text


def test_limitations_e2e_wording_current():
    text = _read("docs/jury/KNOWN_LIMITATIONS.md")
    assert "browser E2E is pending" not in text
    assert "real-browser E2E runs in CI" in text


def test_video_claim_matches_facts():
    """Wave 12 §5: current docs pin the voiced submission video."""
    from genesis_rt import facts
    assert (ROOT / facts.VIDEO_FILE).is_file()
    for rel in ("docs/compliance-matrix.md", "docs/demo-video-plan.md",
                "docs/CLAIMS.md", "docs/devpost-draft.md", "README.md"):
        assert facts.VIDEO_FILE in _read(rel), rel
    for rel in ("docs/demo/MEDIA_VALIDATION_W12.md", "docs/CLAIMS.md"):
        assert str(facts.VIDEO_DURATION_S) in _read(rel), rel


def test_no_stale_video_handoff_claims():
    """Wave 12 §5: edit + voice are done; only upload is pending."""
    matrix = _read("docs/compliance-matrix.md")
    assert "42 s genuine footage" not in matrix
    assert "edit + voice + publication = owner handoff, still pending" not in matrix
    plan = _read("docs/demo-video-plan.md")
    assert "Voice track + final edit +" not in plan
    assert "genesis-rt-demo-w12.mp4" in plan


def test_readme_covers_flagship_capabilities():
    """Wave 12 §5: README must surface the five newer capabilities."""
    text = _read("README.md")
    for token in ("Contract-aware native verification",
                  "qnx8-x86_64-w11-before",
                  "IPC execution timeline",
                  "ci_ir_check.py",
                  "review dossier",
                  "docs/CLAIMS.md"):
        assert token in text, token


def test_devpost_packs_and_checks_current():
    """Wave 12 §5: devpost points at the w11 packs, not the legacy one."""
    text = _read("docs/devpost-draft.md")
    assert "qnx8-x86_64-w11-before" in text
    assert "qnx8-x86_64-w11-after" in text
    assert "b22cea1" not in text
    assert "9/9 native fault-injection" in text
    assert "PUBLICATION_HANDOFF_W12" in text


def test_e2e_count_matches_collected():
    """Wave 12 §5: registry E2E count equals collected browser tests."""
    from genesis_rt import facts
    if importlib.util.find_spec("playwright") is None:
        pytest.skip("playwright not installed (documented-optional e2e dep; "
                    "see INSTALL.md .[e2e])")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/e2e",
         "-o", "addopts=", "--collect-only", "-q", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=180)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    assert m.group(1) == str(facts.E2E_BROWSER_TESTS), m.group(1)


def test_claims_registry_matches_facts():
    """Wave 12 §5: docs/CLAIMS.md agrees with facts.py pins."""
    from genesis_rt import facts
    text = _read("docs/CLAIMS.md")
    for token in (str(facts.TESTS_WITH_SDK),
                  str(facts.TESTS_SDK_FREE_PASSED),
                  str(facts.ADVERSARIAL_TESTS),
                  facts.PACK_BEFORE, facts.PACK_AFTER,
                  facts.VIDEO_FILE, "PUBLICATION_HANDOFF_W12.md"):
        assert token in text, token
    assert (ROOT / facts.PACK_BEFORE / "verify.py").is_file()
    assert (ROOT / facts.PACK_AFTER / "verify.py").is_file()


def test_safety_disclaimer_present_not_certified():
    """Wave 12 §5: no certification language without the disclaimer."""
    for rel in ("README.md", "docs/CLAIMS.md", "docs/devpost-draft.md"):
        text = _read(rel)
        assert "no safety certification" in text.lower(), rel
        assert "certified" not in text.lower(), rel


def test_total_count_matches_collected():
    """Registry total equals the collected suite (catches stale claims)."""
    from genesis_rt import facts
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-o", "addopts=",
         "--collect-only", "-q", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=300)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    assert int(m.group(1)) == facts.TESTS_WITH_SDK, (m.group(1),
                                                     facts.TESTS_WITH_SDK)
    assert facts.TESTS_SDK_FREE_PASSED + facts.TESTS_SDK_FREE_SKIPS == \
        facts.TESTS_WITH_SDK


def test_qnx_workflow_does_not_overclaim_target_run():
    """TITAN: a build-only QNX lane must say so; it may only drop the
    NOT EXECUTED marker once it actually runs the target verifier."""
    wf = _read(".github/workflows/qnx.yml")
    runs_campaign = "qnx_target.py verify" in wf
    if not runs_campaign:
        assert "NOT EXECUTED" in wf
        assert "BUILD-ONLY" in wf
        assert "build-and-run" not in wf


def test_video_status_deferred_everywhere():
    """TITAN: no current-facing doc may present the W12 cut as final."""
    for rel in ("README.md", "docs/CLAIMS.md", "docs/compliance-matrix.md",
                "docs/devpost-draft.md", "docs/jury/JUDGE_SCORECARD.md"):
        text = _read(rel)
        assert re.search(r"DEFERRED", text), rel
    assert "- **Submission video**:" not in _read("README.md")
    assert "- Submission video:" not in _read("docs/CLAIMS.md")


def test_limitations_match_rfc1982_implementation():
    """TITAN: limitations must not call wrap handling 'documented only'
    while guard_policy.c implements RFC 1982 serial arithmetic."""
    lim = _read("docs/limitations-and-safety.md")
    assert "RFC 1982" in _read("target/qnx8/common/guard_policy.c")
    assert "documents the boundary instead" not in lim
    assert "RFC 1982" in lim


def test_claims_e2e_count_matches_facts():
    """Ascension: CLAIMS once said 21 E2E while 24 were collected."""
    from genesis_rt import facts
    m = re.search(r"Real-browser E2E: \*\*(\d+)\*\* collected", _read("docs/CLAIMS.md"))
    assert m is not None
    assert int(m.group(1)) == facts.E2E_BROWSER_TESTS


def test_sched_speedup_claim_withdrawn():
    """Omega2 §4: the 5-Nov RT-priority speedup did not replicate on
    8 Nov; current-facing docs must carry the inconclusive reading,
    never the ~45%/~65% generalization (frozen audits exempt)."""
    for rel in ("docs/jury/WHY_QNX.md",
                "docs/jury/TECHNICAL_EVIDENCE.md",
                "docs/perf-baseline.md"):
        text = _read(rel)
        assert "45%" not in text, rel
        assert "65%" not in text, rel
        assert "no general" in text, rel


def test_current_packs_primary_w11_historical():
    """Omega3 §4.7: current evidence paths are the Omega2 packs; W11
    references survive only under a Historical marker."""
    from genesis_rt import facts
    claims = _read("docs/CLAIMS.md")
    assert facts.PACK_BEFORE in claims and facts.PACK_AFTER in claims
    hist = claims.index("Historical")
    for token in ("w11-before", "w11-after"):
        for m in re.finditer(re.escape(token), claims):
            assert m.start() > hist, f"W11 ref outside history: {token}"
    devpost = _read("docs/devpost-draft.md")
    assert facts.PACK_BEFORE in devpost and facts.PACK_AFTER in devpost
    hist = devpost.index("Historical")
    for token in ("w11-before", "w11-after"):
        for m in re.finditer(re.escape(token), devpost):
            assert m.start() > hist, f"W11 ref outside history: {token}"


def test_release_readiness_postmerge_recorded():
    """Omega3 §4.7: the Omega2 readiness audit records the completed
    merge (past SHAs are immutable history, not brittle pins)."""
    text = _read("docs/audits/OMEGA2_RELEASE_READINESS.md")
    assert "Post-merge verification" in text
    assert "PR #11 merged" in text
    assert "9098564" in text  # merge commit, immutable
    assert "42492043838" in text  # main CI run, immutable
    assert "Merge plan (pre-merge, kept historical)" in text


def test_ai_eval_v5_disclosed_current_docs():
    """Omega3 §4.7: current docs disclose v5 and its open gaps —
    v4 must never be cherry-picked alone."""
    assert "v5" in _read("docs/CLAIMS.md")
    devpost = _read("docs/devpost-draft.md")
    assert "v5" in devpost
    assert "OPEN" in devpost or "open gaps" in devpost
    assert "72" in devpost  # v4+v5 untouched total


def test_devpost_not_submitted_and_video_deferred():
    """Omega3 §4.7: the draft never reads as a submitted entry."""
    devpost = _read("docs/devpost-draft.md")
    assert "NOT submitted" in devpost
    assert "DEFERRED" in devpost


def test_impact_status_not_measured_pinned():
    """Omega3 §4.7: the no-human-data status cannot silently flip."""
    impact = _read("docs/ascension/IMPACT_STUDY.md")
    assert "HUMAN USER BENEFIT NOT YET MEASURED" in impact
    assert "zero invitations sent" in _read("docs/business/pilot-study.md")


def test_unsigned_semantics_disclosed():
    """Omega3 §4.7: hash-only trust is disclosed where packs are
    claimed (integrity != attestation)."""
    claims = _read("docs/CLAIMS.md")
    assert "UNSIGNED" in claims and "hash-only" in claims
    devpost = _read("docs/devpost-draft.md")
    assert "hash-only" in devpost


def test_pilot_durations_consistent():
    """Omega3 §4.7: the 90-120 min/lane protocol estimate is the
    only current figure; the 45-min owner shortcut is corrected."""
    pilot = _read("docs/business/pilot-study.md")
    impact = _read("docs/ascension/IMPACT_STUDY.md")
    assert "90–120 min per lane" in pilot
    assert "90–120 min/lane" in impact
    # The correction note quotes the old figure; pin the live headers only.
    assert "(owner, ~2 × 45 min)" not in impact
    assert "60–90 min/lane, not 45" in impact


def test_no_future_dated_completed_audits():
    """Omega3 §4.7: the 9-Nov misdate in the 8-Nov baseline stays fixed."""
    text = _read("docs/audits/ASCENSION_OMEGA2_BASELINE.md")
    # The correction note quotes the old date; pin the live header only.
    assert "read-only, 9 Nov 2026" not in text
    assert "## Wave-1 audit (8 agents, read-only, 8 Nov 2026)" in text
    assert "Correction 8 Nov 2026 (Omega3" in text


def _load_analyzer():
    spec = importlib.util.spec_from_file_location(
        "omega3_analyzer_pin",
        ROOT / "bench" / "productivity" / "analyze_pilot.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["omega3_analyzer_pin"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_quick_tier_doc_matches_code():
    """Omega3 §6.2: the documented quick triple equals the code's
    QUICK_TASKS, and QUICK is documented as never COMPLETE."""
    ap = _load_analyzer()
    assert tuple(ap.QUICK_TASKS) == ("generate", "campaign", "evidence")
    pilot = _read("docs/business/pilot-study.md")
    for task in ap.QUICK_TASKS:
        assert f"`{task}`" in pilot
    assert "QUICK_PAIRED_PILOT" in pilot
    assert "NEVER equivalent" in pilot
    assert "--quick" in pilot
