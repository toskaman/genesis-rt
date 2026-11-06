# GENESIS RT — Venture & acquisition thesis (Wave 12 §13)

Status: analysis, 2026-11-06. No revenue, no term sheets, no
acquisition discussions exist or are claimed. This document
states what would have to be true for each path, and what
evidence is still missing. Market grounding:
`docs/business/COMPETITIVE_LANDSCAPE.md` (vendor-doc grades),
`docs/business/COMMERCIAL_VISION.md`; pilot instrumentation:
`docs/business/pilot-study.md` + `bench/productivity/analyze_pilot.py`.

## 1. Market map (where the money already moves)

Adjacent paid categories, per the landscape reaudit:

- **QNX-native development**: QNX Tool Suite (Momentics, VS Code
  toolkit) — the default vendor path. GENESIS RT builds on it
  (same qcc, same targets), never against it.
- **Model-based codegen**: Simulink/Embedded Coder, SCADE —
  certified flows, enterprise sales motion.
- **Embedded verification**: VectorCAST (unit/integration incl.
  fault injection, stated QNX support), LDRA, Parasoft
  C/C++test, Qt Coco (qualification kits). Strength:
  qualification + coverage rigor + CI integration.
- **Timing evidence**: Rapita RapiTime (hybrid WCET with
  qualification packs). Complementary: GENESIS RT claims no WCET.
- **ALM/traceability**: Jama, Codebeamer, Polarion — process
  compliance at scale; links are documentary.

Observed structural gap [assessment, not vendor-stated]: none
of the reviewed products generate the system under test from a
machine contract AND bind target transcripts to source revisions
in one replayable file AND re-execute verification when a
requirement changes. That conjunction — contract→native→replay
at zero license cost — is the commercial wedge, aimed at the
prototype/validation loop, not the certified stack.

## 2. Business-model scenarios (illustrative arithmetic)

Assumptions are stated; numbers are scenarios, not forecasts.

- **A. Open core + team server.** Apache-2.0 core stays free.
  Paid: shared evidence store, review queues, retention policy,
  SSO. Assumption: 5–50-dev QNX shops; illustrative
  $50–150/dev/month *if* pilots show reviewers actually replay
  passports (the PMF risk in landscape §9). Missing: WTP study.
- **B. Managed target capacity.** Paid QEMU/HW hours behind the
  runner reference (`docs/runner/SELF_HOSTED_RUNNER.md`).
  Assumption: teams without a target farm. Illustrative
  $0.50–2.00/native-minute *if* queueing beats local QEMU
  setup. Missing: cost basis, demand signal.
- **C. Qualification assistance (services).** Evidence
  packaging for audits — explicitly NOT certification.
  Assumption: suppliers preparing ASPICE/26262 evidence.
  Illustrative fixed-fee engagements. Missing: first design
  partner; disqualified wherever certification is mandatory
  (landscape §5.4).
- **D. Commercial integrations.** ALM one-way push
  (requirement→evidence edges), CI lane steps. Assumption:
  priced inside A or as add-ons. Missing: buyer tracker
  survey data.

Kill criteria (write down before selling): if 3+ pilots show
reviewers do not replay evidence, A is dead; if native setup
takes >1 day for 2+ teams, B is dead until host-first onboarding
wins; C never promises certification outcomes.

## 3. Strategic buyer hypotheses

Each: fit, overlap, build-vs-buy, integration cost, IP value,
distribution, licensing, maturity bar, why-they-wouldn't.

### 3.1 QNX (BlackBerry)

- **Fit**: GENESIS RT is the missing "prove your change on our
  RTOS" loop for the Tool Suite; drives SDP stickiness.
- **Overlap**: none directly — Momentics/VS Code own authoring
  and debugging; GENESIS owns contract→evidence.
- **Build-vs-buy**: the verification semantics (contract-aware
  oracles, impact retest, replay) are 12+ months of domain
  work; the code is Apache-2.0 visible, so "buy" buys team +
  velocity, not secrecy.
- **Integration cost**: medium — adopt IR schema or bridge to
  their roadmap; Studio is a new surface.
- **IP value**: replay format + impact analysis + before/after
  proof UX; patents unlikely, trade value is in the working
  system + tests.
- **Distribution**: bundled with SDP/Tool Suite trials; codelab
  channel already QNX-shaped.
