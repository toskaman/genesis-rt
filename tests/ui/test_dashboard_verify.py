# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""UI tests: dashboard verification core (node) cross-checked vs Python.

The dashboard's <script> is extracted verbatim and executed under node
with DOM shims, so these tests exercise the shipped JS: SHA-256,
canonical JSON, chain re-verification and HTML escaping.
"""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from genesis_rt import codegen, evidence, faultlab, gate
from genesis_rt.ir import canonical_json

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD = REPO_ROOT / "ui" / "dashboard.html"

node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _script() -> str:
    html = DASHBOARD.read_text(encoding="utf-8")
    m = re.search(r"<script>(.*)</script>", html, re.DOTALL)
    assert m, "dashboard must embed its verification script"
    return m.group(1)


def _run_js(calls: list[dict], tmp_path: Path) -> list:
    """Run dashboard JS functions under node. calls: [{fn, arg}]."""
    driver = """
;globalThis.__run = () => {
  const fs = require('fs');
  const enc = new TextEncoder();
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
  const out = job.calls.map((c) => {
    if (c.fn === 'sha256') return sha256Hex(enc.encode(c.arg));
    if (c.fn === 'canon') return canonNode(parseRawJson(c.arg));
    if (c.fn === 'verify') return verifyChainText(c.arg);
    if (c.fn === 'esc') return esc(c.arg);
    throw new Error('unknown fn ' + c.fn);
  });
  fs.writeFileSync(process.argv[3], JSON.stringify(out));
};
globalThis.document = { getElementById: () => ({ addEventListener() {} }) };
"""
    # Note: document shim must exist before the dashboard script runs.
    runner = ("globalThis.document = { getElementById: () => "
              "({ addEventListener() {} }) };\n" + _script() + driver
              + "\nglobalThis.__run();\n")
    run_js = tmp_path / "runner.js"
    job_js = tmp_path / "job.json"
    out_js = tmp_path / "out.json"
    run_js.write_text(runner, encoding="utf-8")
    job_js.write_text(json.dumps({"calls": calls}), encoding="utf-8")
    proc = subprocess.run(["node", str(run_js), str(job_js), str(out_js)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(out_js.read_text(encoding="utf-8"))


def test_all_interpolations_escaped():
    """Static guard: every ${...} in the dashboard script uses esc()."""
    script = _script()
    bare = [m for m in re.finditer(r"\$\{", script)
            if not script.startswith("${esc(", m.start())]
    assert bare == [], "unescaped interpolation in dashboard.html"


@node
def test_sha256_matches_hashlib(tmp_path):
    bodies = ["", "abc", "x" * 1000, "héllo→world",
              canonical_json({"b": [1, 2.0, None], "a": "é"})]
    got = _run_js([{"fn": "sha256", "arg": s} for s in bodies], tmp_path)
    want = [hashlib.sha256(s.encode("utf-8")).hexdigest() for s in bodies]
    assert got == want


@node
def test_canonical_json_fixpoint_vs_python(tmp_path):
    values = [
        {"b": [1, 2.0, None, True], "a": "é→\U0001f600"},
        {"z": 0.0, "neg": -0.0, "f": 1.5, "big": 10 ** 18, "n": -3},
        {"s": "quote\"back\\slash\nnewline\ttab\x01\x7f"},
        {"empty": {}, "arr": [], "deep": {"x": [{"y": [0.1]}]}},
        {"k": "a" * 500, "nums": [round(i * 0.1234, 4) for i in range(50)]},
    ]
    texts = [canonical_json(v) for v in values]
    got = _run_js([{"fn": "canon", "arg": t} for t in texts], tmp_path)
    assert got == texts  # raw-parse + re-emit is the identity on canonical text


@node
def test_escapes_html(tmp_path):
    got = _run_js([{"fn": "esc", "arg": '<script>alert("x&y")</script>'}], tmp_path)
    assert got == ['&lt;script&gt;alert(&quot;x&amp;y&quot;)&lt;/script&gt;']


def _fresh_passport(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    results = faultlab.run_all(amr_ir, ["nominal_navigation", "dropped_message"])
    passport = evidence.build_passport(
        "run-dash", amr_ir, manifest, results,
        {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, ["nominal_navigation", "dropped_message"])
    evidence.attach_verdict(passport, verdict)
    assert evidence.verify_chain(passport) == []
    path = evidence.save_passport(passport, tmp_path / "passport.json")
    return path.read_text(encoding="utf-8")


@node
def test_genuine_passports_verify_in_js(amr_ir, tmp_path):
    sample = (REPO_ROOT / "artifacts" / "samples"
              / "golden_demo_passport.example.json").read_text(encoding="utf-8")
    fresh = _fresh_passport(amr_ir, tmp_path)
    got = _run_js([{"fn": "verify", "arg": sample},
                   {"fn": "verify", "arg": fresh}], tmp_path)
    assert got == [[], []]


@node
def test_tampered_passport_invalid_in_js(amr_ir, tmp_path):
    fresh = _fresh_passport(amr_ir, tmp_path)
    p = json.loads(fresh)
    scen = next(r for r in p["chain"] if r["kind"].startswith("scenario:"))
    scen["body"]["checks"][0]["passed"] = not scen["body"]["checks"][0]["passed"]
    evil = json.dumps(p, indent=2, sort_keys=True)
    assert evidence.verify_chain(json.loads(evil)) != []  # python agrees
    got = _run_js([{"fn": "verify", "arg": evil}], tmp_path)
    assert len(got[0]) > 0 and any("hash mismatch" in e for e in got[0])


@node
def test_noncanonical_number_literal_invalid_in_js(amr_ir, tmp_path):
    """Documented strictness: 0.00 is numeric-identical but textually
    non-canonical, so JS reports INVALID while Python still accepts it."""
    fresh = _fresh_passport(amr_ir, tmp_path)
    assert '"final_y": 0.0' in fresh
    touched = fresh.replace('"final_y": 0.0', '"final_y": 0.00', 1)
    assert evidence.verify_chain(json.loads(touched)) == []
    got = _run_js([{"fn": "verify", "arg": touched}], tmp_path)
    assert len(got[0]) > 0
