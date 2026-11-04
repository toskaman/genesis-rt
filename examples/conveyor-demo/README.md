# Conveyor demo — second machine profile (simulated)

Proves the IR/codegen/runtime contracts generalize beyond the AMR: same
schema, same guard policy, same evidence pipeline, different machine.

```sh
genesis-rt validate examples/conveyor-demo/machine-ir.json
genesis-rt faults examples/conveyor-demo/machine-ir.json
```

Note: the host kinematic simulator models differential drive; conveyor
fault scenarios exercise guard + oracle logic with the conveyor's own
limits (20 ms period, 2.0 m/s). A belt-specific visual twin is roadmap.
