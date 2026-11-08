# Native QNX evidence pack (op-d91bd4133590)

Authentic records from GENESIS RT target op `op-d91bd4133590` (workflow
`full`, repo commit `318d46b`).

## Verify (no QNX SDK, no network, no credentials)

```sh
python verify.py
```

Expected: exit 0 plus the observed claims below. Any modified, missing
or unlisted file, broken passport link, or cross-operation substitution
fails with exit 2. See EXPECTED_RESULTS.md for the reference values.

## Transform from the raw op: LF canonicalization only

- Every evidence file is content-identical to
  `artifacts/runs/target-ops/op-d91bd4133590/` (git-ignored local evidence),
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
