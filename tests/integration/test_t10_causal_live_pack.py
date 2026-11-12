# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""T10: the committed live causal dossier verifies offline, fail-closed."""
import json
import shutil
import subprocess
import sys

import pytest

DOSSIER = "evidence/t10-causal-live-dossier"
PACK = "evidence/qnx8-x86_64-t10-cell-causal-live"


def _run(repo_root, ddir, pack):
    script = repo_root / DOSSIER / "verify_causal.py"
    return subprocess.run([sys.executable, str(script), str(ddir), str(pack)],
                          capture_output=True, text=True, timeout=120)


@pytest.fixture()
def copies(repo_root, tmp_path):
    d = tmp_path / "dossier"
    p = tmp_path / "pack"
    shutil.copytree(repo_root / DOSSIER, d)
    shutil.copytree(repo_root / PACK, p)
    return d, p


def test_committed_dossier_verifies(repo_root):
    r = _run(repo_root, repo_root / DOSSIER, repo_root / PACK)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VERIFY OK" in r.stdout
    assert "winner: H-estop" in r.stdout


def test_dossier_is_live_and_bound_to_pack(repo_root):
    doc = json.loads((repo_root / DOSSIER / "dossier.json")
                     .read_text(encoding="utf-8"))
    manifest = json.loads((repo_root / PACK / "manifest.json")
                          .read_text(encoding="utf-8"))
    assert doc["target_mode"] == "live"
    assert doc["native_op"]["op_id"] == manifest["op_id"]
    assert doc["machine"]["kind"] == "industrial_cell"
    est = next(e for e in doc["experiments"]
               if e["hypothesis_id"] == "H-estop")
    assert est["native_grounding"]["status"] == "present"
    assert est["native_grounding"]["native_check"] == "estop_target"


def test_forged_verdict_fails(repo_root, copies):
    d, p = copies
    doc = json.loads((d / "dossier.json").read_text(encoding="utf-8"))
    doc["hypotheses"][1]["verdict"] = "SUPPORTED"
    (d / "dossier.json").write_text(json.dumps(doc), encoding="utf-8")
    r = _run(repo_root, d, p)
    assert r.returncode == 2
    assert "seal mismatch" in r.stdout


def test_forged_native_transcript_fails(repo_root, copies):
    d, p = copies
    t = p / "transcripts" / "target-estop_target.log"
    t.write_bytes(t.read_bytes().replace(b"DENY", b"ALLW", 1))
    r = _run(repo_root, d, p)
    assert r.returncode == 2
    assert "VERIFY FAILED" in r.stdout


def test_dossier_files_are_checkout_stable(repo_root):
    for base in (DOSSIER, PACK):
        root = repo_root / base
        cr = [q.name for q in root.rglob("*")
              if q.is_file() and b"\r" in q.read_bytes()]
        assert cr == [], cr
