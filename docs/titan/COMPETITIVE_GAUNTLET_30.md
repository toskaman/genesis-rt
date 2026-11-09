# TITAN-1 Competitive Gauntlet — 30 Adversarial Questions

Date: 2026-11-06. HEAD: `12e662e`. Method: each question gets A (current
vulnerability, rated), B (hardening done or planned), C (truthful 10-second
judge rebuttal), D (evidence pointer), E (residual risk). Ratings:
CRITICAL / HIGH / MEDIUM / LOW. Fixes for CRITICAL/HIGH landed before this
report where marked FIXED; the rest are explicit residual risks, not rebuttals.

## Product and VC

### 1. Why isn't this merely a feature an incumbent can copy?

A. MEDIUM. Any single capability (codegen, fault injection, dossier ZIP) is
copyable by QNX Tool Suite / Vector / Siemens with a quarter of work.
B. The moat is the closed loop, not the features: IR → generated C → qcc →
staged bytes → 16 native probes → contract-aware oracle → passport → replay,
all hash-linked. Cloning the loop means rebuilding the provenance chain,
the oracle semantics and the negative-control suite, not one panel.
C. "Copy one panel in a quarter; copy the IR-to-passport proof chain and its
mutation-tested oracle and you have rebuilt the product."
D. `docs/titan/QNX_TECHNICAL_MOAT.md`; `host/genesis_rt/native_oracle.py`;
`tests/unit/test_native_oracle.py` (60); w12-formal op `op-cf7cc4d42aef`
16/16 + sealed passport + replay PASS.
E. A vendor with native-toolchain ownership (QNX itself) could obsolete the
loop by embedding attestation in the toolchain. Partnership beats rivalry.

### 2. Who pays, from which budget and why now?

A. HIGH. No paying user, no measured willingness-to-pay; "engineering teams"
is a budget category, not a buyer. Without a named budget owner this is a
demo, not a business.
B. FIXED (positioning, not revenue): buyer dossier names the payer —
embedded QA / verification lead spending integration-test labor — with a
pilot protocol that measures task time, interventions and evidence quality
before any price talk. No price is claimed without pilot data.
C. "The QA lead who pays for integration-test labor pays; the pilot kit
measures the saving before we name a price."
D. `docs/business/pilot-study.md`; pilot invitation/consent/workloads/analysis
script; `docs/titan/VENTURE_ACQUISITION_THESIS.md` (scenarios labeled
assumptions, zero revenue claimed).
E. Until a real pilot runs, budget-owner fit is a hypothesis. No pilot has
occurred — stated plainly in every commercial doc.

### 3. What is the real unit cost per active engineering team?

A. MEDIUM. "Free, it runs locally" hides the real costs: a QNX SDP license,
a workstation able to run QEMU (4G/4SMP per campaign), and integration labor
(CI wiring, IR authoring). Understating this destroys credibility.
B. Cost model published with three honest buckets: licenses the team already
holds (SDP), near-zero marginal compute (local QEMU, ~4 min/campaign on TCG),
and the dominant term — one-time integration plus per-change IR maintenance.
No per-seat fee exists in the open core.
C. "Compute is ~4 minutes of local QEMU; the real cost is integration labor,
which the pilot measures instead of us guessing."
D. Formal campaign `op-cf7cc4d42aef` (~4 min wall, TCG); `build_qemu_argv`
defaults `-m 4G -smp 4`; `docs/titan/VENTURE_ACQUISITION_THESIS.md`.
E. Support burden for heterogeneous customer targets (non-QEMU boards, custom
BSPs) is unmeasured and could dominate. QEMU-x86_64 only today.

### 4. How can the first 1,000 developers be acquired?

A. HIGH. There is no distribution engine: no marketplace listing, no package
manager presence, no community, no content flywheel running. "Devpost
visibility" is not acquisition.
B. Partial: two codelabs (reproducible, real failure injection), public
evidence packs verifiable without the SDK, CI bridge that meets developers
in PRs, and a publication handoff (video + captions + thumbnail). These are
assets, not a funnel — labeled as such.
C. "We don't have a funnel; we have reproducible codelabs and verifiable
evidence packs, which is where a funnel starts."
D. `docs/codelab/`; `evidence/qnx8-x86_64-w11-*` (+verify.py);
`docs/demo/PUBLICATION_HANDOFF_W12.md`.
E. First-1000 plan needs an owner and a channel budget that do not exist.
Community Choice (Jan 2027) is the only scheduled distribution event.

