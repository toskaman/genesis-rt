#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Verify a GENESIS RT public native-evidence pack.

Usage:  python verify.py [pack_dir]      (default: this file's directory)

Checks (exit 0 = integrity OK, exit 2 = failure):
  1. every manifest file present, digest matches, no unlisted files;
  2. passport hash chain valid (repo implementation when available,
     otherwise an exact stdlib re-implementation of the same algorithm);
  3. cross-file bindings: passport.run_id == op record, target IR digest
     == sealed IR digest (cross-operation substitution is rejected);
  4. reports the observed claims (verdict, matrix, samples) for the human
     to judge against EXPECTED_RESULTS.md -- this tool proves integrity,
     not that the underlying run passed.

Stdlib only. No QNX SDK, no network, no credentials needed.
"""
import hashlib
import json
import sys
from pathlib import Path

GENESIS_PREV = "GENESIS" + "0" * 57  # mirrors genesis_rt.evidence


def _canonical_json(data) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_chain_local(passport: dict, expect_version) -> list:
    """Exact stdlib mirror of genesis_rt.evidence.verify_chain."""
    errors = []
    if passport.get("passport_version") != expect_version:
        errors.append(f"unsupported passport_version: "
                      f"{passport.get('passport_version')!r}")
    chain = passport.get("chain", [])
    if not chain:
        return errors + ["empty chain"]
    prev = GENESIS_PREV
    for i, record in enumerate(chain):
        for key in ("seq", "kind", "body", "prev_hash", "hash"):
            if key not in record:
                errors.append(f"record {i}: missing {key}")
        if record.get("seq") != i:
            errors.append(f"record {i}: bad seq {record.get('seq')!r}")
        if record.get("prev_hash") != prev:
            errors.append(f"record {i}: prev_hash mismatch")
        expect = hashlib.sha256(
            (_canonical_json(record.get("body", {})) + prev).encode("utf-8")
        ).hexdigest()
        if record.get("hash") != expect:
            errors.append(f"record {i} ({record.get('kind')}): hash mismatch")
        prev = record.get("hash", "")
    return errors


def main(argv) -> int:
    pack = Path(argv[1] if len(argv) > 1 else Path(__file__).parent)
    failures: list = []
    manifest_p = pack / "manifest.json"
    if not manifest_p.is_file():
        print(f"FAIL: no manifest.json in {pack}")
        return 2
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))

    print(f"pack: {manifest.get('pack')}  op: {manifest.get('op_id')}  "
          f"commit: {manifest.get('commit')}")
    files = manifest.get("files", {})
    for rel in sorted(files):
        p = pack / rel
        if not p.is_file():
            failures.append(f"missing file: {rel}")
            continue
        got = _sha256_file(p)
        if got != files[rel]:
            failures.append(f"digest mismatch: {rel}")
    actual = {p.relative_to(pack).as_posix() for p in pack.rglob("*")
              if p.is_file()}
    for extra in sorted(actual - set(files) - {"manifest.json"}):
        failures.append(f"unlisted file: {extra}")
    print(f"files: {len(files) - len([f for f in failures if 'digest' in f or 'missing' in f])}"
          f"/{len(files)} digests OK"
          + ("" if not any("unlisted" in f for f in failures)
             else " (UNLISTED FILES PRESENT)"))

    passport = json.loads((pack / "passport.json").read_text(encoding="utf-8"))
    try:
        sys.path.insert(0, str(pack.parent.parent / "host"))
        from genesis_rt.evidence import verify_chain as repo_verify
        errors = repo_verify(passport)
        impl = "repo genesis_rt.evidence.verify_chain"
    except Exception as exc:  # pack used outside a checkout
        errors = verify_chain_local(passport, manifest.get("passport_version"))
        impl = f"stdlib mirror (repo import unavailable: {exc})"
    print(f"passport chain: {len(passport.get('chain', []))} links via {impl}")
    failures.extend(f"chain: {e}" for e in errors)

    op = json.loads((pack / "target-op.json").read_text(encoding="utf-8"))
    target = json.loads((pack / "transcripts" / "qnx-target-record.json")
                        .read_text(encoding="utf-8"))
    if passport.get("run_id") != op.get("op_id"):
        failures.append("binding: passport.run_id != op record op_id "
                        f"({passport.get('run_id')} vs {op.get('op_id')})")
    else:
        print(f"binding: passport.run_id == {op.get('op_id')} OK")
    sealed = (op.get("artifacts") or {}).get("ir_sha256")
    observed = (target.get("ir") or {}).get("ir_sha256")
    if not sealed or sealed != observed:
        failures.append("binding: target IR digest != sealed IR digest")
    else:
        print(f"binding: IR digest {sealed[:16]}... OK")
    if manifest.get("op_id") != op.get("op_id"):
        failures.append("binding: manifest op_id != op record op_id")

    anchor = manifest.get("anchor_passport_sha256")
    if anchor != _sha256_file(pack / "passport.json"):
        failures.append("anchor: passport digest != recorded anchor")
    else:
        print(f"anchor: passport sha256 {anchor[:16]}... OK")

    checks = target.get("checks", [])
    n_pass = sum(1 for c in checks if c.get("passed"))
    perf = json.loads((pack / "performance" / "qnx-perf-record.json")
                      .read_text(encoding="utf-8"))
    print(f"observed: op={op.get('state')} gate={passport.get('gate')} "
          f"matrix={n_pass}/{len(checks)} "
          f"samples={len(perf.get('raw_samples_us', []))} "
          f"qnx_verified={(op.get('artifacts') or {}).get('qnx_verified')}")
    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("VERIFY OK: integrity + bindings hold; compare observed claims "
          "with EXPECTED_RESULTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
