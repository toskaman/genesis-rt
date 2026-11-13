# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M1 (§5.2): user-facing numerical claims stay mutually consistent
and pinned to measured code facts. Fast checks only (no full-suite recount;
absolute totals come from measured runs + CI and are updated with them)."""
from __future__ import annotations

import importlib.util
import json
import os
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
    """OMEGA8 purge: no video file shipped; docs say WITHDRAWN + DEFERRED."""
    assert not list((ROOT / "docs" / "demo").rglob("*.mp4"))
    assert not list((ROOT / "docs" / "demo").rglob("*.webm"))
    for rel in ("docs/compliance-matrix.md", "docs/demo-video-plan.md",
                "docs/CLAIMS.md", "docs/devpost-draft.md", "README.md"):
        assert "WITHDRAWN" in _read(rel), rel


def test_causal_video_claims_match_facts():
    """OMEGA8 purge: withdrawn cuts keep dated validation records."""
    from genesis_rt import facts
    assert facts.VIDEO_WITHDRAWN == "2026-11-12"
    for rel in ("docs/demo/MEDIA_VALIDATION_W12.md",
                "docs/demo/MEDIA_VALIDATION_CAUSAL.md"):
        text = _read(rel)
        assert "WITHDRAWN" in text, rel
        assert facts.VIDEO_WITHDRAWN in text, rel
    for token in ("C5022619C5E82F915482A98EB49CF783061FFEEC113E721D64CB9BF20F4B59DC",
                  "6548BE78C973F4D1628D841471BEC3A3F1D04B2F871928050431230B29EEB0C2"):
        assert token in _read("docs/demo/MEDIA_VALIDATION_CAUSAL.md"), token
    handoff = _read("docs/demo/PUBLICATION_HANDOFF_CAUSAL.md")
    assert "DEFERRED_BY_OWNER" in handoff


def test_no_stale_video_handoff_claims():
    """OMEGA8 purge: plan says withdrawn; no doc claims a shipped cut."""
    matrix = _read("docs/compliance-matrix.md")
    assert "42 s genuine footage" not in matrix
    assert "edit + voice + publication = owner handoff, still pending" not in matrix
    plan = _read("docs/demo-video-plan.md")
    assert "Voice track + final edit +" not in plan
    assert "WITHDRAWN" in plan
    assert "CUTS READY" not in plan
    assert "CUTS READY" not in _read("docs/submission/DEVPOST_FINAL_DRAFT.md")


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
                  "PUBLICATION_HANDOFF_W12.md"):
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
         "--collect-only", "-q", "-rs", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=300)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    # A module whose optional extra is absent (e.g. the browser lane
    # without `.[e2e]`) is skipped at collection, so its tests are not
    # in the total. The registry pins the full-extras total (enforced
    # in CI, which installs requirements.lock); on a partial install
    # the comparison is not meaningful -- skip loudly, never fail a
    # judge who followed the README quickstart.
    uncollected = re.findall(r"^SKIPPED \[\d+\] (\S+?):\d+: (.*)$",
                             proc.stdout, re.M)
    if uncollected:
        if os.environ.get("CI"):
            pytest.fail(f"CI must collect every module: {uncollected}")
        pytest.skip(
            f"{len(uncollected)} test module(s) not collected "
            f"({uncollected[0][1]}); {m.group(1)} collected vs registry "
            f"{facts.TESTS_WITH_SDK} with all extras -- "
            "pip install -e '.[dev,e2e]' to check the pinned total")
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


def test_security_model_get_inventory_count_current():
    """Omega3 P1c §8.2: the prose GET-route count in the local
    security model equals the audited inventory list (it drifted
    31 vs 36 once; the pin test only guards the list)."""
    model = _read("docs/local-security-model.md")
    m = re.search(r"matches_audit`, (\d+)\s+routes", model)
    assert m is not None, "GET count claim missing from security model"
    posture = _read("tests/integration/test_rebinding_posture.py")
    lst = re.search(r"AUDITED_GET_ROUTES = \[(.*?)\]", posture, re.S)
    assert lst is not None
    n = len(re.findall(r'"([^"]+)"', lst.group(1)))
    assert int(m.group(1)) == n, (m.group(1), n)


def _claims_ai_section() -> str:
    text = _read("docs/CLAIMS.md")
    start = text.index("## AI evaluation (current)")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else len(text)]


def _latest_blind_holdout() -> str:
    """Latest COMMITTED (frozen) blind holdout. Untracked drafts
    (e.g. a v8 file being authored) must not move the goalpost."""
    proc = subprocess.run(
        ["git", "ls-files", "evals/planning_holdout_v*.json"],
        capture_output=True, text=True, cwd=ROOT, timeout=60)
    names = (proc.stdout.split() if proc.returncode == 0 else
             [p.name for p in (ROOT / "evals").glob(
                 "planning_holdout_v*.json")])
    versions = [int(m.group(1)) for m in
                (re.fullmatch(r"(?:.*/)?planning_holdout_v(\d+)\.json", n)
                 for n in names) if m is not None]
    assert versions, "no frozen blind holdout datasets found"
    return f"v{max(versions)}"


def test_current_ai_summary_names_latest_blind_eval():
    """Omega4 §2.4: the canonical AI summary must name the latest
    frozen blind evaluation and quantify its unsafe accepts
    (it foregrounded v4/v5 after v6 existed)."""
    section = _claims_ai_section()
    latest = _latest_blind_holdout()
    assert latest in section, f"CLAIMS AI omits latest blind eval {latest}"
    assert re.search(r"\d+ unsafe accepts", section), \
        "CLAIMS AI lacks a quantified unsafe-accept count"


def test_superseded_failures_not_presented_as_latest_open():
    """Omega4 §2.4: failures fixed or superseded by a later blind
    set must not read as the latest open findings."""
    section = _claims_ai_section()
    assert "12 v5 unsafe-accept classes are measured and OPEN" \
        not in section
    assert re.search(r"v5.{0,60}OPEN", section) is None, \
        "v5 failures still read as open findings"


def test_model_consultation_disclosed_current_docs():
    """Omega4 §2.4: current AI disclosures must state whether the
    model was actually consulted (v6: zero times)."""
    assert "consult" in _claims_ai_section().lower()
    draft = _read("docs/submission/DEVPOST_FINAL_DRAFT.md")
    assert "consult" in draft.lower()


def test_readme_flagships_current_source_packs():
    """Omega4 §2.4: the README proof section leads with the
    current-source Omega2 pair; W11 stays as dated history."""
    readme = _read("README.md")
    start = readme.index("## What's proven")
    end = readme.find("\n## ", start + 1)
    proven = readme[start:end if end != -1 else len(readme)]
    assert "omega2-before" in proven and "omega2-after" in proven
    assert proven.index("omega2-before") < proven.index("w11-before"), \
        "historical packs still lead the flagship proof section"


def test_human_impact_not_upgraded_without_records():
    """Omega4 §2.4: the unmeasured-benefit status stands until real
    consented pilot records exist (fixtures never count)."""
    recdir = ROOT / "bench" / "productivity" / "pilot-records"
    real = [p for p in recdir.glob("*.jsonl")] if recdir.is_dir() else []
    real = [p for p in real if not p.stem.startswith(
        ("fixture", "example", "test", "sample"))]
    if not real:
        score = _read("docs/jury/JUDGE_SCORECARD.md")
        assert "HUMAN USER BENEFIT NOT YET MEASURED" in score


def test_no_positive_hardware_signer_or_a11y_overclaims():
    """Omega4 §2.4: QEMU evidence is never physical-hardware proof,
    hashes are never signer authentication, and axe scans are never
    a completed screen-reader pass (denials are fine)."""
    docs = ("README.md", "docs/CLAIMS.md",
            "docs/submission/DEVPOST_FINAL_DRAFT.md",
            "docs/jury/JUDGE_SCORECARD.md",
            "docs/business/COMMERCIAL_VISION.md",
            "docs/jury/KNOWN_LIMITATIONS.md")
    denial = ("no ", "not ", "without", "unsigned", "hash-only",
              "never", "non-", "none ", "unmeasured", "neither")
    for rel in docs:
        text = _read(rel)
        assert re.search(r"(measured|verified|demonstrated|shows?|"
                         r"achieves?|runs? on|tested on) "
                         r"(physical|real) hardware",
                         text, re.I) is None, f"hardware proof claim: {rel}"
        assert re.search(r"WCAG 2\.2 AA conformat|fully WCAG|"
                         r"screen-readers? (verified|complete|passed)",
                         text, re.I) is None, f"a11y overclaim: {rel}"
        low = text.lower()
        assert re.search(r"signed (packs?|evidence|passports?|"
                         r"manifests?|bundles?|dossiers?)",
                         low) is None, f"signed-packs claim: {rel}"
        assert re.search(r"(packs?|evidence|passports?|manifests?|"
                         r"bundles?|dossiers?) (are|were|is) signed",
                         low) is None, f"signed-packs claim: {rel}"
        for m in re.finditer(r"signature|attestation", low):
            line = low[max(0, m.start() - 80):m.end() + 40]
            assert any(d in line for d in denial), \
                f"signer/trust overclaim near {m.group(0)!r}: {rel}"
        for m in re.finditer(r"screen-readers?|screen readers?", low):
            window = low[max(0, m.start() - 120):m.end() + 120]
            assert any(d in window for d in
                       ("outstanding", "pending", "not ", "no ",
                        "missing", "without", "unmeasured")), \
                f"unqualified screen-reader claim: {rel}"


def _collect_count(path: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-o", "addopts=",
         "--collect-only", "-q", "-p", "no:warnings"],
        capture_output=True, text=True, cwd=ROOT, timeout=300)
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m is not None, proc.stdout[-500:]
    return int(m.group(1))


def test_devpost_planning_count_matches_collected():
    """Omega4 attack-1: the submission draft's planning line once
    read 52/52 while 60 collected. Pin it to collection."""
    n = _collect_count("tests/unit/test_planning.py")
    draft = _read("docs/submission/DEVPOST_FINAL_DRAFT.md")
    line = next((ln for ln in draft.splitlines()
                 if "Planning unit tests" in ln), "")
    assert line, "draft lost its planning-tests line"
    assert f"{n}/{n}" in line, f"draft says {line.strip()!r}, collected {n}"


def test_requirements_lock_meets_crypto_floor():
    """Omega4 attack-4: the lock once pinned 43.0.3 against a >=49
    floor (CI installs the lock). Pin major.minor >= 49."""
    lock = _read("requirements.lock")
    m = re.search(r"^cryptography==(\d+)\.(\d+)\.(\d+)\s*$", lock,
                  re.MULTILINE)
    assert m is not None, "lock lost its cryptography pin"
    major, minor = int(m.group(1)), int(m.group(2))
    assert (major, minor) >= (49, 0), f"lock pins {m.group(0)} < 49"


def test_claims_header_tracks_current_baseline():
    """Omega5 sec 6.4: the CLAIMS H1 once stayed Omega2/Omega3-dated
    while the branch measured Omega4/OMEGA5. The heading must name
    the current baseline, not only a superseded one."""
    head = "\n".join(_read("docs/CLAIMS.md").splitlines()[:3])
    assert re.search(r"Omega4|OMEGA5", head), \
        f"CLAIMS header names no current baseline: {head!r}"


def test_v7v8_consultation_mismatches_disclosed():
    """Omega5 sec 6.5: the v7/v8 expect/actual consult gaps must be
    disclosed with case IDs in the consultation audit, and the
    frozen v7/v8 report must point at that audit."""
    audit = _read("docs/audits/OMEGA5_CONSULTATION_AUDIT.md")
    for cid in ("v7-v07", "v7-r57", "v7-r58", "v7-r61",
                "v8-004", "v8-021", "v8-028", "v8-034"):
        assert cid in audit, f"audit omits mismatch case {cid}"
    assert "expect_consult" in audit, "audit omits the harness field"
    omega4 = _read("docs/audits/OMEGA4_AI_EVALUATION.md")
    assert "OMEGA5_CONSULTATION_AUDIT" in omega4, \
        "frozen v7/v8 report does not point at the consult audit"


_V8_QUALIFIERS = ("qualif", "format-preview", "preview exposure",
                  "exposure")


def _doc_blocks(text):
    """Split into paragraphs, then into bullets: a blindness claim
    and its qualification must share one block."""
    for para in re.split(r"\n\s*\n", text):
        yield from re.split(r"\n(?=- )", para)


def _blind_attached_to_v8(block):
    """Per-occurrence attribution: a 'blind' only constrains v8 when
    v8 is the nearest eval id to it (comparisons like 'blind v9
    set ... vs v8' must not fire). Case IDs (v8-004) never count."""
    for m in re.finditer(r"blind\w*", block.lower()):
        window = block[max(0, m.start() - 30):m.end() + 30]
        evals = [(e.start(), e.group(0))
                 for e in re.finditer(r"\bv[4-9]\b", window)
                 if not re.match(r"-\d",
                                 window[e.end():e.end() + 2])]
        if not evals:
            continue
        nearest = min(evals, key=lambda e: abs(e[0] - 30))[1]
        if nearest == "v8":
            return True
    return False


def _assert_v8_qualified(text, rel):
    for block in _doc_blocks(text):
        if "blind" not in block.lower():
            continue
        if not _blind_attached_to_v8(block):
            continue
        assert any(q in block.lower() for q in _V8_QUALIFIERS), \
            f"unqualified v8 blindness in {rel}: {block[:120]!r}"


def test_v8_blindness_always_qualified():
    """Omega5 sec 6.5: v8 authoring had format-preview exposure, so
    no current-facing summary may call v8 blind without the
    qualification in the same paragraph or bullet. Concept check,
    not sentence matching (case IDs like v8-004 are not claims)."""
    for rel in ("docs/CLAIMS.md",
                "docs/submission/DEVPOST_FINAL_DRAFT.md",
                "docs/audits/OMEGA5_AI_EVALUATION.md",
                "docs/jury/KNOWN_LIMITATIONS.md"):
        _assert_v8_qualified(_read(rel), rel)
    parts = re.split(r"(?i)^## addendum\b",
                     _read("docs/audits/OMEGA4_AI_EVALUATION.md"),
                     maxsplit=1, flags=re.MULTILINE)
    assert len(parts) == 2, "OMEGA4 report lost its addendum"
    addendum = [parts[0], parts[1]]
    _assert_v8_qualified(addendum[1], "OMEGA4 addendum")


def test_wrong_kind_disclosed_in_current_summaries():
    """Omega5 sec 6.5: wrong-kind accepts are a distinct metric from
    unsafe accepts and true false rejects; current summaries must
    name them instead of folding them into accuracy."""
    for rel in ("docs/CLAIMS.md",
                "docs/submission/DEVPOST_FINAL_DRAFT.md",
                "README.md",
                "docs/audits/OMEGA5_AI_EVALUATION.md"):
        assert "wrong-kind" in _read(rel).lower(), \
            f"{rel} omits the wrong-kind metric"


def test_devpost_keeps_environment_distinct_counts():
    """Omega5 sec 6.5: the draft once mixed the owner 1376 run with
    the SDK-only 1374 and SDK-free 1370 runs. It must keep the
    three environments visibly distinct."""
    draft = _read("docs/submission/DEVPOST_FINAL_DRAFT.md")
    assert "without axe" in draft, "draft lost the SDK-only env line"
    assert "SDK-free" in draft, "draft lost the SDK-free env line"
    assert "0 skipped" in draft or "0 skips" in draft, \
        "draft lost the owner-run zero-skip statement"


def test_final_draft_limitations_names_latest_blind():
    """OMEGA7 landing (gates P1): the honesty section must point at
    the latest blind set — v10 residual, never a stale v9 pointer."""
    text = _read("docs/submission/DEVPOST_FINAL_DRAFT.md")
    section = text.split("## Limitations", 1)[1].split("\n## ", 1)[0]
    assert "latest blind v10" in section, \
        "Limitations section lost the v10 latest-pointer"
    assert "latest blind v9" not in section, \
        "Limitations section regressed to a stale v9 pointer"


def test_scorecard_current_section_keeps_ai_residuals():
    """Omega5 sec 6.5: the scorecard's current (first) section must
    carry the latest AI residuals, not just the headline scores."""
    text = _read("docs/jury/JUDGE_SCORECARD.md")
    current = text.split("\n---\n", 1)[0]
    assert "unsafe accepts" in current, \
        "current scorecard section omits unsafe accepts"
    assert ("wrong-kind" in current or "consultation" in current), \
        "current scorecard section omits wrong-kind/consult metrics"


def test_filing_day_checklist_present():
    """Titan v3 B-03: the filing-day checklist exists with the hard
    stops (video, deadline, public-through-judging, eligibility)."""
    text = _read("docs/submission/FILING_DAY_CHECKLIST.md")
    for token in ("15 Dec 2026", "29 Jan 2027", "eligibility",
                  "public YouTube", "DEVPOST_FINAL_DRAFT.md",
                  "Developer Tooling"):
        assert token in text, token


def test_bonus_b2_surface_pinned():
    """Titan v3 B-18: the pasted QNX section names each primitive +
    file path, the bonus note leads B2, and the storyboard shows
    the primitives on screen."""
    draft = _read("docs/submission/DEVPOST_FINAL_DRAFT.md")
    pasted = draft.split("## Bonus strategy")[0]
    for token in ("name_attach", "MsgSend", "resmgr",
                  "/dev/genesis/status", "supervisor",
                  "target/qnx8/guard", "target/qnx8/supervisor"):
        assert token in pasted, token
    strategy = draft.split("## Bonus strategy")[1].split("## ")[0]
    assert "Best Use of QNX" in strategy and "lead" in strategy.lower()
    board = _read("docs/submission/VIDEO_STORYBOARD_DEFERRED.md")
    assert "/dev/genesis/status" in board and "pidin" in board


def test_glossary_present_and_linked():
    """Titan v3 B-14: the plain-language glossary defines the AI
    ladder terms and START_HERE points cold readers at it."""
    text = _read("docs/jury/GLOSSARY.md")
    for token in ("Unsafe accept", "Wrong-kind accept",
                  "True false reject", "Consult", "Blind holdout",
                  "Qualified-blind", "Frozen vs regression",
                  "hash-only", "Stale-binary control"):
        assert token in text, token
    assert "GLOSSARY.md" in _read("docs/jury/START_HERE.md")


def test_second_host_provenance_template_present():
    """Titan v3 B-17: the second-host procedure + record template
    exists and stays honestly unfilled until an owner runs it."""
    text = _read("docs/submission/SECOND_HOST_PROVENANCE.md")
    for token in ("TEMPLATE", "qnx_rebuild_check.py", "verify.py",
                  "Host B fingerprint", "Pack hashes match Host A",
                  "Do NOT register"):
        assert token in text, token


_ABSOLUTE_LOCAL_PATH = re.compile(r"C:/|C:\\|/home/|/Users/")
_CODE_SPAN = re.compile(r"`[^`]*`")


def _md_files() -> list[Path]:
    out = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        out.append(path)
    return out


def _strip_redactions(text: str) -> str:
    """Drop code spans that are redacted placeholders (`...`)."""
    return _CODE_SPAN.sub(lambda m: "" if "..." in m.group(0) else m.group(0),
                          text)


def test_docs_have_no_absolute_local_paths():
    """OMEGA6 A5 (E1-class prevention): repo docs never ship absolute
    local paths — they 404 on GitHub and leak the author's layout.
    Redacted placeholders (code spans containing `...`) are allowed."""
    offenders = []
    for path in _md_files():
        body = _strip_redactions(path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(body.splitlines(), 1):
            if _ABSOLUTE_LOCAL_PATH.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}:"
                                 f" {line.strip()[:120]}")
    assert offenders == [], "\n".join(offenders)


