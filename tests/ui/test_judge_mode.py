# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""UI tests: Judge Mode stepper (node) exercises the shipped studio JS.

Same harness shape as test_target_runner.py: the shipped inline
scripts run under node with DOM shims; only the pure judge render
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

KNOWN_TABS = {"judge", "projects", "designer", "source", "pipeline",
              "target", "twin", "lab", "passport", "diff", "evidence",
              "run"}
KNOWN_ACTIONS = {"judge-open-example", "judge-open-source",
                 "judge-run-fault", "judge-open-evidence",
                 "judge-open-designer", "judge-run-verify",
                 "judge-open-dossier", "judge-run-causal"}


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
    if (c.fn === 'jstages') return judgeStages();
    if (c.fn === 'jrender') {
      const j = JSON.parse(c.arg);
      return renderJudgeHtml(j.idx, j.st);
    }
    if (c.fn === 'jclamp') return judgeClamp(JSON.parse(c.arg));
    if (c.fn === 'jbanner') return renderReleaseBannerHtml(JSON.parse(c.arg));
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
def test_eight_stages_drive_real_tabs_and_actions(tmp_path):
    (stages,) = _run_js([{"fn": "jstages", "arg": "null"}], tmp_path)
    assert len(stages) == 8
    assert len({s["id"] for s in stages}) == 8
    for s in stages:
        assert set(s) >= {"id", "title", "tab", "action", "proves",
                          "source"}
        assert s["tab"] in KNOWN_TABS
        assert s["action"] in KNOWN_ACTIONS
        assert s["proves"] and s["source"]
    assert [s["id"] for s in stages] == [
        "machine", "software", "failure", "diagnosis", "correction",
        "verification", "value", "causal"]


@node
def test_clamp_sticks_at_both_ends(tmp_path):
    (lo, hi, mid, neg) = _run_js([{"fn": "jclamp", "arg": "0"},
                                  {"fn": "jclamp", "arg": "99"},
                                  {"fn": "jclamp", "arg": "3"},
                                  {"fn": "jclamp", "arg": "-2"}],
                                 tmp_path)
    assert (lo, hi, mid, neg) == (0, 7, 3, 0)


@node
def test_render_live_marks_and_escapes(tmp_path):
    evil = {"idx": 2, "st": {"online": True,
                             "note": "<script>alert(1)</script>"}}
    (html,) = _run_js([{"fn": "jrender", "arg": json.dumps(evil)}],
                      tmp_path)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "[LIVE]" in html and "[ARCHIVED]" not in html
    assert "judge-run-fault" in html
    assert "POST /jobs" in html  # every result links its source
    for title in ("A · The machine", "C · The failure",
                  "G · The value"):
        assert title in html
    assert "C · The failure · active" in html
    assert "A · The machine · done" in html
    assert "G · The value · todo" in html


@node
def test_render_offline_archived_and_clamped(tmp_path):
    (first, last) = _run_js(
        [{"fn": "jrender",
          "arg": json.dumps({"idx": -5, "st": {"online": False}})},
         {"fn": "jrender",
          "arg": json.dumps({"idx": 99, "st": {"online": False}})}],
        tmp_path)
    for html in (first, last):
        assert "[ARCHIVED]" in html
        assert "run-d10a0b458552" in html
        assert "disabled" in html
    assert "A · The machine · active" in first
    assert "data-jnav=\"prev\" disabled" in first
    assert "H · The causal proof · active" in last
    assert "data-jnav=\"next\" disabled" in last


@node
def test_stage_g_renders_release_state_inline(tmp_path):
    targeted = {"verdict": "PASS", "level": "HOST_TESTED",
                "qnx_verified": False, "release_eligible": False,
                "coverage": {"required": ["a"], "declared": ["a", "b"],
                             "omitted": ["b"]}}
    full = {"verdict": "PASS", "level": "QNX_PERFORMANCE_MEASURED",
            "qnx_verified": True, "release_eligible": True,
            "coverage": {"required": ["a"], "declared": ["a"],
                         "omitted": []}}
    (sub, ok) = _run_js([{"fn": "jbanner", "arg": json.dumps(targeted)},
                         {"fn": "jbanner", "arg": json.dumps(full)}],
                        tmp_path)
    assert "TARGETED run" in sub and "PENDING" in sub
    assert "NOT release eligible" in sub
    assert "release_eligible" in ok and "YES" in ok
    (html,) = _run_js([{"fn": "jrender",
                        "arg": json.dumps(
                            {"idx": 6,
                             "st": {"online": True, "note": "live",
                                    "extra": ok}})}],
                      tmp_path)
    assert "G · The value · active" in html
    assert "YES" in html and "[LIVE]" in html
