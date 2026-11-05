# Competitive landscape & buyer analysis (Wave 9 §17)

Date: 2026-11-05. Method: public vendor/product documentation
reviewed this week (sources inline); no vendor briefings, no
trials, no head-to-head benchmark. Positioning claims are
assessments against GENESIS RT's verified capabilities
(`docs/audits/WAVE9_BASELINE.md` + `TASK4_FORMAL_CAMPAIGN.md`),
not measured superiority. No customers, partners, or market
figures are claimed — see "pilot partner criteria".

## 1. Categories and identified players

**QNX-native development.** QNX SDP 8.0 ships the QNX Tool
Suite: Momentics Eclipse IDE, Toolkit for VS Code, and
command-line profiling/debugging tools ([QNX SDP 8.0 page](https://dev-blackberry-qnx.adobecqms.net/en/products/foundation-software/qnx-software-development-platform)).
These are the default, vendor-supported path for writing and
debugging QNX software. GENESIS RT does not replace them: it
generates `qcc` projects and runs on QNX targets they also
serve. Relationship: build on top, never against.

**Model-based code generation.** MATLAB/Simulink + Embedded
Coder generate production C for ECUs with AUTOSAR/ISO 26262
workflows ([MathWorks](https://in.mathworks.com/solutions/embedded-code-generation/production-code-automotive-ecu.html));
SCADE/TargetLink/ASCET serve high-integrity and automotive
codegen ([industry survey](https://www.embitel.com/model-based-design-of-automotive-software-iso-26262-and-autosar-compliant-new)).
Strength: certified flows, huge installed base. Gap they
leave: heavyweight licensing/process for small teams and
prototype loops; evidence lives in process documents, not in
replayable execution artifacts.

**Embedded verification & static analysis.** Parasoft
C/C++test (static analysis + unit + coverage + compliance),
LDRA tool suite, VectorCAST (unit/integration/system
automation incl. fault injection, with stated QNX support),
Qt Coco (coverage with QNX/Green Hills toolchain support and
ISO 26262/DO-178C qualification kits) ([Parasoft overview](https://www.parasoft.com/blog/best-unit-testing-tools-embedded-software/),
[VectorCAST comparison](https://slashdot.org/software/comparison/LDRA-Tool-Suite-vs-VectorCAST/)).
Strength: qualification kits, coverage rigor, CI integration.
Gap they leave: none generate the system under test from a
machine contract, and none bind target transcripts to source
revisions in one replayable file.

**Timing verification.** Rapita RVS/RapiTime: on-target
measurement + hybrid WCET with DO-178/ISO 26262 evidence
and qualification packs ([Rapita](https://www.rapitasystems.com/products/rapitime)).
GENESIS RT measures IPC latency distributions for regression
only and claims no WCET — RapiTime is the tool a team buys
when timing becomes certification evidence. Complementary.

**Requirements traceability / ALM.** Jama Connect (live
traceability, Trace Scores, ISO 26262/ASPICE/21434),
PTC Codebeamer (ALM+DevOps, compliance templates),
Siemens Polarion (ISO 26262/IEC 62304/DO-178C/ASPICE),
IBM DOORS Next ([2026 comparisons](https://hackernoon.com/best-requirement-management-tools-for-automotive-in-2026-8-platforms-reviewed),
[traceability roundup](https://aijourn.com/best-traceability-software-for-2026-7-platforms-compared/)).
Strength: process compliance at enterprise scale. Gap they
leave: links are documentary; nothing re-executes the
verification when a requirement changes.

## 2. Dimension matrix (assessment, not benchmark)

Y = ships it, P = partial, — = not its job.

| Dimension | GENESIS RT | QNX Tool Suite | Simulink/ECoder | VectorCAST/Coco | Jama/Codebeamer/Polarion | RapiTime |
|---|---|---|---|---|---|---|---|
| Native QNX generation | Y | — (hand-written) | P (generic C) | — | — | — |
| Safety contract expressiveness | P (IR limits+guards) | — | Y | — | P (text reqs) | — |
| Automated fault testing | Y (seeded+oracles) | — | P (SIL) | Y | — | — |
| Reproducible evidence | Y (passport+replay) | P (logs) | P (reports) | Y (reports) | P (records) | Y (reports) |
| Causal change analysis | Y (impact+retest) | — | — | — | P (suspect links) | — |
| Target provenance | Y (build-set binding) | — | — | P | — | P (config) |
| Team workflow | — (single local op) | P | Y | Y | Y | P |
| Learning curve | days (codelabs) | weeks | months | weeks | weeks | weeks |
| Cost model | Apache-2.0 core | SDP license | enterprise | enterprise | enterprise | enterprise |
| Integration burden | low (CLI/API/files) | low | high | medium | high | medium |

Honest reading: incumbents win on qualification, scale,
and depth in their lane; GENESIS RT's edge is the integrated
contract→native-target→replay loop at zero license cost,
aimed at the prototype/validation loop rather than the
certified stack (consistent with `COMMERCIAL_VISION.md` §4).

## 3. Buyer personas

1. **Embedded controls engineer (QNX shop, 5–50 devs).**
   Writes IPC services by hand; debugging is printf + Momentics.
   Pain: "did my limit change break the field behavior, and can
   I prove it?" Entry: codelabs → Studio Target tab on their
   own QEMU/HW target.
2. **Verification lead (industrial/automotive supplier).**
   Owns regression + release gates. Pain: target evidence is
   screenshots and logs that rot. Entry: passports + replay +
   impact retest in CI.
3. **Engineering manager evaluating QNX tooling.** Pain:
   onboarding cost and audit preparation. Entry: pilot kit
   (`docs/business/pilot-study.md`), Judge Mode demo.

N
...[truncated 2754 chars]