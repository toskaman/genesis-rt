#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Host benchmark harness: real, labeled, reproducible timings.

Measures host-side costs only (never presented as target performance):
guard decide() latency distribution, full fault-campaign wall time,
codegen time, and native qcc build time when an SDK is present.

Usage: python scripts/bench_host.py [--samples N] [--out report.json]
Methodology and the latest recorded numbers: docs/perf-baseline.md.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt import build_adapter, codegen, faultlab  # noqa: E402
from genesis_rt import guard_policy as gp  # noqa: E402
from genesis_rt.ir import guard_limits, load_ir_file  # noqa: E402


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    k = min(len(ordered) - 1, int(len(ordered) * pct / 100.0))
    return ordered[k]


def _stats(name: str, samples: list[float], unit: str) -> dict:
    return {
        "name": name,
        "unit": unit,
        "n": len(samples),
        "mean": statistics.fmean(samples) if samples else 0.0,
        "min": min(samples) if samples else 0.0,
        "max": max(samples) if samples else 0.0,
        "p50": _percentile(samples, 50),
        "p95": _percentile(samples, 95),
        "p99": _percentile(samples, 99),
    }


def bench_guard(n: int) -> dict:
    limits = {"period_ms": 10, "max_linear_speed_mps": 1.2,
              "max_angular_speed_radps": 1.0, "freshness_limit_ms": 100}
    cmd = {"magic": gp.PROTOCOL_MAGIC, "version": 1, "size_ok": True,
           "seq": 1, "now_ms": 0, "deadline_ms": 50,
           "linear_mps": 0.5, "angular_radps": 0.0,
           "req_state": gp.ST_NOMINAL, "sensor_age_ms": 0,
           "sim_connected": True, "estop_engaged": 0}
    ctx = gp.GuardContext()
    samples = []
    for i in range(n):
        cmd["seq"] = i + 1
        t0 = time.perf_counter()
        verdict = gp.decide(cmd, ctx, limits)
        samples.append((time.perf_counter() - t0) * 1e6)
        assert verdict["decision"] == gp.ALLOW
        ctx.last_seq = cmd["seq"]
    return _stats("guard_decide", samples, "microseconds")


def bench_campaign(ir_path: Path) -> dict:
    ir = load_ir_file(ir_path)
    t0 = time.perf_counter()
    results = faultlab.run_all(ir)
    wall_ms = (time.perf_counter() - t0) * 1000.0
    return {"scenarios": len(results),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "wall_ms": wall_ms}


def bench_codegen(ir_path: Path) -> dict:
    ir = load_ir_file(ir_path)
    with tempfile.TemporaryDirectory(prefix="bench-gen-") as tmp:
        t0 = time.perf_counter()
        manifest = codegen.generate(ir, Path(tmp) / "gen")
        wall_ms = (time.perf_counter() - t0) * 1000.0
    return {"files": len(manifest["files"]), "wall_ms": wall_ms}


def bench_qcc(ir_path: Path) -> dict:
    env = build_adapter.probe()
    if not env["sdk_present"]:
        return {"status": "blocked", "reason": "no SDK on this host"}
    ir = load_ir_file(ir_path)
    with tempfile.TemporaryDirectory(prefix="bench-qnx-") as tmp:
        gen = Path(tmp) / "gen"
        codegen.generate(ir, gen,
                         genesis_src=str(REPO_ROOT / "target" / "qnx8"))
        t0 = time.perf_counter()
        record = build_adapter.build_qnx(gen)
        wall_ms = (time.perf_counter() - t0) * 1000.0
    return {"status": record["status"], "wall_ms": wall_ms,
            "warnings": sum(1 for ln in (record.get("stdout", "")
                                        + record.get("stderr", "")).splitlines()
                            if "warning" in ln.lower())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="host benchmark harness")
    ap.add_argument("--samples", type=int, default=20000)
    ap.add_argument("--ir", default=str(REPO_ROOT / "examples" / "amr-demo"
                                        / "machine-ir.json"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    ir_path = Path(args.ir)
    report = {
        "scope": "host-only (Windows dev machine); NOT target performance",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": __import__("os").cpu_count(),
        },
        "guard": bench_guard(max(100, args.samples)),
        "campaign": bench_campaign(ir_path),
        "codegen": bench_codegen(ir_path),
        "qcc_build": bench_qcc(ir_path),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
