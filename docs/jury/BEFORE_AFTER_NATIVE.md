# Native before/after proof: one spec value changes QNX runtime behavior

Wave 11, Phase A (S5). Question: does changing the machine contract
provably change the native QNX controller's behavior -- or only the
paperwork? Answer: the behavior, observably, on target -- and each
valid revision now earns its own independently verifiable passport.

## The change (one line)

`control.max_linear_speed_mps`: **1.2 -> 1.6** in the amr-demo IR.
The AFTER IR validates clean against the v1 schema (bound is (0, 10.0]).

- BEFORE op: `op-d08d3d3ea346` (fresh Wave 11 campaign, COMPLETED)
- AFTER op: `op-67a4595a858f` (same `full` workflow, same host, same
  QEMU image, only the IR differs)
- Negative control: `op-ad562b34f8de` (stale-build: IR 1.6 bound to a
  1.2-compiled guard; FAILED, no passport -- see below)

## The causal chain, measured

| Stage | BEFORE (1.2) | AFTER (1.6) |
|---|---|---|
| IR digest (sealed) | `356dc135...5667ce` | `fb2dbb3d...e4d5c` |
| Generated `genesis_config_gen.h:11` | `#define GENESIS_MAX_LINEAR_MPS 1.2` | `#define GENESIS_MAX_LINEAR_MPS 1.6` |
| `genesis_guard` binary sha256 | `4b76cc1c...52664b0d` (14360 B) | `b65afcb4...9bf6560c9` (14360 B) |
| Guard banner on target | `machine=amr-demo-01 limits linear=1.200` | `machine=amr-demo-01 limits linear=1.600` |
| Probe `linear=1.500` decision | `DENY reason=SPEED_OVER_LIMIT` | `ALLOW reason=OK` |
| Matrix | 16/16 | 16/16 |
| Op outcome | COMPLETED, gate PASS, passport sealed | COMPLETED, gate PASS, passport sealed |

BEFORE excerpt (`target-limits_differ.log`):

```text
---PROBE-AMR---
PROBE linear=1.500 estop=0 decision=DENY reason=SPEED_OVER_LIMIT state=1
```

AFTER excerpt:

```text
---PROBE-AMR---
PROBE linear=1.500 estop=0 decision=ALLOW reason=OK state=1
```

## Why both PASS now (Wave 11 contract-aware oracle)

The 1.5 m/s probe is absolute; the guard limit moved from below it
to above it. A correct guard MUST flip DENY->ALLOW. It did.

In Wave 10, `limits_differ` hardcoded the slot-1 probe expectation
(DENY), so AFTER failed 15/16 with no passport -- honest, but the
expectation was tied to one threshold, not to the declared contract.

Wave 11 fixes the expectation, not the guard:
`host/genesis_rt/native_oracle.py` derives the expected decision for
every probe from the validated IR (float32 wire fidelity,
`plan_probes` including below/at/reference/above), and
`scripts/qnx_target.py` evaluates the native replies against that
plan. A valid contract change passes; a genuinely wrong guard still
fails (see Campaign C). The oracle itself is pinned by 60 unit tests
plus mutation and guard-parity tests
(`tests/unit/test_native_oracle.py`, `test_limits_differ.py`).

## Campaign C: the negative control still refuses

op-ad562b34f8de binds the 1.6 IR to a stale guard binary compiled for
1.2: only `limits_differ` fails (guard banner pins 1.200 against an
expected 1.600), the op FAILED at `qemu_verify`, and no passport was
sealed. Fail-closed holds. Local evidence only (git-ignored):
`artifacts/runs/target-ops/op-ad562b34f8de/`.

## Portable evidence

- `evidence/qnx8-x86_64-w11-before/` -- BEFORE pack, `verify.py` prints
  `VERIFY OK` + `matrix=16/16`
- `evidence/qnx8-x86_64-w11-after/` -- AFTER pack, same
- `evidence/w11-before-after/COMPARISON.md` + `comparison.json` --
  linked manifest (anchors, digests, flip); the two provenance
  chains stay independent

```sh
python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before
python evidence/qnx8-x86_64-w11-after/verify.py evidence/qnx8-x86_64-w11-after
```

## What this does not prove

- No hardware attestation: QEMU/QNX 8.0 behavior only.
- No safety certification: the packs are engineering evidence.
- Studio's before/after compare view gained Wave 11 change-proof rows
  (SS7); the full synchronized A/B Twin comparison remains future work.

## Reproduce

Requires the QNX SDK + project QEMU image (see
`docs/jury/REPRODUCE.md`). BEFORE/AFTER bodies: the campaign driver
uses the IR under `examples/amr-demo/` with the single limit value
changed; AFTER = same body with `max_linear_speed_mps` 1.6. Campaign
C = AFTER body with the build phase pointed at the BEFORE guard
(stale-build mode). Compare `target-limits_differ.log`,
`genesis_config_gen.h`, and the guard sha256 in
`qnx-build-record.json` across the op dirs -- or open the Target
Runner tab in Studio, pick the two ops in Before / after comparison,
and read the side-by-side verdict, IR, gate, matrix deltas and the
SS7 change-proof rows (`GET /target/ops/compare?before=...&after=...`).
