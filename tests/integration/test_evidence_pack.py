# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 10 F1: the committed native evidence pack verifies, tampering fails.

The pack under evidence/qnx8-x86_64-verified-*/ is real QNX campaign output.
Every CI run re-verifies it; negative tests prove the verifier rejects
modified, missing, extra, and cross-operation-substituted files.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Pinned to the published pack: a replacement pack must update this test.
PACK = REPO / "evidence" / "qnx8-x86_64-verified-b22cea1"


def _run_verify(pack_dir: Path) -> subprocess.CompletedProcess:
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "PYTHONHOME")}
    return subprocess.run(
        [sys.executable, str(pack_dir / "verify.py"), str(pack_dir)],
        capture_output=True, text=True, timeout=120, env=env)


def test_pack_verifies_clean():
    assert (PACK / "manifest.json").is_file()
    proc = _run_verify(PACK)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VERIFY OK" in proc.stdout
    assert "matrix=16/16" in proc.stdout


def test_pack_verifies_outside_checkout(tmp_path):
    """Stdlib fallback: the pack verifies with no repo import available."""
    clone = tmp_path / "pack"
    shutil.copytree(PACK, clone)
    proc = _run_verify(clone)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "stdlib mirror" in proc.stdout


def test_tampered_file_rejected(tmp_path):
    clone = tmp_path / "pack"
    shutil.copytree(PACK, clone)
    target = clone / "transcripts" / "target-faultinject.log"
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x01
    target.write_bytes(bytes(data))
    proc = _run_verify(clone)
    assert proc.returncode == 2, proc.stdout
    assert "digest mismatch" in proc.stdout


def test_missing_and_extra_file_rejected(tmp_path):
    clone = tmp_path / "pack"
    shutil.copytree(PACK, clone)
    (clone / "performance" / "target-perf.log").unlink()
    (clone / "evil.txt").write_text("smuggled", encoding="utf-8")
    proc = _run_verify(clone)
    assert proc.returncode == 2, proc.stdout
    assert "missing file" in proc.stdout
    assert "unlisted file" in proc.stdout


def test_cross_operation_substitution_rejected(tmp_path):
    """A re-digested manifest cannot hide a rebound op record: the
    passport (untouched, chain valid) no longer matches target-op.json,
    so only the binding check fires."""
    clone = tmp_path / "pack"
    shutil.copytree(PACK, clone)
    op_p = clone / "target-op.json"
    op = json.loads(op_p.read_text(encoding="utf-8"))
    op["op_id"] = "op-deadbeefcafe"
    op_p.write_text(json.dumps(op, indent=1), encoding="utf-8")
    manifest_p = clone / "manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["files"]["target-op.json"] = hashlib.sha256(
        op_p.read_bytes()).hexdigest()
    manifest_p.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    proc = _run_verify(clone)
    assert proc.returncode == 2, proc.stdout
    assert "binding: passport.run_id" in proc.stdout
    assert "hash mismatch" not in proc.stdout


def test_pack_bytes_are_checkout_stable():
    """Anti-rot: pack files are LF-only and git stores them verbatim.

    Regression: a CRLF pack verified locally but failed from a clean
    checkout after git's text conversion rewrote the bytes (29/34
    digests mismatched). The assembler canonicalizes to LF and
    .gitattributes pins evidence/** -text; this test pins both.
    """
    cr_files = [p.relative_to(PACK).as_posix() for p in sorted(PACK.rglob("*"))
                if p.is_file() and b"\r" in p.read_bytes()]
    assert cr_files == [], f"CRLF bytes would break digests: {cr_files}"
    attrs = (REPO / ".gitattributes").read_text(encoding="utf-8")
    assert "evidence/** -text" in attrs


W11A = REPO / "evidence" / "qnx8-x86_64-w11-before"
W11B = REPO / "evidence" / "qnx8-x86_64-w11-after"
W11CMP = REPO / "evidence" / "w11-before-after" / "comparison.json"


def test_wave11_packs_verify_clean():
    for pack in (W11A, W11B):
        assert (pack / "manifest.json").is_file()
        proc = _run_verify(pack)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "VERIFY OK" in proc.stdout
        assert "matrix=16/16" in proc.stdout


def test_wave11_comparison_manifest_matches_packs():
    cmp = json.loads(W11CMP.read_text(encoding="utf-8"))
    assert set(cmp["packs"]) == {"before", "after"}
    for tag, pack in (("before", W11A), ("after", W11B)):
        entry = cmp["packs"][tag]
        anchor = hashlib.sha256(
            (pack / "passport.json").read_bytes()).hexdigest()
        assert anchor == entry["passport_anchor"], tag
        assert entry["gate"] == "PASS", tag
        assert len(entry["matrix"]) == 16, tag
    b, a = cmp["packs"]["before"], cmp["packs"]["after"]
    assert b["ir_digest"] != a["ir_digest"]
    assert b["guard_sha256"] != a["guard_sha256"]
    assert (b["limit"], a["limit"]) == (1.2, 1.6)
    # The iconic flip, read from the packed transcripts (slot-1 sections).
    # NOTE: the marker also appears in the runner "$ command" framing
    # line, so the AMR-side section is parts[1] of 3.
    parts_a = (W11A / "transcripts" / "target-limits_differ.log").read_text(
        encoding="utf-8").split("---PROBE-CONV---")
    parts_b = (W11B / "transcripts" / "target-limits_differ.log").read_text(
        encoding="utf-8").split("---PROBE-CONV---")
    assert len(parts_a) == len(parts_b) == 3, "framing + 2 sections"
    assert ("PROBE linear=1.500 estop=0 decision=DENY reason=SPEED_OVER_LIMIT"
            in parts_a[1])
    assert ("PROBE linear=1.500 estop=0 decision=ALLOW reason=OK"
            in parts_b[1])


def test_wave11_packs_are_checkout_stable():
    for pack in (W11A, W11B):
        cr = [p.relative_to(pack).as_posix() for p in sorted(pack.rglob("*"))
              if p.is_file() and b"\r" in p.read_bytes()]
        assert cr == [], f"CRLF bytes would break digests: {cr}"
