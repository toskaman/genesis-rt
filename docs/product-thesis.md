# Product thesis (one page)

**Problem.** Embedded control prototypes are expensive to integrate and
validate; general-purpose AI code tools produce code without tested timing
or state guarantees, and verification evidence is usually folklore.

**Solution.** GENESIS RT: constrained machine intent → typed Machine IR →
deterministic native QNX codegen → reproducible execution → seeded fault
injection → hash-linked evidence passport + fail-closed release gate.

**Why QNX.** Native synchronous IPC, microkernel isolation, real-time
primitives and process-health frameworks are exactly what a guard-based
controller needs; we make those advantages accessible and visible instead
of hiding behind a POSIX shim.

**Why now.** QNX Everywhere widens developer access; industrial teams want
AI-assisted workflows they can audit. Specification- and evidence-driven
generation is the trustworthy middle path.

**Why it can win.** Coherent end-to-end product, genuine non-trivial
QNX-specific implementation, measurable fault handling, understandable
industrial value. No victory is guaranteed and none is claimed.

**What is real vs roadmap.** Real: IR + validation, deterministic codegen,
native QNX processes + IPC, host fault lab with oracles, evidence passport,
release gate, C/Python conformance, CI. Roadmap: on-target measured runs,
HAM integration, second-device visual twin, full workspace UI, team/cloud
features (only after legal/technical validation and customer discovery).

**Business sketch (not a forecast).** Open-source core + templates; later,
paid collaboration/evidence-retention/audit/support and regulated-domain
extensions subject to QNX commercial licensing. First step: 5–10 serious
customer interviews before any ARR talk.
