# OMEGA7 Causal Engine — Product

One incident. One intelligent investigation. One real execution.
One verified answer.

## The experience

An engineer pastes a failure report. GENESIS RT ranks competing
hypotheses, compiles each into a discriminating experiment, runs
host reproductions plus native QNX grounding, eliminates what the
evidence refutes, and seals a dossier that says which explanation
survived — with every pointer needed to re-check it. A proposed
fix then replays the same experiment through K1 BEFORE/AFTER legs,
and the dossier carries the new verdict.

What the user never does in this flow: read raw logs across tools,
hand-write repro scripts, reconstruct seeds and build provenance,
or assemble screenshots into a report.

## Flagship story (implemented, measured)

A cell halts mid-transfer with ESTOP latched
(`incidents/estop-cell-transfer.json`). One command:

```
genesis-rt causal-repro --incident incidents/estop-cell-transfer.json
```

ranks H-estop first (matched signals: estop, halt, state=3),
reproduces the deny+latch+no-motion signature on the host, grounds
it against the archived native transcript
(`target-estop_target.log`: DENY ESTOP state=3 → reset → ALLOW),
marks the other five hypotheses INCONCLUSIVE with reasons, and
seals the dossier. Measured on the owner machine (n=1, Windows,
Python 3.14, SDK present): reproduce 3.4 s, fix leg 2.1 s,
5.5 s incident-to-proof for six hypotheses.

```
genesis-rt causal-fix --dossier artifacts/dossiers/inc-estop-cell-01 \
  --after-ir examples/cell-demo/cell-ir.json
```

appends the K1 verdict and reseals (measured: PASS, 2.1 s).

## Honest boundaries (this slice)

- Deterministic only: keyword signal matching + oracle verdicts.
  No LLM authors hypotheses here; no semantic understanding is
  claimed. Keyword matching has known false-positive/negative
  limits (documented; e.g. short substrings).
- No probability percentages anywhere: rank + matched signals +
  experiment verdicts are the reported confidence.
- Native grounding defaults to archived Omega2 transcripts,
  labeled ARCHIVED (these are AMR-machine transcripts grounding a
  cell incident — a mechanism-level, not machine-level, match).
- T10 (12 Nov 2026) executed the live path and fixed what that
  surfaced: the slice started a `verify-only` op per hypothesis on
  whatever binaries were left on the target and reported bare
  `completed` without reading the check. It now runs ONE hermetic
  `full` op for the incident's own machine (generate, `qcc`, stage,
  16-check matrix, seal, replay), reads each hypothesis's check from
  the target record (`present` / `check-failed` / `absent` /
  `no-record`), hashes the LF-canonical transcript, and
  `verify_dossier` re-checks those hashes. The first live run failed
  15/16 (`limits_differ`: the oracle refused industrial-cell
  predictions by design); after pinning that the cell compiles the
  shared guard sources, the oracle covers `industrial_cell` and the
  rerun sealed 16/16, `qnx_verified=True` (op-33c56ec417a4,
  `evidence/t10-causal-live-dossier/`). Live grounding corroborates
  mechanisms; it never upgrades a verdict.
- H-stalebin host check is not wired (manifest comparison needs
  staged builds): INCONCLUSIVE on host + archived v2_transitions
  grounding. H-crash/H-seq have no cell injection scenario:
  host INCONCLUSIVE + native grounding where a matrix check exists.
- The dossier is hash-sealed, not signed. Integrity, not
  authentication — same trust level as evidence packs (UNSIGNED).
