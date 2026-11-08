# External build-manifest check (BYOQNX minimal adapter)

Your QNX project stays exactly as it is — its own build system, its
own tests. GENESIS RT adds one capability: **stale-artifact
detection** on the binaries your build already produces.

## Workflow (2 commands)

After a build, hash the output directory into a manifest:

```
PYTHONPATH=host python -m genesis_rt.cli external-write-manifest \
  --workspace ./build-out --project my-controller \
  --toolchain "qcc 12.2.0 gcc_ntox86_64" --out manifest.json
```

Later — after a rebuild, a deploy copy, or a suspicious incident —
re-check the directory against the manifest:

```
PYTHONPATH=host python -m genesis_rt.cli external-check manifest.json \
  --workspace ./build-out
```

Output names every binary MATCH, MISMATCH (with expected vs observed
digests), or ABSENT, and ends in `verdict: CONSISTENT` (exit 0) or
`verdict: STALE` (exit 2). `--json` emits the machine-readable report.

## Trust boundary (read this once)

- Only **digest consistency** is checked. The toolchain string is
  recorded, never verified; no QNX execution is supervised.
- `test_claims` in the manifest are the author's **unverified
  assertion**: counted, labelled `UNVERIFIED_CLAIM`, never evaluated.
- `release_eligible` is always `False`. A consistent external
  workspace is "not stale", never "verified". There is no code path
  from this adapter to the release gate (`host/genesis_rt/gate.py`
  is never imported by `host/genesis_rt/external.py`).
- Manifest binary names are confined to the workspace: absolute
  paths and `..` escapes are refused before any file is read.

## Verified example (8 Nov 2026)

Built the six GENESIS guard/controller/device binaries with the real
qcc 12.2.0 toolchain, manifested the build directory, checked:
6/6 MATCH, CONSISTENT. Flipped one byte of `genesis_guard`, checked
again: 1 MISMATCH named, verdict STALE, `release_eligible: False`.
Same mechanics as the unit suite (`tests/unit/test_external.py`,
14 tests), on real cross-compiled output.
