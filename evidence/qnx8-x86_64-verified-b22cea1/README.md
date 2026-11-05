# Native QNX evidence pack (op-0350e9bd4818)

Authentic records from GENESIS RT target op `op-0350e9bd4818` (workflow
`full`, repo commit `b22cea1`).

## Verify (no QNX SDK, no network, no credentials)

```sh
python verify.py
```

Expected: exit 0 plus the observed claims below. Any modified, missing
or unlisted file, broken passport link, or cross-operation substitution
fails with exit 2. See EXPECTED_RESULTS.md for the reference values.

## Transform from the raw op: none (verbatim)

- Every evidence file is byte-identical to
  `artifacts/runs/target-ops/op-0350e9bd4818/` (git-ignored local evidence).
  Absolute paths reflect the author's build machine; no credentials
  are recorded anywhere in the op (verified before publishing).
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
