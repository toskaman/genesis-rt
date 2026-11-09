# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Omega5 §2: consultation-label audits over frozen evidence.

Pins the v7/v8 expect/actual mismatches as documented history.
The audit reads committed files only; it never runs a provider.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_eval_consults import audit

sys.path.insert(0, str(ROOT / "host"))
sys.path.insert(0, str(ROOT / "scripts"))
from eval_planner import consult_verdict, run


def _audit_v7():
    return audit(
        ROOT / "evals" / "planning_holdout_v7.json",
        [ROOT / "evals" / "results" / "2026-11-09-omega4-v7" / f
         for f in ("qwen2.5-7b.json", "llama3.1-8b.json")])


def _audit_v8():
    return audit(
        ROOT / "evals" / "planning_holdout_v8.json",
        [ROOT / "evals" / "results" / "2026-11-09-omega4-v8" / f
         for f in ("qwen2.5-7b.json", "llama3.1-8b.json")])


def test_v7_consultation_mismatch_pinned():
    """Omega5 §2.1: v7 expected 24 consults, both models made 20.
    The 4 missing cases short-circuited deterministically and passed."""
    rep = _audit_v7()
    assert rep["dataset_sha256"].startswith("d91e3956")
    want = {"v7-v07", "v7-r57", "v7-r58", "v7-r61"}
    for prov in rep["providers"].values():
        assert prov["expected_consults"] == 24
        assert prov["actual_total_consults"] == 20
        assert set(prov["missing_consults"]) == want
        assert prov["unexpected_consults"] == []
        assert prov["multi_call_cases"] == []
        assert set(prov["short_circuited_passed"]) == want
    assert rep["cross_provider_consult_diffs"] == []


def test_v8_consultation_mismatch_pinned():
    """Omega5 §2.2: v8 expected 21 consults, both models made 25.
    The 4 unexpected calls are German Förderband valids the offline
    layer rejects as unknown kind (alias gap, not unsafe accepts)."""
    rep = _audit_v8()
    assert rep["dataset_sha256"].startswith("cb3820fd")
    want = {"v8-004", "v8-021", "v8-028", "v8-034"}
    cases = {c["id"]: c for c in json.loads(
        (ROOT / "evals" / "planning_holdout_v8.json").read_text(
            encoding="utf-8"))["cases"]}
    for cid in want:  # all four are Förderband valids
        assert "rderband" in cases[cid]["request"]
        assert "expect" in cases[cid]
    for prov in rep["providers"].values():
        assert prov["expected_consults"] == 21
        assert prov["actual_total_consults"] == 25
        assert prov["missing_consults"] == []
        assert set(prov["unexpected_consults"]) == want
        assert prov["multi_call_cases"] == []
    assert rep["cross_provider_consult_diffs"] == []


def test_audit_flags_multi_calls_unlabeled_and_diffs(tmp_path):
    """Synthetic fixture: multi-call, unlabeled-with-calls, failed
    short-circuit (missing but NOT passed), and cross-provider
    consult diffs are each reported."""
    ds = {"cases": [
        {"id": "a", "request": "x", "expect_consult": True},
        {"id": "b", "request": "y"},
        {"id": "c", "request": "z", "expect_consult": False},
    ]}
    (tmp_path / "d.json").write_text(json.dumps(ds), encoding="utf-8")
    rows_p = [{"id": "a", "consults": 2, "passed": True},
              {"id": "b", "consults": 1, "passed": True},
              {"id": "c", "consults": 0, "passed": False}]
    rows_q = [{"id": "a", "consults": 0, "passed": False},
              {"id": "b", "consults": 0, "passed": True},
              {"id": "c", "consults": 0, "passed": False}]
    (tmp_path / "p.json").write_text(
        json.dumps({"cases": rows_p}), encoding="utf-8")
    (tmp_path / "q.json").write_text(
        json.dumps({"cases": rows_q}), encoding="utf-8")
    rep = audit(tmp_path / "d.json",
                [tmp_path / "p.json", tmp_path / "q.json"])
    p, q = rep["providers"]["p"], rep["providers"]["q"]
    assert p["multi_call_cases"] == ["a"]
    assert p["unlabeled_with_calls"] == ["b"]
    assert q["missing_consults"] == ["a"]
    assert q["short_circuited_passed"] == []  # missing AND failed
    assert rep["cross_provider_consult_diffs"] == ["a", "b"]


