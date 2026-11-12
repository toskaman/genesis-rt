# Flagship causal dossier, grounded LIVE on QNX 8.0 (T10, 12 Nov 2026)

`dossier.json` is the sealed output of one command on the author box
(Windows, Python 3.14, QNX SDP 8.0, QEMU x86_64 TCG):

```
genesis-rt causal-repro --incident incidents/estop-cell-transfer.json \
  --target live --image-dir E:/qnx800/images/qemu/qemu --accel tcg --cpu max \
  --extra-src <v2 guard> <conveyor guard> --build-set <build set>
```

One hermetic native op (`op-33c56ec417a4`, workflow `full`) generated,
built (`qcc`) and staged the **industrial cell's own** binaries, ran the
16-check matrix on QNX 8.0 (16/16, sealed PASS, `qnx_verified=True`,
replay matched) and every hypothesis read its own native check from
that single record. Wall time 234 s for the whole command (n=1;
QEMU TCG, not a timing claim). The native op is published verbatim as
`evidence/qnx8-x86_64-t10-cell-causal-live/` (its generated README
names commit `839c7a2` and the default ops dir: the op actually ran
from the T10 working tree on top of `839c7a2` — target C sources
unchanged, host oracle extended as described below — with ops under a
scratch directory).

## Verify (no SDK, no network)

```
python evidence/t10-causal-live-dossier/verify_causal.py
```

Exit 0 when: the pack verifies, the dossier seal recomputes, the live op
is the pack's COMPLETED `qnx_verified` op, and each grounded
hypothesis's transcript hash equals the pack transcript. Any edit to the
dossier or to a pack transcript exits 2.

## What "grounded present" means (read before citing)

- It means the hypothesis's **mechanism check ran and passed on QNX**
  in this op (e.g. H-estop → `estop_target`: DENY ESTOP state=3 →
  operator reset → ALLOW). It corroborates the mechanism natively.
- Verdicts (SUPPORTED / INCONCLUSIVE) still come from the host
  reproduction of the incident pattern; a passing native check never
  upgrades a verdict. H-crash, H-stalebin and H-seq stay INCONCLUSIVE
  although their native checks passed: their host experiment did not
  reproduce the incident.
- H-jam and H-stale-sensor have no native injector: host only.
- QEMU x86_64 only; no physical hardware; hash-sealed, not signed.
- Before T10 the oracle refused industrial-cell probe predictions, so
  this run first failed 15/16 (`limits_differ`, fail-closed by design);
  T10 extended the oracle after pinning that the cell compiles the
  shared guard sources (`tests/unit/test_cell_oracle_support.py`), and
  the cell guard matched every prediction for its 1.2 m/s contract.
