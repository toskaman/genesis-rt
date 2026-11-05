# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Adversarial passport tests (§6): forged, recycled or truncated QNX
evidence must never earn an unjustified verification level.

Every case builds a real host-passing passport (AMR IR, full coverage)
and attacks ONLY the imported QNX records. Positive controls prove the
same pipeline still reaches the top tiers with properly bound records.
The `bound_evidence` fixture (tests/conftest.py) is the known-bound
baseline; each test mutates exactly one variable.
"""
import copy
import json

import pytest

from genesis_rt import evidence, faultlab, gate, provenance


@pytest.fixture()
def full(amr_ir):
    return list(amr_ir["verification"]["scenarios"])


def _passport(amr_ir, bound_evidence, full, tag, tgt=None, perf=None):
    results = faultlab.run_all(amr_ir, full)
    return evidence.build_passport(
        f"run-{tag}", amr_ir, bound_evidence["manifest"], results,
        bound_evidence["build"], tgt, qnx_perf=perf)


# --- positive controls: bound evidence earns the top tiers ---

def test_bound_target_evidence_reaches_behavior_verified(
        amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "ok",
                  bound_evidence["target"])
    v = gate.evaluate(p, full)
    assert (v["verdict"], v["level"], v["qnx_verified"],
            v["release_eligible"]) == ("PASS", "QNX_BEHAVIOR_VERIFIED",
                                       True, True)


def test_bound_perf_evidence_reaches_top_tier(amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "perf",
                  bound_evidence["target"], perf=bound_evidence["perf"])
    v = gate.evaluate(p, full)
    assert (v["verdict"], v["level"], v["release_eligible"]) == (
        "PASS", "QNX_PERFORMANCE_MEASURED", True)


# --- 1. forged QNX success: hand-written flags, no provenance ---

def test_forged_target_success_capped_at_executed(
        amr_ir, bound_evidence, full):
    tgt = {"status": "ok", "verified_on_target": True,
           "checks": [{"name": n, "passed": True, "detail": "trust me"}
                      for n in provenance.EXPECTED_TARGET_CHECKS]}
    p = _passport(amr_ir, bound_evidence, full, "forged", tgt)
    v = gate.evaluate(p, full)
    assert v["verdict"] == "PASS"  # host side is genuinely fine
    assert v["level"] == "QNX_EXECUTED"
    assert v["qnx_verified"] is False
    assert v["release_eligible"] is False
    assert any("provenance" in r for r in v["level_reasons"])


# --- 2. cross-machine reuse: conveyor record on an AMR passport ---

def test_cross_machine_record_refused(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    tgt["ir"]["machine_id"] = "conveyor-demo-01"
    p = _passport(amr_ir, bound_evidence, full, "xmach", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False
    assert any("machine" in r for r in v["level_reasons"])


# --- 3. cross-build reuse: staged binaries differ from this build ---

def test_cross_build_record_refused(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    tgt["staged"]["genesis_guard"]["cksum"] = 999999  # another build
    p = _passport(amr_ir, bound_evidence, full, "xbuild", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False
    assert any("genesis_guard" in r for r in v["level_reasons"])


# --- 4. stale IR: record bound to an older IR digest ---

def test_stale_ir_record_refused(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    tgt["ir"]["ir_sha256"] = "00" * 32
    p = _passport(amr_ir, bound_evidence, full, "stale", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False
    assert any("ir_sha256" in r for r in v["level_reasons"])


# --- 5. forged benchmark: measurements inconsistent with samples ---

def test_forged_perf_capped_below_top_tier(amr_ir, bound_evidence, full):
    perf = bound_evidence["perf"]
    perf["measurements"]["ipc_roundtrip_us"]["p50"] = 0.001  # too good
    p = _passport(amr_ir, bound_evidence, full, "fperf",
                  bound_evidence["target"], perf=perf)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"
    assert v["release_eligible"] is True  # behavior tier still earned
    assert any("p50" in r or "distribution" in r
               for r in v["level_reasons"])


def test_perf_without_samples_capped(amr_ir, bound_evidence, full):
    perf = bound_evidence["perf"]
    del perf["raw_samples_us"]
    p = _passport(amr_ir, bound_evidence, full, "nosamp",
                  bound_evidence["target"], perf=perf)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"


# --- 6. missing transcripts ---

def test_missing_transcript_digests_capped(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    del tgt["transcripts"]["v2_transitions"]
    p = _passport(amr_ir, bound_evidence, full, "notr", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert any("transcript" in r for r in v["level_reasons"])


# --- 7. modified binary: size drift on a staged binary ---

def test_modified_staged_binary_refused(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    tgt["staged"]["genesis_device"]["size"] += 1
    p = _passport(amr_ir, bound_evidence, full, "modbin", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert any("genesis_device" in r for r in v["level_reasons"])


# --- 8. incomplete check list: one name dropped, all passing ---

def test_incomplete_check_list_capped(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    dropped = tgt["checks"].pop()
    tgt["matrix"].remove(dropped["name"])
    assert dropped["name"] == "cell_policy"  # last of EXPECTED_TARGET_CHECKS
    p = _passport(amr_ir, bound_evidence, full, "short", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False
    assert any("cell_policy" in r for r in v["level_reasons"])


# --- 9. omitted scenarios: pinned (existing coverage rule) ---

def test_omitted_scenarios_still_block_release(amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "cov",
                  bound_evidence["target"])
    v = gate.evaluate(p, full[:-1])  # drop one declared scenario
    assert v["verdict"] == "PASS"
    assert v["release_eligible"] is False
    assert v["coverage"]["omitted"] == [full[-1]]


# --- 11. duplicate records: pinned (existing rule) ---

def test_duplicate_record_kinds_still_fail(amr_ir, bound_evidence, full):
    p = _passport(amr_ir, bound_evidence, full, "dup",
                  bound_evidence["target"])
    p["chain"].append(copy.deepcopy(
        next(r for r in p["chain"] if r["kind"] == "qnx_target")))
    v = gate.evaluate(p, full)
    assert v["verdict"] == "FAIL"
    assert any("duplicate" in r for r in v["reasons"])


# --- 12. malformed record via the real pipeline path ---

def test_malformed_target_record_fails_pipeline(amr_ir, tmp_path, full):
    from genesis_rt import orchestrator
    bad = tmp_path / "bad-target.json"
    bad.write_text(json.dumps({"no_status": True}), encoding="utf-8")
    irf = tmp_path / "ir.json"
    irf.write_text(json.dumps(amr_ir), encoding="utf-8")
    out = orchestrator.run_pipeline(irf, tmp_path / "art", run_id="advmal",
                                    scenarios=full, target_record=bad)
    assert out["verdict"] == "FAIL"
    assert out["failure"]["step"] == "qnx_target"


# --- 13. incoherent timestamps ---

@pytest.mark.parametrize("started,finished", [
    ("2026-11-04T20:20:00+00:00", "2026-11-04T20:10:00+00:00"),  # end < start
    ("not-a-time", "2026-11-04T20:20:00+00:00"),  # unparsable
    ("2026-11-04T20:10:00+00:00", "2099-01-01T00:00:00+00:00"),  # far future
])
def test_incoherent_timestamps_capped(amr_ir, bound_evidence, full,
                                      started, finished):
    tgt = bound_evidence["target"]
    tgt["started_utc"], tgt["finished_utc"] = started, finished
    p = _passport(amr_ir, bound_evidence, full, "ts", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False


def test_wrong_platform_refused(amr_ir, bound_evidence, full):
    tgt = bound_evidence["target"]
    tgt["target"]["platform"] = "linux_x86_64_host"
    p = _passport(amr_ir, bound_evidence, full, "plat", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert any("platform" in r for r in v["level_reasons"])


# --- 21. cross-target splice: matrix on X, bench on Y (round 2, A2) ---

def test_cross_target_perf_splice_capped(amr_ir, bound_evidence, full):
    """Red-team round 2, A2: a perf record from a different target
    instance than the matrix run must not earn the top tier, even
    when both records are individually well-formed and bound to the
    same build set."""
    perf = bound_evidence["perf"]
    perf["target"]["uname"] = \
        "QNX qnxqemu-OTHER 8.0.0 2025/01/01-00:00:00 x86_64"
    p = _passport(amr_ir, bound_evidence, full, "xtarget",
                  bound_evidence["target"], perf=perf)
    v = gate.evaluate(p, full)
    assert v["verdict"] == "PASS"  # host side is genuinely fine
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"
    assert any("target" in r for r in v["level_reasons"])


# --- 22. unknown provenance versions refused (round 2, A1) ---

def test_future_target_provenance_version_refused(amr_ir, bound_evidence,
                                                 full):
    """Red-team round 2, A1: a record stamped with an unknown future
    provenance_version must not earn behavior-level trust."""
    tgt = bound_evidence["target"]
    tgt["provenance_version"] = 99
    p = _passport(amr_ir, bound_evidence, full, "vfuture", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert any("provenance_version" in r for r in v["level_reasons"])


def test_future_perf_provenance_version_capped(amr_ir, bound_evidence,
                                              full):
    """Red-team round 2, A1: an unknown perf provenance_version caps
    the passport at the behavior tier."""
    perf = bound_evidence["perf"]
    perf["provenance_version"] = 99
    p = _passport(amr_ir, bound_evidence, full, "vpfuture",
                  bound_evidence["target"], perf=perf)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"
    assert any("provenance_version" in r for r in v["level_reasons"])


# --- 23. clock attacks, round 2 (A5) ---

def test_incoherent_perf_window_capped(amr_ir, bound_evidence, full):
    """Red-team round 2, A5: a perf record whose window ends before it
    starts caps the passport at the behavior tier."""
    perf = bound_evidence["perf"]
    perf["started_utc"] = "2026-11-04T20:26:00+00:00"
    perf["finished_utc"] = "2026-11-04T20:25:00+00:00"
    p = _passport(amr_ir, bound_evidence, full, "pclock",
                  bound_evidence["target"], perf=perf)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_BEHAVIOR_VERIFIED"
    assert any("window" in r for r in v["level_reasons"])


@pytest.mark.parametrize("started,finished", [
    ("2026-11-04T20:10:00", "2026-11-04T20:20:00+00:00"),  # naive start
    ("2026-11-04T20:10:00+00:00", "2026-11-04T20:10:00+00:00"),  # zero run
])
def test_ambiguous_target_window_refused(amr_ir, bound_evidence, full,
                                         started, finished):
    """Red-team round 2, A5: timezone-less or zero-duration target
    windows earn no behavior-level trust."""
    tgt = bound_evidence["target"]
    tgt["started_utc"], tgt["finished_utc"] = started, finished
    p = _passport(amr_ir, bound_evidence, full, "tclock", tgt)
    v = gate.evaluate(p, full)
    assert v["level"] == "QNX_EXECUTED"
    assert v["release_eligible"] is False
