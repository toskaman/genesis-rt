# GENESIS CELL demo

A failure-resilient virtual production line: an AMR drives to a
transfer station, a presence sensor + belt interlock gates the
transfer, and an e-stop freezes both legs. Simulation only.

Run it:

```sh
PYTHONPATH=host python -m genesis_rt.cli validate examples/cell-demo/cell-ir.json
PYTHONPATH=host python -m genesis_rt.cli faults examples/cell-demo/cell-ir.json
```
