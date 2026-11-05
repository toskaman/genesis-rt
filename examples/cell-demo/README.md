# GENESIS CELL demo

A failure-resilient virtual production line: an AMR drives to a
transfer station, a presence sensor + belt interlock gates the
transfer, and an e-stop freezes both legs. Simulation only.

Run it:

```sh
PYTHONPATH=host python -m genesis_rt.cli validate examples/cell-demo/cell-ir.json
PYTHONPATH=host python -m genesis_rt.cli faults examples/cell-demo/cell-ir.json
```

## Broken vs fixed (Demo C)

`cell-ir-broken.json` differs by exactly one line: the speed limit is
`0.3 m/s`, below the `0.5 m/s` the controller commands, so the guard
denies every command and 3 of 4 fault scenarios fail. The fix restores
`1.2 m/s`. Both runs produce passports; `compare` shows the causal
chain — contract knob, regenerated C, fixed scenarios, verdict move:

```sh
PYTHONPATH=host python -m genesis_rt.cli demo --ir examples/cell-demo/cell-ir-broken.json
# verdict: FAIL  level: NONE
PYTHONPATH=host python -m genesis_rt.cli demo --ir examples/cell-demo/cell-ir.json
# verdict: PASS  level: QNX_COMPILED (host build; add --target-record +
# --perf-record for the QNX tiers, see docs/quickstart-qnx8-qemu.md)
PYTHONPATH=host python -m genesis_rt.cli compare artifacts/runs/<broken> artifacts/runs/<fixed>
# contract limits changed: max_linear_speed_mps: 0.3 -> 1.2
# fixed: ['cell_nominal_transfer', 'cell_stale_presence', 'cell_transfer_jam']
# verdict changed: True
```

Load the two passports in the Studio Diff tab (`ui/studio.html`)
for the same delta in the browser. Same flow over the local API:
`POST /runs` twice, then `POST /compare` with the two run ids.
