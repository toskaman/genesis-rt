# Adding a machine kind (extension interface)

The bar for a new kind is the flagship bar: validated IR,
deterministic generation, host simulation, fault campaign with
oracles, C policy conformance, native QNX build, evidence
passport, and at least one reproducible counterexample
(`docs/audits/WAVE10_BASELINE.md`, F8). Anything less ships
labeled as a sketch, never as a supported kind.

## Touch-point checklist (in dependency order)

1. **Schema** — `host/genesis_rt/ir.py`: add the kind to
   `MACHINE_KINDS` (~line 20) + a `validate_*` block for its
   kind-specific section (follow `_validate_cell`, ~line 227).
   v2: extend `host/genesis_rt/ir_v2.py`, or reject loudly like
   `industrial_cell` does (never silently drop fields).
2. **Planner hints** — `host/genesis_rt/planner.py`: kind table
   (~line 20), keyword hints (~line 57), scenario list (~line 80).
   Scenarios must be kind-meaningful, not AMR hand-me-downs.
3. **Generation** — `host/genesis_rt/codegen.py` /
   `codegen_v2.py`: kind branch next to `is_cell`
   (`codegen.py:74`); determinism pinned by
   `tests/unit/test_codegen_determinism.py`.
4. **Host physics** — `host/genesis_rt/simulator.py`: a new Sim
   class following the `reset/step/snapshot/final_stats`
   protocol (`DiffDriveSim`, `BeltSim`, `CellSim`).
5. **Fault campaign** — `host/genesis_rt/faultlab.py`:
   scenario IDs + windows + oracles, dispatch in
   `run_scenario`, and a `physics` name for the new sim.
   Scenario records carry `physics` (+ `physics_note` when
   aliased) since Sprint E1 — a silent fallback is a bug.
6. **Guard policy (both sides)** — `host/genesis_rt/guard_policy.py`
   plus `target/qnx8/common/guard_policy.c`, whose check order
   MUST match the Python mirror exactly (see the C header
   comment); conformance vectors in
   `host/genesis_rt/explorer_conformance.py`.
7. **Explorer** — `host/genesis_rt/explorer.py`: kind branches
   next to the `industrial_cell` / `conveyor` ones; bounded
   budget declared, unexplored regions reported.
8. **Twin + Studio** — `host/genesis_rt/twin.py` folds generic
   tracks (confirm your trace keys render); add Studio
   representations in `ui/studio.html` where kind-specific.
9. **Examples** — `examples/<name>/`: valid IR (v1, v2 if
   supported) + broken variants, mirroring the existing demos.
10. **Tests** — unit (validation, oracles), `tests/faults/`,
    C conformance, pipeline/graph integration, and the Judge
    E2E path if the kind is flagship-grade.
11. **Docs** — `docs/machine-ir.md`, `docs/limitations-and-safety.md`,
    and the codelab if flagship-grade.

## Anti-patterns (learned from `robotic_arm_virtual`)

- Schema-accepting a kind with no simulator behind it. The arm
  kind passes validation but runs aliased on the diffdrive
  corridor — disclosed in `docs/limitations-and-safety.md` #10
  and now stamped on every record via `physics_note`.
- Reusing another kind's physics, scenarios, or planner hints
  without saying so in the evidence.
- Claiming target behavior before the C policy + conformance
  vectors exist for the kind.

## Worked sketch (NOT IMPLEMENTED): warehouse sorter

Kind `warehouse_sorter`: stations + routing + zone exclusivity.
New invariants beyond the flagship: at most one carrier per
zone, route reservations released on fault, sort-gate actuation
only while the zone sensor is fresh. Touch points: new `cell`-like
IR block, a `SorterSim` (discrete stations, not corridors), new
scenarios (`zone_conflict`, `route_leak`, `stale_zone_sensor`),
guard rules for exclusivity, C mirror + vectors, explorer
branches. Estimated cost: several days including native campaign
and docs — gated on flagship quality staying intact (§16).

## F8 verdict (Wave 10 Sprint E1)

Second scenario: NOT STARTED. The evaluation above is the
deliverable: the interface is now documented so a team (or a
later wave) can cost and build the sorter without reverse
engineering, and the flagship keeps 100% of the verification
budget until the release gates pass.
