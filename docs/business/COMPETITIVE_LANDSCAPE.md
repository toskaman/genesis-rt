# Competitive landscape & buyer analysis (Wave 9 §17; F9 reaudit Wave 10 Sprint D)

Date: 2026-11-05 (reaudit). Method: public vendor/product
documentation reviewed this week (sources inline); no vendor
briefings, no trials, no head-to-head benchmark.

Evidence grades used below: [verified] = demonstrated in this
repo (`docs/audits/WAVE10_BASELINE.md` + public evidence pack
`evidence/qnx8-x86_64-verified-b22cea1/`); [vendor-doc] =
vendor's own public documentation (§1 sources); [assessment] =
analyst inference from those docs, not vendor-stated;
[hypothesis] = unmeasured belief, kept OUT of the matrix and
labeled as such. No customers, partners, or market figures are
claimed — see §8 "pilot partner criteria".

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
Strength: certified flows, huge installed base [vendor-doc].
Assessment: the enterprise sales motion and process weight fit
large programs better than small-team prototype loops — but no
pricing or onboarding study was conducted, so that stays a
hypothesis. Observed gap [assessment]: verification evidence
lives in process documents, not in replayable execution
artifacts.

**Embedded verification & static analysis.** Parasoft
C/C++test (static analysis + unit + coverage + compliance),
LDRA tool suite, VectorCAST (unit/integration/system
automation incl. fault injection, with stated QNX support),
Qt Coco (coverage with QNX/Green Hills toolchain support and
ISO 26262/DO-178C qualification kits) ([Parasoft overview](https://www.parasoft.com/blog/best-unit-testing-tools-embedded-software/),
[VectorCAST comparison](https://slashdot.org/software/comparison/LDRA-Tool-Suite-vs-VectorCAST/)).
Strength: qualification kits, coverage rigor, CI integration
[vendor-doc]. Assessment — limited to the public docs reviewed;
adjacent vendor features may exist and were not evaluated:
none of the reviewed products generate the system under test
from a machine contract, nor bind target transcripts to source
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
Strength: process compliance at enterprise scale [vendor-doc].
Assessment: links are documentary; none of the reviewed docs
describe re-executing verification when a requirement changes.

## 2. Dimension matrix (graded; hypotheses excluded)

Y = ships it, P = partial, — = not its job. The GENESIS RT
column is [verified]; the Grade column rates the vendor cells.
Learning curve, cost, and integration burden were REMOVED from
this matrix by the F9 reaudit (no common methodology, no
measurements) — see §4 for the honest, unlabeled version.

| Dimension | GENESIS RT | QNX Tool Suite | Simulink/ECoder | VectorCAST/Coco | Jama/Codebeamer/Polarion | RapiTime | Grade (vendor cells) |
|---|---|---|---|---|---|---|---|
| Native QNX generation | Y | — (hand-written) | P (generic C) | — | — | — | vendor-doc |
| Safety contract expressiveness | P (IR limits+guards) | — | Y | — | P (text reqs) | — | vendor-doc |
| Automated fault testing | Y (seeded+oracles) | — | P (SIL) | Y | — | — | vendor-doc; SIL cell assessment |
| Reproducible evidence | Y (passport+replay) | P (logs) | P (reports) | Y (reports) | P (records) | Y (reports) | assessment |
| Causal change analysis | Y (impact+retest) | — | — | — | P (suspect links) | — | assessment |
| Target provenance | Y (build-set binding) | — | — | P | — | P (config) | assessment |
| Team workflow | P (local API+files, single-user) | P | Y | Y | Y | P | vendor-doc |

Honest reading: incumbents win on qualification, scale,
and depth in their lane; GENESIS RT's edge is the integrated
contract→native-target→replay loop at zero license cost
(Apache-2.0, `LICENSE`), aimed at the prototype/validation
loop rather than the certified stack (consistent with
`COMMERCIAL_VISION.md` §4). GENESIS RT builds on top of the
QNX Tool Suite (same `qcc` toolchain, same targets) — it is
positioned as complementary, not as a replacement for mature
certification platforms.

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

## 4. Cost, onboarding, integration: hypotheses, not measurements

The F9 reaudit removed the Learning curve / Cost model /
Integration burden matrix rows: no common methodology, no
measurements. What is actually known:

- GENESIS RT core is Apache-2.0 (`LICENSE`) [verified];
  the products above are sold commercially (assessment from
  their sales pages — no pricing page was reviewed, so no
  figures are cited here).
- A GENESIS RT onboarding path exists (two codelabs, Judge
  Mode, host-only quickstart) [verified]; how long it takes
  a new team is unmeasured (hypothesis, untested).
- The integration surface is CLI/API/files with no server to
  deploy [verified]; comparative integration effort against
  the products above is unmeasured (hypothesis).

## 5. Adoption obstacles (honest)

1. Single-user local tool: no teams, no roles, no shared
   review queue — an adopting team must bridge that gap.
2. A QNX SDP license + target setup are still required for
   the native loop (host-only mode works without them).
3. One flagship scenario (AMR/conveyor cell); buyers outside
   that shape must validate generality themselves.
4. No qualification kits, no certified-toolchain story —
   disqualified wherever process certification is mandatory.
5. The evidence format is new to reviewers; passport/replay
   literacy is a real onboarding cost.

## 6. Integration roadmap (gated on measurement)

1. CI lane: passport verify + impact retest as pipeline
   steps (builds on the existing verifier, no new format).
2. ALM links: export requirement→evidence edges to the
   buyer's tracker (one-way push first; no live sync).
3. Target farm: queue native ops across shared QEMU/HW
   targets (needs the single-op lease generalized).
Each step ships only with a documented pilot measurement
(`pilot-study.md` templates); no step is pre-sold above.

## 7. Pricing hypotheses (no numbers — none are measured)

No prices are set and no willingness-to-pay study exists.
Candidate models to test with real teams:

- Open core (Apache-2.0) + paid team server (shared
  evidence, review queues, retention policy).
- Paid target-farm hours (managed QEMU/HW capacity).
- Qualification-assistance services (evidence packaging
  for audits — explicitly NOT certification itself).
Choosing between these requires pilot data (§8 criteria).

## 8. Pilot partner criteria (no partners claimed)

A useful pilot team: 3+ embedded devs, ships on QNX or
evaluating it, owns a regression loop that hurts today,
can spare one engineer for two half-days, and agrees to
the anonymized measurement protocol in `pilot-study.md`.
Zero teams recruited so far; recruitment starts from the
technical invitation in the pilot kit, not before.

## 9. Product-market-fit risks

- Teams may value IDE/debugger integration over evidence
  depth (Momentics/VS Code own the daily loop).
- Passport/replay may read as audit theater unless a
  reviewer actually replays one during the pilot.
- If native setup (SDP+QEMU/HW) takes a day, the trial
  dies before the value appears — the host-only first
  run must carry the demo.
- Single scenario + single user risks a "hackathon toy"
  perception; the second scenario and the team story are
  the antidotes, in that order.

## Repair note (2026-11-05, Wave 10 Sprint D)

Commit `37acc81` carried this file truncated (sections after
the personas never reached git). The F9 reaudit above
rewrites the missing analysis (§§4–9) from scratch; nothing
is presented as recovered original text.