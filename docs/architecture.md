# Architecture

```
[Local Web UX / CLI]              ui/dashboard.html, host/genesis_rt/{cli,api}.py
         |
[Host Orchestrator]               host/genesis_rt/orchestrator.py (SQLite WAL in api.py)
         |
 +-------+------------+--------------+
 |                    |              |
[NL Planner]      [Machine IR]  [Scenario Lab]
 planner.py        ir.py +       faultlab.py +
 optional AI       schemas/      simulator.py
         |            |              |
         +--> [VALIDATION / POLICY] <-+   (strict whitelist, fail-closed)
                        |
               [Deterministic Codegen]    codegen.py + templates/
                        |
               [QNX Build Adapter]        build_adapter.py (qcc/q++)
                        |
               [QNX 8.0 Target on QEMU]   target/qnx8/
                        |
          +-------------+-------------+
          |             |             |
     [native IPC]  [Supervisor]  [Device Adapter]
     guard/contr.  supervisor/   device/ + status/
          |             |             |
          +-------------+-------------+
                        |
                [Telemetry + Traces]
                        |
                 [Evidence Engine]        evidence.py (hash-linked passport)
                        |
          [Release Gate / Report / Replay] gate.py, scripts/replay.py
```

## Host (non-real-time)

- **Orchestrator**: one pipeline (`validate → codegen → build → verify →
  evidence → gate`), bounded, cancellable by timeout. Local-first.
- **Machine IR**: versioned JSON Schema (`schemas/`); normalized units and
  fixed enumerations; rejects unbounded/unrecognized features.
- **Planner**: constrained intent → IR *proposals*; deterministic offline
  presets. External LLM providers may plug in later but their output takes
  the same validated path and never generates policy directly.
- **Codegen**: trusted templates + IR → C headers/buildfiles. Byte-identical
  for identical input; provenance (versions + IR hash) embedded in output.
- **Build adapter**: probes `QNX_HOST`/`QNX_TARGET`/`qcc`, invokes builds with
  argv lists, requires exit 0 **and** artifacts on disk. Without an SDK it
  records `blocked` — never success, never silent skip.
- **Simulator**: fixed-step 2D kinematics, seeded noise, corridor + obstacles.
  Clearly labelled simulation; its clocks are never mixed with QNX clocks.
- **Evidence**: hash-chained passport (see `evidence-methodology.md`).

## QNX-native target (all in `target/qnx8/`)

1. `genesis_guard` — command server: `name_attach`, `MsgReceive`, `MsgReply`;
   validates magic/version/size, monotonic seq, deadlines, bounds, transitions.
2. `genesis_controller` — periodic client via `name_open`/`MsgSend`; applies
   only `ALLOW`ed replies; no bypass path to the device exists.
3. `genesis_device` — virtual actuator/sensor state; no physical I/O by design.
4. `genesis_status` — resource manager at `/dev/genesis/status` (read-only).
5. `genesis_supervisor` — spawns/monitors children; sole reset authority out
   of SAFE_STOP (QNX HAM remains an optional deployment complement).
6. `common/guard_policy.*` — the shared pure policy, proven identical to the
   Python mirror by the `guard_vector` conformance harness.

## Hard safety boundary

AI and browser UI are never on the actuation-critical path. The QNX-side
guard holds explicit policy independent of host and simulation. Bad data
latches the virtual device to an application-defined stopped state, is
logged, and is replayable in the Fault Lab. Prototype, not certified.
