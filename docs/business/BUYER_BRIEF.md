# GENESIS RT — Buyer Brief (one page)

Date: 8 Nov 2026. Branch: `titan-omega3`. Status: prototype
brief for an embedded/QNX engineering lead. Every numbered
claim below is measured on the current tree; every
unmeasured assumption is labeled HYPOTHESIS. No ROI is
promised and no certified platform is replaced.

## 1. One primary use case

**Verify a requirement change against the binary actually
deployed on QNX, and hand any reviewer evidence they can
replay offline.** The team writes a one-page machine
contract; GENESIS RT compiles it to native QNX software,
runs the fault campaign on the target, and seals a passport
binding requirement → source → binary → observed behavior.

## 2. One representative change (measured, 8 Nov 2026)

AMR v1 → v2: adding guarded safe-stop transitions to a
mobile-robot controller contract.

- BEFORE pack `evidence/qnx8-x86_64-omega2-before/`: 34/34
  digests VERIFY OK, native matrix 16/16 PASS, sealed.
- AFTER pack `evidence/qnx8-x86_64-omega2-after/`: 36/36
  digests VERIFY OK, native matrix 16/16 PASS, sealed.
- Both correct under their own contract
  (`qnx_verified=True`, replay matches).
- Stale control: pairing the v2 contract with the v1-built
  binary fails 14/16, exactly on `estop_target` +
  `v2_transitions` — the governance change is behaviorally
  detected, as designed.

A second, limits-flavored proof (1.2 → 1.6 m/s DENY→ALLOW
flip, 18/18 bit-for-bit `qcc` rebuilds) ships as
historical evidence (`evidence/qnx8-x86_64-w11-*/`).

## 3. One measurable technical benefit

Fault-detection on a fixed, deterministic benchmark
(`bench/productivity/`, methodology v2, 6 Nov 2026): six
engineering tasks take **8 GENESIS commands vs 30
reference commands + 10 manual steps**, catch **5/5
injected faults vs 3/5** for the reference lane, and
re-run with identical semantic summaries. Reference
workflows are synthetic and labeled; this is a property
of the tool, not a measurement of users. HYPOTHESIS
(unmeasured): fewer manual steps shorten review prep —
needs 2–3 pilot reviews to test.

## 4. One auditable proof

Any reviewer, without our machines, runs:

```sh
git clone https://github.com/toskaman/genesis-rt.git
python evidence/qnx8-x86_64-omega2-before/verify.py \
  evidence/qnx8-x86_64-omega2-before
python evidence/qnx8-x86_64-omega2-after/verify.py \
  evidence/qnx8-x86_64-omega2-after
```

stdlib-only verifiers; expected outcome VERIFY OK on both
packs. Tamper controls: modified transcripts, reordered
steps, and cross-operation swaps are refused (24-case
adversarial suite, `facts.ADVERSARIAL_TESTS`). Packs are
hash-only (UNSIGNED) — integrity + replay, not signer
authentication; see `docs/evidence-trust.md`.

## 5. One adoption pathway

1. Day 0: run the codelab (`docs/codelab/README.md`,
   author-operated ~45 min hands-on, re-executed 8 Nov
   2026, Windows + Linux) — contract to running native
   IPC chain on the team's own QNX license.
2. Week 1: point `external-write-manifest` /
   `external-check` at one existing build directory for
   stale-binary detection with zero rewrites
   (`examples/external-demo/README.md`).
3. Month 1: run the quick paired pilot (3 tasks, kit in
   `docs/business/pilot-study.md` + `bench/productivity/`)
   to measure the team's own review-prep time.

Prerequisites: customer's own commercial QNX license
terms (QNX Everywhere non-commercial terms do not
authorize commercial use — `COMMERCIAL_VISION.md` §9);
one engineer comfortable with CLI + QNX target basics;
customer-hosted runners for target CI stages (public
runners cannot hold the SDK — structural, not a bug).

## 6. Boundaries (what it is not)

- Complements Momentics and Parasoft/LDRA/VectorCAST —
  it proves *executed behavior*, it does not analyze
  code or replace qualification suites.
- Prototype maturity: 1629-test host suite + 16-step
  matrix is strong for a hackathon, thin for production.
- QEMU x86_64 only; no ARM/real-hardware timing; no
  safety-certification claim of any kind.
- Human benefit unmeasured: `HUMAN USER BENEFIT NOT YET
  MEASURED` governs until independent pilots run.

Full vision, landscape, roadmap: `COMMERCIAL_VISION.md`,
`COMPETITIVE_LANDSCAPE.md`.
