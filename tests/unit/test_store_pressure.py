# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §14: unusable artifact store fails honestly, never wedges.

A contained stand-in for disk pressure (no destructive fill of real
volumes): when the artifact root cannot take a run directory, the job
goes failed with the cause attached, the API stays up, and a healthy
manager keeps serving.
"""
from __future__ import annotations

import json

from genesis_rt.jobs import JobManager


def test_artifacts_path_is_file_fails_honestly(tmp_path, amr_ir):
    blocker = tmp_path / "artifacts"
    blocker.write_text("not a directory", encoding="utf-8")
    mgr = JobManager(tmp_path / "runs.db", blocker)
    try:
        ir_path = tmp_path / "ir.json"
        ir_path.write_text(json.dumps(amr_ir), encoding="utf-8")
        job_id = mgr.submit(ir_path, scenarios=["nominal_navigation"])
        rec = mgr.wait(job_id, timeout=120)
        assert rec["state"] == "failed", rec
        assert rec["error"], "cause must be attached, not swallowed"
    finally:
        mgr.close()


def test_manager_usable_after_store_failure(tmp_path, amr_ir):
    blocker = tmp_path / "artifacts"
    blocker.write_text("not a directory", encoding="utf-8")
    bad = JobManager(tmp_path / "bad.db", blocker)
    try:
        ir_path = tmp_path / "ir.json"
        ir_path.write_text(json.dumps(amr_ir), encoding="utf-8")
        job_id = bad.submit(ir_path, scenarios=["nominal_navigation"])
        assert bad.wait(job_id, timeout=120)["state"] == "failed"
    finally:
        bad.close()
    good = JobManager(tmp_path / "good.db", tmp_path / "good-artifacts")
    try:
        job_id = good.submit(ir_path, scenarios=["nominal_navigation"])
        rec = good.wait(job_id, timeout=120)
        assert rec["state"] == "succeeded", rec
        assert rec["verdict"] == "PASS"
    finally:
        good.close()
