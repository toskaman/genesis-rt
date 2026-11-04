# AMR demo — differential-drive robot (simulated)

Golden-path example: a virtual mobile robot with a 10 ms control period,
1.2 m/s speed limit and a 100 ms proximity freshness contract.

```sh
genesis-rt validate examples/amr-demo/machine-ir.json
genesis-rt faults examples/amr-demo/machine-ir.json
genesis-rt demo   # full pipeline, writes artifacts/runs/<id>/passport.json
```

Expected host result: 8/8 scenarios pass, gate PASS, `qnx_verified: false`
until the generated build is compiled and executed on a real QNX 8.0
target (see `docs/quickstart-qnx8-qemu.md`).
