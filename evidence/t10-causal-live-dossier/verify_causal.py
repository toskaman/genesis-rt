#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline check: the flagship causal dossier is grounded LIVE on QNX.

Stdlib only, no SDK, no network. Exit 0 = every check below holds,
exit 2 = any finding (fail-closed).

1. The native pack verifies (runs its own verify.py).
2. The dossier seal recomputes (sha256 over canonical JSON).
3. The dossier's single live op is the pack's op, COMPLETED,
   qnx_verified=True.
4. Every live-grounded hypothesis names a check that passed in the
   pack's target record, and its transcript_sha256 equals the pack
   transcript (LF-canonical bytes).
5. The winning hypothesis is grounded ``present`` with its check passed.

Usage: python verify_causal.py [DOSSIER_DIR] [PACK_DIR]
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PACK = HERE.parent / "qnx8-x86_64-t10-cell-causal-live"
UNSEALED = {"seal", "dossier_path"}


def canon_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    ddir = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
    pack = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PACK
    errors: list[str] = []
    rc = subprocess.run([sys.executable, str(pack / "verify.py"), str(pack)],
                        capture_output=True, text=True).returncode
    print(f"pack verify.py: rc={rc}")
    if rc != 0:
        errors.append("native pack does not verify")
    doc = json.loads((ddir / "dossier.json").read_text(encoding="utf-8"))
    body = {k: v for k, v in doc.items() if k not in UNSEALED}
    seal = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()
    ok_seal = seal == doc.get("seal")
    print(f"dossier seal: {'OK' if ok_seal else 'MISMATCH'} "
          f"({str(doc.get('seal'))[:16]}...)")
    if not ok_seal:
        errors.append("dossier seal mismatch")
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    op = doc.get("native_op", {})
    want_op = manifest.get("op_id")
    print(f"native op: {op.get('op_id')} state={op.get('state')} "
          f"qnx_verified={op.get('qnx_verified')} (pack op {want_op})")
    if doc.get("target_mode") != "live":
        errors.append("dossier is not live-grounded")
    if op.get("op_id") != want_op or op.get("state") != "COMPLETED" \
            or op.get("qnx_verified") is not True:
        errors.append("live op does not match a COMPLETED qnx_verified pack")
    record = json.loads((pack / "transcripts" / "qnx-target-record.json")
                        .read_text(encoding="utf-8"))
    passed = {c["name"]: c.get("passed") is True
              for c in record.get("checks", [])}
    grounded = {}
    for exp in doc.get("experiments", []):
        g = exp.get("native_grounding", {})
        hid = exp.get("hypothesis_id")
        if g.get("mode") != "live":
            errors.append(f"{hid}: grounding is not live")
            continue
        if g.get("status") == "no-native-check":
            print(f"  {hid}: host only (no native injector)")
            continue
        chk = g.get("native_check")
        tpath = pack / "transcripts" / f"target-{chk}.log"
        same = tpath.is_file() and canon_sha(tpath) == g.get("transcript_sha256")
        good = g.get("status") == "present" and passed.get(chk) and same
        grounded[hid] = bool(good)
        print(f"  {hid}: {chk} on QNX {'PASS' if passed.get(chk) else 'FAIL'}"
              f", transcript {'matches' if same else 'MISMATCH'}")
        if not good:
            errors.append(f"{hid}: live grounding does not hold")
    winner = doc.get("causality", {}).get("winning_hypothesis")
    print(f"winner: {winner}")
    if not winner or not grounded.get(winner):
        errors.append("winning hypothesis is not grounded on QNX")
    if errors:
        for e in errors:
            print(f"FINDING: {e}")
        print("VERIFY FAILED")
        return 2
    print("VERIFY OK: incident -> winning hypothesis grounded live on "
          "QNX 8.0 (QEMU x86_64), transcripts bound to the native pack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
