# Wave 11 native BEFORE/AFTER comparison manifest

Two independent native QNX campaigns from one valid contract change
(`max_linear_speed_mps` 1.2 → 1.6). Each pack verifies on its own;
this file only links them — provenance chains are NOT conflated.

| | BEFORE | AFTER |
|---|---|---|
| Pack | `evidence/qnx8-x86_64-w11-before/` | `evidence/qnx8-x86_64-w11-after/` |
| Op | op-d08d3d3ea346 | op-67a4595a858f |
| IR digest | 356dc135f27f4586… | fb2dbb3de8a19546… |
| Limit (m/s) | 1.2 | 1.6 |
| Guard sha256 | 4b76cc1c1a909553… | b65afcb42e983095… |
| Probe 1.5 m/s (slot 1) | DENY SPEED_OVER_LIMIT | ALLOW OK |
| Matrix | 16/16 | 16/16 |
| Gate | PASS | PASS |
| Passport links | 15 | 15 |
| Passport anchor | 2cf6bd6e6e3997cd… | 3c6401934e9efb72… |

## Verify

```sh
python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before
python evidence/qnx8-x86_64-w11-after/verify.py evidence/qnx8-x86_64-w11-after
```

Both print `VERIFY OK` and `matrix=16/16`. Cross-check the anchors
against `comparison.json` (machine-readable copy of this table).

## Negative control (Campaign C, NOT a pack)

op-ad562b34f8de bound IR 1.6 to a stale 1.2-built guard: only
`limits_differ` failed (banner pin), no passport sealed. Local
evidence only (`artifacts/runs/target-ops/op-ad562b34f8de/`,
git-ignored); reproducible via the stale-build mode documented in
`docs/jury/BEFORE_AFTER_NATIVE.md`.

## Trust model

Same as each pack README: QEMU/QNX 8.0 behavior, hash-linked
anchors, no hardware attestation, no safety certification.
