# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: standalone passport verifier (scripts/replay.py).

Covers §6 case 10 honestly: a tampered passport whose hash chain was
recomputed still verifies as "chain: valid" (the documented limit of a
chain without a trust anchor), but fails against a published --anchor.
"""
import hashlib
import json
import subprocess
import sys

from genesis_rt import evidence, faultlab
from genesis_rt.ir import canonical_json


def _recompute_chain(records):
    """Rebuild seq/prev_hash/hash over (possibly tampered) record bodies.

    Mirrors the chain rule documented in evidence.py:
    hash = sha256(canonical(body) + prev_hash), 0-based seq.
    """
    prev = evidence.GENESIS_PREV
    out = []
    for i, rec in enumerate(records):
        body = rec["body"]
        h = hashlib.sha256(
            (canonical_json(body) + prev).encode("utf-8")).hexdigest()
        out.append({"seq": i, "kind": rec["kind"], "body": body,
                    "prev_hash": prev, "hash": h})
        prev = h
    return out


def _save(tmp_path, passport, name="passport.json"):
    path = tmp_path / name
    path.write_text(json.dumps(passport, indent=2), encoding="utf-8")
    return path


def _passport(amr_ir, bound_evidence, tag):
    full = list(amr_ir["verification"]["scenarios"])
    return evidence.build_passport(
        f"run-{tag}", amr_ir, bound_evidence["manifest"],
        faultlab.run_all(amr_ir, full),
        bound_evidence["build"], bound_evidence["target"]), full


def _replay(repo_root, *args):
    return subprocess.run(
        [sys.executable, "scripts/replay.py", *args],
        capture_output=True, text=True, timeout=120, cwd=str(repo_root))


def test_replay_accepts_bound_passport(amr_ir, bound_evidence, tmp_path,
                                       repo_root):
    p, full = _passport(amr_ir, bound_evidence, "replay-ok")
    path = _save(tmp_path, p)
    proc = _replay(repo_root, str(path), "--required", *full)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "chain: valid" in proc.stdout
    assert "gate: PASS" in proc.stdout
    assert "provenance: ir=" in proc.stdout


def test_replay_detects_tamper_without_recompute(amr_ir, bound_evidence,
                                                 tmp_path, repo_root):
    p, full = _passport(amr_ir, bound_evidence, "replay-tamper")
    scen = next(r for r in p["chain"] if r["kind"].startswith("scenario:"))
    scen["body"]["forged_note"] = "evil"  # mutate after sealing
    path = _save(tmp_path, p)
    proc = _replay(repo_root, str(path), "--required", *full)
    assert proc.returncode == 1
    assert "chain: INVALID" in proc.stdout


def test_replay_anchor_detects_recomputed_chain(amr_ir, bound_evidence,
                                                tmp_path, repo_root):
    # §6 case 10: recompute the chain after falsification.
    p, full = _passport(amr_ir, bound_evidence, "replay-rehash")
    head_before = p["chain"][-1]["hash"]
    scen = next(r for r in p["chain"] if r["kind"].startswith("scenario:"))
    scen["body"]["forged_note"] = "evil"
    p["chain"] = _recompute_chain(p["chain"])
    assert p["chain"][-1]["hash"] != head_before
    assert evidence.verify_chain(p) == []  # documented limit: chain re-valid
    path = _save(tmp_path, p)
    # Without an anchor, the forgery is undetectable — by design limit.
    proc = _replay(repo_root, str(path), "--required", *full)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Against the published anchor, it fails loudly.
    proc = _replay(repo_root, str(path), "--required", *full,
                   "--anchor", head_before)
    assert proc.returncode == 1
    assert "anchor: MISMATCH" in proc.stdout
    # And the new head anchors the new content fine.
    proc = _replay(repo_root, str(path), "--required", *full,
                   "--anchor", p["chain"][-1]["hash"])
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_replay_transcripts_dir_detects_modified_log(
        amr_ir, bound_evidence, tmp_path, repo_root):
    p, full = _passport(amr_ir, bound_evidence, "replay-tr")
    logs = tmp_path / "logs"
    logs.mkdir()
    tgt = next(r for r in p["chain"] if r["kind"] == "qnx_target")
    for step in sorted(tgt["body"]["transcripts"]):
        blob = f"transcript for {step}\n".encode()
        (logs / f"target-{step}.log").write_bytes(blob)
        tgt["body"]["transcripts"][step] = hashlib.sha256(blob).hexdigest()
    p["chain"] = _recompute_chain(p["chain"])
    path = _save(tmp_path, p)
    proc = _replay(repo_root, str(path), "--required", *full,
                   "--transcripts-dir", str(logs))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "12/12 match" in proc.stdout
    (logs / "target-faultinject.log").write_bytes(b"doctored\n")
    proc = _replay(repo_root, str(path), "--required", *full,
                   "--transcripts-dir", str(logs))
    assert proc.returncode == 1
    assert "transcript MODIFIED: target-faultinject.log" in proc.stdout
