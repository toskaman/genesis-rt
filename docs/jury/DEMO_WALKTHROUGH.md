# Demo walkthrough (judge copy)

Three reproducible paths from a clean clone. Host-only unless marked
`[target]` (needs SDK + QEMU per `docs/quickstart-qnx8-qemu.md`).
All outputs below were recorded 2026-11-05.

## Demo A — Compile a machine (2 min, host)

Intent → validated IR → generated C → real `qcc` build record (or an
honest `blocked` record without an SDK) → fault campaign → passport:

```sh
PYTHONPATH=host python scripts/run_verified_demo.py
# {"run_id": "run-<hex>", "verdict": "PASS", "qnx_verified": false, ...}
PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json
# chain: valid ... gate: PASS (qnx_verified=False)
```

What to look at: `verdict: PASS` comes with a passport whose every
record replays offline. Open `ui/dashboard.html`, load the passport —
each verdict links to its scenario data. `qnx_verified: false` is the
honesty label: host evidence, not target evidence.

## Demo B — Break the factory (5 min, host + [target])

The industrial cell (`examples/cell-demo/`): an AMR drives to a
transfer station, a presence + belt interlock gates the transfer, an
e-stop freezes both legs.

```sh
PYTHONPATH=host python -m genesis_rt.cli faults examples/cell-demo/cell-ir.json
# 4/4 scenarios passed (nominal, stale presence, jam, estop)
```

`[target]` The same interlocks run natively: the 16-step matrix ends
with `cell_policy` (`CELL_POLICY: PASS 12/12` from
`genesis_cellcheck`), and the crash steps prove containment — kill the
controller mid-stream and the device + guard logs freeze within ≤3
lines (`NONGUARD=0`, guard survives); kill the guard and the client's
`MsgSend` fails instead of silently succeeding. Transcripts from the
author run are replayable via `scripts/replay.py --transcripts-dir`.

What to look at: faults are injected, not scripted — the oracles fail
for real on the broken revision (see Demo C), and the guard's DENY
reasons (`SPEED_OVER_LIMIT`, `STALE_SEQ`, `ESTOP`, …) are
machine-readable in every log.

## Demo C — Prove the fix (3 min, host)

One-line contract change, full causal chain. `cell-ir-broken.json`
sets `max_linear_speed_mps: 0.3`, below the 0.5 the controller
commands, so the guard denies everything:

```sh
PYTHONPATH=host python -m genesis_rt.cli demo --ir examples/cell-demo/cell-ir-broken.json
# verdict: FAIL  level: NONE  (3 scenarios fail)
PYTHONPATH=host python -m genesis_rt.cli demo --ir examples/cell-demo/cell-ir.json
# verdict: PASS  level: QNX_COMPILED
PYTHONPATH=host python -m genesis_rt.cli compare artifacts/runs/<broken> artifacts/runs/<fixed>
# contract limits changed: max_linear_speed_mps: 0.3 -> 1.2
# fixed: ['cell_nominal_transfer', 'cell_stale_presence', 'cell_transfer_jam']
# verdict changed: True
```

What to look at: `compare` shows the contract knob, the regenerated C
files, the changed binary hashes, and the fixed scenarios side by
side — this is the difference between GENESIS RT and a code
generator. Same delta in the Studio Diff tab (`ui/studio.html`) and
over the local API (`POST /runs` twice, then `POST /compare`).

## If something fails

- `qcc: not found` → SDK env not sourced in that shell; host path
  still works, QNX steps report `blocked`, never pass.
- `STALE_SEQ` denies → two controllers share one guard; `slay` the
  extra chain (codelab troubleshooting table).
- Anything else → `docs/codelab/README.md` troubleshooting, or
  `KNOWN_LIMITATIONS.md` for what is genuinely not supported.
