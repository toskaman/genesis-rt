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
VERIFY_JS = REPO_ROOT / "ui" / "genesis_verify.js"

node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _inline_scripts(html: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", html, re.DOTALL)


def _script() -> str:
    """The shipped JS: shared core + dashboard + studio inline scripts."""
    core = VERIFY_JS.read_text(encoding="utf-8")
    parts = [core]
    for name in ("dashboard.html", "studio.html"):
        html = (REPO_ROOT / "ui" / name).read_text(encoding="utf-8")
        assert '<script src="genesis_verify.js"></script>' in html, \
            f"{name} must load the shared verification core"
        parts.extend(_inline_scripts(html))
    return "\n".join(parts)


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
    if (c.fn === 'irsha') return irShaOfText(c.arg);
    if (c.fn === 'intent') { const r = renderIntentHtml(c.arg); return r.ok ? r.sha : 'ERR:' + r.html; }
    if (c.fn === 'provenance') return parseProvenance(c.arg);
    if (c.fn === 'source') { const j = JSON.parse(c.arg); return renderSourceHtml(j.files, j.irSha); }
    if (c.fn === 'lab') return renderLabHtml(passportScenarios(JSON.parse(c.arg)));
    if (c.fn === 'diff') { const j = JSON.parse(c.arg); return renderDiffHtml(j.a, j.b); }
    if (c.fn === 'trace') {
      const t = traceEvents(passportScenarios(JSON.parse(c.arg))[0]);
      return { n: t.events.length, headLen: t.headLen, truncated: t.truncated,
               kind: t.kind, keys: t.events.length ? Object.keys(t.events[0]).sort() : [] };
    }
    if (c.fn === 'status') { const j = JSON.parse(c.arg); return renderStatusHtml(j.online, j.env); }
    if (c.fn === 'projects') return renderProjectsHtml(JSON.parse(c.arg));
    if (c.fn === 'history') return renderHistoryHtml(JSON.parse(c.arg));
    if (c.fn === 'irdiff') return renderIrDiffHtml(JSON.parse(c.arg));
    if (c.fn === 'stategraph') return stateGraphSvg(JSON.parse(c.arg));
    if (c.fn === 'summary') return renderSummaryHtml(JSON.parse(c.arg));
    if (c.fn === 'jobreduce') {
      const r = reduceJobEvents(JSON.parse(c.arg));
      return { state: r.state, phase: r.phase, verdict: r.verdict,
               n: r.log.length, lastSeq: r.lastSeq };
    }
    if (c.fn === 'jobhtml') { const j = JSON.parse(c.arg); return renderJobHtml(j.id, reduceJobEvents(j.events), j.error || null); }
    if (c.fn === 'jobs') return renderJobsHtml(JSON.parse(c.arg));
    if (c.fn === 'keyerr') return keyFromError(c.arg);
    if (c.fn === 'scen') return renderScenarioChecks(JSON.parse(c.arg));
    if (c.fn === 'graph') { const j = JSON.parse(c.arg); return renderGraphHtml(j.graph, j.opts); }
    if (c.fn === 'graphnode') { const j = JSON.parse(c.arg); return renderGraphNodeHtml(j.graph, j.id, j.opts || {}); }
    if (c.fn === 'graphdiff') return renderGraphDiffHtml(JSON.parse(c.arg));
    throw new Error('unknown fn ' + c.fn);
  });
  fs.writeFileSync(process.argv[3], JSON.stringify(out));
};
globalThis.document = { getElementById: () => ({ addEventListener() {} }) };
"""
    # Note: document shim must exist before the page scripts run.
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


def test_all_interpolations_escaped():
    """Static guard: every ${...} in shipped UI scripts uses esc()."""
    pages = {"genesis_verify.js": VERIFY_JS.read_text(encoding="utf-8")}
    for name in ("dashboard.html", "studio.html"):
        path = REPO_ROOT / "ui" / name
        if path.exists():
            pages[name] = "\n".join(_inline_scripts(
                path.read_text(encoding="utf-8")))
    for name, script in pages.items():
        bare = [m for m in re.finditer(r"\$\{", script)
                if not script.startswith("${esc(", m.start())]
        assert bare == [], f"unescaped interpolation in {name}"


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
def test_studio_irsha_matches_python(repo_root, tmp_path):
    """JS normalization+hash reproduces the manifest digest from raw text."""
    from genesis_rt.codegen import ir_sha256
    from genesis_rt.ir import load_ir_file
    for name in ("amr-demo", "conveyor-demo"):
        raw = (repo_root / "examples" / name / "machine-ir.json"
               ).read_text(encoding="utf-8")
        want = ir_sha256(load_ir_file(repo_root / "examples" / name
                                      / "machine-ir.json"))
        got = _run_js([{"fn": "irsha", "arg": raw},
                       {"fn": "intent", "arg": raw}], tmp_path)
        assert got == [want, want], name


@node
def test_studio_source_pin_check(amr_ir, tmp_path):
    manifest = codegen.generate(amr_ir, tmp_path / "gen")
    header = (tmp_path / "gen" / "genesis_config_gen.h"
              ).read_text(encoding="utf-8")
    files = json.dumps({"files": [{"name": "genesis_config_gen.h",
                                   "text": header}],
                        "irSha": manifest["ir_sha256"]})
    (got,) = _run_js([{"fn": "source", "arg": files}], tmp_path)
    assert "matches loaded IR" in got and "amr-demo-01" in got
    (got,) = _run_js([{"fn": "source", "arg": json.dumps(
        {"files": [{"name": "genesis_config_gen.h", "text": header}],
         "irSha": "0" * 64})}], tmp_path)
    assert "MISMATCH vs loaded IR" in got
    (got,) = _run_js([{"fn": "provenance", "arg": header}], tmp_path)
    assert got == {"id": "amr-demo-01", "kind": "differential_drive_robot",
                   "sha": manifest["ir_sha256"]}
    from genesis_rt.codegen_v2 import generate_v2
    from genesis_rt.ir_v2 import load_ir_v2_file
    v2 = load_ir_v2_file(REPO_ROOT / "examples" / "amr-demo"
                         / "machine-ir-v2.json")
    generate_v2(v2, tmp_path / "gen2")
    header2 = (tmp_path / "gen2" / "genesis_machine_gen.h"
               ).read_text(encoding="utf-8")
    (got,) = _run_js([{"fn": "provenance", "arg": header2}], tmp_path)
    assert got["id"] == "amr-demo-01" and len(got["sha"]) == 64


def _fresh_passport_for(ir, scenarios, tmp_path, tag):
    manifest = codegen.generate(ir, tmp_path / f"gen-{tag}")
    results = faultlab.run_all(ir, scenarios)
    passport = evidence.build_passport(
        f"run-{tag}", ir, manifest, results,
        {"status": "blocked", "verified_on_target": False})
    verdict = gate.evaluate(passport, scenarios)
    evidence.attach_verdict(passport, verdict)
    assert evidence.verify_chain(passport) == []
    path = evidence.save_passport(passport, tmp_path / f"{tag}.json")
    return path.read_text(encoding="utf-8")


@node
def test_studio_lab_and_trace_diff(amr_ir, tmp_path):
    text = _fresh_passport_for(amr_ir, ["nominal_navigation"], tmp_path, "lab")
    (lab,) = _run_js([{"fn": "lab", "arg": text}], tmp_path)
    assert "nominal_navigation" in lab
    (trace,) = _run_js([{"fn": "trace", "arg": text}], tmp_path)
    assert trace["kind"] == "diff" and trace["n"] > 0
    assert {"x", "y", "theta"} <= set(trace["keys"])
    assert trace["truncated"] is True and trace["headLen"] == 20  # 150 slimmed


@node
def test_studio_trace_belt(repo_root, tmp_path):
    from genesis_rt.ir import load_ir_file
    conv = load_ir_file(repo_root / "examples" / "conveyor-demo"
                        / "machine-ir.json")
    text = _fresh_passport_for(conv, ["nominal_navigation"], tmp_path, "belt")
    (trace,) = _run_js([{"fn": "trace", "arg": text}], tmp_path)
    assert trace["kind"] == "belt" and trace["n"] > 0
    assert {"position", "speed", "jammed"} <= set(trace["keys"])


@node
def test_studio_diff_fixed_and_invalid(amr_ir, tmp_path):
    clean = _fresh_passport_for(amr_ir, ["nominal_navigation"], tmp_path, "dB")
    manifest = codegen.generate(amr_ir, tmp_path / "gen-dA")
    results = faultlab.run_all(amr_ir, ["nominal_navigation"])
    results[0]["status"] = "fail"  # structural failure, rechained honestly
    results[0]["checks"] = [{"name": "progress", "passed": False,
                             "detail": "no motion"}]
    bad = evidence.build_passport(
        "run-dA", amr_ir, manifest, results,
        {"status": "blocked", "verified_on_target": False})
    evidence.attach_verdict(
        bad, gate.evaluate(bad, ["nominal_navigation"]))
    assert evidence.verify_chain(bad) == []
    bad_text = json.dumps(bad, indent=2, sort_keys=True)
    assert evidence.verify_chain(json.loads(bad_text)) == []
    (got,) = _run_js([{"fn": "diff", "arg": json.dumps({"a": bad_text,
                                                        "b": clean})}],
                     tmp_path)
    assert "FIXED" in got and "nominal_navigation" in got
    evil = bad_text.replace('"status": "fail"', '"status": "pass"', 1)
    (got,) = _run_js([{"fn": "diff", "arg": json.dumps({"a": evil,
                                                        "b": clean})}],
                     tmp_path)
    assert "INVALID chain" in got and "FIXED" not in got


@node
def test_studio_passport_rejects_tampered(amr_ir, tmp_path):
    fresh = _fresh_passport(amr_ir, tmp_path)
    p = json.loads(fresh)
    scen = next(r for r in p["chain"] if r["kind"].startswith("scenario:"))
    scen["body"]["checks"][0]["passed"] = not scen["body"]["checks"][0]["passed"]
    evil = json.dumps(p, indent=2, sort_keys=True)
    (got,) = _run_js([{"fn": "verify", "arg": evil}], tmp_path)
    assert len(got) > 0  # chain invalid: studio glue keeps Lab/Twin empty


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


# -- Studio Live pure core (node) -------------------------------------


@node
def test_live_status_online_offline(tmp_path):
    (off,) = _run_js([{"fn": "status",
                       "arg": json.dumps({"online": False, "env": None})}],
                     tmp_path)
    assert "offline" in off and "serve" in off
    env = {"api": "0.2.0",
           "environment": {"sdk_present": True,
                           "qemu": {"present": False}}}
    (on,) = _run_js([{"fn": "status",
                       "arg": json.dumps({"online": True, "env": env})}],
                     tmp_path)
    assert "live" in on and "SDK" in on and "no QEMU" in on


@node
def test_live_projects_and_escape(tmp_path):
    (empty,) = _run_js([{"fn": "projects", "arg": "[]"}], tmp_path)
    assert "No projects yet" in empty
    rows = [{"pid": "prj-abcdef012345", "name": "<script>x</script>",
             "machine": "amr-demo-01", "schema_version": 1, "head": 2}]
    (got,) = _run_js([{"fn": "projects", "arg": json.dumps(rows)}], tmp_path)
    assert "<script>" not in got and "&lt;script&gt;" in got
    assert "prj-abcdef012345" in got and "amr-demo-01" in got


@node
def test_live_history_and_irdiff(tmp_path):
    from genesis_rt.projects import ir_diff

    revs = [{"rev": 1, "machine": "amr-demo-01", "ir_sha256": "a" * 64},
            {"rev": 2, "machine": "amr-demo-01", "ir_sha256": "b" * 64}]
    (hist,) = _run_js([{"fn": "history", "arg": json.dumps(revs)}], tmp_path)
    assert "r1" in hist and "r2" in hist and "a" * 16 in hist
    diff = ir_diff({"control": {"v": 1.2}, "gone": 1},
                   {"control": {"v": 0.9}, "new": 2})
    diff["from"], diff["to"] = 1, 2
    (got,) = _run_js([{"fn": "irdiff", "arg": json.dumps(diff)}], tmp_path)
    assert "control.v" in got and "GONE" not in got
    assert "removed" in got and "added" in got and "changed" in got
    same = {"from": 1, "to": 1, "changed": [], "truncated": False}
    (got,) = _run_js([{"fn": "irdiff", "arg": json.dumps(same)}], tmp_path)
    assert "identical" in got


def _v2_summary(repo_root):
    from genesis_rt.ir_v2 import load_ir_v2_file
    from genesis_rt.projects import summarize

    v2 = load_ir_v2_file(repo_root / "examples" / "amr-demo"
                         / "machine-ir-v2.json")
    return summarize(2, v2)


@node
def test_live_state_graph_v2(repo_root, tmp_path):
    summary = _v2_summary(repo_root)
    (svg,) = _run_js([{"fn": "stategraph", "arg": json.dumps(summary)}],
                     tmp_path)
    assert svg.count('data-state=') == 3
    assert "init" in svg and "safe_stop" in svg
    assert 'class="node init"' in svg and 'class="node safe"' in svg
    assert "start" in svg  # transition event label
    (fallback,) = _run_js([{"fn": "stategraph",
                            "arg": json.dumps({"states": []})}],
                          tmp_path)
    assert "No state machine" in fallback and "<svg" not in fallback


@node
def test_live_summary_renders_backend_facts(repo_root, tmp_path):
    summary = _v2_summary(repo_root)
    (got,) = _run_js([{"fn": "summary", "arg": json.dumps(summary)}],
                     tmp_path)
    assert "amr-demo-01" in got and "schema" in got
    assert "states / transitions" in got
    assert "stale_sensor" in got  # fault responses
    assert summary["ir_sha256"][:16] in got


@node
def test_live_job_reducer_dedupes_and_reads_verdict(tmp_path):
    events = [
        {"job_id": "j", "seq": 0, "kind": "queued", "message": "job accepted"},
        {"job_id": "j", "seq": 1, "kind": "started", "message": "worker picked up job"},
        {"job_id": "j", "seq": 1, "kind": "started", "message": "worker picked up job"},
        {"job_id": "j", "seq": 2, "kind": "validated", "message": "machine=x"},
        {"job_id": "j", "seq": 3, "kind": "verdict", "message": "verdict=PASS level=1"},
        {"job_id": "j", "seq": 4, "kind": "done", "message": "verdict=PASS"},
        {"not": "an event"},
    ]
    (got,) = _run_js([{"fn": "jobreduce", "arg": json.dumps(events)}],
                     tmp_path)
    assert got == {"state": "succeeded", "phase": "succeeded",
                   "verdict": "PASS", "n": 5, "lastSeq": 4}
    mid = [{"job_id": "j", "seq": 0, "kind": "queued", "message": "q"},
           {"job_id": "j", "seq": 2, "kind": "generated", "message": "status=ok"}]
    (got,) = _run_js([{"fn": "jobreduce", "arg": json.dumps(mid)}], tmp_path)
    assert (got["state"], got["phase"]) == ("active", "generated")


@node
def test_live_job_html_paints_verdict_and_error(tmp_path):
    events = [{"job_id": "j", "seq": 0, "kind": "queued", "message": "q"}]
    payload = {"id": "run-1", "events": events, "error": None}
    (got,) = _run_js([{"fn": "jobhtml", "arg": json.dumps(payload)}],
                     tmp_path)
    assert "run-1" in got and "queued" in got
    assert "aria-live" in got  # progress announced to screen readers
    failed = {"id": "run-2", "events": events, "error": "boom <b>"}
    (got,) = _run_js([{"fn": "jobhtml", "arg": json.dumps(failed)}],
                     tmp_path)
    assert "boom &lt;b&gt;" in got and "boom <b>" not in got


@node
def test_live_jobs_list_and_empty(tmp_path):
    (empty,) = _run_js([{"fn": "jobs", "arg": "[]"}], tmp_path)
    assert "No runs yet" in empty
    rows = [{"job_id": "run-a", "state": "succeeded", "verdict": "PASS"},
            {"job_id": "run-b", "state": "running", "verdict": None}]
    (got,) = _run_js([{"fn": "jobs", "arg": json.dumps(rows)}], tmp_path)
    assert "run-a" in got and "run-b" in got and "PASS" in got


@node
def test_live_key_from_error(tmp_path):
    calls = [
        {"fn": "keyerr",
         "arg": "invalid IR: control.max_linear_speed_mps must be a number"},
        {"fn": "keyerr", "arg": "ir-v2: $.states[2]: unknown state 'x'"},
        {"fn": "keyerr", "arg": "something went wrong"},
    ]
    got = _run_js(calls, tmp_path)
    assert got == ["max_linear_speed_mps", "states", None]


@node
def test_live_scenario_checks(tmp_path):
    (got,) = _run_js([{"fn": "scen",
                       "arg": json.dumps(["nominal_navigation", "dropped>x"])}],
                     tmp_path)
    assert got.count('checked') == 2 and "dropped&gt;x" in got
    (empty,) = _run_js([{"fn": "scen", "arg": "[]"}], tmp_path)
    assert "No scenarios" in empty


def _graph_passport(amr_ir, tmp_path, tag, scenarios=None, mutate=None):
    manifest = codegen.generate(amr_ir, tmp_path / f"gen-{tag}")
    scenarios = scenarios if scenarios is not None else list(
        amr_ir["verification"]["scenarios"])
    results = faultlab.run_all(amr_ir, scenarios)
    if mutate is not None:
        mutate(results)
    p = evidence.build_passport(f"run-{tag}", amr_ir, manifest, results,
                                {"status": "missing"})
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios))


def _v2_ir(repo_root):
    return json.loads((repo_root / "examples" / "amr-demo" /
                       "machine-ir-v2.json").read_text(encoding="utf-8"))


@node
def test_live_graph_requirements_verdict_and_gaps(amr_ir, tmp_path,
                                                  repo_root):
    from genesis_rt.evidence_graph import build_graph

    p = _graph_passport(amr_ir, tmp_path, "js")
    g = build_graph(p, _v2_ir(repo_root))
    (got,) = _run_js([{"fn": "graph",
                       "arg": json.dumps({"graph": g, "opts": {}})}],
                     tmp_path)
    assert "run-js" in got and "gate PASS" in got
    assert "REQ-AMR-01" in got and "Over-limit" in got
    assert "target unbound" in got and "qnx_verified" in got
    assert "Evidence gaps" in got  # unbound target stays visible
    assert "Attach an IR" not in got
    bare = build_graph(p)
    (got,) = _run_js([{"fn": "graph",
                       "arg": json.dumps({"graph": bare, "opts": {}})}],
                     tmp_path)
    assert "Attach an IR above" in got
    assert "REQ-AMR-01" not in got


@node
def test_live_graph_filters_by_scenario_status_and_search(
        amr_ir, tmp_path, repo_root):
    from genesis_rt.evidence_graph import build_graph

    def fail(results):
        for res in results:
            if res["scenario"] == "dropped_message":
                res["checks"][0]["passed"] = False
                res["status"] = "fail"

    g = build_graph(_graph_passport(amr_ir, tmp_path, "jsf", mutate=fail),
                    _v2_ir(repo_root))
    calls = [
        {"fn": "graph", "arg": json.dumps(
            {"graph": g, "opts": {"scenario": "speed_command_over_limit"}})},
        {"fn": "graph", "arg": json.dumps(
            {"graph": g, "opts": {"status": "failed"}})},
        {"fn": "graph", "arg": json.dumps(
            {"graph": g, "opts": {"q": "genesis_config"}})},
    ]
    scen, failed, found = _run_js(calls, tmp_path)
    assert "scenario:speed_command_over_limit" in scen
    assert "scenario:nominal_navigation" not in scen
    assert "check:dropped_message:gap_detected" in failed
    assert "check:nominal_navigation:no_denials" not in failed
    assert "Failed checks" in failed
    assert "file:genesis_config_gen.h" in found
    assert "scenario:nominal_navigation" not in found


@node
def test_live_graph_escapes_hostile_labels(amr_ir, tmp_path):
    from genesis_rt.evidence_graph import build_graph

    g = build_graph(_graph_passport(amr_ir, tmp_path, "jsx"))
    g["nodes"][3]["label"] = "<script>alert(1)</script>"
    (got,) = _run_js([{"fn": "graph",
                       "arg": json.dumps({"graph": g, "opts": {}})}],
                     tmp_path)
    assert "<script>alert" not in got
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in got
    (detail,) = _run_js([{"fn": "graphnode", "arg": json.dumps(
        {"graph": g, "id": g["nodes"][3]["id"]})}], tmp_path)
    assert "<script>alert" not in detail


@node
def test_live_graph_node_detail_links_and_file_action(amr_ir, tmp_path,
                                                      repo_root):
    from genesis_rt.evidence_graph import build_graph

    g = build_graph(_graph_passport(amr_ir, tmp_path, "jsn"),
                    _v2_ir(repo_root))
    (req,) = _run_js([{"fn": "graphnode", "arg": json.dumps(
        {"graph": g, "id": "req:REQ-AMR-01"})}], tmp_path)
    assert "Over-limit" in req and "verified_by" in req
    assert "scenario:speed_command_over_limit" in req
    (no_file,) = _run_js([{"fn": "graphnode", "arg": json.dumps(
        {"graph": g, "id": "file:genesis_config_gen.h"})}], tmp_path)
    assert "Open generated text" not in no_file
    (with_file,) = _run_js([{"fn": "graphnode", "arg": json.dumps(
        {"graph": g, "id": "file:genesis_config_gen.h",
         "opts": {"runId": "run-jsn"}})}], tmp_path)
    assert "Open generated text" in with_file
    (missing,) = _run_js([{"fn": "graphnode", "arg": json.dumps(
        {"graph": g, "id": "nope"})}], tmp_path)
    assert "Unknown node" in missing


@node
def test_live_graph_diff_shows_limit_change(amr_ir, amr_ir_dict, tmp_path):
    import copy

    from genesis_rt.evidence_graph import build_graph, compare_graphs
    from genesis_rt.ir import validate_ir

    before = build_graph(_graph_passport(amr_ir, tmp_path, "jsd-a"))
    changed = copy.deepcopy(amr_ir_dict)
    changed["control"]["max_linear_speed_mps"] = 0.9
    after_ir = validate_ir(changed)
    scenarios = list(after_ir["verification"]["scenarios"])
    results = faultlab.run_all(after_ir, scenarios)
    manifest = codegen.generate(after_ir, tmp_path / "gen-jsd-b")
    pb = evidence.build_passport("run-jsd-b", after_ir, manifest, results,
                                 {"status": "missing"})
    after = build_graph(
        evidence.attach_verdict(pb, gate.evaluate(pb, scenarios)))
    diff = compare_graphs(before, after)
    (got,) = _run_js([{"fn": "graphdiff", "arg": json.dumps(diff)}],
                     tmp_path)
    assert "run-jsd-a" in got and "run-jsd-b" in got
    assert "limit:max_linear_speed_mps" in got
    assert "0.9" in got and "value" in got
    same = compare_graphs(before, before)
    (got,) = _run_js([{"fn": "graphdiff", "arg": json.dumps(same)}],
                     tmp_path)
    assert "No node changed" in got
