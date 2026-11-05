# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: Twin 2.0 replay-track model, fidelity, CLI."""
import copy
import json

import pytest

from genesis_rt import evidence, faultlab, gate, twin
from genesis_rt.twin import (TwinChainError, TwinInputError, TwinTooLarge,
                             check_fidelity, describe_source, detect_kind,
                             fold_trace, frame_at, render_track_text,
                             track_from_passport, verify_track)


def _passport(ir, bound_evidence, scenarios, tag):
    results = faultlab.run_all(ir, scenarios)
    p = evidence.build_passport(f"run-{tag}", ir,
                                bound_evidence["manifest"], results,
                                bound_evidence["build"], None)
    return evidence.attach_verdict(p, gate.evaluate(p, scenarios)), results


def test_fold_diff_trace_restates_ticks(amr_ir):
    res = faultlab.run_scenario(amr_ir, "corrupted_message")
    track = fold_trace(res["trace"])
    ticks = [e for e in res["trace"] if e["kind"] == "tick"]
    assert track["kind"] == "diff"
    assert track["source"] == "host-sim"
    assert track["interp"] == "stepwise-hold"
    assert len(track["frames"]) == len(ticks)
    assert track["frames"][0]["motion"] == {
        "x": ticks[0]["x"], "y": ticks[0]["y"], "theta": ticks[0]["theta"]}
    assert check_fidelity(track, res["trace"]) == []


def test_fold_belt_and_cell_kinds(amr_ir, cell_ir, repo_root):
    conv = json.loads((repo_root / "examples" / "conveyor-demo"
                       / "machine-ir.json").read_text(encoding="utf-8"))
    from genesis_rt.ir import validate_ir
    conv = validate_ir(conv)
    belt = fold_trace(faultlab.run_scenario(conv, "belt_jam")["trace"])
    assert belt["kind"] == "belt"
    assert set(belt["frames"][0]["motion"]) == {
        "position", "speed", "jammed"}
    cell = fold_trace(faultlab.run_scenario(
        cell_ir, "cell_estop_during_transfer")["trace"])
    assert cell["kind"] == "cell"
    assert cell["frames"][0]["leg"] in ("amr", "belt")
    assert "cell_phase" in cell["frames"][0]["motion"]


def test_detect_kind_prefers_cell_over_belt():
    assert detect_kind([{"t": 0, "cell_phase": "X", "position": 1.0}]) == "cell"
    assert detect_kind([{"t": 0, "position": 1.0}]) == "belt"
    assert detect_kind([{"t": 0, "x": 1.0}]) == "diff"
    assert detect_kind([]) == "diff"


def test_markers_cover_fault_deny_state_and_phase(amr_ir, cell_ir):
    track = fold_trace(faultlab.run_scenario(
        amr_ir, "corrupted_message")["trace"])
    labels = [m["label"] for m in track["markers"]]
    assert "fault corrupted started" in labels
    assert "fault cleared" in labels
    assert any(l.startswith("guard DENY:") for l in labels)
    assert any("guard state" in l for l in labels)
    assert any(m["severity"] == "fail" for m in track["markers"])
    cell = fold_trace(faultlab.run_scenario(
        cell_ir, "cell_estop_during_transfer")["trace"])
    assert any(m["label"].startswith("phase ->")
               for m in cell["markers"])


def test_slim_trace_marks_gap_without_bridging(amr_ir, bound_evidence):
    passport, _results = _passport(amr_ir, bound_evidence,
                                   ["corrupted_message"], "slim")
    body = [r["body"] for r in passport["chain"]
            if r["kind"] == "scenario:corrupted_message"][0]
    assert body["trace"]["truncated"] is True
    track = fold_trace(body["trace"])
    assert track["truncated"] is True
    assert track["gap_at"] == 20
    assert track["frames"][19]["gap_after"] is True
    assert track["frames"][20]["gap_after"] is False
    assert any(m["label"].startswith("trace gap")
               for m in track["markers"])
    assert check_fidelity(track, body["trace"]) == []


def test_frame_at_is_stepwise_hold(amr_ir):
    track = fold_trace(faultlab.run_scenario(
        amr_ir, "corrupted_message")["trace"])
    first, last = track["frames"][0], track["frames"][-1]
    assert frame_at(track, first["t_ms"] - 1) == 0
    assert frame_at(track, first["t_ms"]) == 0
    mid = track["frames"][10]["t_ms"]
    assert frame_at(track, mid + 1) == 10
    assert frame_at(track, last["t_ms"] + 10**9) == len(track["frames"]) - 1
    with pytest.raises(TwinInputError):
        frame_at({"frames": []}, 0)


