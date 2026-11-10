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
  labeled ARCHIVED. The live-target path is implemented
  (TargetRunner verify-only + bounded poll + timeout-cancel) but
  NOT executed in this environment (no QEMU session here);
  fake-runner tests cover completed/op-failed/timeout/start-failed.
- H-stalebin host check is not wired (manifest comparison needs
  staged builds): INCONCLUSIVE on host + archived v2_transitions
  grounding. H-crash/H-seq have no cell injection scenario:
  host INCONCLUSIVE + native grounding where a matrix check exists.
- The dossier is hash-sealed, not signed. Integrity, not
  authentication — same trust level as evidence packs (UNSIGNED).
