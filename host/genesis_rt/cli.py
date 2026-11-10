# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Command line: `genesis-rt <validate|plan|generate|simulate|faults|demo|compare|check-env|serve>`."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_KEY_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _locate_error_line(path: str, message: str) -> int | None:
    """Best-effort file:line span for a validator message (OMEGA6 C3).

    CLI presentation only — the validator is untouched. Identifier-ish
    words from the message (longest first) are matched against quoted
    keys/values (JSON) or `key:` lines (YAML); returns None when
    nothing matches (e.g. a missing key), leaving the message as-is.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    words = sorted(set(_KEY_WORD.findall(message)), key=len, reverse=True)
    for word in words:
        if len(word) < 3:
            continue
        for lineno, line in enumerate(lines, 1):
            if (f'"{word}"' in line or f"'{word}'" in line
                    or re.search(rf"(^|[\s{{,]){re.escape(word)}\s*:",
                                 line)):
                return lineno
    return None


def _cmd_validate(args: argparse.Namespace) -> int:
    from .ir import IRValidationError, load_ir_file
    from .ir_v2 import load_ir_v2_file
    try:
        version = _peek_schema_version(args.ir)
        if version == 1:
            ir = load_ir_file(args.ir)
        elif version == 2:
            ir = load_ir_v2_file(args.ir)
        else:
            raise IRValidationError(
                f"{args.ir}: unsupported schema_version={version!r}")
    except IRValidationError as exc:
        line = _locate_error_line(args.ir, str(exc))
        if line is not None and f"{args.ir}:{line}" not in str(exc):
            raise IRValidationError(
                f"{args.ir}:{line}: {exc}") from None
        raise
    print(f"valid: schema v{version} {ir['machine']['id']} ({ir['machine']['kind']}) "
          f"scenarios={len(ir['verification']['scenarios'])}")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    from .ir import canonical_json
    from .planning import plan_machine
    ir = plan_machine(args.request, machine_id=args.machine_id,
                      provider=getattr(args, "provider", "offline"))
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


def _cmd_external_check(args: argparse.Namespace) -> int:
    from .external import check_workspace, render_text
    report = check_workspace(args.manifest, args.workspace)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0 if report["verdict"] == "CONSISTENT" else 2


def _cmd_external_write_manifest(args: argparse.Namespace) -> int:
    from .external import write_manifest
    manifest = write_manifest(args.workspace, args.project,
                              args.toolchain, args.only or None)
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


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


def _cmd_verify_change(args: argparse.Namespace) -> int:
    from .change import render_card_text, verify_change
    runs_dir = Path(args.artifacts_dir
                    or str(REPO_ROOT / "artifacts" / "runs"))
    verdict = verify_change(args.before, args.after, runs_dir,
                            runs_dir.parent / "change",
                            change_id=args.id,
                            scenarios=args.scenarios)
    if args.json:
        print(json.dumps({k: v for k, v in verdict.items()
                          if k != "verdict_path"},
                         indent=2, sort_keys=True))
    else:
        print(render_card_text(verdict), end="")
    # Mirror `demo`: a rendered card for a FAIL after-leg still exits 1;
    # a leg that cannot run raises ChangeLegError (exit 2 via main()).
    return 0 if verdict["verdict"] == "PASS" else 1


def _cmd_demo_break(args: argparse.Namespace) -> int:
    import tempfile as _tempfile
    import time as _time

    from .breakdemo import BUDGET_S, run_break_demo
    t0 = _time.monotonic()
    if args.workspace:
        report = run_break_demo(args.workspace)
    else:
        with _tempfile.TemporaryDirectory(prefix="genesis-break-") as tmp:
            report = run_break_demo(tmp)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"sealed {len(report['binaries'])} binaries -> CONSISTENT")
        print(f"mutated genesis_guard -> {report['stale']['verdict']}: "
              f"{', '.join(report['stale']['stale_binaries'])}")
        print(f"stale-refusal demo: STALE in {report['elapsed_s']}s "
              f"(budget {BUDGET_S:.0f}s) — the wrong binary cannot pass.")
    if _time.monotonic() - t0 > BUDGET_S:
        print(f"OVER BUDGET: demo exceeded {BUDGET_S:.0f}s", file=sys.stderr)
        return 1
    return 0


_QUICKSTART_EXAMPLES = {
    "cell": "examples/cell-demo/cell-ir.json",
    "amr": "examples/amr-demo/machine-ir.json",
    "conveyor": "examples/conveyor-demo/machine-ir.json",
}


def _cmd_quickstart(args: argparse.Namespace) -> int:
    from .ir import IRValidationError
    from .orchestrator import run_pipeline
    ir_path = args.ir or str(REPO_ROOT / _QUICKSTART_EXAMPLES[args.example])
    try:
        version = _peek_schema_version(ir_path)
        if version == 1:
            from .ir import load_ir_file
            ir = load_ir_file(ir_path)
        elif version == 2:
            from .ir_v2 import load_ir_v2_file
            ir = load_ir_v2_file(ir_path)
        else:
            raise IRValidationError(
                f"{ir_path}: unsupported schema_version={version!r}")
    except (IRValidationError, OSError, ValueError) as exc:
        print(f"invalid: {exc}")
        return 2
    machine = ir["machine"]["id"]
    summary = run_pipeline(ir_path, REPO_ROOT / "artifacts" / "runs")
    if args.json:
        print(json.dumps({
            "ir": ir_path, "machine": machine, "valid": True,
            "verdict": summary["verdict"], "level": summary["level"],
            "release_eligible": summary["release_eligible"],
            "qnx_verified": summary["qnx_verified"],
            "passport": summary["passport"],
            "elapsed_s": summary["elapsed_s"]}, indent=2, sort_keys=True))
    else:
        print(f"valid: schema v{version} {machine} "
              f"({ir['machine']['kind']}) "
              f"scenarios={len(ir['verification']['scenarios'])}")
        print(f"run: {summary['run_id']}  verdict: {summary['verdict']}  "
              f"level: {summary['level']}  "
              f"release_eligible: {summary['release_eligible']}  "
              f"qnx_verified: {summary['qnx_verified']}  "
              f"elapsed: {summary['elapsed_s']}s")
        print(f"passport: {summary['passport']}")
        for name, outcome in summary["steps"]["verification"][
                "scenarios"].items():
            print(f"  {name}: {outcome}")
        print("next: genesis-rt verify-change --before <a> --after <b>  "
              "# prove one change")
        print("next: genesis-rt demo-break  # watch STALE refuse a mutant")
    return 0 if summary["verdict"] == "PASS" else 1


def _watch_check(ir_path: str) -> tuple[bool, str]:
    """Validate once; returns (ok, one verdict line). Presentation only —
    the validator stays the authority (C3 file:line spans preserved)."""
    from .ir import IRValidationError
    try:
        version = _peek_schema_version(ir_path)
        if version == 1:
            from .ir import load_ir_file
            ir = load_ir_file(ir_path)
        elif version == 2:
            from .ir_v2 import load_ir_v2_file
            ir = load_ir_v2_file(ir_path)
        else:
            raise IRValidationError(
                f"{ir_path}: unsupported schema_version={version!r}")
    except (IRValidationError, OSError, ValueError) as exc:
        line = _locate_error_line(ir_path, str(exc))
        detail = f"{ir_path}:{line}: {exc}" if line is not None \
            else f"{ir_path}: {exc}"
        return False, f"INVALID {detail}"
    return True, (f"VALID schema v{version} {ir['machine']['id']} "
                  f"({ir['machine']['kind']})")


def _cmd_watch(args: argparse.Namespace) -> int:
    import time as _time
    if args.once:
        ok, line_out = _watch_check(args.ir)
        print(line_out)
        return 0 if ok else 2
    last: tuple[float, int] | None = None
    rc = 0
    t0 = _time.monotonic()
    try:
        while True:
            try:
                stat = Path(args.ir).stat()
                sig: tuple[float, int] | None = (stat.st_mtime, stat.st_size)
            except OSError:
                sig = None
            if sig != last:
                last = sig
                ok, line_out = _watch_check(args.ir)
                print(line_out, flush=True)
                rc = 0 if ok else 2
            if args.timeout is not None and \
                    _time.monotonic() - t0 >= args.timeout:
                return rc
            _time.sleep(args.interval)
    except KeyboardInterrupt:
        print("watch stopped.", file=sys.stderr)
        return rc


def _cmd_new(args: argparse.Namespace) -> int:
    from .newmachine import (NewMachineError, OFFERED_KINDS, TEMPLATES,
                             build_machine_ir, resolve_kind)
    if args.out is None:
        print("missing --out FILE (where to write the IR)")
        return 2
    out = Path(args.out)
    if out.exists() and not args.force:
        print(f"exists: {out} (refusing to overwrite; use --force)")
        return 2
    try:
        if args.interactive:
            print(f"kinds: {', '.join(OFFERED_KINDS)} "
                  "(arm excluded until arm physics lands)")
            kind = input("kind: ")
            machine_id = input("machine id: ")
            template = json.loads(
                (REPO_ROOT / TEMPLATES[resolve_kind(kind)]
                 ).read_text(encoding="utf-8"))
            overrides: dict[str, str] = {}
            for key in sorted(template["control"]):
                raw = input(f"{key} [{template['control'][key]}]: ").strip()
                if raw:
                    overrides[key] = raw
        else:
            if args.kind is None or args.id is None:
                print("missing --kind KIND and --id ID "
                      "(or use --interactive)")
                return 2
            kind, machine_id = args.kind, args.id
            overrides = {}
            for item in args.set or []:
                if "=" not in item:
                    print(f"invalid --set {item!r} (want KEY=VALUE)")
                    return 2
                key, _, value = item.partition("=")
                overrides[key.strip()] = value.strip()
        ir = build_machine_ir(kind, machine_id, overrides, out)
    except NewMachineError as exc:
        print(f"invalid: {exc}")
        return 2
    print(f"machine written: {out} ({ir['machine']['kind']})")
    print(f"next: genesis-rt validate {out}")
    print(f"next: genesis-rt quickstart --ir {out}  # run it")
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


def _cmd_impact(args: argparse.Namespace) -> int:
    from .impact import (analyze_impact, release_status, render_impact_text,
                         render_release_text)
    before = json.loads(Path(args.ir_before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.ir_after).read_text(encoding="utf-8"))
    if args.passport_after:
        passport = json.loads(Path(args.passport_after).read_text(
            encoding="utf-8"))
        base = json.loads(Path(args.passport_before).read_text(
            encoding="utf-8")) if args.passport_before else None
        status = release_status(before, after, passport, base)
        if args.json:
            print(json.dumps(status, indent=2, sort_keys=True))
        else:
            print(render_release_text(status), end="")
    else:
        report = analyze_impact(before, after)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_impact_text(report), end="")
    return 0


def _cmd_explore(args: argparse.Namespace) -> int:
    from .explorer import explore, render_explore_text
    ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))
    params: dict[str, Any] = {}
    for item in args.param or []:
        if "=" not in item:
            raise ValueError(f"--param needs k=v, got {item!r}")
        key, raw = item.split("=", 1)
        try:
            params[key] = float(raw)
        except ValueError:
            raise ValueError(f"--param {key} needs a number, got {raw!r}")
    budgets: dict[str, Any] = {}
    if args.max_scripts is not None:
        budgets["max_scripts"] = args.max_scripts
    if args.max_findings is not None:
        budgets["max_findings"] = args.max_findings
    if args.max_seconds is not None:
        budgets["max_seconds"] = args.max_seconds
    report = explore(ir, invariant=args.invariant, params=params,
                     strategies=args.strategy or None,
                     budgets=budgets or None, seed=args.seed)
    text = json.dumps(report, indent=2, sort_keys=True) if args.json \
        else render_explore_text(report)
    if args.out:
        Path(args.out).write_text(text if text.endswith("\n") else text + "\n",
                                  encoding="utf-8")
    else:
        print(text if text.endswith("\n") else text + "\n", end="")
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    from .explorer import replay, render_replay_text
    record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))
    result = replay(record, ir)
    if args.conformance:
        from .explorer_conformance import replay_conformance
        from .ir import guard_limits
        from .projects import validate_any
        _version, norm = validate_any(ir)
        result["conformance"] = replay_conformance(
            result["record"], guard_limits(norm), args.repo_root)
    text = json.dumps(result, indent=2, sort_keys=True) if args.json \
        else render_replay_text(result)
    print(text if text.endswith("\n") else text + "\n", end="")
    return 0


def _cmd_twin(args: argparse.Namespace) -> int:
    from .twin import render_track_text, track_from_passport
    passport = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    track = track_from_passport(passport, args.scenario)
    text = json.dumps(track, indent=2, sort_keys=True) if args.json \
        else render_track_text(track)
    if args.out:
        Path(args.out).write_text(text if text.endswith("\n") else text + "\n",
                                  encoding="utf-8")
    else:
        print(text if text.endswith("\n") else text + "\n", end="")
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    from .bench_productivity import TASK_IDS, render_text, run_all
    tasks = args.tasks.split(",") if args.tasks else list(TASK_IDS)
    out = Path(args.out) if args.out else (
        REPO_ROOT / "bench" / "productivity" / "last-run")
    report = run_all(out, tasks, reproduce=not args.no_reproduce)
    print(render_text(report), end="")
    print(f"report: {out / 'REPORT.json'}")
    bad = [t for t in report["tasks"] if t.get("reproducible") is False]
    return 1 if bad else 0


def _cmd_check_env(args: argparse.Namespace) -> int:
    from .build_adapter import probe
    print(json.dumps(probe(), indent=2))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        from .api import create_app
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"serve needs the api extra: pip install -e '.[api]' ({exc})",
              file=sys.stderr)
        return 2
    # Single worker on loopback: job state (pool, done-events) is in-process;
    # multi-worker mode would need an external job queue. Pool bounds pipelines.
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, workers=1)
    return 0


def _cmd_sign_pack(args: argparse.Namespace) -> int:
    try:
        from . import signing
    except ImportError as exc:
        print(f"sign-pack needs cryptography: pip install cryptography ({exc})",
              file=sys.stderr)
        return 2
    pack = Path(args.pack)
    manifest = pack / "manifest.json"
    if not manifest.is_file():
        print(f"no manifest.json in {pack}", file=sys.stderr)
        return 2
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or not meta.get("pack"):
        print("manifest.json has no pack name", file=sys.stderr)
        return 2
    key_pem = Path(args.key).read_text(encoding="utf-8")
    try:
        envelope = signing.sign_manifest(
            manifest_bytes=manifest.read_bytes(),
            purpose=signing.PURPOSE_EVIDENCE_PACK,
            signer_id=args.signer_id, key_id=args.key_id,
            private_pem=key_pem, scope={"pack": meta["pack"]},
            supersedes=args.supersedes)
    except signing.SignatureError as exc:
        print(f"signing failed: {exc}", file=sys.stderr)
        return 1
    out = pack / "manifest.sig.json"
    out.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"signed {meta['pack']} key={args.key_id} "
          f"signer={args.signer_id} -> {out}")
    return 0


def _cmd_verify_pack(args: argparse.Namespace) -> int:
    try:
        from . import signing
    except ImportError as exc:
        print(f"verify-pack needs cryptography: pip install cryptography ({exc})",
              file=sys.stderr)
        return 2
    pack = Path(args.pack)
    manifest = pack / "manifest.json"
    sig = pack / "manifest.sig.json"
    verdict: dict[str, object] = {"pack": str(pack), "status": "INVALID"}
    if not manifest.is_file():
        verdict["reason"] = "no manifest.json"
    elif not signing.is_signed(pack):
        verdict["status"] = "UNSIGNED"
        verdict["reason"] = ("no manifest.sig.json: integrity is hash-only, "
                             "no signer bound")
    else:
        try:
            trust_raw = json.loads(Path(args.trust).read_text(
                encoding="utf-8"))
            trust = trust_raw.get("keys", {})
            meta = json.loads(manifest.read_text(encoding="utf-8"))
            body = signing.verify_envelope(
                envelope=json.loads(sig.read_text(encoding="utf-8")),
                manifest_bytes=manifest.read_bytes(), trust=trust,
                purpose=signing.PURPOSE_EVIDENCE_PACK,
                scope={"pack": meta.get("pack")})
            verdict = {"pack": meta.get("pack"), "status": "SIGNED_VALID",
                       "signer_id": body.get("signer_id"),
                       "key_id": body.get("key_id"),
                       "signed_utc": body.get("signed_utc")}
        except (signing.SignatureError, ValueError, OSError,
                TypeError, AttributeError) as exc:
            verdict["reason"] = str(exc)
    if args.json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    elif verdict["status"] == "SIGNED_VALID":
        print(f"{verdict['pack']}: SIGNED_VALID signer={verdict['signer_id']} "
              f"key={verdict['key_id']}")
    else:
        print(f"{pack}: {verdict['status']}: {verdict.get('reason')}")
    return {"SIGNED_VALID": 0, "UNSIGNED": 2}.get(
        str(verdict["status"]), 1)


def _runner_dirs(args: argparse.Namespace) -> tuple:
    from pathlib import Path as _P
    jobs = _P(args.jobs_dir) if args.jobs_dir else REPO_ROOT / "artifacts" / "runner-jobs"
    ops = _P(args.ops_dir) if args.ops_dir else REPO_ROOT / "artifacts" / "target-ops"
    return jobs, ops


def _cmd_runner_submit(args: argparse.Namespace) -> int:
    import os as _os
    import time as _time
    from . import runner as _runner
    token = _os.environ.get("GENESIS_RUNNER_TOKEN")
    if not token:
        print("GENESIS_RUNNER_TOKEN is not set", file=sys.stderr)
        return 2
    jobs_dir, ops_dir = _runner_dirs(args)
    body = Path(args.job).read_bytes()
    cfg = _runner.RunnerConfig(
        repo_root=REPO_ROOT, jobs_dir=jobs_dir, target_ops_dir=ops_dir,
        image_dir=args.image_dir, adapter=args.adapter)
    target = None
    if args.adapter == "local":
        from .target import TargetRunner
        target = TargetRunner(ops_dir)
    try:
        try:
            rec = _runner.submit(body, _runner.sign_body(body, token),
                                 config=cfg, token=token, target=target)
        except _runner.RunnerAuthError as exc:
            print(f"auth failed: {exc}", file=sys.stderr)
            return 1
        except _runner.RunnerBusy as exc:
            print(f"target busy: {exc}", file=sys.stderr)
            return 2
        except _runner.RunnerError as exc:
            print(f"rejected: {exc}", file=sys.stderr)
            return 1
        if args.no_wait or rec.get("status") in _runner.TERMINAL_JOB:
            print(json.dumps(rec, indent=2, sort_keys=True, default=str))
            return 0 if rec.get("status") == "COMPLETED" else 1
        deadline = _time.time() + rec.get("timeout_s", 600) + 120
        while _time.time() < deadline:
            cur = _runner.status(cfg, rec["job_id"]) or {}
            if cur.get("status") in _runner.TERMINAL_JOB:
                print(json.dumps(cur, indent=2, sort_keys=True, default=str))
                return 0 if cur.get("status") == "COMPLETED" else 1
            _time.sleep(2.0)
        print(f"timed out waiting for {rec['job_id']}", file=sys.stderr)
        return 1
    finally:
        if target is not None:
            target.close()


def _cmd_runner_status(args: argparse.Namespace) -> int:
    from . import runner as _runner
    jobs_dir, _ = _runner_dirs(args)
    cfg = _runner.RunnerConfig(repo_root=REPO_ROOT, jobs_dir=jobs_dir,
                               target_ops_dir=REPO_ROOT / "artifacts")
    rec = _runner.status(cfg, args.job_id)
    if rec is None:
        print(f"unknown job: {args.job_id}", file=sys.stderr)
        return 2
    print(json.dumps(rec, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_runner_cancel(args: argparse.Namespace) -> int:
    from . import runner as _runner
    jobs_dir, ops_dir = _runner_dirs(args)
    cfg = _runner.RunnerConfig(repo_root=REPO_ROOT, jobs_dir=jobs_dir,
                               target_ops_dir=ops_dir)
    from .target import TargetRunner
    target = TargetRunner(ops_dir)
    try:
        try:
            rec = _runner.cancel(cfg, args.job_id, target)
        except _runner.RunnerError as exc:
            print(f"cancel failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(rec, indent=2, sort_keys=True, default=str))
        return 0
    finally:
        target.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="genesis-rt", description="GENESIS RT host toolchain")
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="strictly validate a Machine IR file")
    v.add_argument("ir"); v.set_defaults(func=_cmd_validate)
    pl = sub.add_parser("plan", help="draft a validated IR proposal from a short request")
    pl.add_argument("request"); pl.add_argument("--machine-id", default="machine-01")
    pl.add_argument("--provider", choices=["offline", "llm"], default="offline",
                    help="offline (default, deterministic) or llm (opt-in, env-configured)")
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
    ec = sub.add_parser("external-check",
                        help="digest-consistency of an external build dir vs a manifest")
    ec.add_argument("manifest", help="external manifest JSON (schema v1)")
    ec.add_argument("--workspace", required=True,
                    help="directory holding the built binaries")
    ec.add_argument("--json", action="store_true")
    ec.set_defaults(func=_cmd_external_check)
    ewm = sub.add_parser("external-write-manifest",
                         help="hash a build dir into an external manifest")
    ewm.add_argument("--workspace", required=True)
    ewm.add_argument("--project", required=True)
    ewm.add_argument("--toolchain", required=True,
                     help="free-text toolchain id (recorded, not verified)")
    ewm.add_argument("--only", nargs="*", default=None,
                     help="cover only these files (default: all)")
    ewm.add_argument("--out", default=None)
    ewm.set_defaults(func=_cmd_external_write_manifest)
    cmp = sub.add_parser("compare", help="diff two pipeline run directories")
    cmp.add_argument("run_a"); cmp.add_argument("run_b")
    cmp.add_argument("--json", action="store_true"); cmp.set_defaults(func=_cmd_compare)
    vc = sub.add_parser("verify-change",
                        help="prove one IR change: run BEFORE+AFTER, render one verdict card")
    vc.add_argument("--before", required=True, help="before-revision Machine IR file")
    vc.add_argument("--after", required=True, help="after-revision Machine IR file")
    vc.add_argument("--id", default=None, help="change id (default: chg-<random>)")
    vc.add_argument("--scenarios", nargs="*", default=None,
                    help="run only these scenarios on both legs")
    vc.add_argument("--artifacts-dir", default=None,
                    help="runs directory (default: artifacts/runs; "
                         "verdict.json goes to artifacts/change/<id>/)")
    vc.add_argument("--json", action="store_true")
    vc.set_defaults(func=_cmd_verify_change)
    db = sub.add_parser("demo-break",
                        help="seal, mutate one binary, watch STALE refuse it")
    db.add_argument("--workspace", default=None,
                    help="keep the demo workspace here (default: temp dir)")
    db.add_argument("--json", action="store_true")
    db.set_defaults(func=_cmd_demo_break)
    qs = sub.add_parser("quickstart",
                        help="validate + run an example, print the card")
    qs.add_argument("--example", default="cell",
                    choices=sorted(_QUICKSTART_EXAMPLES),
                    help="bundled example (default: cell)")
    qs.add_argument("--ir", default=None,
                    help="Machine IR file (overrides --example)")
    qs.add_argument("--json", action="store_true")
    qs.set_defaults(func=_cmd_quickstart)
    wt = sub.add_parser("watch",
                        help="re-validate an IR file on every save")
    wt.add_argument("ir", help="Machine IR file to watch")
    wt.add_argument("--once", action="store_true",
                    help="validate once and exit")
    wt.add_argument("--interval", type=float, default=0.5,
                    help="poll interval in seconds (default: 0.5)")
    wt.add_argument("--timeout", type=float, default=None,
                    help="stop after SECONDS (exit code is last verdict)")
    wt.set_defaults(func=_cmd_watch)
    nw = sub.add_parser("new",
                        help="build a first Machine IR from an example")
    nw.add_argument("--kind", default=None,
                    help="machine kind (cell, amr, conveyor, or full name)")
    nw.add_argument("--id", default=None, help="machine id")
    nw.add_argument("--out", default=None, help="where to write the IR file")
    nw.add_argument("--set", action="append", default=None,
                    help="knob override KEY=VALUE (repeatable)")
    nw.add_argument("--force", action="store_true",
                    help="overwrite an existing --out file")
    nw.add_argument("--interactive", action="store_true",
                    help="prompt for kind, id and knobs")
    nw.set_defaults(func=_cmd_new)
    gr = sub.add_parser("graph", help="render the evidence graph of a passport")
    gr.add_argument("passport")
    gr.add_argument("--ir", default=None,
                    help="Machine IR JSON (resolves requirement nodes)")
    gr.add_argument("--json", action="store_true"); gr.set_defaults(func=_cmd_graph)
    im = sub.add_parser("impact", help="change-impact between two IR revisions")
    im.add_argument("ir_before"); im.add_argument("ir_after")
    im.add_argument("--json", action="store_true")
    im.add_argument("--passport-after", default=None,
                    help="new-run passport.json: full release comparison")
    im.add_argument("--passport-before", default=None,
                    help="before-run passport.json: binary-change verdict")
    im.set_defaults(func=_cmd_impact)
    ex = sub.add_parser("explore", help="search for invariant counterexamples")
    ex.add_argument("ir")
    ex.add_argument("--invariant", default="no_over_limit_allow")
    ex.add_argument("--param", action="append", default=None,
                    help="invariant param k=v (repeatable)")
    ex.add_argument("--strategy", action="append", default=None,
                    help="boundary|pairs|windows|mutate (repeatable)")
    ex.add_argument("--max-scripts", type=int, default=None)
    ex.add_argument("--max-findings", type=int, default=None)
    ex.add_argument("--max-seconds", type=int, default=None)
    ex.add_argument("--seed", type=int, default=0)
    ex.add_argument("--out", default=None)
    ex.add_argument("--json", action="store_true")
    ex.set_defaults(func=_cmd_explore)
    rp = sub.add_parser("replay", help="re-run an explorer finding")
    rp.add_argument("record", help="finding record JSON (from explore --json)")
    rp.add_argument("ir", help="IR to replay on (original or fixed)")
    rp.add_argument("--json", action="store_true")
    rp.add_argument("--conformance", action="store_true",
                    help="also replay vectors through the C guard")
    rp.add_argument("--repo-root", default=".",
                    help="checkout root (locates target/qnx8)")
    rp.set_defaults(func=_cmd_replay)
    bn = sub.add_parser("bench", help="run the productivity benchmark")
    bn.add_argument("--tasks", default=None,
                    help="comma-separated task ids (default: all)")
    bn.add_argument("--out", default=None, help="report directory")
    bn.add_argument("--no-reproduce", action="store_true",
                    help="skip the genesis re-run reproducibility check")
    bn.set_defaults(func=_cmd_bench)
    tw = sub.add_parser("twin", help="fold a passport scenario into a replay track")
    tw.add_argument("passport", help="evidence passport JSON file")
    tw.add_argument("--scenario", required=True, help="scenario name to fold")
    tw.add_argument("--json", action="store_true")
    tw.add_argument("--out", default=None, help="write the track JSON here")
    tw.set_defaults(func=_cmd_twin)
    c = sub.add_parser("check-env", help="probe for a QNX SDK toolchain")
    c.set_defaults(func=_cmd_check_env)
    sv = sub.add_parser("serve", help="start the local web API (needs api extra)")
    sv.add_argument("--port", type=int, default=8077); sv.set_defaults(func=_cmd_serve)
    sg = sub.add_parser("sign-pack", help="Ed25519-sign an evidence-pack manifest")
    sg.add_argument("pack"); sg.add_argument("--key", required=True)
    sg.add_argument("--signer-id", required=True); sg.add_argument("--key-id", required=True)
    sg.add_argument("--supersedes", default=None)
    sg.set_defaults(func=_cmd_sign_pack)
    vf = sub.add_parser("verify-pack", help="verify an evidence-pack signature (0 valid, 2 unsigned, 1 invalid)")
    vf.add_argument("pack"); vf.add_argument("--trust", required=True)
    vf.add_argument("--json", action="store_true")
    vf.set_defaults(func=_cmd_verify_pack)
    rs = sub.add_parser("runner-submit", help="submit a signed native-verification job (token in GENESIS_RUNNER_TOKEN)")
    rs.add_argument("--job", required=True); rs.add_argument("--adapter", default="local", choices=("local", "fake"))
    rs.add_argument("--jobs-dir", default=None); rs.add_argument("--ops-dir", default=None)
    rs.add_argument("--image-dir", default=None); rs.add_argument("--no-wait", action="store_true")
    rs.set_defaults(func=_cmd_runner_submit)
    rt = sub.add_parser("runner-status", help="show a runner job record")
    rt.add_argument("--job-id", required=True); rt.add_argument("--jobs-dir", default=None)
    rt.add_argument("--ops-dir", default=None)
    rt.set_defaults(func=_cmd_runner_status)
    rc = sub.add_parser("runner-cancel", help="cancel a runner job")
    rc.add_argument("--job-id", required=True); rc.add_argument("--jobs-dir", default=None)
    rc.add_argument("--ops-dir", default=None)
    rc.set_defaults(func=_cmd_runner_cancel)
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
