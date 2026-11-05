# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt import codegen, provenance  # noqa: E402
from genesis_rt.ir import load_ir_file  # noqa: E402


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def amr_ir_path(repo_root: Path) -> Path:
    return repo_root / "examples" / "amr-demo" / "machine-ir.json"


@pytest.fixture()
def amr_ir(amr_ir_path: Path) -> dict:
    return load_ir_file(amr_ir_path)


@pytest.fixture()
def amr_ir_dict(amr_ir_path: Path) -> dict:
    return json.loads(amr_ir_path.read_text(encoding="utf-8"))


@pytest.fixture()
def cell_ir_path(repo_root: Path) -> Path:
    return repo_root / "examples" / "cell-demo" / "cell-ir.json"


@pytest.fixture()
def cell_ir(cell_ir_path: Path) -> dict:
    return load_ir_file(cell_ir_path)


@pytest.fixture()
def bound_evidence(amr_ir: dict, tmp_path: Path) -> dict:
    """Bound QNX evidence (single source for the §6 contract fixtures).

    Returns manifest + build/target/perf records that satisfy every
    provenance binding, so tests asserting high tiers start from a
    KNOWN-BOUND baseline and mutate exactly one variable. Each test
    gets fresh dicts (function-scoped); mutate freely.
    """
    manifest = codegen.generate(amr_ir, tmp_path / "gen-bound")
    build_bins = {}
    for name in ("genesis_guard", "genesis_controller", "genesis_device",
                 "genesis_status", "genesis_supervisor",
                 "genesis_faultinject"):
        build_bins[name] = {"sha256": "ab" * 32,
                            "cksum": 1000 + len(name),
                            "size": 14000 + len(name)}
    build = {"status": "ok", "verified_on_target": False,
             "built_utc": "2026-11-04T20:00:00+00:00",
             "qcc_version": "12.2.0,gcc_ntox86_64",
             "binaries": build_bins}
    staged = {n: {"cksum": b["cksum"], "size": b["size"]}
              for n, b in build_bins.items()}
    staged["genesis_guard_conv"] = {"cksum": 4242, "size": 14360}
    staged["genesis_guard_v2"] = {"cksum": 4343, "size": 15136}
    target = {
        "status": "ok", "verified_on_target": True, "user": "qnxuser",
        "provenance_version": 1,
        "matrix": list(provenance.EXPECTED_TARGET_CHECKS),
        "checks": [{"name": n, "passed": True, "detail": "ok"}
                   for n in provenance.EXPECTED_TARGET_CHECKS],
        "started_utc": "2026-11-04T20:10:00+00:00",
        "finished_utc": "2026-11-04T20:20:00+00:00",
        "target": {"platform": "qnx8_x86_64_qemu",
                   "uname": "QNX qnxqemu 8.0.0 2025/01/01-00:00:00 x86_64"},
        "ir": {"machine_id": amr_ir["machine"]["id"],
               "ir_sha256": manifest["ir_sha256"]},
        "staged": staged,
        "transcripts": {n: "cd" * 32
                        for n in provenance.EXPECTED_TARGET_CHECKS},
    }
    samples = [200.0 + (i % 50) for i in range(1000)]
    perf = {
        "status": "ok", "verified_on_target": True,
        "provenance_version": 1,
        "started_utc": "2026-11-04T20:25:00+00:00",
        "finished_utc": "2026-11-04T20:26:00+00:00",
        "target": dict(target["target"]),
        "staged": {n: dict(v) for n, v in staged.items()},
        "method": {"probe": "genesis_faultinject bench"},
        "measurements": {"ipc_roundtrip_us": dict(
            provenance.perf_distribution(samples), unit="microseconds")},
        "raw_samples_us": samples,
    }
    return {"manifest": manifest, "build": build,
            "target": target, "perf": perf}