### 5. Why will teams continue using it?

A. MEDIUM. Hackathon tools die when the novelty fades unless they sit in the
daily path. A Studio you must remember to open loses to `qcc && scp`.
B. Retention is designed around the PR, not the Studio: CI IR check comments
impact on every contract change, the runner posts native verdicts, and the
dossier becomes the review artifact. The daily surface is code review, which
teams already open.
C. "Nobody has to remember Studio — the proof arrives inside the code review
they already read."
D. `scripts/ci_ir_check.py`; `docs/runner/SELF_HOSTED_RUNNER.md`;
`POST /review/plan` + Review panels (`tests/integration/test_review_api.py`,
`tests/ui/test_review_panels.py`, 11 green).
E. CI value collapses without a licensed self-hosted target runner; host-only
CI is useful but not the flagship loop. Single-user local tool today.

### 6. What happens when an established vendor clones the workflow?

A. MEDIUM. Same as Q1 but post-traction: a Vector/Siemens "verification
dossier" with sales distribution could freeze us out of enterprise accounts.
B. Defenses, in order: (1) Apache-2.0 core + open evidence formats — cloning
validates the category and our artifacts stay interoperable; (2) depth of the
QNX-native oracle and negative suite, which is slow to replicate faithfully;
(3) acquisition positioning — being the team that built the loop is the exit,
not beating Siemens at distribution.
C. "Clone the workflow and you validate our category; our open evidence
format still reads your dossier — or acquires ours."
D. See `docs/titan/VENTURE_ACQUISITION_THESIS.md` (buyer
hypotheses with reasons-against for each); `evidence/` pack format + verify.
E. Open formats cut both ways: a cloner can emit "compatible" dossiers with
weaker oracles. Schema conformance tests for third-party emitters don't exist.

### 7. What recurring problem sustains GENESIS after the hackathon?

A. LOW. This is the strongest card: every controller change re-opens the same
expensive questions — what broke, what must re-run, is the evidence still
valid. That work recurs per commit, not per project.
B. The product is already shaped around recurrence: change-impact analysis
per diff, stale-evidence tracking per revision, before/after native comparison
per contract edit. Each release makes the next change cheaper to verify.
C. "Every commit re-opens the same question — what must re-run and is the
proof still valid. That question never stops recurring."
D. `host/genesis_rt/impact.py` + Change-impact Studio view; stale-evidence
states; `docs/jury/BEFORE_AFTER_NATIVE.md` (1.2→1.6 both 16/16, predicted
DENY→ALLOW flip).
E. Recurrence assumes teams keep changing controllers in GENESIS-tracked IRs.
Adoption of the IR as source-of-truth is the gating habit, still unproven.

## AI and deterministic engineering

### 8. How do we prevent fabricated or hallucinated evidence?

A. HIGH if AI touched verdicts. A model that can write PASS into a passport
destroys the entire value proposition.
B. FIXED (architecture): no model output can reach a verdict. The offline
planner only drafts IR text that must pass deterministic validation; the gate
(`gate.py`) reads hashes, digests and oracle outputs only. There is no code
path from planner text to PASS. Optional LLM assistance (P2) was evaluated
and NOT shipped — no provider, no dependency, no claim.
C. "No AI output can reach a verdict — the gate reads hashes and oracle
outputs only, and there is no model in the release path."
D. `host/genesis_rt/gate.py`; `docs/planning-eval.md` (28-case eval);
`WAVE11_RELEASE.md` §AI (provider unavailable → not shipped).
E. A future LLM integration re-opens this; the safety contract (propose-only,
validate-everything) must be re-proven then, not assumed now.

### 9. Why use AI where deterministic code suffices?

A. LOW — asked and answered by not doing it. The bundled planner is a
template engine, honestly labeled, not a generative model.
B. No change needed: planning-eval compares the offline planner against its
28-case set; LLM drafting stays an unevaluated option. We do not pay model
cost, latency or hallucination risk for work that grep + schema do better.
C. "We don't — the planner is deterministic templates, honestly labeled, and
the LLM stays out until it beats that baseline."
D. `docs/planning-eval.md`; planner module + tests; no network calls in the
verify path (see Q20).
E. Marketing pressure to "add AI" could dilute this stance. The scorecard
(Q: Innovation) credits the proof loop, not model hype.