- **Licensing**: Apache-2.0 core is acquirable; enterprise
  add-ons (A/B) would need clean IP assignment from day one.
- **Maturity bar**: second scenario, team workflow, 2+ external
  pilots with replayed evidence.
- **Why they wouldn't**: single-maintainer risk, QEMU-only
  record, "hackathon toy" perception (landscape §9), or a
  decision that evidence depth belongs to partners (Vector,
  Rapita) rather than the RTOS vendor.

### 3.2 Vector Informatik

- **Fit**: VectorCAST owns test automation with stated QNX
  support; GENESIS adds contract-driven generation + replayable
  target binding upstream of their execution strength.
- **Overlap**: partial — fault injection and CI integration
  exist in VectorCAST; the IR→codegen→impact loop does not.
- **Build-vs-buy**: Vector builds verification depth well; the
  buy case is time-to-QNX-developer-mindshare via an open core.
- **Integration cost**: medium-high — map IR concepts onto
  VectorCAST environments and automotive process expectations.
- **IP value**: impact/retest engine + evidence format as an
  interchange candidate.
- **Distribution**: automotive supplier channel; pilot
  criteria (§8 landscape) match their customer profile.
- **Licensing**: same as 3.1; automotive customers will ask
  about qualification story early — answer is "not certified"
  until kits exist.
- **Maturity bar**: automotive-shaped second scenario,
  requirements round-trip with a real ALM, 3+ supplier pilots.
- **Why they wouldn't**: automotive process weight crushes the
  lightweight loop; core team too small to absorb; preference
  for partner/integration over acquisition.

### 3.3 Siemens Digital Industries Software (Polarion/Codebeamer side)

- **Fit**: ALM owns documentary traceability; GENESIS makes
  links executable (change requirement → re-verify → fresh
  evidence). "Live traceability that re-runs" is the pitch.
- **Overlap**: low — Polarion/Codebeamer do not execute
  verification; GENESIS RT has no ALM process depth.
- **Build-vs-buy**: executing verification on QNX targets is
  far from ALM core competence; buy-or-partner beats build.
- **Integration cost**: high — enterprise ALM process models,
  permissions, and scale expectations vs. a single-user local
  tool today (landscape §5.1).
- **IP value**: the executable-link concept + replay format;
  most value realized as an integration, not a product line.
- **Distribution**: enterprise ALM installed base; slowest
  sales cycle of the three.
- **Licensing**: Apache-2.0 core fits a connector strategy;
  enterprise server (A) would be rebuilt on their stack.
- **Maturity bar**: ALM one-way push shipped + measured,
  team workflow, enterprise security review passed.
- **Why they wouldn't**: slowest path to revenue, biggest
  integration bill, cultural mismatch with a hacker-built
  single-user tool.

### 3.4 Deliberately not pursued now

- **MathWorks/SCADE vendors**: certified codegen giants; the
  wedge (lightweight replay loop) is orthogonal to their
  qualification-led motion. Partner later, not buyer now.
- **Rapita**: complementary timing depth, but acquiring a
  pre-revenue prototype loop adds nothing to a WCET business.
- **Hyperscalers / generic DevOps vendors**: no QNX/embedded
  distribution; the domain gap exceeds the asset value.

## 4. What must happen before any of this is real

1. Two external pilots with replayed evidence (kit is ready:
   `pilot-study.md`, consent, interview, survey, analyzer).
2. Second industrial scenario (warehouse sorting candidate —
   Wave 12 §17, deferred, not started).
3. Team workflow (shared review queue) or an explicit
   single-user positioning with team-server pricing validated.
4. Clean IP: contributor assignments, dependency license audit
   (current: Apache-2.0 + standard OSS test deps).
5. No fabrication, ever: every claim above traces to
   vendor-doc, assessment, or labeled hypothesis per the
   landscape grading discipline.

## 5. One-paragraph thesis

GENESIS RT owns a narrow, demonstrated, open-source loop —
machine contract in, native QNX evidence out, independently
replayable — that incumbents document around but do not ship.
Its commercial future is either an open-core team product for
QNX shops (A, possibly +B) or a strategic capability inside a
verification or ALM portfolio (Vector, QNX, Siemens DIS, in
that order of near-term fit). Both paths require the same
next evidence: external pilots where reviewers actually
replay passports. Until then, this thesis is a plan with
kill criteria, not a valuation.
