# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""UI tests: target runner tab (node) exercises the shipped studio JS.

Same harness shape as test_dashboard_verify.py: the shipped inline
scripts run under node with DOM shims; only the pure render/reduce
functions are invoked.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STUDIO = REPO_ROOT / "ui" / "studio.html"
VERIFY_JS = REPO_ROOT / "ui" / "genesis_verify.js"

node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _inline_scripts(html: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", html, re.DOTALL)


def _script() -> str:
    core = VERIFY_JS.read_text(encoding="utf-8")
    html = STUDIO.read_text(encoding="utf-8")
    assert '<script src="genesis_verify.js"></script>' in html
    return "\n".join([core] + _inline_scripts(html))


def _run_js(calls: list[dict], tmp_path: Path) -> list:
    driver = """
;globalThis.__run = () => {
  const fs = require('fs');
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
  const out = job.calls.map((c) => {
    if (c.fn === 'topreduce') {
      const r = reduceTargetEvents(JSON.parse(c.arg));
      return { state: r.state, phase: r.phase, n: r.log.length,
               lastSeq: r.lastSeq };
    }
    if (c.fn === 'tophtml') {
      const j = JSON.parse(c.arg);
      return renderTargetHtml(j.id, reduceTargetEvents(j.events), j.record);
    }
    if (c.fn === 'tops') return renderTargetOpsHtml(JSON.parse(c.arg));
    if (c.fn === 'topdecision') {
      return renderDecisionHtml(JSON.parse(c.arg));
    }
    if (c.fn === 'topcompare') {
      return renderCompareHtml(JSON.parse(c.arg));
    }
    throw new Error('unknown fn ' + c.fn);
  });
  fs.writeFileSync(process.argv[3], JSON.stringify(out));
};
"""
    runner = ("globalThis.document = { getElementById: () => "
              "({ addEventListener() {} }), querySelectorAll: () => [] };\n"
              + _script() + driver + "\nglobalThis.__run();\n")
    run_js = tmp_path / "runner.js"
    job_js = tmp_path / "job.json"
    out_js = tmp_path / "out.json"
    run_js.write_text(runner, encoding="utf-8")
    job_js.write_text(json.dumps({"calls": calls}), encoding="utf-8")
    proc = subprocess.run(["node", str(run_js), str(job_js), str(out_js)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(out_js.read_text(encoding="utf-8"))


@node
def test_reduce_folds_terminal_and_phase(tmp_path):
    events = [
        {"seq": 0, "kind": "op_started", "message": "workflow=full"},
        {"seq": 1, "kind": "state", "message": "VALIDATING"},
        {"seq": 2, "kind": "step_done", "message": "validate: ok"},
        {"seq": 3, "kind": "op_completed", "message": "all steps done"},
    ]
    (got,) = _run_js([{"fn": "topreduce", "arg": json.dumps(events)}], tmp_path)
    assert got == {"state": "COMPLETED", "phase": "VALIDATING", "n": 4,
                   "lastSeq": 3}


@node
def test_reduce_dedups_seq(tmp_path):
    events = [
        {"seq": 0, "kind": "op_started", "message": "x"},
        {"seq": 0, "kind": "op_started", "message": "x"},
        {"seq": 1, "kind": "op_failed", "message": "boom"},
    ]
    (got,) = _run_js([{"fn": "topreduce", "arg": json.dumps(events)}], tmp_path)
    assert (got["state"], got["n"], got["lastSeq"]) == ("FAILED", 2, 1)


@node
def test_html_shows_phases_steps_and_escapes(tmp_path):
    evil = "<script>alert(1)</script>"
    record = {"op_id": "op-abc123def456", "workflow": "full",
              "state": "BLOCKED", "reason": evil,
              "steps": [{"name": "env", "state": "blocked", "detail": evil}],
              "artifacts": {"sdk_present": False}}
    events = [{"seq": 0, "kind": "op_started", "message": "workflow=full"},
              {"seq": 1, "kind": "op_blocked", "message": evil}]
    arg = json.dumps({"id": "op-abc123def456", "events": events,
                      "record": record})
    (html,) = _run_js([{"fn": "tophtml", "arg": arg}], tmp_path)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    for phase in ("PENDING", "VALIDATING", "BUILDING", "STAGING",
                  "VERIFYING", "MEASURING", "SEALING", "REPLAYING",
                  "COMPLETED"):
        assert phase in html
    assert "BLOCKED" in html and "sdk_present" in html


@node
def test_ops_table_empty_and_rows(tmp_path):
    (empty, rows) = _run_js([{"fn": "tops", "arg": "[]"},
                             {"fn": "tops", "arg": json.dumps([
                                 {"op_id": "op-111111111111",
                                  "workflow": "full", "state": "COMPLETED"},
                                 {"op_id": "op-222222222222",
                                  "workflow": "build-only",
                                  "state": "FAILED"}])}], tmp_path)
    assert "No target ops yet" in empty
    assert "op-111111111111" in rows and "op-222222222222" in rows
    assert rows.count('data-op="op-') == 2


def test_tab_chrome_present():
    html = STUDIO.read_text(encoding="utf-8")
    assert 'data-tab="target"' in html
    assert 'id="tab-target"' in html
    for cid in ("top-workflow", "top-image", "top-run", "top-cancel",
                "top-out", "top-refresh", "top-history", "top-cmp-before",
                "top-cmp-after", "top-cmp-run", "top-compare"):
        assert f'id="{cid}"' in html
    for fn in ("reduceTargetEvents", "renderTargetHtml",
               "renderTargetOpsHtml", "renderDecisionHtml",
               "renderCompareHtml", "targetRel", "targetRun",
               "openTargetOp", "openTargetStream", "refreshTargetHistory",
               "loadTargetDecision", "compareTargetOps",
               "fillCompareSelects"):
        assert f"function {fn}(" in html or f"async function {fn}(" in html


@node
def test_html_dossier_link_only_when_settled(tmp_path):
    settled = json.dumps({
        "id": "op-abc123def456",
        "events": [{"seq": 0, "kind": "op_started", "message": "x"},
                   {"seq": 1, "kind": "op_completed", "message": "done"}],
        "record": {"op_id": "op-abc123def456", "state": "COMPLETED"}})
    active = json.dumps({
        "id": "op-abc123def456",
        "events": [{"seq": 0, "kind": "op_started", "message": "x"}],
        "record": {"op_id": "op-abc123def456", "state": "EXECUTING"}})
    (done_html, live_html) = _run_js([{"fn": "tophtml", "arg": settled},
                                      {"fn": "tophtml", "arg": active}],
                                     tmp_path)
    assert 'id="top-dossier"' in done_html
    assert "/target/ops/op-abc123def456/dossier" in done_html
    assert "top-dossier" not in live_html


@node
def test_html_decision_placeholder_only_when_settled(tmp_path):
    settled = json.dumps({
        "id": "op-abc123def456",
        "events": [{"seq": 0, "kind": "op_started", "message": "x"},
                   {"seq": 1, "kind": "op_completed", "message": "done"}],
        "record": {"op_id": "op-abc123def456", "state": "COMPLETED"}})
    active = json.dumps({
        "id": "op-abc123def456",
        "events": [{"seq": 0, "kind": "op_started", "message": "x"}],
        "record": {"op_id": "op-abc123def456", "state": "EXECUTING"}})
    (done_html, live_html) = _run_js([{"fn": "tophtml", "arg": settled},
                                      {"fn": "tophtml", "arg": active}],
                                     tmp_path)
    assert 'id="top-decision"' in done_html
    assert "top-decision" not in live_html


@node
def test_decision_renders_verdict_why_and_escapes(tmp_path):
    evil = "<img src=x onerror=alert(1)>"
    decision = {
        "op_id": "op-abc123def456", "verdict": "FAIL", "state": "FAILED",
        "gate": "deny", "gate_level": "qnx-verified",
        "release_eligible": False, "qnx_verified": False,
        "matrix": {"total": 16, "passed": 15, "failed": ["limits_differ"],
                   "all_passed": False},
        "missing_evidence": [], "chain_errors": [],
        "why": ["native check failed: limits_differ", evil],
    }
    (html,) = _run_js([{"fn": "topdecision", "arg": json.dumps(decision)}],
                      tmp_path)
    assert "Release decision" in html
    assert "FAIL" in html and "limits_differ" in html
    assert "<img" not in html and "&lt;img" in html


@node
def test_compare_renders_sides_diff_and_escapes(tmp_path):
    evil = "<script>alert(1)</script>"
    long_before = "a" * 64
    long_after = "b" * 64
    long_tc = "qcc " + "x" * 120
    cmp = {
        "before": {"op_id": "op-aaaaaaaaaaaaaaaa", "verdict": "PASS",
                   "ir_digest": long_before, "gate": "PASS",
                   "gate_level": "QNX_EXECUTED",
                   "release_eligible": True, "toolchain": long_tc},
        "after": {"op_id": "op-bbbbbbbbbbbbbbbb", "verdict": "FAIL",
                  "ir_digest": long_after, "gate": "UNKNOWN",
                  "gate_level": "not sealed",
                  "release_eligible": False, "toolchain": evil},
        "diff": {"ir_changed": True, "verdict_changed": True,
                 "gate_changed": True, "release_changed": True,
                 "toolchain_changed": True,
                 "newly_failed": ["limits_differ"], "newly_passed": [],
                 "matrix_before": "2/2", "matrix_after": "1/2"},
    }
    (html,) = _run_js([{"fn": "topcompare", "arg": json.dumps(cmp)}],
                      tmp_path)
    assert "op-aaaaaaaaaaaaaaaa" in html and "op-bbbbbbbbbbbbbbbb" in html
    assert "limits_differ" in html and "(changed)" in html
    assert "/target/ops/op-aaaaaaaaaaaaaaaa/dossier" in html
    assert "/target/ops/op-bbbbbbbbbbbbbbbb/dossier" in html
    assert "2/2" in html and "1/2" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    # Long values are truncated consistently on both sides.
    assert long_before not in html and long_after not in html
    assert "a" * 24 + "…" in html and "b" * 24 + "…" in html
    assert "not sealed" in html


@node
def test_html_folds_absolute_op_dirs_to_relative(tmp_path):
    abs_target = "C:\\Users\\demo\\ops\\op-abc123def456\\target"
    abs_perf = "C:\\Users\\demo\\ops\\op-abc123def456\\perf"
    record = {"op_id": "op-abc123def456", "state": "COMPLETED",
              "steps": [{"name": "qemu_verify", "state": "done",
                         "detail": f"target matrix PASS (see {abs_target})"}],
              "artifacts": {"target_dir": abs_target,
                            "perf_dir": abs_perf}}
    events = [{"seq": 0, "kind": "op_started",
               "message": f"work {abs_target}"},
              {"seq": 1, "kind": "op_completed", "message": "done"}]
    arg = json.dumps({"id": "op-abc123def456", "events": events,
                      "record": record})
    (html,) = _run_js([{"fn": "tophtml", "arg": arg}], tmp_path)
    assert abs_target not in html and abs_perf not in html
    assert "C:\\Users" not in html
    assert "(see target/)" in html and "work target/" in html
