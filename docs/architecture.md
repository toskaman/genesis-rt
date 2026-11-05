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
               [Deterministic Codegen]    codegen.py / codegen_v2.py + templates/
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
  evidence → gate`), bounded, cancellable by timeout. Local-first. CLI and
  pipeline dispatch v1/v2 through strict per-version loaders (`_load_any_ir`);
  v2 is never reinterpreted as v1.
- **Machine IR**: versioned JSON Schema (`schemas/`); normalized units and
  fixed enumerations; rejects unbounded/unrecognized features. Host Fault Lab
  enforces the numeric guard contract (period, speed limits, freshness) for
  v1 and v2 equally; state-machine transitions are verified on-target
  (`v2_transitions` matrix step), not in the host mirror.
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
- **Jobs API**: `POST /jobs` submits to a bounded pool (2 workers) and
  returns 202; `GET /jobs/{id}` polls, `GET .../events` streams SSE
  (job_id + ordered seq, reconnect-safe), `DELETE` cancels via the
  orchestrator checkpoints. `POST /runs` stays a sync facade with an
  unchanged response shape. Loopback-only, foreign-Origin writes 403.
  Cancelled/failed/crashed/interrupted jobs never carry a verdict.
- **Studio Live** (`ui/studio.html` + `/projects`, `/validate`,
  `/examples`, `/env`, `/jobs/.../files`, `/runs/.../passport/raw`,
  `/graphs`, `/graphs/compare`):
  projects are server-side IR revisions under git-ignored
  `artifacts/studio/projects` (validated, atomic writes, capped
  history); the Designer edits JSON against authoritative backend
  validation with a read-only v2 state graph; the Pipeline tab streams
  the same job events the API exposes and opens byte-exact passports
  so the browser re-verifies the literal hash chain. Static
  file-inspection tabs work with no backend.
- **Evidence Graph** (`host/genesis_rt/evidence_graph.py`): folds one
  hash-verified passport (+ optional IR for `verification.requirements`)
  into typed `{nodes, edges}` — requirement → IR → limit/file →
  build → binary → target/process/check → scenario → oracle →
  trace → verdict. No invented edges: missing links render as
  `missing`/`unverified`; tampered or version-unknown passports raise
  `InvalidPassport` (HTTP 409), oversize input `GraphTooLarge`
  (HTTP 400). `compare_graphs` diffs two graphs by node id with
  bounded field diffs. `graph` CLI subcommand renders text/JSON.
  Browsers POST the raw passport text (never a re-serialized object:
  JS turns `1.0` into `1`, which breaks the chain) — the API accepts
  the passport as a dict or as raw JSON text.
- **Requirements-to-Release** (`host/genesis_rt/impact.py`): compares
  two validated IR revisions (precise requirement→scenario mapping;
  conservative global retest for limits/control/machine/contracts;
  fail-closed on unclassified digest moves; generated files
  reported, never scope triggers) and checks one run passport
  against the after-revision (`release_status`: chain finding vs
  rejection, current/stale evidence, retested/pending sets, binary
  change via an optional base passport). Targeted retest is rapid
  feedback only — the full gate still decides release eligibility.
  Served by the `impact` CLI, `POST /impact`, `POST /impact/release`
  and `GET /projects/{pid}/impact`; Studio renders project impact,
  retest banners and the Evidence release check.
- **IR numeric canonicalization** (`ir.py`, `ir_v2.py`): validators
  store float-semantic fields as float and collapse integral floats
  to int, so a JSON round-trip through a float-unaware producer
  (JS `1.0`→`1`) cannot move `ir_sha256`. Fractional values are
  never truncated; v1 strict-int fields reject floats as before.
  Existing example digests are pinned unchanged by history-lock
  tests (`tests/unit/test_ir_canonical_numbers.py`).

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