### 10. What are actual end-to-end latency measurements?

A. MEDIUM. Latency claims without numbers are filler; TCG numbers could also
scare (emulation is slow) if quoted without context.
B. FIXED (measured, this wave): TCG boot→SSH-banner 21 s (smoke
`%TEMP%/tcg_smoke.py` log); formal 13-step campaign ~4 min wall (build +
boot + stage 9 binaries + 16 native checks + 1000 perf samples + seal +
replay); host-only pipeline ~1 s per IR; full host test-file suites 22–35 s.
QEMU timings are labeled engineering observations, never HW guarantees.
C. "Twenty-one seconds to SSH, four minutes for the full 16-check native
campaign with a thousand perf samples — measured today on TCG."
D. `op-cf7cc4d42aef` record (`%TEMP%/w12-formal/`): COMPLETED 13/13, 16/16,
gate PASS, replay PASS; `docs/audits/TASK4_FORMAL_CAMPAIGN.md` (~197 s prior).
E. WHPX is down on this host (needs reboot), so no accelerated number exists;
TCG is the honest, slower figure. First cold-boot build + stage dominates.

### 11. Which benchmarks validate correctness against fair baselines?

A. MEDIUM. Benchmark v2 (8 GENESIS cmds vs 30+10 reference, faults 5/5 vs
3/5) is synthetic and author-designed; a hostile reviewer calls it
home-field advantage.
B. Hardened, not solved: v2 replaced the deliberately-simple checker with a
competent schema-validation reference; the comparator was re-run this wave
with identical totals (reproducibility proven); baselines document their own
limits; no human-hour savings are inferred from machine runtime.
C. "The v2 baseline is a competent validator, not a strawman — and we claim
command counts, never developer hours."
D. `bench/productivity/` + `analyze_pilot.py` (3 tests green); Wave 12
re-validation (totals identical, diffs only paths/timings/run-ids).
E. Real validation needs the pilot (independent humans, fair manual
reference). Until then "8 vs 30" measures workflow shape, not productivity.

### 12. How would malicious specifications or documents affect the system?

A. HIGH. IRs arrive from PRs, forks and file imports — classic injection
surface (path traversal in staged names, giant payloads, schema bombs).
B. FIXED (layers, tested): strict schema validation before any use
(`ir.py`/`ir_v2.py`); staged names allowlisted to `genesis_*`
(`build_set.py` refuses others); job bodies capped (`MAX_JOB_BYTES`,
`MAX_IR_BYTES`); untrusted PR code runs host-only CI with no target,
credentials or signing keys; imported artifacts treated as untrusted
throughout (`docs/local-security-model.md`).
C. "Every IR is schema-jailed before use, staged names are allowlisted, and
untrusted PRs never touch the target or any key."
D. `tests/unit/test_runner.py` shape/pin tests; `test_jobs_admission.py`;
`RunnerConfig` bounds; `SELF_HOSTED_RUNNER.md` trust boundaries.
E. A malicious IR that is schema-valid but semantically hostile (e.g. resource
exhaustion via legal-but-huge scenario lists) relies on downstream caps, not
on validation alone. Fuzzing budget for the validators is zero.

### 13. What happens when an optional AI provider changes?

A. LOW. Nothing depends on one: there is no provider integration, no key, no
network call in any verify/build/review path.
B. No action: the architecture keeps provider-shaped holes (draft text in,
validated IR out) but no adapter is wired. Swapping a future provider cannot
change verdicts because verdicts never consult it (see Q8).
C. "Nothing breaks — nothing is connected. Verdicts never consult a model."
D. Grep-clean: no API keys, no model endpoints in `host/` or `scripts/`
(config), `planning-eval.md` offline-only.
E. If an LLM is ever wired, provider drift (model-version behavior change)
becomes a real regression source needing pinned evals. Not today's problem.

### 14. Why use Machine IR and a deterministic gate rather than a fully autonomous agent?

