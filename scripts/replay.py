#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Re-verify a passport: chain integrity + gate re-evaluation.

Standalone verifier (§6): needs only the repo's host/ package and the
passport file — no Studio, no API, no QNX SDK.

Usage: python scripts/replay.py <passport.json> [--required a b c]
           [--anchor <head-sha256>] [--transcripts-dir DIR]

Exit 0 only if the chain is valid AND the gate passes AND every
requested extra check holds.

--anchor pins the chain-head hash published out-of-band (commit
message, PROGRESS log, second copy). A tampered passport whose chain
was recomputed still verifies as "chain: valid" — that is the honest
limit of a hash chain without a trust anchor — but its head differs
from the published anchor, so the forgery is detected.

--transcripts-dir recomputes the sha256 of target-<step>.log files and
compares them to the digests embedded in the qnx_target record.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host"))

from genesis_rt import gate  # noqa: E402
from genesis_rt.evidence import load_passport, verify_chain  # noqa: E402


def _check_anchor(passport: dict, anchor: str) -> list[str]:
    head = passport["chain"][-1]["hash"] if passport.get("chain") else None
    if head != anchor:
        return [f"anchor MISMATCH: chain head {head} != published {anchor}"]
    return []


def _check_transcripts(passport: dict, transcripts_dir: str) -> list[str]:
    errors: list[str] = []
    rec = next((r for r in passport.get("chain", [])
                if r.get("kind") == "qnx_target"), None)
    if rec is None:
        return ["no qnx_target record to check transcripts against"]
    digests = rec.get("body", {}).get("transcripts")
    if not isinstance(digests, dict):
        return ["qnx_target record carries no transcript digests"]
    root = Path(transcripts_dir)
    for step, want in sorted(digests.items()):
        blob = root / f"target-{step}.log"
        if not blob.exists():
            errors.append(f"transcript missing: target-{step}.log")
            continue
        got = hashlib.sha256(blob.read_bytes()).hexdigest()
        if got != want:
            errors.append(f"transcript MODIFIED: target-{step}.log "
                          f"(sha256 {got[:12]}... != {str(want)[:12]}...)")
    if not errors:
        print(f"transcripts: {len(digests)}/{len(digests)} match")
    return errors


def _print_provenance(passport: dict) -> None:
    by_kind = {r["kind"]: r.get("body", {}) for r in passport.get("chain", [])}
    irb, build, tgt = (by_kind.get("ir", {}), by_kind.get("qnx_build", {}),
                       by_kind.get("qnx_target", {}))
    print(f"provenance: ir={str(irb.get('ir_sha256'))[:12]}... "
          f"machine={irb.get('machine', {}).get('id')}")
    bins = build.get("binaries") or {}
    qcc = build.get("qcc_version")  # fixture/minimal shape
    if qcc is None:
        env = build.get("environment") or {}
        raw = env.get("qcc_version", "")
        default = next((ln.strip() for ln in str(raw).splitlines()
                        if "(default)" in ln), None)
        qcc = default.split()[0].rstrip(",") if default else "?"
    print(f"  build: {len(bins)} binaries digested (qcc {qcc})")
    staged = (tgt.get("staged") or {})
    print(f"  target: {len(staged)} staged binaries observed, "
          f"platform={(tgt.get('target') or {}).get('platform')}, "
          f"window={tgt.get('started_utc')}..{tgt.get('finished_utc')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay-verify an evidence passport")
    ap.add_argument("passport")
    ap.add_argument("--required", nargs="*", default=None)
    ap.add_argument("--anchor", default=None,
                    help="expected chain-head sha256 (out-of-band trust anchor)")
    ap.add_argument("--transcripts-dir", default=None,
                    help="dir with target-<step>.log files to re-digest")
    args = ap.parse_args()
    passport = load_passport(args.passport)
    errors = verify_chain(passport)
    print(f"chain: {'valid' if not errors else 'INVALID'}")
    for e in errors:
        print(f"  {e}")
    if args.anchor is not None:
        anchor_errors = _check_anchor(passport, args.anchor)
        print(f"anchor: {'match' if not anchor_errors else 'MISMATCH'}")
        for e in anchor_errors:
            print(f"  {e}")
        errors += anchor_errors
    if args.transcripts_dir is not None:
        transcript_errors = _check_transcripts(passport, args.transcripts_dir)
        for e in transcript_errors:
            print(f"  {e}")
        errors += transcript_errors
    _print_provenance(passport)
    if args.required is None:
        ir_rec = next((r for r in passport["chain"] if r["kind"] == "ir"), None)
        required = ir_rec["body"]["scenarios"] if ir_rec else []
    else:
        required = args.required
    verdict = gate.evaluate(passport, required)
    print(f"gate: {verdict['verdict']} (qnx_verified={verdict['qnx_verified']})")
    for r in verdict["reasons"]:
        print(f"  {r}")
    return 0 if (not errors and verdict["verdict"] == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