def _row(cid, flag, calls):
    return {"id": cid, "expected_consult": flag, "consults": calls}


def test_verdict_enforces_exactly_one_when_expected():
    """Omega5 §2.4: llm rows labeled true must show exactly 1 call."""
    rows = [_row("a", True, 1), _row("b", True, 0), _row("c", True, 3)]
    v = consult_verdict(rows, "llm")
    assert v == {"missing_consults": ["b"],
                 "unexpected_consults": ["c"]}


def test_verdict_enforces_zero_when_forbidden():
    """Omega5 §2.4: llm rows labeled false must show 0 calls."""
    rows = [_row("a", False, 0), _row("b", False, 1)]
    v = consult_verdict(rows, "llm")
    assert v == {"missing_consults": [], "unexpected_consults": ["b"]}


def test_verdict_ignores_unlabeled_and_offline():
    """Omega5 §2.4: unlabeled cases are never violations; the
    offline provider cannot consult so nothing is enforced."""
    rows = [_row("a", None, 5), _row("b", True, 0), _row("c", False, 2)]
    assert consult_verdict(rows, "offline") == {
        "missing_consults": [], "unexpected_consults": []}
    v = consult_verdict([_row("a", None, 5)], "llm")
    assert v == {"missing_consults": [], "unexpected_consults": []}


def test_harness_rows_carry_consult_and_kind_fields():
    """Omega5 §2.4/§4.4: every row records the declared label and
    the wrong-kind flag; the summary separates the new metrics."""
    rep = run("offline", "planning_eval.json")
    rows = rep["cases"]
    assert all({"expected_consult", "consults", "language"} <= set(r)
               for r in rows)
    assert all("wrong_kind" in r for r in rows
               if r["type"] == "valid")
    s = rep["summary"]
    for key in ("wrong_kind_accepts", "veto_refusals",
                "fallback_eligible", "missing_consults",
                "unexpected_consults", "by_language"):
        assert key in s, key
    assert s["missing_consults"] == [] and s["unexpected_consults"] == []


def test_audit_cli_exit_zero_on_frozen_v8(tmp_path):
    """The CLI describes evidence; mismatches do not fail the audit."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_eval_consults.py"),
         "--dataset", "planning_holdout_v8.json",
         "--results",
         "evals/results/2026-11-09-omega4-v8/qwen2.5-7b.json",
         "--out", str(tmp_path / "a.json")],
        capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert proc.returncode == 0, proc.stderr
    out = json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))
    assert out["providers"]["qwen2.5-7b"]["actual_total_consults"] == 25


def test_eval_main_exits_1_on_missing_consult(monkeypatch, tmp_path):
    """Omega5 attack P2: main()'s exit-1 wiring, not just the pure
    verdict function. A deterministically short-circuited
    expect_consult case under a never-called stub llm provider
    fails strict and passes --no-strict. No network, no Ollama."""
    import eval_planner

    class _StubLLM:
        consults = 0

        def __getattr__(self, name):
            raise AssertionError(f"model path must not run: {name}")

    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "fix.json").write_text(json.dumps({"cases": [{
        "id": "fix-r01", "request": "Build a crop-spraying drone fleet",
        "language": "en", "expect_consult": True,
        "expect_reject": "unsupported", "category": "unsupported",
    }]}), encoding="utf-8")
    monkeypatch.setattr(eval_planner, "LLMProvider", _StubLLM)
    monkeypatch.setattr(eval_planner, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["eval_planner.py", "--provider",
                                      "llm", "--dataset", "fix.json"])
    assert eval_planner.main() == 1
    monkeypatch.setattr(sys, "argv", ["eval_planner.py", "--provider",
                                      "llm", "--dataset", "fix.json",
                                      "--no-strict"])
    assert eval_planner.main() == 0
