# Multi-build provenance (provenance v2)

Status: implemented and unit-tested on the host (5 Nov 2026). **Not yet
exercised on the QNX target** with a real build set (see "Migration").

## The gap it closes

The on-target matrix (`scripts/qnx_target.py`, 14 steps since Wave 3A) runs three kinds of
executables:

| Staged name | Produced by | Used by steps |
|---|---|---|
| `genesis_guard`, `genesis_controller`, `genesis_device`, `genesis_status`, `genesis_supervisor`, `genesis_faultinject` (+ `genesis_cellcheck` for cell IRs) | the build of the pipeline under test (primary build) | all |
| `genesis_guard_conv` | a separate build of a **conveyor** IR | `limits_differ`, `conv_chain` |
| `genesis_guard_v2` | a separate build of the **AMR IR v2** | `v2_transitions` |

Provenance v1 bound the primary build's binaries to what the target staged,
but accepted any other staged `genesis_*` executable without origin. An AMR
guard copied as `genesis_guard_conv`, or an old binary from another build,
would not have been detected.

## Model

A **build set** (`build_set_version: 1`) maps each secondary staged name to
an entry derived from the evidence passport of the build that produced it:
machine id and kind, schema version, IR digest, generator version, qcc
version, build time, build id (digest of IR digest + build time + toolchain +
every output digest), sha256 / POSIX cksum / size, source run id and the
source passport's chain head. Code: `host/genesis_rt/buildset.py`.

The gate (`provenance.validate_target_binding` / `validate_perf_binding`)
requires for any tier above `QNX_EXECUTED`:

1. every staged executable belongs to exactly one build (primary or one
   entry): unattributed and ambiguous executables are refused;
2. entries are well formed (sha256 hex digests, all fields present, the
   entry's `staged_name` matches its key);
3. staged cksum + size equal the entry's;
4. secondaries required by the matrix steps are present with the declared
   origin (`REQUIRED_SECONDARIES`: conveyor kind for `genesis_guard_conv`;
   schema v2 AMR for `genesis_guard_v2`; source binary `genesis_guard`);
   a secondary built from the primary IR is refused;
5. no reused provenance: an entry cannot carry the primary build id, and
   one build id cannot describe two IRs;
6. the perf record carries the same build set as the verified matrix run.

Tests: `tests/unit/test_buildset.py` (one test per attack: wrong machine
guard, wrong IR version, old binary from another build, right name / wrong
contents, missing secondary, modified secondary, reused provenance,
inconsistent manifest, unregistered executable, tampered perf build set,
legacy v1). A mutation check (each rule disabled in turn) is caught by at
least one test.

## Producing and checking a build set

```console
# 1. passports of the secondary builds (one pipeline run each, with QNX SDK)
genesis-rt demo --ir examples/conveyor-demo/machine-ir.json      # -> run-CONV
genesis-rt demo --ir examples/amr-demo/machine-ir-v2.json        # -> run-AMRV2
# 2. build set
python scripts/build_set.py create -o artifacts/build-set.json \
  --entry genesis_guard_conv=genesis_guard:artifacts/runs/run-CONV/passport.json \
  --entry genesis_guard_v2=genesis_guard:artifacts/runs/run-AMRV2/passport.json
# 3. stage the binaries as before, then bind the campaign
python scripts/qnx_target.py verify --ir examples/cell-demo/cell-ir.json \
  --build-set artifacts/build-set.json
python scripts/qnx_target.py perf --build-set artifacts/build-set.json
# 4. independent replay, re-deriving every entry from its source passport
python scripts/replay.py <campaign passport> --anchor <head> \
  --transcripts-dir <dir> --require-build-set-replay \
  --source-passport artifacts/runs/run-CONV/passport.json \
  --source-passport artifacts/runs/run-AMRV2/passport.json
```

## Assurance limits

- The target offers POSIX `cksum` (CRC32) as its rendezvous; sha256 is the
  host-side inspection digest. CRC catches accidental mismatch, not a forger
  who controls the host (threat model A2/A3).
- An entry is as trustworthy as its source passport. Replay re-verifies that
  passport's hash chain and recomputes the entry; it cannot detect a source
  passport forged in full by the operator (A3).

## Migration

- New records are written with `provenance_version: 2`. v1 records stay
  readable.
- A v1 record whose staged set contains nothing beyond the primary build
  keeps its tier.
- A v1 record that stages executables from other builds is **capped at
  `QNX_EXECUTED`** with an explicit reason. This applies to every matrix run
  published before 5 Nov 2026 (including run-652e31767c28 and
  run-8009ee91097e): their hash chains and anchors still replay as before,
  but re-evaluating the gate no longer grants `QNX_BEHAVIOR_VERIFIED` /
  `QNX_PERFORMANCE_MEASURED`. They are not upgraded; a fresh target cycle with
  `--build-set` is required to regain those tiers.
- The matrix itself is not changed by provenance v2 (14 steps after Wave 3A `guard_crash`, which uses only primary-build executables).
