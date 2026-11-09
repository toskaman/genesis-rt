# GENESIS RT — competitive positioning (v3 research)

> RESEARCH + DOCS ONLY. No contact, no submissions, no media created, no releases/tags,
> no secrets, no history rewrites. Frozen evals untouched
> (`genesis-rt/evals/*.json`, `evals/results/*` — not opened, not cited by value).
> Reader posture on `genesis-rt`: this file lives under `v3-research/` only.
>
> Method: every factual claim reuses a body opened in this session (local docs +
> fetched vendor pages). Search output located candidates only. Labels:
> **VERIFIED FACT** (read in the cited body) / **OBSERVATION** (synthesis, no new
> facts) / **ASSUMPTION** (inference, flagged) with confidence high/med/low.
> No metrics, scores, feedback, or testimonials invented. Competitor fields with
> no inspected source say **UNKNOWN**.

## Label legend + sources opened

Local bodies opened (all read in full window this session):

- `hackathon-knowledge/PORTFOLIO_COMPETITIVE_AUDIT.md` — genesis-rt §P3 (status,
  counts, readiness, license, limits)
- `hackathon-knowledge/REFERENCE_PROJECT_ANALYSIS.md` — transferable principles §1–8
- `genesis-rt/README.md` — pitch, proven claims, AI eval v9 summary, quickstart
- `genesis-rt/docs/CLAIMS.md` — canonical claim registry (tests, native matrix,
  packs, AI ladder, CI, video, limitations, features)
- `genesis-rt/docs/architecture.md` — host/target architecture, evidence engine
- `genesis-rt/docs/limitations-and-safety.md` — 10-item honesty list
- `genesis-rt/docs/jury/START_HERE.md` — 5-minute judge path
- `genesis-rt/docs/jury/WHY_GENESIS_RT.md` — problem/approach/novelty/boundaries
- `genesis-rt/docs/jury/WHY_QNX.md` — QNX-native substance + inconclusive RT result
- `genesis-rt/docs/jury/COMPLIANCE.md` — category, original work, license

Vendor bodies opened (fetched this session, full text grepped from saved fetch):