def test_docs_have_no_outside_repo_links():
    """OMEGA6 A5: markdown `../` links must resolve inside the repo
    (post-E1 the audit copies link repo-relative)."""
    offenders = []
    for path in _md_files():
        body = _CODE_SPAN.sub("", path.read_text(encoding="utf-8"))
        for match in re.finditer(r"\]\(([^)]+)\)", body):
            target = match.group(1).strip().split("#")[0].split(" ")[0]
            if ".." not in target or target.startswith("http"):
                continue
            resolved = (path.parent / target).resolve()
            if resolved != ROOT and ROOT not in resolved.parents:
                offenders.append(f"{path.relative_to(ROOT)} -> {target}")
    assert offenders == [], "\n".join(offenders)


def test_hero_line_front_doored():
    """OMEGA6 C1: the one-line value prop sits on all three
    front doors (README, Studio landing, Devpost first screen)."""
    hero = "generates inspectable evidence about the behavior of"
    flat = lambda rel: re.sub(r"\s+", " ", _read(rel))
    assert hero in flat("README.md")
    assert hero in flat("ui/studio.html")
    assert hero in flat("docs/submission/DEVPOST_FINAL_DRAFT.md")


def test_wow_commands_documented():
    """OMEGA8 W1-W4: every new wow command is built AND documented."""
    from genesis_rt.cli import build_parser
    parser = build_parser()
    action = next(a for a in parser._actions
                  if type(a).__name__ == "_SubParsersAction")
    table = _read("README.md")
    for cmd in ("demo-break", "quickstart", "watch", "new"):
        assert cmd in action.choices, f"{cmd} not wired in CLI"
        assert f"genesis-rt {cmd}" in table, f"{cmd} missing from README"


