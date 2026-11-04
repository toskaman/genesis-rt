# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: benchmark harness schema (never timing thresholds)."""
import importlib.util
import math


def _load_bench(repo_root):
    spec = importlib.util.spec_from_file_location(
        "bench_host_under_test", repo_root / "scripts" / "bench_host.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_guard_stats_schema(repo_root):
    bench = _load_bench(repo_root)
    stats = bench.bench_guard(500)
    assert stats["name"] == "guard_decide"
    assert stats["unit"] == "microseconds"
    assert stats["n"] == 500
    for key in ("mean", "min", "max", "p50", "p95", "p99"):
        assert math.isfinite(stats[key]) and stats[key] >= 0.0
    assert stats["min"] <= stats["p50"] <= stats["p95"] <= stats["max"]
    assert stats["min"] <= stats["mean"] <= stats["max"]


def test_campaign_codegen_schema(repo_root):
    bench = _load_bench(repo_root)
    ir = repo_root / "examples" / "amr-demo" / "machine-ir.json"
    campaign = bench.bench_campaign(ir)
    assert campaign["scenarios"] == 8 and campaign["passed"] == 8
    assert campaign["wall_ms"] > 0
    codegen = bench.bench_codegen(ir)
    assert codegen["files"] == 2 and codegen["wall_ms"] > 0


def test_qcc_bench_reports_status(repo_root):
    bench = _load_bench(repo_root)
    ir = repo_root / "examples" / "amr-demo" / "machine-ir.json"
    record = bench.bench_qcc(ir)
    assert record["status"] in ("ok", "blocked")
    if record["status"] == "ok":
        assert record["wall_ms"] > 0 and record["warnings"] == 0
