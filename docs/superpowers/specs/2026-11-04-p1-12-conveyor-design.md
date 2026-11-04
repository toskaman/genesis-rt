# P1 #12 design: conveyor depth (BeltSim + jam + guard estop)

Autonomous mode: no interactive gates per standing order. This spec
records intent, decomposition, and contracts. Plan:
`docs/superpowers/plans/2026-11-04-p1-12-conveyor.md`.

## Intent

Make the conveyor showcase genuinely distinct from the AMR (§4.3):
belt physics, jam detection with recovery, guard-level emergency stop.
AMR keeps its 8 scenarios; conveyor gets belt-meaningful ones. Nothing
functionally equivalent with renamed constants.

## Decomposition (ship in slices, suite green at each)

- **Slice A (host): BeltSim + jam.** Kind-dispatched sims, `belt_jam`
  scenario + observed-behavior oracle, per-kind planner lists, conveyor
  IR lists updated, sabotage tests. No guard/wire change.
- **Slice B (host + C parity): guard estop.** `estop_engaged` input via
  the wire `reserved[0]` byte (frame size unchanged), `R_ESTOP` deny +
  latch in both mirrors, harness + vectors extended, `estop_pressed`
  scenario on both sims. faultinject stays 9/9 (target estop proof =
  follow-up, recorded).
- **Slice C (target, optional): belt on QNX.** Belt device model +
  conveyor matrix steps. Only after A+B are green and reviewed.

## Contracts

- `MachineSim` protocol (`simulator.py`): `reset(seed)`, `apply(v, w)`,
  `stopped()`, `snapshot()` (motion dict for traces),
  `final_stats()` (oracle dict). DiffDriveSim keeps exact behavior;
  BeltSim: 1D position/speed, `set_jam()` (apply ignored, speed decays
  to 0), no drift while jammed.
- Loop (`faultlab.run_scenario`): sim chosen by
  `ir["machine"]["kind"]` (`conveyor` → BeltSim, else DiffDriveSim).
  Fault mechanics (gaps, seq, magic, deadlines, sensor age) unchanged.
  `belt_jam` window kind drives `set_jam()`; unknown kinds fail loud.
- Jam oracle (observed behavior, §6.4-clean): jam observed (commanded
  motion with ~zero actual during window), zero belt creep while
  jammed, motion resumes post-window, no unvalidated motion. No
  harness-applied stop is counted as success.
- E-stop oracle: every in-window command denied `R_ESTOP`, safe stop
  latched, recovery only after supervisor reset; post-window allows.
- `SCENARIO_IDS` grows (`belt_jam`, then `estop_pressed`); planner
  emits per-kind lists; `run_all` defaults to the IR's list;
  `test_all_scenarios` compares against the IR list (contract
  refinement: "all" = IR-declared).
- Conveyor IR (v1+v2): nominal, speed-over-limit, delayed, belt_jam
  (estop_pressed added in slice B). `stale_proximity_150ms` leaves the
  conveyor lists (AMR-named mechanic; documented in the commit).
- Determinism: same seeds-per-scenario scheme; new scenarios get
  `1000+i` seeds automatically.

## Self-review

- No placeholders; files, ids, and oracle properties fixed above.
- Consistent: v1 pipeline untouched for AMR outputs; additive changes
  plus two justified contract refinements (IR-list comparison,
  conveyor list membership).
- Scope: A then B; C explicitly optional. faultinject 9/9 frozen.
- Ambiguity resolved: jam is sim-level (detection+integrity+
  recovery), estop is guard-level (deny+latch); belt creep = any
  |Δposition| > 1e-6 during full-jam ticks.
