# WAVE 9 BASELINE — reality audit (2026-11-05)

- External ref HEAD: `24e0171fe3624939391536c02133f5d084610bbc` (nothing newer existed on origin).
- Local HEAD at audit: `fc05e3a` (10 Wave-8 commits ahead, pushed; `host-ci success` on fc05e3a confirmed via gh).
- Fresh local run (this box, Windows + QNX SDP 8.0 + QEMU 11.1.0 + node + gcc): **817/817 green, 0 skips** (758 prior baseline + 59 new Wave-8 tests).
- Fresh native proof this wave: op-a507c7ecb9cf — 11/11 runner steps, qcc 12.2.0 build, **16/16 target matrix PASS** on QNX 8.0.0 x86_64 (TCG; WHPX broken on host, needs reboot), 0 orphans. Artifacts: `artifacts/runs/target-ops/op-a507c7ecb9cf/` (git-ignored).
- Fresh CI-equivalent: verified demo PASS + anchored replay `gate: PASS (qnx_verified=False)` + C policy compile clean.

Status: VERIFIED = freshly executed here; IMPLEMENTED = code+tests present and green; PARTIAL = works but incomplete vs Wave-9 bar; BLOCKED = external dependency; MISSING = absent.

## Capability matrix

| Feature | Source files | Unit test | Integration test | Browser test | QNX native test | Raw evidence | Entry point | Docs | Limitation | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Machine IR v1/v2 + validation | host/genesis_rt/ir*.py, projects.py | test_ir_v2 (74), test_ir_validation (35) | test_projects_api | designer tab | — (host-side) | suite green | Studio Designer, CLI validate | PROGRESS.md | none known | VERIFIED |
| Deterministic QNX C codegen | host/genesis_rt/codegen*.py | test_codegen_v2 (13), determinism (12) | test_codegen_v2_behavior | — | cellcheck host compile | qcc build in op | CLI generate, Target Runner | architecture.md | none known | VERIFIED |
| Native qcc build + provenance | host/genesis_rt/build_adapter.py | test_build_adapter (8) | test_qnx_build* | — | qnx 6/6 incl qcc 12.2.0 | op gen/ + binaries | Target Runner, CLI | quickstart-qnx8-qemu.md | none known | VERIFIED |
| 16-check target matrix | scripts/qnx_target.py cmd_verify | test_qemu_stop (9) | test_device_chain (11) | — | fresh 16/16 PASS (op-a507) | target/*.log + qnx-target-record.json | Target Runner, CLI verify | quickstart | WHPX broken (host reboot); TCG proven | VERIFIED |
| Fault injection host+target | target/*/genesis_faultinject.c | guard_crash (9), sched (10) | guard_v2_behavior (10) | Lab tab | matrix faultinject/cell_policy | target logs | Lab tab, CLI faults | codelab | none known | VERIFIED |
| Supervision / crash containment | genesis_supervisor.c | crash_containment (17) | — | — | matrix supervisor_* | target logs | (native) | PROGRESS.md | none known | VERIFIED |
| Passport + anchored replay | evidence.py, replay.py | provenance (7), buildset (30) | test_replay (6) | Passport tab | target record binds | gate PASS observed | Passport tab, CLI | passport-threat-model.md | none known | VERIFIED |
| Release eligibility fail-closed | provenance.py gate | evidence_gate (16) | test_explain? (none) | Evidence tab | — | suite green | Evidence tab | KNOWN_LIMITATIONS (stale text) | targeted-vs-full UX missing | PARTIAL |
| Wrap-safe 32-bit timing | time_wrap host+C | test_time_wrap (16) | test_c_conformance | — | fresh matrix on new binaries | target logs | — | PROGRESS.md | none known | VERIFIED |
| Studio Live + projects | ui/studio.html, projects.py | — | test_projects_api (14) | ui 42/42 | — | harness green | Studio tabs | README (spotty) | Judge Mode missing | VERIFIED |
| Async jobs + SSE + admission | jobs.py, api.py | admission (3), lifecycle (6) | test_jobs (17) | pipeline tab | — | 429 + burst tests | Pipeline tab, POST /jobs | local-security-model.md | retention policies missing | VERIFIED |
| Target Runner + API + tab | target.py, api.py, studio.html | target_ops (15) | test_target_api (8) | test_target_runner (5) | full op COMPLETED | op record + target/* | Target tab, POST /target/ops | PROGRESS.md | seal/replay steps deferred (3b) | VERIFIED |
| Origin/PUT guard + threat model | api.py guard | — | origin tests (3 files) | — | — | 200→403 proven | (middleware) | local-security-model.md | Host/DNS-rebinding unaudited | PARTIAL |
| Evidence Graph | evidence_graph.py | test_evidence_graph (10) | — | Evidence tab | — | suite green | Evidence tab | PROGRESS.md | judge/cross-link UX thin | PARTIAL |
| Counterexample Explorer | explorer.py | (covered in suites) | test_explore_* | Lab tab | — | suite green | Lab tab | PROGRESS.md | no shrinking/persistence (§12) | PARTIAL |
| Digital Twin 2.0 | twin.py | test_twin (14) | test_twin_api (3) | twin tab | — | suite green | Twin tab | PROGRESS.md | A/B + diagnosis UX (§13) | PARTIAL |
| Impact / requirements→release | impact.py | test_impact (13) | test_impact_api (5) | Impact section | — | suite green | project Impact | PROGRESS.md | Proof-to-Decision UX missing | PARTIAL |
| Productivity benchmark | bench/productivity/ | test_bench_productivity (7) | — | — | — | synthetic refs only | CLI bench | bench docs | synthetic baselines (§16) | PARTIAL |
| Codelab (basic) | docs/codelab/ | — | — | — | — | prior validation | docs | codelab | advanced QNX tutorial missing | PARTIAL |
| Offline AI planner | planner module | planning (15) | — | — | — | 28-case set (prior) | CLI plan | PROGRESS.md | real LLM: no endpoint (§14) | BLOCKED |
| Second use case | — | — | — | — | — | — | — | — | absent (§15) | MISSING |
| Judge Mode | — | — | — | — | — | — | — | demo-video-plan (stale) | absent (§18) | MISSING |
| Soak / reliability campaign | — | lifecycle (partial) | — | — | — | — | — | — | absent (§24) | MISSING |
| Red-team evidence audit | tests/unit/test_passport_adversarial (18) | 18 green | — | — | tamper ctl in matrix | suite green | — | — | full campaign missing (§25) | PARTIAL |
| Devpost draft | docs/devpost-draft.md | — | — | — | — | — | docs | — | quotes 527 tests (now 817) | PARTIAL |
| Jury docs | docs/jury/* | — | — | — | — | — | docs | — | KNOWN_LIMITATIONS says static UI | PARTIAL |
| Demo video plan | docs/demo-video-plan.md | — | — | — | — | — | docs | — | terminal-centric, predates Studio flow | PARTIAL |
| Commercial dossier | docs/business/ | — | — | — | — | — | docs | — | predates Target Runner/proof | PARTIAL |

## Phase-1 remainder (Wave-9 §31)

Done in Wave 8 (verified above): API security PUT/PATCH (Host/DNS audit remains), bounded admission, Studio orchestration, fresh native proof.
Unfinished, highest impact first:
1. Task 3b: seal/replay steps in the runner (passport binding for ops) + Studio passport link.
2. Task 4: formal §8 campaign record (procedure + tamper control) reusing op-a507 evidence.
3. §8 Host/DNS-rebinding audit (security PARTIAL → VERIFIED).
4. Retention policies (§9 remainder).