def test_fidelity_catches_fold_defects(amr_ir):
    res = faultlab.run_scenario(amr_ir, "nominal_navigation")
    good = fold_trace(res["trace"])
    assert check_fidelity(good, res["trace"]) == []
    dropped = copy.deepcopy(good)
    dropped["frames"].pop()
    assert any("count" in e for e in check_fidelity(dropped, res["trace"]))
    shuffled = copy.deepcopy(good)
    shuffled["frames"][0]["t_ms"], shuffled["frames"][1]["t_ms"] = \
        shuffled["frames"][1]["t_ms"], shuffled["frames"][0]["t_ms"]
    assert check_fidelity(shuffled, res["trace"]) != []
    bad_marker = copy.deepcopy(good)
    bad_marker["markers"].append({"i": 10**6, "t_ms": 0, "label": "x",
                                  "severity": "info"})
    assert any("out of range" in e
               for e in check_fidelity(bad_marker, res["trace"]))
    bad_interp = copy.deepcopy(good)
    bad_interp["interp"] = "linear"
    assert any("stepwise" in e
               for e in check_fidelity(bad_interp, res["trace"]))
    assert any("unreadable" in e for e in check_fidelity(good, {"nope": 1}))


def test_verify_track_shape():
    track = fold_trace([{"t": 0, "kind": "tick", "fault": "none",
                         "decision": "ALLOW", "reason": "ok",
                         "state": 1, "x": 0.0, "y": 0.0, "theta": 0.0}])
    assert verify_track(track) == []
    assert verify_track(track_from_json(track)) == []
    assert verify_track([]) == ["track must be an object"]
    bad = copy.deepcopy(track)
    bad["version"] = 99
    assert any("version" in e for e in verify_track(bad))
    bad = copy.deepcopy(track)
    bad["kind"] = "spaceship"
    assert any("kind" in e for e in verify_track(bad))
    bad = copy.deepcopy(track)
    bad["source"] = "mars"
    assert any("source" in e for e in verify_track(bad))
    bad = copy.deepcopy(track)
    bad["frames"][0]["i"] = 7
    assert any("index" in e for e in verify_track(bad))


def track_from_json(track):
    return json.loads(json.dumps(track))


def test_fold_rejects_bad_input():
    with pytest.raises(TwinInputError):
        fold_trace([{"t": 0, "kind": "tick"}], source="qnx-live")
    with pytest.raises(TwinInputError):
        fold_trace([{"kind": "tick"}])
    with pytest.raises(TwinInputError):
        fold_trace({"events_head": {}})
    with pytest.raises(TwinInputError):
        fold_trace(42)
    big = [{"t": i, "kind": "tick", "x": 0.0, "y": 0.0, "theta": 0.0}
           for i in range(twin.MAX_FRAMES + 1)]
    with pytest.raises(TwinTooLarge):
        fold_trace(big)


def test_track_from_passport_happy_and_unknown(amr_ir, bound_evidence):
    passport, _results = _passport(amr_ir, bound_evidence,
                                   ["corrupted_message"], "tw")
    track = track_from_passport(passport, "corrupted_message")
    assert track["scenario"] == "corrupted_message"
    assert track["run_id"] == "run-tw"
    assert track["run"]["run_source"] == "host-only"
    assert track["checks"] and track["stats"]
    with pytest.raises(TwinInputError) as exc:
        track_from_passport(passport, "nope")
    assert "corrupted_message" in str(exc.value)


def test_track_from_passport_refuses_tamper(amr_ir, bound_evidence):
    passport, _results = _passport(amr_ir, bound_evidence,
                                   ["nominal_navigation"], "tw2")
    passport["chain"][-1]["body"]["scenarios_passed"] = 99
    with pytest.raises(TwinChainError):
        track_from_passport(passport, "nominal_navigation")


def test_describe_source_labels_qnx_bound_honestly():
    bound = {"chain": [{"kind": "gate_verdict",
                        "body": {"verdict": "PASS", "qnx_verified": True}}]}
    desc = describe_source(bound)
    assert desc["run_source"] == "qnx-bound"
    assert desc["track_source"] == "host-sim"
    assert "host-simulation" in desc["note"]
    assert describe_source({"chain": []})["run_source"] == "host-only"


def test_render_track_text(amr_ir, bound_evidence):
    passport, _results = _passport(amr_ir, bound_evidence,
                                   ["corrupted_message"], "txt")
    text = render_track_text(track_from_passport(passport,
                                                 "corrupted_message"))
    assert "corrupted_message" in text
    assert "stepwise hold" in text
    # Slim passports keep head+tail only: the mid-trace DENY is in the
    # gap, and the render says so instead of inventing it.
    assert "trace gap" in text
    res = faultlab.run_scenario(amr_ir, "corrupted_message")
    full = dict(fold_trace(res["trace"]), scenario="corrupted_message")
    assert "guard DENY" in render_track_text(full)


def test_cli_twin_frames(amr_ir, bound_evidence, tmp_path, capsys):
    from genesis_rt.cli import main
    passport, _results = _passport(amr_ir, bound_evidence,
                                   ["corrupted_message"], "cli")
    path = tmp_path / "passport.json"
    path.write_text(json.dumps(passport), encoding="utf-8")
    assert main(["twin", str(path), "--scenario",
                 "corrupted_message"]) == 0
    assert "corrupted_message" in capsys.readouterr().out
    out = tmp_path / "track.json"
    assert main(["twin", str(path), "--scenario", "corrupted_message",
                 "--json", "--out", str(out)]) == 0
    assert verify_track(json.loads(out.read_text(encoding="utf-8"))) == []
    assert main(["twin", str(path), "--scenario", "missing"]) == 2
