#!/usr/bin/env python3
# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Assemble a public native-evidence pack from a COMPLETED target op.

Usage (from the repo root):
  python scripts/build_evidence_pack.py --op op-<id> --out evidence/<name>

Copies the op's passport, IR, build/target/perf records and transcripts
VERBATIM except LF line-ending canonicalization (any content rewrite
would break the passport hash chain; LF makes digests stable across
platforms and git checkouts), excludes target binaries (digests
preserved; binaries may statically link QNX libc), and writes
manifest.json + verify.py + README.md + EXPECTED_RESULTS.md.

Refuses non-COMPLETED ops and binding mismatches. Idempotent for a fixed
--out (rebuild overwrites).
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VERIFY_SRC = REPO / "scripts" / "verify_evidence_pack.py"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_canonical(src: Path, dst: Path) -> None:
    """Copy a text evidence file, canonicalizing line endings to LF.

    The pack is digest-pinned: CRLF bytes would make digests depend on
    the author's platform and on git's text conversion. LF on disk +
    `evidence/** -text` in .gitattributes keeps committed bytes stable.
    Content (hence the passport chain, computed over parsed JSON) is
    unaffected; only \\r\\n/\\r -> \\n.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    dst.write_bytes(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--op", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit", default=None)
    args = ap.parse_args(argv)

    ops_dir = REPO / "artifacts" / "runs" / "target-ops"
    op_dir = ops_dir / args.op
    rec_p = ops_dir / f"{args.op}.json"
    if not rec_p.is_file() or not op_dir.is_dir():
        print(f"error: unknown op {args.op}", file=sys.stderr)
        return 2
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    if rec.get("state") != "COMPLETED":
        print(f"error: op {args.op} is {rec.get('state')}, not COMPLETED",
              file=sys.stderr)
        return 2
    commit = args.commit or subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"], capture_output=True,
        text=True, cwd=REPO).stdout.strip()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "transcripts").mkdir(parents=True)
    (out / "performance").mkdir(parents=True)
    (out / "sources").mkdir(parents=True)

    for name in ("ir.json", "passport.json", "qemu-console.log",
                 "qnx-build-record.json", "stage-manifest.json",
                 "gen-manifest.json"):
        _copy_canonical(op_dir / name, out / name)
    for p in sorted((op_dir / "target").glob("*")):
        _copy_canonical(p, out / "transcripts" / p.name)
    for p in sorted((op_dir / "perf").glob("*")):
        _copy_canonical(p, out / "performance" / p.name)
    for p in sorted((op_dir / "gen").glob("*")):
        if p.suffix in (".mk", ".h", ".c"):
            _copy_canonical(p, out / "sources" / p.name)
    _copy_canonical(rec_p, out / "target-op.json")
    ev_p = ops_dir / f"{args.op}.events.jsonl"
    if ev_p.is_file():
        _copy_canonical(ev_p, out / "op-events.jsonl")
    bs_src = Path((rec.get("params") or {}).get("build_set", ""))
    if bs_src.is_file():
        _copy_canonical(bs_src, out / "build-set.json")

    passport = json.loads((out / "passport.json").read_text(encoding="utf-8"))
    target = json.loads((out / "transcripts" / "qnx-target-record.json")
                        .read_text(encoding="utf-8"))
    perf = json.loads((out / "performance" / "qnx-perf-record.json")
                      .read_text(encoding="utf-8"))
    op_sanitized = json.loads((out / "target-op.json").read_text(encoding="utf-8"))

    # Pre-check bindings before publishing.
    sealed = (op_sanitized.get("artifacts") or {}).get("ir_sha256")
    if passport.get("run_id") != op_sanitized.get("op_id"):
        print("error: passport.run_id != op_id", file=sys.stderr)
        return 2
    if not sealed or sealed != (target.get("ir") or {}).get("ir_sha256"):
        print("error: target IR digest != sealed IR digest", file=sys.stderr)
        return 2

    binaries = ((passport.get("environment") or {}).get("qnx") or {}).get(
        "binaries", {})
    (out / "binaries.json").write_bytes(
        json.dumps({"note": "digests only; QNX binaries excluded (may "
                             "statically link QNX libc)",
                    "binaries": binaries}, indent=1).encode("utf-8"))

    checks = target.get("checks", [])
    n_pass = sum(1 for c in checks if c.get("passed"))
    samples = perf.get("raw_samples_us", [])
    wanted = (op_sanitized.get("artifacts") or {}).get("wanted", [])
    info_detail = next((c.get("detail", "") for c in checks
                        if c.get("detail", "").startswith("QNX")), "")
    qnx_line = info_detail.splitlines()[0][:160] if info_detail else "?"
    build_rec = json.loads((out / "qnx-build-record.json")
                           .read_text(encoding="utf-8"))
    qcc_raw = ((build_rec.get("environment") or {}).get("qcc_version") or "")
    qcc_line = " ".join(qcc_raw.split())[:160] or "?"

    readme = f"""# Native QNX evidence pack ({args.op})

