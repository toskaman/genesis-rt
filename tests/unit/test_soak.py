# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 10 Sprint E3 (§19): bounded soak — repeated load, no residue.

One warmup job, then a mixed load (success / fail-fast / malformed)
through the real JobManager + pipeline. Afterwards the process must be
indistinguishable from post-warmup: same thread count, bounded memory
growth, bounded DB, no stray files. Thresholds are regression
tripwires with wide margins, not performance claims.
"""
import gc
import json
import threading
import tracemalloc

from genesis_rt.jobs import JobManager

# Regression tripwires (observed 2026-11-05, 25 jobs: +18 KiB Python
# heap, 1.1 MiB DB — passports are retained per job by design, hence
# the DB scales linearly in job count; see docs/audits/SOAK_WAVE10.md).
SOAK_JOBS = 24
MAX_MEM_GROWTH_B = 2 * 1024 * 1024
MAX_DB_BYTES = 5 * 1024 * 1024


def _write_ir(tmp_path, amr_ir):
    path = tmp_path / "soak-ir.json"
    path.write_text(json.dumps(amr_ir), encoding="utf-8")
    return path


def _db_bytes(db_path):
    total = 0
    for suffix in ("", "-wal", "-shm"):
        p = db_path.parent / (db_path.name + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def _settle(mgr, job_id):
    rec = mgr.wait(job_id, timeout=120)
    assert rec["state"] in ("succeeded", "failed", "cancelled"), rec
    return rec


def test_soak_mixed_load_leaves_no_residue(tmp_path, amr_ir):
    tracemalloc.start()
    try:
        mgr = JobManager(tmp_path / "runs.db", tmp_path / "artifacts")
        try:
            ir_path = _write_ir(tmp_path, amr_ir)
            bad_path = tmp_path / "no-such.json"
            garbage = tmp_path / "garbage.json"
            garbage.write_text("{not json", encoding="utf-8")
            # Warmup: pool threads spawn lazily — baseline after first job.
            warm = mgr.submit(ir_path, run_id="soak-warm")
            assert _settle(mgr, warm)["state"] == "succeeded"
            threads_before = threading.active_count()
            snap_before = tracemalloc.take_snapshot()
            # Mixed load: success, fail-fast (missing IR), malformed.
            kinds = ["ok", "missing", "garbage"]
            terminal = {"succeeded": 0, "failed": 0}
            for i in range(SOAK_JOBS):
                kind = kinds[i % 3]
                src = {"ok": ir_path, "missing": bad_path,
                       "garbage": garbage}[kind]
                jid = mgr.submit(src, run_id=f"soak-{i:02d}")
                rec = _settle(mgr, jid)
                if kind == "ok":
                    assert rec["state"] == "succeeded", rec
                else:
                    assert rec["state"] == "failed", rec  # never success
                terminal[rec["state"]] += 1
            assert terminal == {"succeeded": 8, "failed": 16}
            gc.collect()
            assert threading.active_count() == threads_before
            growth = sum(s.size_diff for s in
                         tracemalloc.take_snapshot().compare_to(
                             snap_before, "filename"))
            assert growth < MAX_MEM_GROWTH_B, growth
            assert _db_bytes(tmp_path / "runs.db") < MAX_DB_BYTES
            assert len(mgr._done) <= 200  # completion-event track cap
            leftovers = {p.name for p in tmp_path.iterdir()}
            assert leftovers <= {"runs.db", "runs.db-wal", "runs.db-shm",
                                 "artifacts", "soak-ir.json", "garbage.json",
                                 "no-such.json"}, leftovers
        finally:
            mgr.close()
    finally:
        tracemalloc.stop()


def test_soak_cancel_storm_settles_cleanly(tmp_path, amr_ir):
    mgr = JobManager(tmp_path / "runs.db", tmp_path / "artifacts",
                     max_workers=1)
    try:
        ir_path = _write_ir(tmp_path, amr_ir)
        gate = threading.Event()
        real_work = mgr._work
        mgr._work = lambda job_id, *a: gate.wait(timeout=30)
        try:
            ids = [mgr.submit(ir_path, run_id=f"cx-{i}") for i in range(4)]
            for jid in ids:
                rec = mgr.cancel(jid)
                assert rec["state"] in ("cancelled", "running", "queued"), rec
        finally:
            gate.set()
            mgr._work = real_work
        for jid in ids:
            rec = mgr.wait(jid, timeout=60)
            assert rec["state"] in ("cancelled", "succeeded"), rec
    finally:
        mgr.close()