def test_causal_commands_documented():
    """Causal slice: every new causal command is built AND documented."""
    from genesis_rt.cli import build_parser
    parser = build_parser()
    action = next(a for a in parser._actions
                  if type(a).__name__ == "_SubParsersAction")
    table = _read("README.md")
    for cmd in ("causal-repro", "causal-fix"):
        assert cmd in action.choices, f"{cmd} not wired in CLI"
        assert f"genesis-rt {cmd}" in table, f"{cmd} missing from README"


def test_qnx_footprint_table_present():
    """OMEGA6 D4: the QNX evidence doc carries the measured C
    footprint (text/data/bss) with RSS honestly unmeasured."""
    text = _read("docs/jury/WHY_QNX.md")
    assert "## Native binary footprint" in text
    for token in ("genesis_guard", "6641", "genesis_faultinject",
                  "8136", "ntox86_64-size",
                  "No resident-set claim is made"):
        assert token in text, token


def test_v10_trigger_rule_pinned():
    """OMEGA6 D6: the v10 rule lives in the roadmap-facing
    limitations doc — planner change implies a fresh blind set."""
    text = _read("docs/jury/KNOWN_LIMITATIONS.md")
    assert "v10 rule" in text
    assert "frozen-before-fix blind set (v10)" in text


def test_pack_file_counts_state_verify_py_exclusion():
    """OMEGA6 A6 (B-19): on-disk pack counts include the verifier
    itself (35/37); docs claim payload files excluding it (34/36)
    and must say so, or a hostile reviewer screenshots the gap."""
    from genesis_rt import facts
    counts = {}
    for rel, want_total, want_payload in (
            (facts.PACK_BEFORE, 35, 34), (facts.PACK_AFTER, 37, 36)):
        files = [p for p in (ROOT / rel).rglob("*") if p.is_file()]
        payload = [p for p in files if p.name != "verify.py"]
        assert len(files) == want_total, (rel, len(files))
        assert len(payload) == want_payload, (rel, len(payload))
        counts[rel] = (len(files), len(payload))
    assert counts  # both packs measured, not assumed
    for rel in ("docs/CLAIMS.md",
                "docs/submission/DEVPOST_FINAL_DRAFT.md"):
        text = _read(rel)
        assert "34 payload files + verify.py" in text, rel
        assert "36 payload files + verify.py" in text, rel
