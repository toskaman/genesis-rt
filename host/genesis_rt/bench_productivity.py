# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M4 (§12): Engineering Productivity Benchmark harness.

Runs six concrete engineering tasks through two lanes:

- genesis: the real GENESIS RT CLI (validate/generate/faults/demo/
  compare + scripts/replay.py), invoked as subprocesses;
- ref: checked-in reference workflows (scripts/bench_ref/*)
  modeling diligent manual practice — including a COMPETENT
  stock-`jsonschema` validation lane with a hand-maintained
  schema — plus manual steps a developer would do by hand.
  Reference steps are counted, never faked: manual work is
  reported as manual work, and anything the reference cannot
  produce (a bound verdict, an oracle campaign) is reported
  missing — never stubbed.

Measures what is measurable: command counts, machine wall time
(labeled with the machine; never a hardware claim), manual
steps (counted, never timed), produced artifacts,
injected-fault detection, and lane reproducibility (genesis
lane re-run → identical semantic summaries). No human labor
savings are estimated anywhere.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BENCH_VERSION = 2
SCOPE_NOTE = ("wall_s is machine time on the recording host; "
              "manual steps are counted, never timed; "
              "no labor savings estimated")
CMD_TIMEOUT_S = 180
TASK_IDS = ("validate", "generate", "campaign", "evidence", "compare",
            "regression")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class BenchError(RuntimeError):
    """The benchmark itself failed (not a task verdict)."""


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def run_cmd(argv: list[str], *, cwd: Path,
            timeout: int = CMD_TIMEOUT_S) -> dict[str, Any]:
    """Run one command, capturing wall time, exit and output tail."""
    import os as _os
    env = dict(_os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "host")
    env["PYTHONIOENCODING"] = "utf-8"
    start = time.perf_counter()
    try:
        proc = subprocess.run(argv, cwd=str(cwd), env=env,
                              capture_output=True, text=True,
                              timeout=timeout)
    except FileNotFoundError:
        return {"argv": argv, "exit": "blocked",
                "wall_s": round(time.perf_counter() - start, 3),
                "out": f"executable not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"argv": argv, "exit": "timeout",
                "wall_s": round(time.perf_counter() - start, 3),
                "out": f"timed out after {timeout}s"}
    out = (proc.stdout + proc.stderr)[-2000:]
    return {"argv": argv, "exit": proc.returncode,
            "wall_s": round(time.perf_counter() - start, 3), "out": out}


def manifest(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    items = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        data = path.read_bytes()
        items.append({"path": str(path.relative_to(root)),
                      "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    return items


def _cli(*args: str) -> list[str]:
    return [sys.executable, "-m", "genesis_rt.cli", *args]


def _ref(name: str, *args: str) -> list[str]:
    return [sys.executable, str(REPO_ROOT / "scripts" / "bench_ref" / name),
            *args]


def _fixtures(workdir: Path) -> dict[str, str]:
    workdir.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / "examples" / "amr-demo" / "machine-ir.json"
    amr = json.loads(src.read_text(encoding="utf-8"))
    (workdir / "amr.json").write_text(json.dumps(amr, indent=2),
                                      encoding="utf-8")
    broken = dict(amr)
    broken["turbo"] = True  # strict schema rejects unknown keys
    (workdir / "amr_broken.json").write_text(json.dumps(broken, indent=2),
                                             encoding="utf-8")
    tight = json.loads(json.dumps(amr))
    tight["control"]["max_linear_speed_mps"] = 0.05  # nominal needs 0.5
    (workdir / "amr_tight.json").write_text(json.dumps(tight, indent=2),
                                            encoding="utf-8")
    return {"amr": str(workdir / "amr.json"),
            "broken": str(workdir / "amr_broken.json"),
            "tight": str(workdir / "amr_tight.json")}


def _run_lane(cmds: list[list[str]], collect: Any,
              root: Path | None = None) -> dict[str, Any]:
    results = [run_cmd(argv, cwd=REPO_ROOT) for argv in cmds]
    wall = round(sum(r["wall_s"] for r in results), 3)
    base = root or REPO_ROOT
    return {"cmds": results, "n_cmds": len(cmds), "wall_s": wall,
            "exit": results[-1]["exit"] if results else "empty",
            "artifacts": manifest(collect(), base)}


def _scenarios(ir_path: str) -> list[str]:
    doc = json.loads(Path(ir_path).read_text(encoding="utf-8"))
    return list(doc["verification"]["scenarios"])


# --- tasks ---------------------------------------------------------------
def task_validate(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    genesis = _run_lane([_cli("validate", fx["amr"])], list)
    genesis["summary"] = {"exit": genesis["exit"]}
    ref = _run_lane([_ref("validate_schema.py", fx["amr"])], list)
    ref["summary"] = {"exit": ref["exit"]}
    ref["manual_steps"] = [
        "hand-author and version-track amr.schema.json per IR revision",
        "triage stock-validator errors back to IR semantics by eye",
    ]
    g_bad = run_cmd(_cli("validate", fx["broken"]), cwd=REPO_ROOT)
    r_bad = run_cmd(_ref("validate_schema.py", fx["broken"]), cwd=REPO_ROOT)
    return {
        "id": "validate", "title": "Validate a machine contract",
        "genesis": genesis, "ref": ref,
        "fault": {"case": "unknown top-level key 'turbo'",
                  "genesis_detected": g_bad["exit"] != 0,
                  "ref_detected": r_bad["exit"] != 0},
    }


def task_generate(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    gen = workdir / "gen"
    genesis = _run_lane([_cli("generate", fx["amr"], "--out", str(gen))],
                        lambda: list(gen.rglob("*")) if gen.is_dir() else [],
                        workdir)
    genesis["summary"] = {
        "exit": genesis["exit"],
        "files": {a["path"]: a["sha256"] for a in genesis["artifacts"]},
    }
    refgen = workdir / "refgen"
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    ref_cmds = [_ref("render_guard.py", fx["amr"], "--out", str(refgen))]
    if cc is not None:
        ref_cmds.append([cc, "-fsyntax-only",
                         str(refgen / "guard_stunt.h")])
    ref = _run_lane(ref_cmds, lambda: list(refgen.rglob("*"))
                    if refgen.is_dir() else [], workdir)
    ref["summary"] = {"exit": ref["exit"], "cc_available": cc is not None}
    ref["manual_steps"] = [
        "adapt the stunt template by hand per machine kind/field",
    ]
    g_bad = run_cmd(_cli("generate", fx["broken"], "--out",
                         str(workdir / "gen_bad")), cwd=REPO_ROOT)
    r_bad = run_cmd(_ref("render_guard.py", fx["broken"], "--out",
                         str(workdir / "refgen_bad")), cwd=REPO_ROOT)
    return {
        "id": "generate", "title": "Generate the QNX controller sources",
        "genesis": genesis, "ref": ref,
        "fault": {"case": "generate from a contract with key 'turbo'",
                  "genesis_detected": g_bad["exit"] != 0,
                  "ref_detected": r_bad["exit"] != 0},
    }


def _campaign_summary(out: str, exit: Any) -> dict[str, Any]:
    passed = total = None
    for line in out.splitlines():
        if "scenarios passed" in line:
            try:
                head = line.split("scenarios passed")[0].strip()
                num, den = head.split("/")
                passed, total = int(num), int(den)
            except ValueError:
                pass
    return {"exit": exit, "passed": passed, "total": total}


def task_campaign(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    scenarios = _scenarios(fx["amr"])
    genesis = _run_lane([_cli("faults", fx["amr"])], list)
    genesis["summary"] = _campaign_summary(
        genesis["cmds"][0]["out"], genesis["exit"])
    ref_cmds = [_cli("simulate", fx["amr"], "--scenario", name)
                for name in scenarios]
    ref = _run_lane(ref_cmds, list)
    ref["summary"] = {"exit": [c["exit"] for c in ref["cmds"]],
                      "all_ok": all(c["exit"] == 0 for c in ref["cmds"])}
    ref["manual_steps"] = [
        f"eyeball {len(scenarios)} scenario outputs for regressions",
        f"AND {len(scenarios)} exit codes by hand (no oracle verdict)",
    ]
    g_bad = run_cmd(_cli("faults", fx["tight"]), cwd=REPO_ROOT)
    g_sum = _campaign_summary(g_bad["out"], g_bad["exit"])
    r_bad = [run_cmd(_cli("simulate", fx["tight"], "--scenario", name),
                     cwd=REPO_ROOT) for name in scenarios]
    return {
        "id": "campaign", "title": "Run the fault-injection campaign",
        "genesis": genesis, "ref": ref,
        "fault": {"case": "limit 0.05 below the nominal 0.5 m/s",
                  "genesis_detected": g_sum["exit"] != 0,
                  "ref_detected": any(c["exit"] != 0 for c in r_bad)},
    }


def _demo_facts(out: str) -> dict[str, Any]:
    run_id = passport = verdict = None
    for line in out.splitlines():
        if line.startswith("run:"):
            run_id = line.split()[1]
        elif line.startswith("passport:"):
            passport = line.split("passport:")[1].strip()
        elif "verdict:" in line:
            verdict = line.split("verdict:")[1].split()[0]
    run_dir = (str(REPO_ROOT / "artifacts" / "runs" / run_id)
               if run_id else None)
    return {"run_id": run_id, "run_dir": run_dir, "passport": passport,
            "verdict": verdict}


def task_evidence(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    demo = run_cmd(_cli("demo", "--ir", fx["amr"]), cwd=REPO_ROOT)
    facts = _demo_facts(demo["out"])
    if not facts["passport"]:
        raise BenchError(f"demo produced no passport: {demo['out'][-500:]}")
    replay = run_cmd([sys.executable, str(REPO_ROOT / "scripts" / "replay.py"),
                      facts["passport"]], cwd=REPO_ROOT)
    genesis = {"cmds": [demo, replay], "n_cmds": 2,
               "wall_s": round(demo["wall_s"] + replay["wall_s"], 3),
               "exit": replay["exit"],
               "artifacts": manifest([Path(facts["passport"])], REPO_ROOT)}
    genesis["summary"] = {"verdict": facts["verdict"],
                          "chain": "valid" if "chain: valid" in replay["out"]
                          else "NOT valid",
                          "verdict_bound": True}
    log = workdir / "campaign.log"
    faults = run_cmd(_cli("faults", fx["amr"]), cwd=REPO_ROOT)
    log.write_text(faults["out"], encoding="utf-8")
    pkg = workdir / "pkg"
    collect = run_cmd(_ref("collect_package.py", str(log), "--out",
                           str(pkg)), cwd=REPO_ROOT)
    ref = {"cmds": [faults, collect], "n_cmds": 2,
           "wall_s": round(faults["wall_s"] + collect["wall_s"], 3),
           "exit": collect["exit"],
           "artifacts": manifest(list(pkg.rglob("*")), workdir)}
    ref["summary"] = {"checks_present": (pkg / "CHECKS.md").is_file(),
                      "verdict_bound": False}
    ref["manual_steps"] = [
        "write CHECKS.md verdict summary by hand (absent: not faked)",
        "confirm package contents by re-reading logs",
    ]
    tampered = workdir / "passport_tampered.json"
    raw = bytearray(Path(facts["passport"]).read_bytes())
    raw[len(raw) // 2] ^= 0x01
    tampered.write_bytes(bytes(raw))
    g_tamper = run_cmd([sys.executable, str(REPO_ROOT / "scripts"
                                            / "replay.py"), str(tampered)],
                       cwd=REPO_ROOT)
    pkg_manifest = (pkg / "MANIFEST.sha256").read_text(encoding="utf-8")
    log.write_text(log.read_text(encoding="utf-8") + "tampered\n",
                   encoding="utf-8")
    repkg = workdir / "pkg2"
    run_cmd(_ref("collect_package.py", str(log), "--out", str(repkg)),
            cwd=REPO_ROOT)
    ref_tamper = ((repkg / "MANIFEST.sha256").read_text(encoding="utf-8")
                  != pkg_manifest)
    return {
        "id": "evidence", "title": "Produce a reviewable evidence package",
        "genesis": genesis, "ref": ref, "run_dir": facts["run_dir"],
        "fault": {"case": "1 flipped byte in the stored package",
                  "genesis_detected": g_tamper["exit"] != 0,
                  "ref_detected": ref_tamper,
                  "note": "both detect tamper; only genesis binds a verdict",
                  },
    }


def task_compare(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    run_dirs = []
    for key in ("amr", "tight"):
        demo = run_cmd(_cli("demo", "--ir", fx[key]), cwd=REPO_ROOT)
        facts = _demo_facts(demo["out"])
        if not facts["run_dir"]:
            raise BenchError(f"demo produced no run dir: {demo['out'][-500:]}")
        run_dirs.append(facts["run_dir"])
    before, after = run_dirs
    cmp_cmd = run_cmd(_cli("compare", before, after, "--json"), cwd=REPO_ROOT)
    genesis = {"cmds": [cmp_cmd], "n_cmds": 1, "wall_s": cmp_cmd["wall_s"],
               "exit": cmp_cmd["exit"], "artifacts": []}
    genesis["summary"] = {"exit": cmp_cmd["exit"],
                          "names_limit_value": "0.05" in cmp_cmd["out"]}
    diff = run_cmd(["git", "diff", "--no-index", "--stat", before, after],
                   cwd=REPO_ROOT)
    ref = {"cmds": [diff], "n_cmds": 1, "wall_s": diff["wall_s"],
           "exit": diff["exit"], "artifacts": []}
    ref["summary"] = {"exit": diff["exit"],
                      "names_limit_value": "0.05" in diff["out"]}
    ref["manual_steps"] = [
        "interpret which diffs matter for release (no verdicts)",
        "dig out the changed value with a full diff + reading",
    ]
    return {
        "id": "compare", "title": "Compare two releases (0.05 limit)",
        "genesis": genesis, "ref": ref,
        "fault": {"case": "changed limit value visible without digging",
                  "genesis_detected": "0.05" in cmp_cmd["out"],
                  "ref_detected": "0.05" in diff["out"]},
    }


def task_regression(workdir: Path) -> dict[str, Any]:
    fx = _fixtures(workdir)
    scenarios = _scenarios(fx["amr"])
    before = run_cmd(_cli("faults", fx["tight"]), cwd=REPO_ROOT)
    after = run_cmd(_cli("faults", fx["amr"]), cwd=REPO_ROOT)
    genesis = {"cmds": [before, after], "n_cmds": 2,
               "wall_s": round(before["wall_s"] + after["wall_s"], 3),
               "exit": after["exit"], "artifacts": []}
    genesis["summary"] = {
        "before": _campaign_summary(before["out"], before["exit"]),
        "after": _campaign_summary(after["out"], after["exit"]),
    }
    ref_cmds = ([_cli("simulate", fx["tight"], "--scenario", name)
                 for name in scenarios]
                + [_cli("simulate", fx["amr"], "--scenario", name)
                   for name in scenarios])
    ref = _run_lane(ref_cmds, list)
    ref["summary"] = {"exits": [c["exit"] for c in ref["cmds"]]}
    ref["manual_steps"] = [
        f"diff {2 * len(scenarios)} outputs by eye to confirm the fix",
    ]
    return {
        "id": "regression", "title": "Reproduce a failure, confirm the fix",
        "genesis": genesis, "ref": ref, "fault": None,
    }


TASKS = {"validate": task_validate, "generate": task_generate,
         "campaign": task_campaign, "evidence": task_evidence,
         "compare": task_compare, "regression": task_regression}


def run_task(task_id: str, workdir: Path,
             reproduce: bool = True) -> dict[str, Any]:
    """Run one task in both lanes, plus a genesis re-run for repro."""
    if task_id not in TASKS:
        raise BenchError(f"unknown task {task_id!r} (want {TASK_IDS})")
    workdir.mkdir(parents=True, exist_ok=True)
    report = TASKS[task_id](workdir / "lane")
    if reproduce:
        rep = TASKS[task_id](workdir / "repro")
        same = (rep["genesis"]["summary"] == report["genesis"]["summary"])
        report["reproducible"] = same
        report["reproduce_note"] = ("genesis semantic summaries identical"
                                    if same else
                                    "GENESIS SUMMARIES DIFFER")
    else:
        report["reproducible"] = None
        report["reproduce_note"] = "reproducibility check skipped"
    return report


def run_all(out_dir: Path, tasks: list[str] | None = None,
            reproduce: bool = True) -> dict[str, Any]:
    """Run the benchmark; write REPORT.json under out_dir."""
    wanted = list(tasks) if tasks else list(TASK_IDS)
    for task_id in wanted:
        if task_id not in TASKS:
            raise BenchError(f"unknown task {task_id!r} (want {TASK_IDS})")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [run_task(task_id, out_dir / task_id, reproduce)
               for task_id in wanted]
    report = {
        "bench_version": BENCH_VERSION,
        "scope": SCOPE_NOTE,
        "date_utc": _utc_now(),
        "env": {"platform": platform.platform(),
                "python": platform.python_version(),
                "cpus": __import__("os").cpu_count()},
        "tasks": results,
        "totals": {
            "genesis_cmds": sum(t["genesis"]["n_cmds"] for t in results),
            "ref_cmds": sum(t["ref"]["n_cmds"] for t in results),
            "ref_manual_steps": sum(len(t["ref"].get("manual_steps", []))
                                    for t in results),
            "faults_genesis_detected": sum(
                1 for t in results
                if t["fault"] and t["fault"]["genesis_detected"]),
            "faults_ref_detected": sum(
                1 for t in results
                if t["fault"] and t["fault"]["ref_detected"]),
            "faults_total": sum(1 for t in results if t["fault"]),
            "reproducible": all(t.get("reproducible") for t in results
                                if t.get("reproducible") is not None),
        },
    }
    (out_dir / "REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def render_text(report: dict[str, Any]) -> str:
    lines = ["GENESIS RT Engineering Productivity Benchmark",
             f"date: {report['date_utc']} env: {report['env']['platform']}",
             ""]
    for task in report["tasks"]:
        g, r = task["genesis"], task["ref"]
        lines.append(f"[{task['id']}] {task['title']}")
        lines.append(f"  genesis: {g['n_cmds']} cmds, {g['wall_s']}s wall, "
                     f"exit={g['exit']}, artifacts={len(g['artifacts'])}, "
                     f"repro={task.get('reproducible')}")
        lines.append(f"  ref:     {r['n_cmds']} cmds, {r['wall_s']}s wall, "
                     f"exit={r['exit']}, "
                     f"manual={len(r.get('manual_steps', []))} steps, "
                     f"artifacts={len(r['artifacts'])}")
        for step in r.get("manual_steps", []):
            lines.append(f"    manual: {step}")
        if task["fault"]:
            f = task["fault"]
            lines.append(f"  fault '{f['case']}': genesis="
                         f"{'DETECTED' if f['genesis_detected'] else 'MISSED'}"
                         f" ref={'DETECTED' if f['ref_detected'] else 'MISSED'}"
                         + (f" ({f['note']})" if f.get("note") else ""))
    t = report["totals"]
    lines += ["",
              f"totals: genesis {t['genesis_cmds']} cmds vs ref "
              f"{t['ref_cmds']} cmds + {t['ref_manual_steps']} manual steps",
              f"faults: genesis {t['faults_genesis_detected']}/"
              f"{t['faults_total']} vs ref {t['faults_ref_detected']}/"
              f"{t['faults_total']}; reproducible={t['reproducible']}",
              f"scope: {report.get('scope', SCOPE_NOTE)}"]
    return "\n".join(lines) + "\n"