Authentic records from GENESIS RT target op `{args.op}` (workflow
`{op_sanitized.get("workflow")}`, repo commit `{commit}`).

## Verify (no QNX SDK, no network, no credentials)

```sh
python verify.py
```

Expected: exit 0 plus the observed claims below. Any modified, missing
or unlisted file, broken passport link, or cross-operation substitution
fails with exit 2. See EXPECTED_RESULTS.md for the reference values.

## Transform from the raw op: LF canonicalization only

- Every evidence file is content-identical to
  `artifacts/runs/target-ops/{args.op}/` (git-ignored local evidence),
  with line endings canonicalized to LF so digests verify on every
  platform. Absolute paths reflect the author's build machine; no
  credentials are recorded anywhere in the op (verified before
  publishing).
- Target binaries excluded: only sha256/size/cksum digests ship (see
  binaries.json) — the linked binaries may contain QNX libc code.

## Trust model (read before citing)

- Proves: these exact bytes passed a 16-step on-target matrix on
  QNX 8.0/QEMU, sealed PASS, replay matched, digests bound.
- Does NOT prove: physical hardware behavior, hard-real-time
  guarantees, safety certification, or anything about other runs.
- QEMU timings are regression aids, not timing guarantees.
- The anchor is hash-linked (manifest + git history), not a
  hardware-backed attestation.
"""
    (out / "README.md").write_bytes(readme.encode("utf-8"))
    expected = f"""# Expected results ({args.op})

Observed values at pack build time. `python verify.py` reprints the
observed claims; compare them with this file.

- op state: {op_sanitized.get("state")}
- gate verdict: {passport.get("gate")}
- qnx_verified: {(op_sanitized.get("artifacts") or {}).get("qnx_verified")}
- matrix: {n_pass}/{len(checks)} checks passed
- fault scenarios sealed: {len(wanted)} ({", ".join(wanted[:4])}...)
- passport chain links: {len(passport.get("chain", []))}
- performance samples: {len(samples)} ({perf.get("method", "?")})
- provenance: v{target.get("provenance_version")} err={target.get("provenance_error")}
- replay (in-op): {(op_sanitized.get("artifacts") or {}).get("replay")}
- target identity: {qnx_line}
- toolchain: {qcc_line}
- IR digest: {sealed}
- passport anchor (sha256): {_sha256_file(out / "passport.json")}
"""
    (out / "EXPECTED_RESULTS.md").write_bytes(expected.encode("utf-8"))

    _copy_canonical(VERIFY_SRC, out / "verify.py")
    files = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files[p.relative_to(out).as_posix()] = _sha256_file(p)
    manifest = {
        "pack": out.name,
        "pack_version": 1,
        "op_id": args.op,
        "commit": commit,
        "created_utc": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds"),
        "passport_version": passport.get("passport_version"),
        "anchor_passport_sha256": _sha256_file(out / "passport.json"),
        "files": files,
    }
    (out / "manifest.json").write_bytes(json.dumps(manifest, indent=1)
                                           .encode("utf-8"))
    print(f"pack: {out} ({len(files)} files, commit {commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