A. LOW. An agent that "handles verification" is un-auditable: its reasoning
is not replayable, its verdicts are not diffable, and its failures are not
regression-testable.
B. The IR is the audit surface: versioned schema, canonical JSON, content
digests; the gate is pure functions over digests and oracle outputs. Every
verdict replays byte-identically (`replay` step PASS in every formal op).
An agent can propose IR edits later; it can never *be* the verdict.
C. "Because a verdict must replay byte-identically — agents propose, digests
dispose."
D. `ir.py` canonical JSON + digests; `gate.py`; replay PASS in
`op-cf7cc4d42aef` and both Wave 11 passports.
E. IR expressiveness bounds what can be verified; machines outside the schema
get nothing. Schema growth is maintenance debt with no owner yet.

## Systems engineering

### 15. How does bounded admission behave under 10,000 attempted requests?

A. HIGH if unbounded: 10k queued pipelines would OOM the host or wedge the
target lease. The pre-Wave-9 design had no explicit pending cap.
B. FIXED: `MAX_LIVE_JOBS=50` (HTTP 429 beyond, no silent queue),
`MAX_WORKERS=2`, `MAX_TRACKED_JOBS=200`, per-job event caps (1000 × 2000
chars), single live target op (`TargetBusy` otherwise). A 10k burst admits
≤50 and rejects the rest fast with an explicit overload response. Soak: 100
jobs/108 s, no worker-thread leak; SSE reconnect + storage-pressure tested.
C. "Fifty admitted, the rest get an instant 429 — the queue cannot grow, by
construction."
D. `host/genesis_rt/jobs.py` (constants + `live >= max_live` 429);
`tests/unit/test_jobs_admission.py`; `docs/audits/SOAK_WAVE11.md`.
E. 429-storm clients can still burn CPU on rejections; no rate-limit backoff
headers. The 10k-burst figure itself is reasoned from caps, not load-tested
live — a measured burst test is owed before any enterprise claim.

### 16. Which failures are single points of failure?

A. MEDIUM. Honest list: the one QEMU target (exclusive lease — by design),
the workstation disk holding SQLite + op stores, the operator's QNX license,
and this host's WHPX state (currently down). Pretending otherwise would be
the real failure.
B. Each SPOF fails closed and loudly: target lease conflicts → `TargetBusy`,
never double-drive; dead guest mid-matrix → FAILED, no passport (proven live
by `op-03090cb5e414`); disk pressure → controlled errors, isolated test
stores; missing SDK → honest BLOCKED + host-only mode, never faked native.
C. "One target, one disk, one license — each fails closed and says so, and a
dead guest has never produced a green verdict."
D. `TargetLock`; `op-03090cb5e414` fail-closed proof; storage-pressure tests;
`check-env` honest capability reporting.
E. No HA story: no second target, no replicated store, no takeover. That is
correct scope for a local dev tool and a blocker for any "managed service"
pitch until designed.

### 17. What are actual memory, CPU, storage and startup costs?

A. MEDIUM. Unmeasured resource claims ("lightweight!") are how tools die on
real workstations.
B. FIXED (measured/stated): API server = 1 uvicorn worker, 2 job threads,
idle RSS in the tens of MB (Python + SQLite, no resident models); per
campaign = one QEMU (`-m 4G -smp 4`, transient) + op dir in the low MBs
(transcripts, logs, passport); startup = import + `check-env` probes,
seconds; op/job stores are files under `artifacts/` + tmp dirs with
retention policy (`docs/retention-and-cleanup.md`).
C. "Idle server: tens of megabytes. Per campaign: one 4-gig QEMU and a few
megabytes of evidence — then it all stops."
D. `cli.py` serve (workers=1, 127.0.0.1); `build_qemu_argv` defaults;
`retention-and-cleanup.md`; soak reports (no handle/thread growth).
E. No long-horizon disk-growth measurement (weeks of daily campaigns) and no
RSS ceiling test under adversarial SSE fan-out. Job store retention is
count-based (200 tracked), not byte-based.

### 18. Can confidential industrial data escape the workstation?

A. HIGH. IRs encode real machine behavior; a tool that phones home with them
is undeployable in OT/regulated shops.
B. FIXED (architecture): the server binds `127.0.0.1` only; no telemetry, no
update checks, no external calls in any pipeline (verify/build/review/replay
all local); host allowlist (`localhost`, `127.0.0.1`, `::1`); same-origin +
method coverage on mutating routes; target password env-only, never in
params/logs (threat model + red-team rounds 1–2).
C. "It cannot phone home — it binds loopback, makes zero external calls, and
the only secret lives in an env var that never touches a log."
D. `cli.py:298` (`host="127.0.0.1"`); `api.py:151` host check;
`docs/local-security-model.md`; `docs/audits/RED_TEAM_ROUND*.md`.
E. The workstation itself is the trust boundary: a compromised laptop owns
everything (evidence included — see Q8's operator-rewrite caveat, mitigated
only by optional Ed25519 signing with external key custody). No DLP integration.

