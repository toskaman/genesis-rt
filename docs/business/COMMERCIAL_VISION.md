# GENESIS RT — Commercial Vision

> Status: hackathon prototype (Apache-2.0), QEMU/QNX 8.0 only, no
> safety certification. This document describes where the product could
> go, not where it is. Every capability claim below points at shipped,
> tested behavior; every market claim is labeled as hypothesis until
> validated with real teams.

## 1. Target user and core problem

**User:** the embedded software engineer (or 3–10 person team) building
a prototype controller on QNX — robotics, factory automation, medical
devices, test benches — who today hand-writes IPC glue, hand-runs fault
checks, and hand-assembles evidence for design reviews.

**Problem:** going from "the machine must never do X" to "here is the
QNX software, the fault campaign, and the proof it behaved" takes weeks
of repetitive, error-prone work: message-passing scaffolding, guard
logic, supervision, fault injection, log archaeology, and review decks
that rot the day after they are written.

**GENESIS RT's answer:** a typed machine contract compiles to native
QNX software *plus* its fault campaign *plus* an inspectable evidence
passport. Verified today: contract → validated IR → generated C →
`qcc` build (0 warnings) → on-target 16-step matrix → replayable
passport (full host suite green — run `pytest -o addopts=""` for the current count; on-target evidence labeled
`QNX_PERFORMANCE_MEASURED`, never faked).

## 2. What a team gets on day one (measured, not promised)

- A new engineer goes from contract to a running native QNX IPC chain
  in ~45 minutes following `docs/codelab/README.md` (every command
  verified 2026-11-05; Windows + Linux variants).
- 8 fault scenarios per machine run identically on host (Python mirror)
  and as conformance vectors against the shipped C policy — the guard
  you test is the guard you ship.
- The counterfactual workflow (`compare` + Studio Compare Workspace)
  shows broken-vs-fixed side by side: contract diff, C diff, behavior
  delta, passport delta.
- Scheduling experiments (`qnx_target.py sched`, 4 configs × 200
  samples measured) and the 16-step target matrix are one command each.
- Productivity benchmark (2026-11-06, `bench/productivity/`): six
  engineering tasks take 8 GENESIS commands vs 30 reference commands
  + 10 manual steps, catch 5/5 injected faults vs 3/5 (methodology v2, competent stock-jsonschema validate reference), and re-run
  with identical semantic summaries. Reference workflows are
  synthetic and labeled;
  no human labor savings are estimated, no pilot claimed.
- Existing QNX projects get stale-binary detection without rewriting
  anything: `external-write-manifest` hashes a build directory,
  `external-check` reports per-binary MATCH/MISMATCH/ABSENT
  (`examples/external-demo/README.md`, verified 8 Nov 2026 on real
  qcc output). Imported test verdicts are counted as UNVERIFIED_CLAIM
  only — they never gate anything and never grant eligibility.

## 3. Use cases

1. **Prototype acceleration** — stand up a testable QNX controller
   from a contract instead of hand-wiring IPC + supervision.
2. **Policy validation** — change a limit or transition, recompile,
   watch the target behavior change (Test A–E methodology).
3. **Fault-campaign automation** — seeded, replayable scenarios with
   oracles that can genuinely fail (mutation-checked).
4. **Change traceability** — every behavior delta links IR digest →
   source digest → toolchain → binary digest → target record → verdict.
5. **Regression analysis** — perf baselines with percentiles and raw
   series; scheduling comparisons with execution context attached.
6. **CI integration** — host CI today (GitHub Actions); target stages
   via self-hosted runners with an SDK (never claimed on public
   runners).
7. **Evidence dossiers** — passports a reviewer can replay offline
   with `scripts/replay.py`, including tamper-detection controls.
8. **Pre-hardware demos** — customer/partner demos on QEMU with honest
   labeling of what is simulated vs. measured.

## 4. Landscape: actually-identified alternatives

No head-to-head benchmark was run; the table below positions by
category, not by superiority. Each tool below is strong in its lane.

| Need | Incumbent / alternative | GENESIS RT position |
|---|---|---|
| QNX IPC scaffolding | Hand-written Momentics/QNX Tool Suite projects | Generates guard + controller + device + supervisor from one contract |
| Model-based codegen | MATLAB/Simulink + Embedded Coder, SCADE, IBM Rhapsody | Lighter, text-first IR; evidence-first rather than certification-first |
| Safety RTOS frameworks | Apex.OS (ROS 2-based), Elektrobit, Vector MICROSAR | Complementary: GENESIS RT targets the prototype/validation loop, not the certified stack |
| Static analysis | Helix QAC, Coverity, Parasoft C/C++test, LDRA | Complementary: analyzes code; GENESIS RT proves executed behavior |
| Requirements traceability | Jama, Polarion, Codebeamer | Artifact-level digest chain instead of document links |
| Fault injection | Hand scripts, CANoe fault setups | Seeded campaigns with oracles + replay |
| CI for embedded | Jenkins, GitLab + custom target farms | Host/target split honestly separated; target stages need customer runners |

**Differentiator (the one-line claim):** GENESIS RT doesn't merely
generate code — it generates independently replayable evidence about
the behavior of the code. None of the tools above ship a
contract→target→replay loop in one Apache-2.0 package.

Deep dive (Wave 9 §17): `COMPETITIVE_LANDSCAPE.md` — sourced
vendor notes, 10-dimension matrix, buyer personas, integration
roadmap, pricing hypotheses, pilot-partner criteria, PMF risks.

## 5. QNX advantage

- The product exercises what makes QNX QNX: microkernel message
  passing (`MsgSend`/`MsgReceive`/`MsgReply`), `name_attach` services,
  resource-manager telemetry (`/dev/genesis/status`), SCHED_FIFO/RR
  experimentation, and process supervision — all demonstrated on QNX
  SDP 8.0 (QSTI image, QEMU x86_64).
