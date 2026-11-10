# OMEGA7 Workflow Comparison — Manual vs Causal

## Conventional baseline (10 manual steps,established flow)

1. Read incident. 2. Find logs. 3. Guess cause. 4. Write repro
script. 5. Prepare target. 6. Execute. 7. Capture logs.
8. Compare binaries/runs. 9. Validate repair. 10. Assemble report.

## Causal flow (2 commands, measured)

```
genesis-rt causal-repro --incident <file>   # steps 2–8 automated
genesis-rt causal-fix --dossier <dir> --after-ir <ir>  # steps 9–10
```

Measured on the owner machine, flagship estop incident, cell IR
(n=1, Windows, Python 3.14, SDK present, 10 Nov 2026):

| Phase | Time | Pipelines | Outcome |
|---|---|---|---|
| reproduce (6 hypotheses) | 3.4 s | 4 host legs | H-estop SUPPORTED, 5 INCONCLUSIVE w/ reasons |
| fix (K1 BEFORE/AFTER) | 2.1 s | 2 legs | PASS, dossier resealed |
| incident → proof total | **5.5 s** | 6 | sealed dossier, `verify_dossier` valid |

What the machine time excludes (honest): install/clone/setup,
human reading of the dossier, and any live-target boot
(archived grounding used; live path unexecuted here).

## Human section (NOT MEASURED)

No participants yet — see `docs/research/OMEGA7_USER_STUDY.md`.
Do not cite machine-time deltas as productivity gains. The
template: paired Ns, median task times per lane, correctness,
second-engineer verification time, limitations.
