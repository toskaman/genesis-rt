# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Command line: `genesis-rt <validate|plan|generate|simulate|faults|demo|compare|check-env|serve>`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _cmd_validate(args: argparse.Namespace) -> int:
    from .ir import IRValidationError, load_ir_file
    from .ir_v2 import load_ir_v2_file
    version = _peek_schema_version(args.ir)
    if version == 1:
        ir = load_ir_file(args.ir)
    elif version == 2:
        ir = load_ir_v2_file(args.ir)
    else:
        raise IRValidationError(f"{args.ir}: unsupported schema_version={version!r}")
    print(f"valid: schema v{version} {ir['machine']['id']} ({ir['machine']['kind']}) "
          f"scenarios={len(ir['verification']['scenarios'])}")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    from .ir import canonical_json
    from .planning import plan_machine
    ir = plan_machine(args.request, machine_id=args.machine_id)
    out = args.out or f"{args.machine_id}.json"
    Path(out).write_text(json.dumps(ir, indent=2) + "\n", encoding="utf-8")
    print(f"proposal written: {out} ({ir['machine']['kind']})")
    print(f"canonical sha256: {__import__('hashlib').sha256(canonical_json(ir).encode()).hexdigest()}")
    return 0


def _peek_schema_version(path: str) -> int | None:
    if Path(path).suffix.lower() in (".yaml", ".yml"):
        return 1  # v1 only; v2 documents are JSON
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw.get("schema_version") if isinstance(raw, dict) else None


def _cmd_generate(args: argparse.Namespace) -> int:
    import os
    from .codegen import generate
    from .ir import IRValidationError, load_ir_file
    from .ir_v2 import load_ir_v2_file
    from .codegen_v2 import generate_v2
    version = _peek_schema_version(args.ir)
    if version == 1:
        ir = load_ir_file(args.ir)
        generate_fn = generate
    elif version == 2:
        ir = load_ir_v2_file(args.ir)
        generate_fn = generate_v2
    else:
        raise IRValidationError(
            f"{args.ir}: unsupported schema_version={version!r}")
    genesis_src = getattr(args, "genesis_src", None)
    if genesis_src is None:
        # Point the makefile at THIS checkout's target sources, whatever
        # --out depth the user chose (the "../.." default only fits
        # two-level out dirs like artifacts/gen-amr).
        target = REPO_ROOT / "target" / "qnx8"
        if target.is_dir():
            genesis_src = os.path.relpath(target, Path(args.out).resolve()
                                          ).replace(os.sep, "/")
        else:  # installed layout without target sources: keep default
            genesis_src = "../../target/qnx8"
    manifest = generate_fn(ir, args.out, genesis_src=genesis_src)
    print(f"generated: {args.out} (schema v{version})")
    for name, digest in sorted(manifest["files"].items()):
        print(f"  {name}  sha256:{digest[:16]}...")
    return 0


def _load_any_ir(path: str) -> tuple[int, dict]:
    """Load a v1 or v2 IR with the matching strict loader (never reinterpret)."""
    from .ir import IRValidationError, load_ir_file
    from .ir_v2 import load_ir_v2_file
    version = _peek_schema_version(path)
    if version == 1:
        return 1, load_ir_file(path)
    if version == 2:
        return 2, load_ir_v2_file(path)
    raise IRValidationError(
        f"{path}: unsupported schema_version={version!r} (supported: 1, 2)")


def _nominal_scenario(ir: dict) -> str:
    kind = ir["machine"]["kind"]
    declared = list(ir["verification"]["scenarios"])
    preferred = "cell_nominal_transfer" if kind == "industrial_cell" else "nominal_navigation"
    if preferred in declared:
        return preferred
    raise ValueError(f"machine kind {kind!r} declares no nominal scenario "
                     f"({preferred!r} not in verification.scenarios)")


def _cmd_simulate(args: argparse.Namespace) -> int:
    from .faultlab import run_scenario
    version, ir = _load_any_ir(args.ir)
    scenario = args.scenario or _nominal_scenario(ir)
    if scenario not in ir["verification"]["scenarios"]:
        raise ValueError(
            f"scenario {scenario!r} is not declared by {ir['machine']['id']} "
            f"({ir['machine']['kind']}); declared: "
            f"{', '.join(ir['verification']['scenarios'])}")
    res = run_scenario(ir, scenario)
    stats = res["stats"]
    extra = " ".join(f"{k}={stats[k]}" for k in ("allows", "denies", "final_x")
                     if k in stats)
    print(f"schema v{version} {ir['machine']['id']} {scenario}: {res['status']} {extra}".rstrip())
    return 0 if res["status"] == "pass" else 1


