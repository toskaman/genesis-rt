# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""UI tests: Wave 12 review panels (node) exercise the shipped studio JS.

Same harness shape as test_target_runner.py: the shipped inline
scripts run under node with DOM shims; only the pure render functions
are invoked. The IPC payload comes from the real backend endpoint so
backend drift breaks this test; the brief summary comes from the real
proofos summarizer.
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

pytest.importorskip("fastapi", reason="api extra not installed")
pytest.importorskip("httpx", reason="httpx needed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from genesis_rt import api as api_mod  # noqa: E402
from genesis_rt.proofos import build_plan, summarize_plan  # noqa: E402


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
    if (c.fn === 'ipchtml') {
      return renderIpcTimelineHtml(JSON.parse(c.arg));
    }
    if (c.fn === 'reviewhtml') {
      return renderReviewBriefHtml(JSON.parse(c.arg));
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


def _ipc_payload() -> dict:
    app = api_mod.create_app()
    with TestClient(app) as cli:
        r = cli.get("/ipc-timeline")
    assert r.status_code == 200, r.text
    return r.json()


def _brief_summary() -> dict:
    plan = build_plan(source_commit="s" * 40, base_commit="b" * 40, changes=[{
        "path": "examples/x.json", "status": "changed", "valid": True,
        "renamed_from": None, "ir_sha256_before": "a" * 64,
        "ir_sha256_after": "b" * 64, "limits_changed": True,
        "requirements_changed": 1, "retest": ["nominal_navigation"]}])
    return summarize_plan(plan)


@node
def test_ipc_panel_renders_real_capture(tmp_path):
    (html,) = _run_js([{"fn": "ipchtml", "arg": json.dumps(_ipc_payload())}],
                      tmp_path)
    assert "GENESIS_IPC_TRACE=1" in html
    assert "SEND" in html and "RECV" in html and "REPLY" in html
    assert "unknown (not measured)" in html  # device span never invented
    assert "ALLOW" in html or "DENY" in html
    assert "QEMU" in html


@node
def test_ipc_panel_handles_missing_capture(tmp_path):
    (html,) = _run_js([{"fn": "ipchtml",
                        "arg": json.dumps({"available": False,
                                           "reason": "gone"})}],
                      tmp_path)
    assert "unavailable" in html and "gone" in html


@node
def test_ipc_panel_flags_incomplete_spans(tmp_path):
    payload = _ipc_payload()
    payload["trips"][0].pop("reply_ns")
    (html,) = _run_js([{"fn": "ipchtml", "arg": json.dumps(payload)}],
                      tmp_path)
    assert "incomplete span" in html


@node
def test_review_panel_renders_six_sections(tmp_path):
    (html,) = _run_js([{"fn": "reviewhtml",
                        "arg": json.dumps(_brief_summary())}],
                      tmp_path)
    for title in ("What changed", "Why it matters", "What was tested",
                  "What happened", "Can we trust the evidence",
                  "Can the change be accepted", "Residual risks"):
        assert title in html, title


@node
def test_review_panel_escapes_untrusted_text(tmp_path):
    summary = _brief_summary()
    summary["what_changed"][0]["path"] = "<img src=x onerror=alert(1)>"
    summary["residual_risks"][0] = "<script>alert(2)</script>"
    (html,) = _run_js([{"fn": "reviewhtml", "arg": json.dumps(summary)}],
                      tmp_path)
    assert "<img" not in html
    assert "<script>" not in html
    assert "&lt;img" in html
    assert "&lt;script&gt;" in html