- QNX Momentics Tool Suite —
  [vendor page](https://get.qnx.com/products/neutrino-rtos/qnx-momentics.html?lang=en)
- Parasoft C/C++test (defense/aero edition page, describes the unified platform) —
  [vendor page](https://www.parasoft.com/products/c-ctest-ppc-mil-aero/)
- VectorCAST platform page —
  [vendor page](https://www.vector.com/en/product/vectorcast/)
- LDRA tool suite page —
  [vendor page](https://ldra.com/products/ldra-tool-suite/)
- QNX Devpost (`https://qnx.devpost.com/`) — fetch **403 Forbidden** this session:
  category wording and submission list are **UNKNOWN** from primary source.
  GENESIS RT's category is known only from its own compliance doc (see §1).

No OSS test-framework body and no adjacent Devpost submission body was opened:
those columns are explicitly UNKNOWN (§6–7).

---

## 1. GENESIS RT baseline (what is being positioned)

- **Category + shape.** Developer Tooling & Host Tools; contract-aware
  change-verification + evidence layer for QNX. VERIFIED FACT (high):
  `docs/jury/COMPLIANCE.md`, `README.md` L8–13.
- **One-liner.** Constrained machine description → typed Machine IR → deterministic
  native QNX 8.0 multi-process controller → seeded fault injection → hash-linked
  evidence passport where every green verdict links to a real trace.
  VERIFIED FACT (high): `README.md` §60-second pitch; PORTFOLIO §P3.
- **Current proof (Omega2, current source).** BEFORE (AMR v1) + AFTER (AMR v2)
  packs, 16/16 PASS sealed on both contracts, stale control 14/16 failing exactly
  on the changed behavior (`estop_target` + `v2_transitions`); offline stdlib-only
  `verify.py`; native IPC timeline; CI IR impact bridge; one-click dossier ZIP.
  VERIFIED FACT (high): `README.md` L29–51, `docs/CLAIMS.md` §Native/§Packs.
- **Scale of the harness.** 1376 collected (1370 passed + 6 honest skips SDK-free);
  24 adversarial passport tests; 28/28 planning eval; 32 real-browser E2E; 16/16
  on-target matrix + 1000 perf samples + 9/9 native fault-injection over IPC.
  VERIFIED FACT (high): `docs/CLAIMS.md` §Test counts/§Native.
- **AI posture.** Blind holdout v9 (160 cases, frozen): offline 142/160, Qwen/Llama
  150/160 each, 5 unsafe accepts of 112 rejects (same 5 deterministic-layer cases
  on all providers), 0 wrong-kind accepts; model proposes, deterministic gate
  disposes. VERIFIED FACT (high): `README.md` L60–71, `docs/CLAIMS.md` §AI.
- **QNX-native substance.** `name_attach`/`MsgReceive`/`MsgReply`/`MsgSend` guard +
  controller, fixed versioned IPC protocol, `/dev/genesis/status` resource manager,
  bounded supervision (3× RESPAWN then GIVE_UP), crash-containment matrix steps,
  `qcc -Vgcc_ntox86_64` 0 warnings. RT-scheduling experiment reported
  **inconclusive** (no speedup claimed). VERIFIED FACT (high):
  `docs/jury/WHY_QNX.md`, `docs/architecture.md` §QNX-native.
- **Honest limits (bounds every comparison below).** QEMU-only (no physical HW, no
  safety cert); host fault campaigns are simulated (`qnx_verified` labels the
  difference); passports hash-only UNSIGNED; STALE control is prose-grade (no
  sealed transcript); no pilots, human benefit unmeasured; video
  `DEFERRED_BY_OWNER`, Devpost unfiled. VERIFIED FACT (high):
  `docs/CLAIMS.md` §Known limitations/§Video, `docs/limitations-and-safety.md`,
  PORTFOLIO §P3.
- **License + reproduce.** Apache-2.0; core stdlib-only; judge path is clone →
  `pip install pytest pyyaml` → two `PYTHONPATH=host python scripts/…` commands →
  `verdict: PASS, chain: valid, gate: PASS` with `qnx_verified: false` on host.
  VERIFIED FACT (high): `COMPLIANCE.md`, `START_HERE.md` §1.
- **Transferable principles it already follows** (OBSERVATION, high — mapped from
  `REFERENCE_PROJECT_ANALYSIS.md` §Transferable): refusal-first (fail-closed gate,
  `no-test => no-pass`); published failures (5 unsafe accepts, inconclusive RT
  result, prose-grade STALE disclosed); measured-vs-estimated separation
  (`qnx_verified`, host/target tiers, metric vocabulary never merged); tiered
  onboarding (SDK-free demo → full suite → QNX SDK path); runnable demo artifacts
  (passport + `replay.py` + `verify.py`, not just video); deterministic verifier
  owns the verdict; public history + green host-CI signal; one ledger
  (`docs/CLAIMS.md` + `facts.py` + consistency tests).

---

## 2. Competitor profiles (only what was read)

### A. QNX Momentics Tool Suite (platform-native IDE + profiler)

- **What it is.** Eclipse-based IDE + command-line tools for building, debugging,
  and optimizing on QNX; C/C++ optimized; project wizards; Git/EGit + other VCS
  via Eclipse plugins. VERIFIED FACT (high): vendor page ("comprehensive,
  Eclipse-based integrated development environment", "optimized environment for C
  and C++ development", "command-line or graphical IDE").
- **Strengths on paper.** System profiler (kernel-trace visualization), application
  profiler, memory analysis, code-coverage tool, multi-core profiling,
  instrumented kernel; unified debugging integrated with the suite. VERIFIED FACT
  (high): vendor page feature list + profiler/coverage paragraphs.
- **What the page does NOT describe.** No contract language, no requirement-change
  verification, no before/after behavioral comparison, no hash-linked evidence
  passport, no fail-closed release gate, no fault-injection campaign with oracles.
  OBSERVATION (high): absent from the fetched body; capability UNKNOWN beyond that
  (absence from one page ≠ absence from the product).
- **Pricing / time-to-value / ease-of-use:** UNKNOWN (no pricing, trial, or
  tutorial body opened).

### B. Parasoft C/C++test + CT + DTP (commercial verification platform)

- **What it is.** All-in-one automated testing for C/C++: static analysis + unit
  testing + code coverage + requirements traceability in a single workflow; CT
  extends coverage/traceability/reporting; DTP adds web dashboards + analytics.
  VERIFIED FACT (high): vendor page ("unifies static analysis, unit testing, code
  coverage, and requirements traceability in a single workflow").
- **Depth signals.** Pattern-based + dataflow + abstract-interpretation analysis;
  MISRA C 2023 / MISRA C++ 2023 / AUTOSAR C++14 / CERT C+C++ / CWE / OWASP;
  TÜV SÜD certification; process standards DO-178C DAL-A, ISO 26262, ISO 21434,
  IEC 62304, IEC 61508, EN 50128; unit tests executable on host/virtual/hardware
  targets. VERIFIED FACT (high): vendor page §§Static Analysis/Unit Testing/
  Functional Safety & Compliance.
- **Evidence/CI story.** DTP traceability between test cases ↔ code ↔ requirements
  in DOORS Next, Polarion, Codebeamer, Jama, Jira; IDE integrations (VS Code,
  Visual Studio, Eclipse); CI/CD pipeline integration; GoogleTest support.
  VERIFIED FACT (high): vendor page (DTP paragraph + integrations paragraph).
- **What the page does NOT describe.** No machine-contract → codegen loop, no
  QNX-IPC-native behavioral oracle, no before/after change proof with stale-binary
  detection, no offline stranger-replayable passport, no published unsafe-accept /
  blind-eval numbers. OBSERVATION (high): absent from the fetched body; otherwise
  UNKNOWN.
- **Pricing / time-to-value / ease-of-use:** UNKNOWN (commercial; no trial body
  opened).

### C. LDRA tool suite (commercial lifecycle verification)

- **What it is.** Integrated critical-embedded suite for validation, verification,
  and requirements traceability; open extensible architecture integrating
  lifecycle traceability + static/dynamic analysis + unit/system-level testing on
  "virtually any host or target platform". VERIFIED FACT (high): vendor page
  lede (exact quote).
- **Depth signals.** Capability catalogue includes requirements traceability,
  structural coverage + requirements-based testing, MC/DC, data/control-flow and
  coupling analysis, unit/integration/system test, WCET, CI/CD/CV, change-impact
  and change-based testing, tool-qualification support; standards DO-178C,
  ISO 26262, MISRA; certification services + mentoring offered. VERIFIED FACT
  (high): vendor page capability/standards lists.
- **Closest overlap to watch.** "Change impact analysis" + "change based testing"
  capabilities are the nearest conceptual neighbor to GENESIS RT's change
  verification — but the fetched body gives no mechanism (no contract semantics,
  no oracle derivation, no before/after transcript comparison), so behavioral
  equivalence is UNKNOWN. OBSERVATION (med).
- **What the page does NOT describe.** No QNX-specific target story on the fetched
  page, no evidence-passport format, no offline replay, no published eval
  failures. OBSERVATION (high): absent from the fetched body; otherwise UNKNOWN.
- **Pricing / time-to-value / ease-of-use:** UNKNOWN.

### D. VectorCAST (commercial embedded test automation)

- **What it is.** Embedded test platform automating unit, integration, and coverage
  testing across the lifecycle for C/C++/Ada safety-critical systems; harnesses,
  regression execution, coverage collection, and certification reporting run
  automatically; test cases produced directly from source. VERIFIED FACT (high):
  vendor page ("automates unit, integration, and coverage testing", "produces test
  cases directly from source code").
- **Depth signals.** Statement/branch/MC-DC coverage built-in with project+unit
  views; qualification/validation packages for DO-178B/C, IEC 61508, ISO 26262,
  EN 50716, IEC 62304 incl. TÜV SÜD certificates; requirements traceability +
  regression + coverage reporting; VectorCAST/QA for CI trending. VERIFIED FACT
  (high): vendor page §§Advantages/Products/standards.
- **Workflow fit.** Jenkins, VS Code, Simulink, 80+ compilers, native GoogleTest
  (existing suites come across without rewriting). VERIFIED FACT (high):
  vendor page integrations paragraph.
- **What the page does NOT describe.** No contract-first codegen, no seeded
  fault-injection over native IPC with contract-aware oracles, no stale-binary /
  recycled-evidence refusal, no hash-chained offline passport. OBSERVATION
  (high): absent from the fetched body; otherwise UNKNOWN.
- **Pricing / time-to-value / ease-of-use:** UNKNOWN.

### E. CI / evidence-platform class (build CI + ALM + dashboards)

- **What was verified.** CI integration is a first-class claim on both the
  Parasoft page (CI/CD pipelines, coverage "as part of the CI process") and the
  VectorCAST page (Jenkins, VectorCAST/QA trending); ALM-side evidence lives in
  DOORS Next / Polarion / Codebeamer / Jama / Jira via the Parasoft DTP
  paragraph. VERIFIED FACT (high): Parasoft + VectorCAST vendor pages.
- **What stays UNKNOWN.** No Jenkins/GitHub Actions/GitLab, ALM-vendor, or
  dashboard-vendor body was opened this session, so feature-by-feature comparison
  (artifacts, attestations, trending, review UX, pricing, setup friction) is
  UNKNOWN. Generic CI (red/green per push, log archival) is ASSUMPTION (low) —
  not asserted as fact.
- **Working distinction (OBSERVATION, med).** In the verified bodies, CI/ALM
  platforms *collect and link* evidence produced elsewhere; none of the fetched
  bodies describes *generating* contract-aware behavioral evidence (oracles
  derived from a validated spec, before/after target comparison, stale-evidence
  refusal) the way GENESIS RT's `scripts/qnx_target.py` + `impact.py` + `gate.py`
  do. The generation-vs-collection split is the positioning wedge; see §9.

### F. OSS unit-test / coverage class (CppUTest / Ceedling / GoogleTest / gcov-class)

- **Status: UNKNOWN — no body opened.** No OSS framework README, doc, or repo was
  inspected this session, so capability, time-to-value, and ease-of-use are all
  UNKNOWN. This section exists only to prevent silent invention.
- **Narrow verified touchpoints (do not over-read).** GoogleTest appears in the
  fetched bodies only as *integrated-by* Parasoft ("TÜV-certified GoogleTest")
  and VectorCAST ("native GoogleTest support"). VERIFIED FACT (high) that the two
  commercial vendors name it; everything else about OSS frameworks is UNKNOWN.
- **OBSERVATION (low).** OSS harnesses plausibly beat GENESIS RT on adoption
  friction (no new contract language to learn) and lose on the evidence loop
  (no contract-aware oracles, no passport, no gate described anywhere in the
  inspected sources) — but without an opened OSS body this is positioning
  hypothesis, not fact. ASSUMPTION (low).

### G. Adjacent QNX-hackathon / Devpost submissions

- **Status: UNKNOWN — not inspectable.** The Devpost page fetch returned 403 this
  session; no submission gallery, entry, or rival repo body was opened. Any claim
  about direct hackathon rivals (count, approach, quality) would be invented.
- **Only verified anchors.** GENESIS RT's own category (Developer Tooling & Host
  Tools) and original-work/license facts come from `COMPLIANCE.md` (high). The
  hackathon's official category wording, judging weights, and submission count
  are UNKNOWN from primary source this session.

---

## 3. Comparison across the ten asked dimensions

Legend: **G** = GENESIS RT · **M** = Momentics · **P** = Parasoft-class ·
**L** = LDRA-class · **V** = VectorCAST-class · **C** = CI/evidence platforms ·
**O** = OSS harness class · **D** = Devpost adjacents.
Cells without a citation are UNKNOWN — the table compresses §2; prose below it
carries the labels.

| Dimension | G | M | P / L / V (commercial verification) | C | O | D |
|---|---|---|---|---|---|---|
| Problem | Requirement-change → trusted QNX behavior + proof (`WHY_GENESIS_RT.md`) | Build/debug/optimize on QNX (vendor page) | Defect/standard/coverage compliance for safety-critical C/C++ (P/V/L pages) | Run + link + trend evidence (P/V integration paras) | UNKNOWN (no body) | UNKNOWN |
| User | Embedded prototyper / reviewer / judge needing a behavior verdict, SDK-free readable | QNX C/C++ developer in IDE or CLI (vendor page) | Dev + test + quality leads on certified programs (V page: "developers, test engineers, quality leads") | Build/release + quality/ALM owners (ASSUMPTION low) | UNKNOWN | UNKNOWN |
| Time-to-value | Minutes SDK-free: 2 commands → PASS + replayable passport (`START_HERE.md` §1) | UNKNOWN (no trial body) | UNKNOWN (commercial eval; no trial body) | UNKNOWN | UNKNOWN | UNKNOWN |
| Ease-of-use | New contract language to learn; then one-command pipeline + Studio + dossier (`README.md`, `CLAIMS.md` §Product) | Eclipse-familiar IDE + wizards (vendor page); QNX learning curve UNKNOWN | IDE + CI integrations (P/V pages); setup/learning cost UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Capability | IR → deterministic codegen → native matrix → fault campaigns → passport → gate → compare (`architecture.md`) | Profilers, coverage, memory, debug (vendor page) | Static+dynamic, unit/integration/system, coverage incl. MC/DC, qualification packs (P/L/V pages) | Collect/link/trend (P/V paras); generation UNKNOWN | UNKNOWN | UNKNOWN |
| Depth | Narrow + deep on 3 machine kinds (AMR/conveyor/cell), v1+v2, 16-step matrix; no cert (CLAIMS + limits) | Deep on QNX runtime insight (instrumented kernel, multi-core) (vendor page) | Deep on standards + coverage + qualification (P/L/V pages) | UNKNOWN depth per product | UNKNOWN | UNKNOWN |
| Reliability | Fail-closed gate (missing/skipped/crashed/tampered ⇒ FAIL) + 24 adversarial tests + conformance vectors (CLAIMS, WHY) | UNKNOWN (no reliability body) | TÜV/qualification packaging (P/V pages); per-run semantics UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Evidence | Hash-linked passport, offline `verify.py`/`replay.py`, `qnx_verified` tiers, BEFORE/AFTER + stale control (CLAIMS) | Logs/traces/profiler views (OBSERVATION from feature list; format UNKNOWN) | Reports + DTP dashboards + ALM traceability (P page); cert reports (V page); formats UNKNOWN in detail | Dashboards + ALM links (P page); generic artifact claims UNKNOWN | UNKNOWN | UNKNOWN |
| Demo | SDK-free 2-min proof + 1376-test suite + Studio + dossier; final video PENDING (START_HERE, CLAIMS §Video) | UNKNOWN (no demo body) | UNKNOWN (tours named on P page, not opened) | UNKNOWN | UNKNOWN | UNKNOWN |
| Differentiation | Only inspected source combining contract-aware oracles + native QNX IPC execution + stale refusal + offline hash passport (§9) | Only QNX-vendor-native IDE/profiler in set (vendor page) | Only qualifiable standards/coverage story in set (P/L/V pages) | Only cross-tool aggregation story (P/V paras) | UNKNOWN | UNKNOWN |

---

## 4. What competitors make easier or clearer (their edge — credited, not conceded)

1. **Momentics: live runtime insight.** An interactive system/application profiler
   over an instrumented kernel answers "where is it slow / stuck *right now*" in
   a way GENESIS RT's 16-step matrix + IPC timeline (regression artifacts, QEMU
   timing explicitly non-guarantee) does not attempt. OBSERVATION (high) from the
   vendor feature list vs `WHY_QNX.md` timing disclaimer.
2. **Parasoft/LDRA/VectorCAST: standards-shaped verification.** MISRA/AUTOSAR/CERT
   enforcement, structural coverage incl. MC/DC, and TÜV-backed qualification
   packages speak the language of certification audits (DO-178C, ISO 26262,
   IEC 61508/62304, EN 50716/50128). GENESIS RT explicitly claims *no* functional
   safety qualification. VERIFIED FACT (high) both sides: P/L/V pages +
   `docs/limitations-and-safety.md` §1.
3. **Parasoft DTP / VectorCAST/QA class: management-grade trending.** Dashboards,
   project-level coverage over time, and ALM traceability (DOORS/Polarion/
   Codebeamer/Jama/Jira) answer "are we getting safer across releases" for an
   organization. GENESIS RT answers "did *this change* behave" for one contract
   pair. OBSERVATION (high) from the P/V integration paragraphs vs `impact.py`
   per-revision scope (`architecture.md`).
4. **Commercial harnesses: zero-new-language adoption.** Tests generated from
   existing source (V page: "directly from source code") or auto-generated unit
   tests (P page) meet brownfield code where it is; GENESIS RT requires
   expressing the machine in its IR first — a real adoption tax for legacy code.
   OBSERVATION (med).
5. **Ecosystem integrations.** 80+ compilers (V), VS Code/Visual Studio/Eclipse +
   CI/CD (P), Simulink (V), ALM tools (P) — the commercial class plugs into
   existing pipelines; GENESIS RT's CI story is currently one checked-in script
   (`ci_ir_check.py`) + a BUILD-ONLY QNX workflow with no registered runner.
   VERIFIED FACT (high): P/V pages + `docs/CLAIMS.md` §CI.

---

## 5. Unserved needs (gaps visible between the inspected bodies)

1. **Change-level behavioral verdicts for QNX prototypes.** Nobody's fetched page
   describes: change one requirement → re-verify natively → get a BEFORE/AFTER
   behavioral diff with a stale-binary refusal. LDRA names "change impact /
   change based testing" but gives no mechanism (UNKNOWN); the rest describe
   file/commit-level testing, not contract-knob → verdict moves. OBSERVATION (med).
2. **Stranger-replayable proof without the vendor toolchain.** `verify.py` /
   `replay.py` run on stdlib-only Python with no SDK; every green links to a
   trace; `qnx_verified` separates host from target claims. No fetched competitor
   body describes an equivalent offline, signer-independent, tamper-evident
   artifact a judge can re-verify in minutes. OBSERVATION (high on GENESIS side,
   med on the gap — absence from four pages, not proof of market absence).
3. **Honest negative controls as product.** Seeded fault campaigns with oracles
   that can genuinely fail + an explicit STALE control failing 14/16 on the
   changed behavior + a prose-grade label where sealing is missing. The
   transferable principles (§2 of the REFERENCE doc) call this the cheapest
   credibility available, and none of the competitor pages exhibits it.
   OBSERVATION (med).
4. **QNX-IPC-native verification semantics.** Guard/controller over
   `MsgSend`/`MsgReceive`, resmgr telemetry, supervision + crash containment as
   *asserted matrix steps* — Momentics profiles this runtime but (per the fetched
   page) does not verify contracts against it; the verification vendors are
   target-generic ("any host or target", L page). OBSERVATION (med).
5. **Blinded, published AI-assistance measurement.** Frozen 160-case holdout, 5
   unsafe accepts disclosed with deterministic-layer attribution, consultation
   audit with explained mismatches. No competitor page opened here publishes any
   eval failure. OBSERVATION (med; scope limited to opened bodies).

---

## 6. What GENESIS RT does that they cannot (precise, bounded version)

"Cannot" below means: **no mechanism described in any inspected competitor body,
with a concrete GENESIS RT mechanism cited** — not a claim about competitors'
roadmaps or unopened docs (those are UNKNOWN).

1. **Contract-aware oracles.** Expectations derive from the validated IR per run
   (`v2_transitions` / `limits_differ`), not fixed thresholds — so a requirement
   change moves verdicts *by construction* (Omega2: same 16/16 harness, STALE
   fails exactly the changed steps). VERIFIED FACT (high): `docs/CLAIMS.md`
   §Native ("expectations derive from the validated IR"). No fetched competitor
   body describes IR-derived oracles. OBSERVATION (high).
2. **Deterministic IR → native QNX system + provenance.** Byte-identical codegen
   for identical input with versions + IR hash embedded; multi-build provenance
   (host mirror + `qcc` x86_64); C/Python guard-policy identity proven by
   compiled conformance vectors. VERIFIED FACT (high): `architecture.md`
   (§Codegen, §QNX-native), `README.md` IPC section. Competitor codegen story:
   UNKNOWN (V generates *tests* from source — the inverse direction).
3. **Stale-binary / recycled-evidence refusal.** `external-write-manifest` +
   `external-check`, `no-test => no-pass`, tampered/version-unknown passports
   raising `InvalidPassport` — 13+ forgery classes refused per the judge copy, 24
   adversarial tests per the registry. VERIFIED FACT (high): `WHY_GENESIS_RT.md`,
   `docs/CLAIMS.md`, `architecture.md` (Evidence Graph errors). No fetched
   competitor body describes stale-recycling refusal. OBSERVATION (high).
4. **One-command counterfactual engineering.** Broken-vs-fixed, BEFORE/AFTER
   packs, `compare` / Studio Diff / `POST /compare`, impact + release-status
   per revision — with the full gate (not the targeted retest) deciding release.
   VERIFIED FACT (high): `architecture.md` (Requirements-to-Release),
   `WHY_GENESIS_RT.md`. Nearest neighbor (LDRA change-based testing) has no
   inspectable mechanism → equivalence UNKNOWN.
5. **SDK-free judge verification in minutes.** Clone → two commands → PASS +
   `chain: valid` + offline replay; `ui/dashboard.html` works from disk with no
   backend; dossier ZIP carries report + raw data + offline verify. VERIFIED
   FACT (high): `START_HERE.md` §1, `README.md` quickstart, `CLAIMS.md` §Packs.
   Competitor time-to-value: UNKNOWN (no trial bodies opened) — so this is a
   demonstrated GENESIS RT property, not a measured head-to-head win.
6. **Labeled-trust evidence tiers.** `qnx_verified` on every passport; UNSIGNED
   hash-only trust stated with the exact `--trust local → exit 2` behavior;
   host-discovered vs C-reproduced vs native discovery tiers in the Explorer.
   VERIFIED FACT (high): `docs/CLAIMS.md` §Packs/§Known limitations,
   `architecture.md` (Explorer). No fetched competitor body shows tiered
   trust labels. OBSERVATION (high).

Explicit non-claims (where GENESIS RT does NOT beat them): no static analysis,
no coverage metrics, no MISRA/CERT enforcement, no qualification packages, no
certification services, no multi-target support, no ALM integration, no
organizational trending — all VERIFIED FACT (high) by absence from
`docs/CLAIMS.md` §Product/§Limitations vs presence on P/L/V pages.

---

## 7. Why a judge would pick it (Developer Tooling & Host Tools)

Framed for the entry's own category (VERIFIED FACT, high: `COMPLIANCE.md` —
Devpost's official wording UNKNOWN this session after the 403):

1. **It is a tool for building on QNX, verified on QNX.** Message passing,
   resource manager, supervision, crash containment, and a 16/16 native matrix
   are executed on QNX 8.0/QEMU and replayable — the QNX-specific substance the
   category rewards, not middleware that happens to run there. VERIFIED FACT
   (high): `WHY_QNX.md`, `CLAIMS.md` §Native.
2. **The demo is the proof, and the proof re-runs.** Two commands, no SDK, every
   green linked to a trace, tamper controls included, BEFORE/AFTER side by side.
   A judge verifies the claim during judging instead of trusting a slide.
   VERIFIED FACT (high): `START_HERE.md` §1–2, `README.md` §What's proven.
3. **It refuses to impress dishonestly.** Inconclusive RT result published, 5
   unsafe accepts disclosed with layer attribution, STALE labeled prose-grade,
   UNSIGNED trust spelled out, video absence admitted with the historical cut
   explicitly disqualified. That posture is exactly transferable principles
   #1–3 (refusal-first, published failure, measured-vs-estimated). VERIFIED FACT
   (high): limits docs + `WHY_QNX.md` + `CLAIMS.md` §AI/§Video.
4. **One memorable line survives the judging pile.** "It doesn't merely generate
   code. It generates inspectable evidence about the behavior of the code."
   VERIFIED FACT (high — quoted): `WHY_GENESIS_RT.md` closing line.
5. **Forkable after judging.** Apache-2.0, public history from day one, stdlib-only
   core, codelabs (45-min native IPC, 15-min stale-binary for your own build) —
   the entry keeps working for the ecosystem after prizes are announced.
   VERIFIED FACT (high): `COMPLIANCE.md`, `README.md` codelabs row.
6. **Known risk, stated plainly.** Final video PENDING + Devpost unfiled is the
   single submission blocker (PORTFOLIO §P3, priority P0), and QEMU-only bounds
   the safety story. A judge picking it bets on the evidence loop, not on
   production readiness — which is precisely what the entry claims. VERIFIED FACT
   (high): `CLAIMS.md` §Video, PORTFOLIO §P3.

---

## 8. Unresolved evidence (do not treat as facts)

- U1. Competitor pricing, trial friction, setup time, and learning curve —
  no pricing/trial/tutorial body opened for any competitor. UNKNOWN.
- U2. OSS harness class (CppUTest/Ceedling/GoogleTest/gcov/…) — no body opened;
  only GoogleTest *mentions* inside P/V pages verified. UNKNOWN.
- U3. Devpost official category text, judging weights, submission count, and any
  adjacent submission — Devpost fetch 403. UNKNOWN.
- U4. LDRA change-impact/change-based testing mechanism — capability names only,
  no mechanism in the fetched body. Equivalence to GENESIS RT impact analysis:
  UNKNOWN.
- U5. Commercial-vendor offline/stranger-replayable evidence formats — reporting
  named, formats not detailed in fetched bodies. UNKNOWN.
- U6. GENESIS RT human-productivity gain — zero pilots (`CLAIMS.md`:
  `docs/business/pilot-study.md` records zero invitations). UNKNOWN by the
  project's own admission; do not imply any.
- U7. Competitor QNX-target specifics (Momentics aside) — P/L/V pages are
  target-generic in the fetched bodies. UNKNOWN.
- U8. All clone SHAs / page contents are 2026-11-09-session snapshots; vendors
  may have moved since.

## 9. Evidence log

- `PORTFOLIO_COMPETITIVE_AUDIT.md` (full read) → §1 baseline counts/status + §7.6
  blocker.
- `REFERENCE_PROJECT_ANALYSIS.md` (full read) → §1 principles mapping + §5.3/§7.3
  posture argument.
- `genesis-rt/README.md` (full read) → §§1–3, 6–7 proof + quickstart claims.
- `genesis-rt/docs/CLAIMS.md` (full read) → §§1–3, 5–8 numbers/tiers/limits/video.
- `genesis-rt/docs/architecture.md` (full read) → §3 capability + §6 mechanisms.
- `genesis-rt/docs/limitations-and-safety.md` (full read) → §1 limits + §4.2.
- `genesis-rt/docs/jury/{START_HERE,WHY_GENESIS_RT,WHY_QNX,COMPLIANCE}.md`
  (full reads) → §§1, 3–4, 6–7.
- Vendor fetches (bodies grepped from saved fetch text): Momentics feature +
  profiler paragraphs; Parasoft unified-workflow + standards + DTP/CI
  paragraphs; VectorCAST automation + coverage + integration paragraphs; LDRA
  lede + capability/standards lists → §2.A–E, §§3–6.
- Frozen evals: not opened, not cited. No `genesis-rt` writes; no git mutations.
