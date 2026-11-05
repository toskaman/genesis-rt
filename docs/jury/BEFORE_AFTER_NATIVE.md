# Native before/after proof: one spec value changes QNX runtime behavior

Wave 10, Sprint B (§12). Question: does changing the machine contract
provably change the native QNX controller's behavior — or only the
paperwork? Answer: the behavior, observably, on target.

## The change (one line)

`control.max_linear_speed_mps`: **1.2 → 1.6** in the amr-demo IR
(`examples/amr-demo/machine-ir.json`). The AFTER IR validates clean
against the v1 schema (bound is (0, 10.0]).

- BEFORE op: `op-0350e9bd4818` (fresh Wave 10 campaign, COMPLETED)
- AFTER op: `op-df9b3668e5f7` (same `full` workflow, same host, same
  QEMU image, only the IR differs)

## The causal chain, measured

| Stage | BEFORE (1.2) | AFTER (1.6) |
|---|---|---|
| IR digest (sealed) | `356dc135…5667ce` | `fb2dbb3d…e4d5c` |
| Generated `genesis_config_gen.h:11` | `#define GENESIS_MAX_LINEAR_MPS 1.2` | `#define GENESIS_MAX_LINEAR_MPS 1.6` |
| `genesis_guard` binary sha256 | `4b76cc1c…664b0d` (14360 B) | `b65afcb4…560c9` (14360 B) |
| Guard banner on target | `machine=amr-demo-01 limits linear=1.200` | `machine=amr-demo-01 limits linear=1.600` |
| Probe `linear=1.500` decision | `DENY reason=SPEED_OVER_LIMIT` | `ALLOW reason=OK` |
| Matrix | 16/16 | 15/16 (`limits_differ` FAIL) |
| Op outcome | COMPLETED, gate PASS, passport sealed | FAILED at `qemu_verify`, **no passport sealed** |

Raw transcripts (local, git-ignored):

- `artifacts/runs/target-ops/op-0350e9bd4818/target/target-limits_differ.log`
- `artifacts/runs/target-ops/op-df9b3668e5f7/target/target-limits_differ.log`

BEFORE excerpt:

```text
---PROBE-AMR---
PROBE linear=1.500 estop=0 decision=DENY reason=SPEED_OVER_LIMIT state=1
```

AFTER excerpt:

```text
---PROBE-AMR---
PROBE linear=1.500 estop=0 decision=ALLOW reason=OK state=1
```

## Why this is the honest outcome, not a test bug

- The 1.5 m/s probe is absolute; the guard limit moved from below it
  to above it. A correct guard MUST flip DENY→ALLOW. It did.
- `limits_differ` expects the probe to DENY on slot 1 (geometry
  `0 < lim < 1.5` fails closed), so the check FAILs — loudly, with
  the ALLOW in the transcript. The other 15 checks still pass: the
  fault-injection probes are relative to the compiled-in limit
  (`FI_CRUISE = 0.4×limit`, `FI_OVER = 2×limit+1`), so their
  outcomes are limit-invariant by construction.
- The op FAILED at `qemu_verify` (9/13) and sealed nothing: a failed
  campaign cannot mint a PASS passport. Fail-closed holds.

## What this does not prove

- No synchronized A/B comparison view exists in Studio yet (P1 UI,
  NOT STARTED); this page is the comparison artifact.
- The AFTER evidence is local-only (no sealed passport to publish —
  by design). Reproduce with the commands below.

## Reproduce

```powershell
$env:PYTHONPATH = 'host'
$env:GENESIS_TARGET_PASSWORD = '<qnxuser password>'
python -u -m genesis_rt.cli serve --port 8089  # terminal 1
```

```powershell
# terminal 2: BEFORE body is the Wave 10 campaign body; AFTER flips one value
python -u /tmp/w10_afterbody.py  # 1.2 -> 1.6 (or edit by hand)
python -u /tmp/qlab/campaign_after.py
```

Compare `target-limits_differ.log`, `genesis_config_gen.h`, and the
guard sha256 in `qnx-build-record.json` across the two op dirs.