### 19. What happens when network connections fail mid-operation?

A. MEDIUM. Two networks matter: host↔guest SSH (user-net, flaky under load)
and browser↔API SSE. A drop must never yield a half-verdict.
B. FIXED (semantics + tests): SSH failure mid-matrix → step FAILED, op
FAILED, no passport, cleanup runs (proven by the externally-killed-guest
op); SSE drops → client resubscribes from `after=` seq with no lost/stale
state (reconnect tests); browser refresh mid-job recovers identity from the
job store (21 real-browser E2E incl. recovery paths).
C. "A dropped cable fails the run loudly and keeps the evidence — it can
never mint half a passport."
D. `op-03090cb5e414`; SSE reconnect tests; browser E2E recovery suite.
E. A partition that heals mid-cleanup (guest killed, then SSH works again)
leaves attribution to the hermetic staging rule (leftovers dropped
pre-stage). Two clients racing one op is guarded by the target lock, not by
fine-grained op ownership.

### 20. What remains functional entirely offline?

A. LOW. This is a designed strength: the whole loop runs air-gapped given a
local SDK + image.
B. Everything except fetching the repo and (future) publishing the video:
codegen, qcc build, QEMU boot, 16 native checks, oracle, gate, passport,
replay, dossier export, Studio, CI host checks — zero network calls. The
public evidence packs verify with `verify.py` and no SDK at all.
C. "Everything that matters — build it, boot it, prove it, replay it — with
the cable unplugged."
D. `verify.py` SDK-free verification of both Wave 11 packs; no-network unit
scope (`test_qemu_stop.py` docstring as policy example); offline planner.
E. First-time setup needs the network (clone, pip install, QNX SDP
acquisition). Offline does not mean license-free: the SDP license is still
required for native builds.

## Live demonstration

### 21. What happens with corrupted or adversarial input?

A. HIGH. Demo-time garbage (truncated IR, swapped binary, edited transcript)
must fail visibly, never green.
B. FIXED (demonstrated live paths): truncated/invalid IR → validator rejects
with field-level errors before any build; swapped binary → digest mismatch,
`limits_differ`/binding checks FAIL, gate refuses (Campaign C,
`op-ad562b34f8de`); edited transcript → chain/tamper checks refuse; tampered
dossier → verifier rejects (host E2E). Every refusal names the artifact.
C. "Corrupt anything and watch it fail by name — swapped binary, edited
transcript, truncated IR — never a quiet green."
D. Campaign C; dossier tamper E2E; `test_limits_differ_binding.py` (11);
`runner.py` shape/pin rejections.
E. Error messages are accurate but engineer-grade; a non-technical judge may
need the narration to parse them. UX copy for refusal paths is thin.

### 22. What happens with unsupported machine types or arbitrary documents?

A. MEDIUM. Feeding a toaster manual or a v99 schema should not crash the
server, hang a job, or — worst — coerce into a fake PASS.
B. Unknown `machine_kind`/schema → validation error naming the supported set
before any work is scheduled; binary/non-JSON uploads → parse rejection with
size caps enforced first. No coercion path exists: unvalidated input cannot
reach codegen, and codegen output cannot reach the gate without a digest.
C. "Unknown machines get a named rejection listing what is supported — the
server never guesses, never hangs, never passes them."
D. `ir.py`/`ir_v2.py` validators + error tests; `MAX_JOB_BYTES`/`MAX_IR_BYTES`
caps; jobs admission tests.
E. The supported set is small (amr/conveyor/cell × v1/v2) — honest but
narrow. A judge asking "does it do robotic arms?" gets a correct, deflating
no (see venture thesis: breadth is explicitly deferred).

### 23. How can a judge distinguish real QNX execution from simulation?

