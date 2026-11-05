# Passport Threat Model (§6)

What a GENESIS RT evidence passport proves, against whom, and what it
explicitly does **not** prove. Read this before citing a passport as proof
of anything.

## 1. Trust boundary

```
              UNTRUSTED until validated                 TRUSTED after binding
┌────────────────────────────────────┐  ┌──────────────────────────────────┐
│ target_record / perf_record JSON   │─▶│ gate tiers (provenance bindings) │
│ (imported files, any origin)       │  │ replay.py (independent re-check) │
│ transcripts/*.log                  │  │                                  │
└────────────────────────────────────┘  └──────────────────────────────────┘
```

Imported records are untrusted input. The gate caps every tier above
`QNX_EXECUTED` unless the record is bound to the current IR, the current
build, and an in-window QNX execution (see `host/genesis_rt/provenance.py`).

## 2. Assurance levels (distinct, do not conflate)

| Level | Question answered | Mechanism |
|---|---|---|
| 1. Integrity checking | "Was this file altered after sealing?" | sha256 hash chain over canonical JSON |
| 2. Provenance verification | "Does this evidence belong to THIS ir/build/target run?" | ir/build/target/time/platform bindings |
| 3. Trusted local execution | "Did these bytes run on that machine just now?" | uname + staged cksum/size rendezvous + capture window |
| 4. Independent replay | "Can a third party re-check the verdict from the artifacts?" | `scripts/replay.py` + published `--anchor` + transcripts |
| 5. Hardware attestation | "Did genuine untampered hardware execute this?" | **NOT PROVIDED** (no trust anchor, no TPM/QNX Secure Boot claim) |

A level-N claim never implies level N+1.

## 3. Attacker capabilities and coverage

Attacker **A1 — sloppy/curious user**: hand-edits a passport to "fix" a
result, reuses yesterday's target_record with today's IR, forgets a
transcript.

- Stopped by levels 1–3: chain mismatch, binding refusal with an explicit
  level_reason, matrix-drift refusal.
- Covered by `tests/unit/test_passport_adversarial.py` (18 cases) and
  `tests/integration/test_replay.py`.

Attacker **A2 — motivated forger with repo access**: recomputes the whole
hash chain after falsification, forges perf distributions, crafts a
complete but fictional record set.

- Recomputed chain verifies standalone (§6 case 10 — the documented limit
  of a chain without a trust anchor).
- Detected **only** by level 4: the forged head differs from the
  out-of-band published `--anchor` (commit message, PROGRESS log, second
  copy), and forged transcripts differ from independently kept logs
  (`--transcripts-dir`).
- Blind spots remain: a forger who also controls the anchor publication
  channel is out of scope — that is precisely what level 5 would require.

Attacker **A3 — malicious local operator**: controls the machine that runs
the target pipeline end-to-end and recomputes every digest consistently.

- **NOT STOPPED.** No software-only scheme on a fully controlled machine
  can be. Level 3 binds "these bytes ran on that OS image in that window",
  not "no human interfered".
- Mitigation is procedural: run the pipeline on a machine the claimant
  does not administer, or publish anchors promptly to a channel they do
  not control.

Attacker **A4 — network / target impersonator**: fake QNX target answers
SSH with invented uname/cksum.

- Out of scope for the current pipeline (known-host SSH to a local VM,
  password from `GENESIS_TARGET_PASSWORD`, no target-side signing key).
- Documented, not solved. A target-side signing key would promote level 3
  toward per-target authenticity but still not to hardware attestation.

## 4. What each binding proves (and costs)

- **ir_sha256 + machine_id**: the target run configured the exact IR the
  passport claims. Cost: stale records fail loudly on any IR edit.
- **build binaries sha256/cksum/size**: the staged target binaries are the
  ones qcc produced for this build. Cost: any rebuild requires a fresh
  target cycle for high tiers. `cksum` (POSIX CRC) is the rendezvous
  primitive because it exists on stock QNX; sha256 is the inspection
  digest. Both are recorded; CRC catches accidental mismatch, not a
  determined forger (A2/A3 recompute both — see above).
- **capture window**: started/finished bracketing with 3600 s future skew.
  Proves coherence (run happened around the claimed time), not NTP-grade
  time. Generous skew is deliberate: targets prove coherence, not clock
  discipline.
- **platform pin**: only `qnx8_x86_64_qemu` records feed QNX tiers today.
  Numbers measured under QEMU/TCG are reproducibility data, not hardware
  timing guarantees.
- **build set (provenance v2, multi-build)**: the matrix also runs
  executables the pipeline under test did not build (`genesis_guard_conv`
  from a conveyor IR build, `genesis_guard_v2` from an AMR IR v2 build).
  Each one must be registered in a build set derived from the passport of
  the build that produced it (`scripts/build_set.py`), and every staged
  executable must belong to exactly one build. Refused: unattributed or
  ambiguous executables, staged bytes that differ from the registered
  build, wrong machine kind / schema version / source binary, an entry
  reusing the primary build id or one build id for two IRs, a required
  secondary missing. `scripts/replay.py --source-passport` re-derives each
  entry from its source passport. Cost: a campaign needs the passports of
  every build it stages. See `docs/multi-build-provenance.md`.
- **matrix pin**: exactly the 13 known checks, in order. A renamed,
  dropped, or extra check fails closed.
- **perf binding**: same staged rendezvous + window + platform, plus
  nearest-rank percentiles (no interpolation — reported values are always
  observed samples).

## 5. Residual risks (accepted, listed)

1. A3 (malicious operator) is undefeated by design — procedural
   mitigations only.
2. A4 (target impersonation) — no target-side key yet.
3. `--password` flag exposes the secret in the process list; prefer the
   `GENESIS_TARGET_PASSWORD` env var.
4. TCG timing numbers must never be quoted as hardware real-time bounds.
5. Legacy records without provenance cap at `QNX_EXECUTED`, never FAIL —
   a compatibility floor, not a finding. Provenance v1 records that stage
   executables from other builds (every matrix run before 5 Nov 2026) are
   capped the same way under provenance v2: they are never upgraded.
6. A build-set entry is only as trustworthy as its source passport; an
   operator who forges a whole source passport is A3 (undefeated).

## 6. Verify it yourself

```console
# Full host suite (includes 18 adversarial + 4 replay tests)
python -m pytest tests/ -q
# Independent re-verification of a passport (stdlib only + host/)
python scripts/replay.py artifacts/runs/<run>/passport.json
# With a published anchor and kept transcripts:
python scripts/replay.py artifacts/runs/<run>/passport.json \
  --anchor <published-head-sha256> --transcripts-dir <run>/transcripts
```
