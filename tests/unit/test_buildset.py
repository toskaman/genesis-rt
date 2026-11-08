# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Multi-build provenance (§6, provenance v2): every staged executable of a
verification campaign must be attributable to exactly one build.

Each test mutates ONE variable of the known-bound fixture and asserts the
gate refuses the behavior tier with the specific reason."""
import copy

import pytest

from genesis_rt import buildset, codegen, provenance
from genesis_rt.evidence import build_passport
from genesis_rt.gate import _level, evaluate


def _reasons(ev, amr_ir):
    ir_body = {"ir_sha256": ev["manifest"]["ir_sha256"], "machine": amr_ir["machine"]}
    return provenance.validate_target_binding(
        ir_body=ir_body, build_body=ev["build"], target_body=ev["target"])


def _entries(ev):
    return ev["target"]["build_set"]["entries"]


def test_bound_fixture_has_no_reasons(bound_evidence, amr_ir):
    assert _reasons(bound_evidence, amr_ir) == []


def test_wrong_machine_guard_rejected(bound_evidence, amr_ir):
    e = _entries(bound_evidence)["genesis_guard_conv"]
    e["machine_kind"] = "differential_drive_robot"  # an AMR guard staged as conveyor
    r = _reasons(bound_evidence, amr_ir)
    assert any("genesis_guard_conv: wrong origin: machine_kind" in x for x in r)


def test_wrong_ir_version_rejected(bound_evidence, amr_ir):
    _entries(bound_evidence)["genesis_guard_v2"]["schema_version"] = 1
    r = _reasons(bound_evidence, amr_ir)
    assert any("genesis_guard_v2: wrong origin: schema_version=1" in x for x in r)


def test_old_binary_from_another_build_rejected(bound_evidence, amr_ir):
    # same name on target, bytes of an older build
    bound_evidence["target"]["staged"]["genesis_guard_conv"]["cksum"] = 1
    r = _reasons(bound_evidence, amr_ir)
    assert any("genesis_guard_conv: staged bytes differ from its registered build" in x
               for x in r)


def test_correct_filename_wrong_contents_rejected(bound_evidence, amr_ir):
    bound_evidence["target"]["staged"]["genesis_guard_v2"]["size"] += 8
    assert any("genesis_guard_v2: staged bytes differ" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_missing_secondary_binary_rejected(bound_evidence, amr_ir):
    del _entries(bound_evidence)["genesis_guard_v2"]
    del bound_evidence["target"]["staged"]["genesis_guard_v2"]
    r = _reasons(bound_evidence, amr_ir)
    assert any("genesis_guard_v2: required by matrix steps ['v2_transitions']" in x
               for x in r)


def test_registered_but_not_staged_rejected(bound_evidence, amr_ir):
    del bound_evidence["target"]["staged"]["genesis_guard_v2"]
    assert any("genesis_guard_v2: registered in the build set but not staged" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_modified_secondary_guard_rejected(bound_evidence, amr_ir):
    _entries(bound_evidence)["genesis_guard_conv"]["cksum"] = 4243  # entry edited
    assert any("genesis_guard_conv: staged bytes differ" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_reused_provenance_across_irs_rejected(bound_evidence, amr_ir):
    ents = _entries(bound_evidence)
    ents["genesis_guard_v2"]["build_id"] = ents["genesis_guard_conv"]["build_id"]
    assert any("already describes another IR (reused provenance)" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_entry_claiming_primary_build_rejected(bound_evidence, amr_ir):
    ev = bound_evidence
    primary = buildset.build_id(ev["build"], ev["manifest"]["ir_sha256"])
    _entries(ev)["genesis_guard_conv"]["build_id"] = primary
    assert any("reuses the primary build id" in x for x in _reasons(ev, amr_ir))


def test_secondary_built_from_primary_ir_rejected(bound_evidence, amr_ir):
    _entries(bound_evidence)["genesis_guard_conv"]["ir_sha256"] = \
        bound_evidence["manifest"]["ir_sha256"]
    assert any("built from the primary IR" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_unregistered_executable_rejected(bound_evidence, amr_ir):
    bound_evidence["target"]["staged"]["genesis_mystery"] = {"cksum": 7, "size": 7}
    assert any("genesis_mystery: staged on target but registered in no build" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_ambiguous_attribution_rejected(bound_evidence, amr_ir):
    e = copy.deepcopy(_entries(bound_evidence)["genesis_guard_conv"])
    e["staged_name"] = "genesis_device"
    _entries(bound_evidence)["genesis_device"] = e
    assert any("genesis_device: claimed by the primary build AND the build set" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_inconsistent_manifest_entry_name_rejected(bound_evidence, amr_ir):
    _entries(bound_evidence)["genesis_guard_conv"]["staged_name"] = "genesis_guard_v2"
    assert any("entry declares staged_name" in x for x in _reasons(bound_evidence, amr_ir))


@pytest.mark.parametrize("field", ["ir_sha256", "build_id", "sha256", "source_passport_head"])
def test_malformed_digest_rejected(bound_evidence, amr_ir, field):
    _entries(bound_evidence)["genesis_guard_conv"][field] = "not-a-digest"
    assert any(f"{field} is not a sha256 hex digest" in x
               for x in _reasons(bound_evidence, amr_ir))


def test_missing_build_set_rejected(bound_evidence, amr_ir):
    del bound_evidence["target"]["build_set"]
    assert any("build set missing" in x for x in _reasons(bound_evidence, amr_ir))


def test_perf_with_different_build_set_capped(bound_evidence, amr_ir):
    ev = bound_evidence
    ev["perf"]["build_set"]["entries"]["genesis_guard_conv"]["source_run_id"] = "run-other"
    r = provenance.validate_perf_binding(build_body=ev["build"], target_body=ev["target"],
                                         perf_body=ev["perf"])
    assert any("perf build set differs" in x for x in r)


def test_legacy_v1_with_extras_capped_never_upgraded(bound_evidence, amr_ir):
    ev = bound_evidence
    ev["target"]["provenance_version"] = 1
    del ev["target"]["build_set"]
    r = _reasons(ev, amr_ir)
    assert any("provenance v1 record stages 2 executable(s) from other builds" in x
               for x in r)
    level, _ = _level(True, {
        "ir": {"body": {"ir_sha256": ev["manifest"]["ir_sha256"],
                        "machine": amr_ir["machine"]}},
        "qnx_build": {"body": ev["build"]}, "qnx_target": {"body": ev["target"]}})
    assert level == "QNX_EXECUTED"


def test_legacy_v1_single_build_still_bound(bound_evidence, amr_ir):
    ev = bound_evidence
    ev["target"]["provenance_version"] = 1
    del ev["target"]["build_set"]
    for n in ("genesis_guard_conv", "genesis_guard_v2"):
        del ev["target"]["staged"][n]
    assert _reasons(ev, amr_ir) == []


def _source_passport(ir, tmp_path, build_status="ok"):
    manifest = codegen.generate(ir, tmp_path / "src-gen")
    build = {"status": build_status, "built_utc": "2026-11-04T19:50:00+00:00",
             "environment": {"qcc_version": "cc: 12.2.0,gcc_ntox86_64"},
             "binaries": {"genesis_guard": {"sha256": "e1" * 32, "cksum": 4242,
                                            "size": 14360}}}
    return build_passport("run-src000000001", ir, manifest, [], qnx_build=build)


def test_entry_from_real_passport_binds_origin(amr_ir, tmp_path):
    p = _source_passport(amr_ir, tmp_path)
    e = buildset.entry_from_passport(p, source_binary="genesis_guard",
                                     staged_name="genesis_guard_x")
    assert e["machine_id"] == amr_ir["machine"]["id"]
    assert e["machine_kind"] == amr_ir["machine"]["kind"]
    assert e["cksum"] == 4242 and e["size"] == 14360
    assert e["source_passport_head"] == p["chain"][-1]["hash"]
    assert len(e["build_id"]) == 64
    bs = buildset.make_build_set([e])
    assert bs["entries"]["genesis_guard_x"] is e


def test_entry_refuses_tampered_source_passport(amr_ir, tmp_path):
    p = _source_passport(amr_ir, tmp_path)
    p["chain"][2]["body"]["binaries"]["genesis_guard"]["cksum"] = 1
    with pytest.raises(ValueError, match="chain invalid"):
        buildset.entry_from_passport(p, source_binary="genesis_guard",
                                     staged_name="genesis_guard_x")


def test_entry_refuses_blocked_build(amr_ir, tmp_path):
    p = _source_passport(amr_ir, tmp_path, build_status="blocked")
    with pytest.raises(ValueError, match="need 'ok'"):
        buildset.entry_from_passport(p, source_binary="genesis_guard",
                                     staged_name="genesis_guard_x")


def test_entry_refuses_unknown_binary(amr_ir, tmp_path):
    p = _source_passport(amr_ir, tmp_path)
    with pytest.raises(ValueError, match="not among"):
        buildset.entry_from_passport(p, source_binary="genesis_nope",
                                     staged_name="genesis_guard_x")


def test_duplicate_staged_name_refused(amr_ir, tmp_path):
    p = _source_passport(amr_ir, tmp_path)
    e = buildset.entry_from_passport(p, source_binary="genesis_guard",
                                     staged_name="genesis_guard_x")
    with pytest.raises(ValueError, match="duplicate"):
        buildset.make_build_set([e, dict(e)])


def test_gate_end_to_end_v2_reaches_top_tier_and_tamper_caps(bound_evidence, amr_ir):
    ev = bound_evidence
    by_kind = {"ir": {"body": {"ir_sha256": ev["manifest"]["ir_sha256"],
                               "machine": amr_ir["machine"]}},
               "qnx_build": {"body": ev["build"]}, "qnx_target": {"body": ev["target"]},
               "qnx_perf": {"body": ev["perf"]}}
    assert _level(True, by_kind)[0] == "QNX_PERFORMANCE_MEASURED"
    ev["target"]["build_set"]["entries"]["genesis_guard_conv"]["machine_kind"] = "amr"
    level, reasons = _level(True, by_kind)
    assert level == "QNX_EXECUTED"
    assert any("wrong origin" in r for r in reasons)
    assert callable(evaluate)


def _run(script, *argv):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    return subprocess.run([sys.executable, str(root / "scripts" / script), *argv],
                          capture_output=True, text=True, timeout=120)


def test_build_set_script_and_replay_roundtrip(amr_ir, tmp_path):
    import json

    from genesis_rt.evidence import save_passport
    src = _source_passport(amr_ir, tmp_path)
    src_path = save_passport(src, tmp_path / "src.json")
    out = tmp_path / "bs.json"
    r = _run("build_set.py", "create", "-o", str(out),
             "--entry", f"genesis_guard_x=genesis_guard:{src_path}")
    assert r.returncode == 0, r.stdout + r.stderr
    bs = json.loads(out.read_text())
    assert bs["entries"]["genesis_guard_x"]["source_run_id"] == "run-src000000001"
    # a campaign passport carrying this build set in its qnx_target record
    manifest = codegen.generate(amr_ir, tmp_path / "camp-gen")
    camp = build_passport("run-camp00000001", amr_ir, manifest, [],
                          qnx_target={"status": "ok", "build_set": bs})
    camp_path = save_passport(camp, tmp_path / "camp.json")
    ok = _run("replay.py", str(camp_path), "--source-passport", str(src_path),
              "--require-build-set-replay")
    assert "build-set: 1/1 entries replayed" in ok.stdout, ok.stdout
    # tamper the recorded entry -> replay names the field
    bs["entries"]["genesis_guard_x"]["machine_kind"] = "conveyor"
    camp2 = build_passport("run-camp00000002", amr_ir, manifest, [],
                           qnx_target={"status": "ok", "build_set": bs})
    bad = _run("replay.py", str(save_passport(camp2, tmp_path / "camp2.json")),
               "--source-passport", str(src_path), "--require-build-set-replay")
    assert bad.returncode == 1
    assert "differs from its source passport on ['machine_kind']" in bad.stdout
    missing = _run("replay.py", str(camp_path), "--require-build-set-replay")
    assert "not supplied (not replayed)" in missing.stdout and missing.returncode == 1


def test_build_set_script_refuses_bad_spec(tmp_path):
    r = _run("build_set.py", "create", "-o", str(tmp_path / "x.json"),
             "--entry", "nonsense")
    assert r.returncode != 0


def _alias_v2_to_primary(ev):
    prim = ev["build"]["binaries"]["genesis_guard"]
    e = _entries(ev)["genesis_guard_v2"]
    e["ir_sha256"] = ev["manifest"]["ir_sha256"]
    e["sha256"] = prim["sha256"]
    e["cksum"] = prim["cksum"]
    e["size"] = prim["size"]
    ev["target"]["staged"]["genesis_guard_v2"] = {
        "cksum": prim["cksum"], "size": prim["size"]}


def test_primary_build_alias_allowed(bound_evidence, amr_ir):
    # v2 ops stage the v2 guard twice (slot-1 + genesis_guard_v2):
    # same IR, byte-identical to the primary binary. That is an
    # alias, not attribution fraud, so no refusal is earned.
    _alias_v2_to_primary(bound_evidence)
    r = _reasons(bound_evidence, amr_ir)
    assert not any("built from the primary IR" in x for x in r)
    assert r == []


def test_same_ir_different_bytes_still_rejected(bound_evidence, amr_ir):
    # The fraud shape the rule exists for: primary IR claimed for
    # foreign bytes. The alias exception must not swallow it.
    _alias_v2_to_primary(bound_evidence)
    e = _entries(bound_evidence)["genesis_guard_v2"]
    e["sha256"] = "ff" * 32
    e["cksum"] = 424242
    bound_evidence["target"]["staged"]["genesis_guard_v2"] = {
        "cksum": 424242, "size": e["size"]}
    r = _reasons(bound_evidence, amr_ir)
    assert any("built from the primary IR" in x for x in r)