A. CRITICAL. If the demo cannot prove "this ran on QNX", the flagship claim
collapses into theater. This is the question the whole submission must answer.
B. FIXED (layered, independently checkable): (1) target identity block —
`QNX qnxqemu 8.0.0 … x86pc x86_64` uname captured per run; (2) native-only
artifacts — QNX PIDs, `slog2`/SLM lines, CLOCK_MONOTONIC IPC timeline from
target stamps; (3) provenance — staged-binary cksums re-read from the guest
and matched to the manifest; (4) independent replay — `verify.py` recomputes
every check from raw transcripts without our server; (5) honest labeling —
every surface says host vs target, QEMU vs hardware.
C. "Read the uname, re-read the guest checksums, then run verify.py yourself
— the proof doesn't need our server or our word."
D. `op-cf7cc4d42aef/target/` (16 logs + record); `evidence/ipc-timeline/`;
both public packs + `verify.py` OK; BEFORE_AFTER flip (DENY→ALLOW at 1.5).
E. QEMU-not-hardware remains the honest ceiling: timing is observational,
and a sufficiently deep skeptic notes we attest the guest, not silicon. No
hardware run exists. Stated in every QNX doc.

### 24. What produces the strongest authentic WOW moment within fifteen seconds?

A. LOW (execution risk, not product risk). A 15-second window needs one
unfakeable beat, not a tour.
B. The chosen beat: the 1.5 m/s probe flipping DENY→ALLOW between two
sealed passports — same probe, two contracts (1.2 vs 1.6), two 16/16
verdicts, both replayable. It compresses the entire thesis (contract-aware
proof, not fixed assertions) into one screen. Backup beat: live tamper
rejection — edit one byte, watch the chain refuse.
C. "Same probe, two contracts, opposite verdicts — both proven. Fifteen
seconds, zero acting."
D. `docs/jury/BEFORE_AFTER_NATIVE.md`; `docs/demo/genesis-rt-demo-w12.mp4`
(decision scene + subtitles); `SHOT_EVIDENCE.md` mapping.
E. The flip needs the comparison view loaded and narrated; cold, unexplained,
it reads as "two green screens". The video carries the narration; live demos
need the speaker to land the one sentence (see Q30).

## Product elevation

### 25. Which engineering task is genuinely reduced or eliminated?

A. MEDIUM. "10x faster verification" without a measured task is vapor. The
honest unit is narrower.
B. The eliminated task is *manual re-attribution after a contract edit*:
today an engineer re-runs suites by memory and re-assembles evidence by hand;
GENESIS derives the affected set (impact), runs exactly it (targeted + full
gate), and emits the dossier. Measured proxies: 8 vs 30+10 commands, 5/5 vs
3/5 faults caught (v2, synthetic). Human-time measurement awaits the pilot.
C. "Nobody re-assembles proof by hand after a limit change — impact, re-run
and dossier are derived, not remembered."
D. Impact module + review plan; benchmark v2; pilot workload definitions
(task scripts that will measure the human delta).
E. IR authoring/maintenance is NEW work created by the tool; net savings are
unmeasured. If IR upkeep exceeds re-attribution savings for small teams, the
pitch inverts — the pilot must test small teams explicitly.

### 26. Why does GENESIS make QNX more valuable to developers?

A. LOW. QNX's strengths (microkernel isolation, message passing,
determinism) are exactly what GENESIS observes and proves; QNX's weakness
(verification labor) is what GENESIS automates. Fit is structural, not
sloganeering.
B. Every flagship artifact is QNX-native: guard/supervisor/resource-manager
processes, real IPC timelines, crash-containment probes, scheduling
experiments. The codelabs teach QNX concepts (message passing, supervision,
recovery) through GENESIS exercises — the tool markets the platform while
using it.
C. "QNX gives you isolation worth proving; GENESIS proves it per commit —
the tool sells the platform it runs on."
D. `docs/codelab/ADVANCED-QNX.md` (IPC, supervision, recovery labs);
`WHY_QNX.md`; IPC timeline; 16 native checks incl. crash family.
E. Single-platform bet: value concentrates on QNX 8 x86_64/QEMU. Linux/RTOS
ports would dilute the QNX story that justifies the partnership case.

### 27. What ecosystem flywheel could improve the product with adoption?