def _cmd_faults(args: argparse.Namespace) -> int:
    from .faultlab import run_all
    version, ir = _load_any_ir(args.ir)
    results = run_all(ir)
    print(f"schema v{version} {ir['machine']['id']} ({ir['machine']['kind']})")
    for r in results:
        st = r["stats"]
        print(f"{r['scenario']}: {r['status']} "
              f"(allows={st.get('allows', '-')} denies={st.get('denies', '-')})")
    bad = [r for r in results if r["status"] != "pass"]
    print(f"{len(results) - len(bad)}/{len(results)} scenarios passed")
    return 1 if bad else 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from .orchestrator import run_pipeline
    ir_path = args.ir or str(REPO_ROOT / "examples" / "amr-demo" / "machine-ir.json")
    summary = run_pipeline(ir_path, REPO_ROOT / "artifacts" / "runs",
                           target_record=args.target_record,
                           perf_record=args.perf_record)
    print(f"run: {summary['run_id']}  verdict: {summary['verdict']}  "
          f"level: {summary['level']}  "
          f"release_eligible: {summary['release_eligible']}  "
          f"qnx_verified: {summary['qnx_verified']}  elapsed: {summary['elapsed_s']}s")
    print(f"passport: {summary['passport']}")
    for lr in summary["steps"]["gate"].get("level_reasons", []):
        print(f"  level: {lr}")
    for name, outcome in summary["steps"]["verification"]["scenarios"].items():
        print(f"  {name}: {outcome}")
    for reason in summary["steps"]["gate"]["reasons"]:
        print(f"  gate: {reason}")
    return 0 if summary["verdict"] == "PASS" else 1


def _cmd_compare(args: argparse.Namespace) -> int:
    from .compare import compare_runs, render_text
    comp = compare_runs(args.run_a, args.run_b)
    if args.json:
        print(json.dumps(comp, indent=2, sort_keys=True))
    else:
        print(render_text(comp), end="")
        for name, diff in comp["generated"]["diffs"].items():
            print(f"--- diff: {name} ---")
            print(diff, end="" if diff.endswith("\n") else "\n")
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    from .evidence_graph import build_graph, render_graph_text
    passport = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    ir = json.loads(Path(args.ir).read_text(encoding="utf-8")) if args.ir else None
    graph = build_graph(passport, ir)
    if args.json:
        print(json.dumps(graph, indent=2, sort_keys=True))
    else:
        print(render_graph_text(graph), end="")
    return 0


def _cmd_check_env(args: argparse.Namespace) -> int:
    from .build_adapter import probe
    print(json.dumps(probe(), indent=2))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from .api import create_app
    import uvicorn  # type: ignore[import-not-found]
    # Single worker on loopback: job state (pool, done-events) is in-process;
    # multi-worker mode would need an external job queue. Pool bounds pipelines.
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, workers=1)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="genesis-rt", description="GENESIS RT host toolchain")
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="strictly validate a Machine IR file")
    v.add_argument("ir"); v.set_defaults(func=_cmd_validate)
    pl = sub.add_parser("plan", help="draft a validated IR proposal from a short request")
    pl.add_argument("request"); pl.add_argument("--machine-id", default="machine-01")
    pl.add_argument("--out", default=None); pl.set_defaults(func=_cmd_plan)
    g = sub.add_parser("generate", help="deterministically generate QNX C build files")
    g.add_argument("ir"); g.add_argument("--out", default="generated")
    g.add_argument("--genesis-src", default=None,
                   help="override the makefile GENESIS_SRC (default: relative path "
                        "from --out to this checkout's target/qnx8)")
    g.set_defaults(func=_cmd_generate)
    s = sub.add_parser("simulate", help="run the nominal (or a named) scenario")
    s.add_argument("ir")
    s.add_argument("--scenario", default=None,
                   help="declared scenario id (default: the kind's nominal scenario)")
    s.set_defaults(func=_cmd_simulate)
    f = sub.add_parser("faults", help="run the fault-injection campaign")
    f.add_argument("ir"); f.set_defaults(func=_cmd_faults)
    d = sub.add_parser("demo", help="run the full verified demo pipeline")
    d.add_argument("--ir", default=None)
    d.add_argument("--target-record", default=None,
                   help="qnx-target-record.json from scripts/qnx_target.py verify")
    d.add_argument("--perf-record", default=None,
                   help="qnx-perf-record.json from scripts/qnx_target.py perf")
    d.set_defaults(func=_cmd_demo)
    cmp = sub.add_parser("compare", help="diff two pipeline run directories")
    cmp.add_argument("run_a"); cmp.add_argument("run_b")
    cmp.add_argument("--json", action="store_true"); cmp.set_defaults(func=_cmd_compare)
    gr = sub.add_parser("graph", help="render the evidence graph of a passport")
    gr.add_argument("passport")
    gr.add_argument("--ir", default=None,
                    help="Machine IR JSON (resolves requirement nodes)")
    gr.add_argument("--json", action="store_true"); gr.set_defaults(func=_cmd_graph)
    c = sub.add_parser("check-env", help="probe for a QNX SDK toolchain")
    c.set_defaults(func=_cmd_check_env)
    sv = sub.add_parser("serve", help="start the local web API (needs api extra)")
    sv.add_argument("--port", type=int, default=8077); sv.set_defaults(func=_cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