- The guard/policy split maps naturally onto QNX process isolation:
  a crashed device or controller cannot corrupt the guard's decisions
  (proven by the crash-containment matrix steps).
- Roadmap leverage: HAM integration if/when available on the target
  image, adaptive-partition measurements, on-hardware determinism
  campaigns — each a credible enterprise feature, each gated on real
  measurement, none claimed today.

## 6. Hypotheses to validate (with real teams, post-hackathon)

1. Teams will write/keep a typed contract if the compiler loop is
   under a minute (today: validate+generate is seconds; full target
   matrix is minutes — measure with pilot teams).
2. Evidence passports shorten design reviews (target: review prep from
   days to hours; unmeasured — needs 2–3 pilot reviews).
3. The keyword planner + eval set is a sufficient on-ramp vs. a real
   LLM provider (provider seam exists; no LLM bundled by design).
4. Target-stage CI via customer runners is acceptable (public runners
   can't hold the SDK — a structural constraint, not a bug).
5. Industrial-cell multi-machine specs generalize beyond the demo cell
   (needs a second, customer-shaped cell).

## 7. Adoption obstacles (honest)

- **Prototype maturity:** a 1292-test host suite (Omega2 SDK-free: 1286 passed + 6 honest skips; with the SDK the 6 SDK-gated tests also run) and a 16-step matrix are strong
  for a hackathon, thin for production. Needs hardening sprints,
  fuzzing depth, and long-session robustness.
- **QNX licensing:** see §9 — customers need their own commercial QNX
  terms; GENESIS RT cannot bundle the OS or toolchain.
- **No certification story:** the evidence chain helps *prepare*
  qualification material but claims no standard compliance (ISO 26262,
  IEC 61508, 62304). Saying otherwise would be disqualifying.
- **Single-target heritage:** QEMU x86_64 only; ARM BSPs and real
  hardware timing are unmeasured work items.
- **Small IR surface:** v1 + v2 cover three machine kinds + one cell;
  real plants need bigger vocabularies (extensible by design, not yet
  extended).

## 8. Business model options (to be tested, not chosen)

1. **Open core (recommended):** Apache-2.0 compiler + fault lab +
   passport format free forever; paid Studio Cloud (shared evidence
   vault, review workflows, regression dashboards, SSO).
2. **Support contracts:** SLA support + hardening sprints for teams
   adopting the open core in pilot programs.
3. **Qualification assistance:** services helping customers turn
   passports into qualification evidence packs (explicitly *assistance*,
   never a certification claim).
4. **Target-farm appliance/CI:** managed runners with licensed QNX
   toolchains for the target stages (heaviest option; partner-dependent).

Support-cost drivers: QNX version skew (SDP 7.x vs 8.x), BSP-specific
target bring-up, customer IR-vocabulary extensions, and evidence
retention at scale (retention policy ships; petabyte scale does not).

## 9. Licensing and dependencies

- GENESIS RT itself: **Apache-2.0** (see `LICENSE`). Host deps are
  standard PyPI packages (see `pyproject.toml`); no GPL contamination
  in the shipped path (audit in `docs/jury/COMPLIANCE.md`).
- **QNX Everywhere (non-commercial) SDK terms do not authorize
  commercial use of QNX itself.** Any commercial deployment of
  GENESIS RT-generated software on QNX requires the customer's own
  commercial QNX license terms with BlackBerry QNX. This document
  assumes that from day one; nothing here suggests otherwise.
- No QNX headers, binaries, images, or license keys are in this repo
  or in any published artifact (CI enforces proprietary-file and
  secret scans).

## 10. Industrial roadmap (post-hackathon, gated on measurement)

1. **Harden:** fuzzing depth, long-session robustness, second
   customer-shaped cell, ARM/QEMU + one real board campaign.
2. **Prove value:** 2–3 pilot teams, measured review-prep time,
   published (anonymized) before/after numbers.
3. **Productize:** Studio Cloud MVP (vault + reviews + dashboards),
   target-runner reference deployment, vocabulary extension packs.
4. **Partner:** QNX partner ecosystem engagement for toolchain/BSP
   coverage and HAM/adaptive-partition features.

Timed overlay (each gate must pass before the next starts):

- **Days 1–30:** hardening sprint (fuzzing depth, long-session
  robustness) + first pilot-invitation round. Success = suite green
  on a second host class + one team running the kit.
- **Days 31–60:** pilot execution + measured review-prep time.
  Success = `PAIRED_PILOT_LIMITED` or better with published
  anonymized numbers (never generalized).
- **Days 61–90:** packaging (target-runner reference deployment,
  one vocabulary extension pack) + partner conversations.
  Success = a second pilot team signed or a scoped hardening
  contract.

## 11. The pitch (60 seconds, for a QNX engineering lead)

> "Your team writes a one-page machine contract. GENESIS RT compiles it
> to native QNX software — guard, controller, supervision included —
> runs the fault campaign on your target, and hands you a passport
> that proves what happened, replayable offline by any reviewer.
> Change a limit, recompile, and the target behavior changes the same
> day — with the before/after evidence side by side. It's Apache-2.0,
> it runs on your QNX license, and the 45-minute codelab takes your
> new hire from zero to a running IPC chain. The prototype is QEMU-only
> and uncertified — we're here to harden it with two pilot teams, not
> to oversell it."

## 12. What success looks like in 12 months

A QNX engineer at a pilot customer says *"I wish I had this tool"* —
then opens a passport from last quarter's campaign, replays it, and
trusts the verdict. Everything else is commentary.