A. MEDIUM. No flywheel spins yet; claiming network effects pre-network is
fiction.
B. Designed (not running): more IRs → richer counterexample corpus → better
fault scenarios and oracle vectors for everyone; more target runs → tighter
perf baselines per machine kind; CI bridge → dossier becomes the shared
review language across teams. Each loop is architected (corpus formats,
baselines, open pack schema) but empty.
C. "Every run donates counterexamples and perf baselines back to the corpus
— the tenth team verifies faster than the first."
D. Counterexample persistence format; `perf-baseline.md`; open evidence-pack
schema (`verify.py`).
E. Cold start: the corpus, baselines and shared language have exactly one
contributor (us). Flywheel claims stay in the thesis as designed-not-running
until external runs exist. Data-sharing consent for the corpus is unbuilt.

### 28. Which regulations or engineering standards create demand without implying mandatory certification?

A. MEDIUM. Name-dropping ISO 26262/IEC 61508 invites "are you certified?"
(which we are not) while ignoring them wastes the demand signal.
B. Positioned carefully: the dossier *assists* qualification workflows
(traceability, repeatability, independent replay) for teams working toward
IEC 61508 / ISO 26262 / UL 4600 style evidence — and every doc states it is
not a certification and we claim none. Demand comes from audit pain, which
exists with or without our certificate.
C. "Audits demand traceable, replayable evidence — we produce exactly that,
and we claim no certificate of any kind."
D. `docs/limitations-and-safety.md`; dossier review section
("not a functional-safety certification" spelled out); pilot kit privacy page.
E. A buyer misreading "qualification assistance" as "qualified tool" is a
live misinterpretation risk; the wording is policed by the drift guard, but
sales conversations (none yet) are where it would actually break.

### 29. Which implementation details establish a technically defensible advantage?

A. LOW. This is the receipts question — answered by pointing at code, not
adjectives.
B. The defensible set: (1) contract-aware oracle with IR-derived expectations
+ mutation-tested non-vacuity; (2) multi-build provenance (build sets chain
source passports, hermetic staging, byte-compare); (3) fail-closed gate with
live-kill proof; (4) deterministic codegen (byte-identical secondaries across
waves); (5) Windows-host race hardening (waiter retry, OEM-safe captures,
bounded replace retries — all regression-tested).
C. "Mutation-tested oracle, chained multi-build provenance, a gate proven by
live-kill, and byte-identical rebuilds — read the code."
D. `native_oracle.py` + 60 oracle tests; `buildset.py` + `build_set.py`;
`op-03090cb5e414`; w11-vs-w12 secondary digests (identical); commit `12e662e`.
E. Defensibility ≠ invulnerability: each item is documented well enough to
reimplement given time (see Q1/Q6). The defense is velocity + depth, and both
need continuous investment post-hackathon.

### 30. What single sentence should judges remember?

A. LOW. If the submission needs thirty sentences to land, it has already lost.
B. The sentence, used consistently across video, Devpost and codelab close:
"Every embedded software change deserves a proof, not just a green checkmark."
It names the user (embedded teams), the trigger (every change), the artifact
(a proof) and the enemy (hollow green). Nothing else contends.
C. "Every embedded software change deserves a proof, not just a green
checkmark."
D. `docs/demo/NARRATION_W11.md` close; `docs/devpost-draft.md` lede;
`PRODUCT_STRATEGY.md` promise line.
E. A sentence is not a moat. If the demo, the replay and the dossier don't
make a skeptic nod within three minutes, the sentence is decoration.

## Fix log (this wave, before release)

- CRITICAL Q23 layers re-verified on the fresh w12-formal campaign
  (`op-cf7cc4d42aef`): uname block, guest cksums, replay PASS — all present.
- HIGH Q15: waiter/record races fixed and regression-tested (`12e662e`);
  measured 10k-burst test still owed (residual risk kept).
- HIGH Q8/Q12: no-model-in-verdict invariant restated with code paths; LLM
  remains unevaluated and unshipped — no new claim made.
- HIGH Q2/Q4: commercial docs explicitly state zero pilots, zero revenue,
  zero WTP data; pilot kit is the instrument, not the result.

## Open residual risks (do not rebut — own them)

1. No external pilot, no measured productivity delta, no revenue signal.
2. No measured 10k-burst load test (caps reasoned, not fired).
3. QEMU-only evidence; WHPX down; no hardware run.
4. Single-user local tool; no team server, no HA, manual key rotation.
5. Small machine-kind coverage; second-example economics unproven.
6. No distribution engine beyond scheduled hackathon visibility.
7. Validator fuzzing budget zero; semantically-hostile-but-valid IRs rely on
   downstream caps.
