# OMEGA7 Demo Script — Causal Slice (copy-paste)

Prereqs: repo checkout, Python env, no SDK/QEMU needed for the
archived path. All commands from the repo root.

## 1. Reproduce the incident (one command)

```
genesis-rt causal-repro --incident examples/causal-demo/estop-cell-transfer.json --json
```

Expect: exit 0, `winning_hypothesis: H-estop`, five
INCONCLUSIVE with per-hypothesis reasons, seal present.

## 2. Inspect the dossier

```
cat artifacts/dossiers/inc-estop-cell-01/dossier.json
ls artifacts/dossiers/inc-estop-cell-01/   # dossier.json + before-ir.json
```

## 3. Prove the fix (same experiment, K1 legs)

```
genesis-rt causal-fix --dossier artifacts/dossiers/inc-estop-cell-01 --after-ir examples/cell-demo/cell-ir.json
```

Expect: exit 0, fix verdict PASS, `supersedes` set to prior seal.

## 4. Verify independently + tamper refusal

```
python -c "from host.genesis_rt.causal_run import verify_dossier; print(verify_dossier('artifacts/dossiers/inc-estop-cell-01/dossier.json'))"
```

Expect `valid: True`. Then flip one verdict byte in a COPY and
re-run: expect `valid: False` with a seal-mismatch error.

## 5. Studio one-click

Serve (`genesis-rt serve`), open Studio → Guided demo → Next ×7
→ stage H → run. Winner/verdicts/seal render inline; full proof
in the API response.

## 6. Reset

```
rm -rf artifacts/dossiers/inc-estop-cell-01 artifacts/runs/inc-estop-cell-01-* artifacts/change/inc-estop-cell-01-*
```

## Live-target variant (owner QEMU only)

Boot the image, export the session, then add `--target live`
to step 1. Grounding records op id + terminal state; without a
reachable target it reports `start-failed` honestly — never a
fake native run.
