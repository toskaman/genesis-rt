# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Orchestrator: validate -> codegen -> build -> verify -> evidence -> gate.

Single-entry pipeline used by the CLI, API and demo script. Every step
records a structured outcome; QNX steps without an SDK are recorded as
"blocked" and never as passed.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from . import build_adapter, codegen, evidence, faultlab, gate
from .ir import load_ir_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_SRC = REPO_ROOT / "target" / "qnx8"


def run_pipeline(ir_path: str | Path, artifacts_dir: str | Path,
                 run_id: str | None = None,
                 scenarios: list[str] | None = None) -> dict[str, Any]:
    t0 = time.monotonic()
    run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    adir = Path(artifacts_dir)
    run_dir = adir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    steps: dict[str, Any] = {}

    ir = load_ir_file(ir_path)
    steps["validate"] = {"status": "ok", "machine": ir["machine"]["id"]}

    gen_dir = run_dir / "generated"
    manifest = codegen.generate(ir, gen_dir, genesis_src=str(TARGET_SRC))
    steps["codegen"] = {"status": "ok", "manifest": manifest}

    steps["host_cc_check"] = build_adapter.check_host_cc(gen_dir, TARGET_SRC)

    qnx_record = build_adapter.build_qnx(gen_dir)
    steps["qnx_build"] = {k: v for k, v in qnx_record.items() if k != "environment"}
    steps["qnx_build"]["environment_sdk_present"] = bool(
        qnx_record.get("environment", {}).get("sdk_present", False))

    wanted = scenarios or list(ir["verification"]["scenarios"])
    results = faultlab.run_all(ir, wanted)
    steps["verification"] = {
        "status": "ok",
        "scenarios": {r["scenario"]: r["status"] for r in results},
    }

    passport = evidence.build_passport(run_id, ir, manifest, results, qnx_record)
    verdict = gate.evaluate(passport, wanted)
    evidence.attach_verdict(passport, verdict)
    ppath = evidence.save_passport(passport, run_dir / "passport.json")
    steps["gate"] = verdict

    return {"run_id": run_id, "run_dir": str(run_dir),
            "passport": str(ppath), "verdict": verdict["verdict"],
            "qnx_verified": verdict["qnx_verified"], "steps": steps,
            "elapsed_s": round(time.monotonic() - t0, 2)}
