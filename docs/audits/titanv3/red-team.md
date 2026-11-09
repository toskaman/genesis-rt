# GENESIS RT (titan-omega-v3) — Final Red-Team Judge Simulation

> DOCS ONLY. No contact, no submission, no media produced, no releases/tags,
> no secrets, no force-push, no history rewrite. Frozen evals untouched
> (`genesis-rt/evals/*.json`, `evals/results/*` — not opened, not cited by value).
> Reader posture: branch read via a private scratch worktree
> (`$env:TEMP\redteam-wt-02f10ad8`, detached HEAD `8b35839`), read-only;
> shared checkout untouched (verified clean); worktree removed after reading.
> This file under `v3-research/` is the only write.
>
> Method: every factual claim reuses a body opened in this session (see §6).
> Search output located candidates only. Labels: **VERIFIED FACT** (read in the
> cited body and/or executed this session) / **OBSERVATION** (synthesis) /
> **ASSUMPTION** (inference, flagged), with confidence high/med/low.
> No metrics, scores, feedback, or testimonials invented. All numbers are quoted
> from cited bodies or from commands executed this session. Scores in §4 are
> **INTERNAL** hostile simulations, deliberately deflated, and are not predictions
> of official judging.
>
> Rule anchor: final video **DEFERRED BY OWNER**, Devpost **NOT submitted**
> (VERIFIED FACT, high:
> [README.md](../../../README.md#L52-L54),
> [DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L1-L6)).
> Official criteria: four **equally weighted** (25% each implied) — Technological
> Implementation, Design, Potential Impact, Innovation & AI Creativity — plus a
> Stage-One pass/fail gate and criterion-1-first tie-breaks
> (per [qnx-forensics.md](./qnx-forensics.md#L32-L41)).
> Branch under review: `origin/titan-omega-v3` = `8b35839` "Titan v3:
> K1 prove-my-change + B-03/B-14/B-17/B-18 (1395 tests green)"
> (VERIFIED FACT, high — worktree HEAD read this session).
> Internal self-score on this branch: **31/40** (9.5/8/5/8.5; independent
> reviewer 29/40)
> (VERIFIED FACT, high:
> [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L18-L37)).

## 1. Perspective A — Product / impact judge ("who is this for, and does it matter?")

**Strongest reason to award first place.**
The product answers a real, expensive question — "a requirement changed, prove
the target matches" — with a closed loop instead of a dashboard: contract →
native QNX build → 16/16 on-target matrix → hash-linked passport a stranger can
replay offline with stdlib-only `verify.py`, plus one-click BEFORE/AFTER verdict
cards via the new `verify-change` (VERIFIED FACT, high:
[README.md](../../../README.md#L27-L45);
[change.py](../../../host/genesis_rt/change.py#L70-L119);
live run this session: cell broken→fixed produced FAIL→PASS with knob table
`max_linear_speed_mps: 0.3 → 1.2`, 3 fixed scenarios, both chains valid).
The review-dossier ZIP (report + raw + offline verify) is a genuine
reviewer/auditor workflow artifact, not a screenshot pile (VERIFIED FACT, high:
[demo-story.md](./demo-story.md#L120-L125)).
OBSERVATION (med): this is the only entry-shaped artifact in the inspected
evidence that hands a *non-operator* (reviewer, auditor, judge) a verifiable
object rather than a claim.

**Strongest reason to reject.**
No human has ever used it for real work: `HUMAN USER BENEFIT NOT YET MEASURED`
governs, with zero pilots, zero invitations, zero records (VERIFIED FACT, high:
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L185-L199);
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L40-L41)).
A product judge comparing this against any entry with named users, a deployment,
or measured time saved will file GENESIS RT under "impressive prototype, no
evidence of use" — and the criterion text demands "a credible, specific case
for a real problem in a QNX market" (per qnx-forensics §Judging).
OBSERVATION (high): honesty about zero pilots earns trust but zero points; the
criterion scores impact, not candor about its absence.

**Most serious weakness.**
The impact story is aimed at QNX teams shipping requirement changes, yet the
entry workflow every new user must survive — hand-writing 45+ lines of strict
JSON Machine IR — is the project's own documented "most painful workflow" with
a 13-action entry funnel (VERIFIED FACT, high:
[killer-feature.md](./killer-feature.md#L23-L46)).
K1 polishes the *change* loop for existing IR authors; the *first-machine*
funnel is untouched on this branch. A product judge asks "who adopts this on
Monday?" and the honest answer is "someone who already speaks Machine IR" —
a population of approximately the author.

**Most memorable part.**
"The wrong binary cannot pass": stale control 14/16 failing exactly on
`estop_target` + `v2_transitions` (VERIFIED FACT, high:
[README.md](../../../README.md#L29-L39)).
OBSERVATION (high): this is a DP3-grade one-metric identity ("one-metric
identities travel", per
[winners-delta.md](./winners-delta.md#L382-L383)) —
it survives the judging pile as one sentence, and the one-line prose-grade
honesty label makes it sticky rather than suspicious.

**Missing evidence.**
Any external human signal: one pilot record, one cold-reader comprehension
note, one screen-reader session log, one second-host provenance fill. All four
protocols/templates exist and all four are unfilled/unexecuted (VERIFIED FACT,
high: [DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L194-L199);
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L38-L41);
[SECOND_HOST_PROVENANCE.md](../../../docs/submission/SECOND_HOST_PROVENANCE.md#L1-L9)).
The product judge's file currently contains zero lines written by anyone but
the author and agents.

**Recommended final improvement.**
Run the quick-tier paired pilot exactly per protocol (2 independent teams,
3 quick tasks, both lanes) and publish dated raws — the only move that adds
Impact points rather than Impact prose (per
[backlog.md](./backlog.md#L84-L100)).
If owner bandwidth allows only one human act before filing, this beats the
screen-reader session and the cold-read test on criterion weight (25% of total
sits at ~half marks).

## 2. Perspective B — Technical expert ("is it real engineering, and is it sound?")

**Strongest reason to award first place.**
Depth that survives inspection: 1395 collected tests pinned to a single
`facts.py` source of truth with 55 docs-consistency pins, deterministic
codegen, C/Python guard equivalence proven by compiled conformance vectors,
fail-closed gate semantics (`no-test ⇒ no-pass`), 24 adversarial passport
tests over 13+ forgery classes, and a blind AI-eval ladder (v9: 160 cases,
142/150/150, 5 unsafe disclosed by class, 0 wrong-kind) with published raws
and a consultation audit (VERIFIED FACT, high:
[facts.py](../../../host/genesis_rt/facts.py#L15-L20);
[README.md](../../../README.md#L58-L71);
[JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L9-L16);
[WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L24-L38)).
This session: K1's 8 integration tests passed and a live `verify-change` run
produced a correct verdict card end to end — the new code is composition of
green paths, as specified. OBSERVATION (high): the refusal-first posture
(blocked-not-passed without SDK, UNSIGNED labeled, inconclusive RT published)
is exactly what a technical expert hopes to find and almost never does.

**Strongest reason to reject.**
Every native claim funnels through one unverified choke point: author-machine
provenance. The QNX CI lane is BUILD-ONLY by design (never boots QEMU, never
runs the matrix), cross-SDP reproducibility is unverified, and the second-host
provenance record is an unfilled template (VERIFIED FACT, high:
[JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L20);
[SECOND_HOST_PROVENANCE.md](../../../docs/submission/SECOND_HOST_PROVENANCE.md#L27-L45)).
A hostile expert reads the whole native story as "trust the author's laptop
plus a hash" — and hash-only UNSIGNED packs answer "was it modified" but not
"who attests this ran on QNX" (VERIFIED FACT, high:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L36-L37)).
The exfiltration-risk rationale for no native runner is reasonable, but a
reason is not a second signal.

**Most serious weakness.**
`robotic_arm_virtual` passes schema validation while the host mirror runs it
on differential-drive corridor physics — no arm physics on host or target —
with aliasing merely labeled in scenario records (VERIFIED FACT, high:
[limitations-and-safety.md](../../../docs/limitations-and-safety.md#L33-L37)).
Still present on this branch (item 10, unchanged). OBSERVATION (high): labeled
or not, arm verdicts computed by car physics are one hostile skim away from
"fabricated results," and this is the single finding that could flip a
technical judge from trust to suspicion across *all* verdicts. The backlog's
pre-deadline fix (loud rejection / experimental quarantine) was attempted and
found contract-blocked on this branch (per prior implementer result: planner
returns validator-pinned proposals, 5+ tests pin arm-valid), so the weakness
ships.

**Most memorable part.**
The docs-consistency test gate: 55 tests pinning prose claims (counts, video
status, crypto floor, pack paths, eval status) to `facts.py`, each tracing to
a named past incident (VERIFIED FACT, high:
[recon.md](./recon.md#L171-L174);
[JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L9-L16)).
OBSERVATION (med): process-theatre-shaped, but the red-green test for K1's own
pins plus the v9-overlap pin show the gate bites rather than decorates. A
technical expert remembers "the repo that tests its README."

**Missing evidence.**
(1) A sealed STALE transcript: the credibility keystone (negative control
14/16) remains operator-recorded prose-grade with no sealed transcript in the
packs (VERIFIED FACT, high:
[README.md](../../../README.md#L35-L37)).
(2) A native 2^32 clock-crossing vector — the wrap path is host- and
conformance-tested only (VERIFIED FACT, high:
[limitations-and-safety.md](../../../docs/limitations-and-safety.md#L14-L22)).
(3) Any fix-then-measure on the 5 unsafe accepts / 14 consultation mismatches
on a NEW frozen set (v10) — correctly not done by rerunning v9, but therefore
still open (VERIFIED FACT, high:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L28-L35)).

**Recommended final improvement.**
Seal the STALE transcript into the evidence pack with the same hash-chain +
offline verify as BEFORE/AFTER (backlog B-13). It converts the headline moment
from the strongest claim with the weakest artifact into a sealed negative
control — the highest technical-credibility yield per day of the remaining
options, and it needs only a QEMU rerun, not a redesign.

## 3. Perspective C — Sponsor / competition evaluator ("does this serve QNX and the rules?")

**Strongest reason to award first place.**
Genuine, specific, QNX-native substance in the right category: synchronous
message passing with a fixed versioned protocol and `NONGUARD=0` asserted
every step, a `/dev/genesis/status` resource manager, bounded supervision with
dedicated matrix steps, crash-containment steps whose small blast radius is
argued *from* microkernel isolation, and a 0-warning `qcc` build with 16/16
on-target — in Developer Tooling & Host Tools, where the tool *builds for* QNX
(VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L1-L49);
[COMPLIANCE.md](../../../docs/jury/COMPLIANCE.md#L5-L18)).
QEMU is explicitly allowed and no hardware is required (per qnx-forensics
§Sponsor/tech), and the B2 bonus candidacy (message passing, resmgr, monotonic
timers, RT experiments, supervision, crash containment) is first-class and
measured (VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L51-L56)),
with B2-first surfacing now pinned (filing checklist + storyboard B2 shot:
`cat /dev/genesis/status` + `pidin`, VERIFIED FACT, high:
[FILING_DAY_CHECKLIST.md](../../../docs/submission/FILING_DAY_CHECKLIST.md#L33-L35);
[VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L34)).
Two in-period codelabs cover the B1 second selection (per qnx-forensics M-check
B1). OBSERVATION (high): this is a credible Overall-category plus B2 shape, and
the "complements Momentics/Parasoft/LDRA/VectorCAST, never replaces them"
framing flatters the ecosystem instead of threatening it (VERIFIED FACT, high:
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L187-L189)).

**Strongest reason to reject.**
There is no entry. Video DEFERRED BY OWNER, Devpost NOT submitted, hard stop
15 Dec 2026 14:00 ET with no edits after (VERIFIED FACT, high: README L52-54;
[qnx-forensics.md](./qnx-forensics.md#L25-L30)).
A sponsor evaluator cannot score vapor: every strength above is currently a
branch, not a submission. Worse, the failure mode is silent — a last-week
recording crunch risks a rushed video that violates the <180 s / QEMU-visible /
clean-rights constraints, and a single violation (e.g. third-party music,
over-length ramble past 3:00 that judges need not watch) degrades the whole
submission surface the award depends on. OBSERVATION (high): at this moment the
project's biggest competitor is its own calendar.

**Most serious weakness.**
The scored criterion "Potential Impact" explicitly asks "why real-time QNX is
the right choice" — and the RT-scheduling experiment's headline is
*inconclusive* (5 Nov speedup not reproduced 8 Nov on jury-fixed sources, no
speedup claimed; VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L19-L28)).
Correct honesty, weak ammunition. A hardware-backed rival with measured
deterministic-latency numbers wins this cell outright, and no disclosure
elegance changes the comparison. Combined with QEMU-only + TCG-timing-as-
regression-aid (VERIFIED FACT, high:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L9-L10)),
the entry's QNX story is deep on IPC/architecture and empty on real-time
performance — half the sponsor's love language.

**Most memorable part.**
The one-page honesty contract: "Anything presented as measured comes with
method + raw artifacts; anything pending is labelled pending. That distinction
is the point of the project." (VERIFIED FACT, high — quoted:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L43-L44)).
OBSERVATION (med): sponsor evaluators read hundreds of entries that blur
measured and claimed; a team that publishes its inconclusive result, its 5
unsafe accepts, its prose-grade control, and its zero pilots in the *submission
draft itself* is memorable precisely because it refuses to be impressive.

**Missing evidence.**
(1) The filed submission itself (live URL + committed copy of filed text).
(2) The final video (public YouTube, <180 s, QEMU visible). (3) Owner §3
eligibility self-confirmation (not research-verifiable; VERIFIED FACT, high:
[qnx-forensics.md](./qnx-forensics.md#L124)).
(4) A re-check of Rules + homepage near filing for §11.5 amendments (live
values: 9 named judges, 968 participants at last fetch — OBSERVATION, med, per
[qnx-forensics.md](./qnx-forensics.md#L99-L103)).
All four are owner-gated; the filing-day checklist now exists to catch them
(VERIFIED FACT, high: FILING_DAY_CHECKLIST.md full file).

**Recommended final improvement.**
Record the video BEFORE the final code freeze window, not after: lock the
storyboard's B2 shot and the stale-moment honesty line now, record against a
tagged candidate commit, and keep a sealed-transcript-plus-`verify.py` fallback
segment in the can in case the target is unavailable on recording day (the
storyboard already authorizes this fallback and forbids faking a live run;
VERIFIED FACT, high:
[VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L56-L61)).
Filing early with a good video beats filing late with a perfect tree — the
deadline is the only undefeated rival.

## 4. Official QNX criteria — hostile INTERNAL scoring (prefer the competitor)

Weights are exact per the forensics refresh: four equally-weighted criteria
(25% each implied; no numeric split published), Stage-One pass/fail gate,
tie-breaks in criterion order 1→4. Scores below are **INTERNAL** red-team
simulations, deliberately deflated, scored as a judge hunting for reasons to
prefer a rival. They are not predictions. Internal self-score for contrast:
31/40 (9.5/8/5/8.5); independent reviewer 29/40
([JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L18-L37)).

### Stage-One gate (pass/fail, unweighted)

**Simulated verdict: PASS** (OBSERVATION, high). Theme fit is direct (a tool
that builds/tests QNX 8.0 software) and the required SDK/API application is
genuine (`qcc` native build, on-target matrix, QEMU explicitly allowed).
No plausible gate failure — unless the entry is never filed, which fails
louder than any gate.

### Criterion 1 — Technological Implementation (weight 25%)

**INTERNAL hostile score: 8.0/10** (self: 9.5; reviewer: 9).

- *Supporting evidence.* Real engineering effort at unusual depth: 1395-test
  suite green, deterministic codegen, C/Python conformance vectors, native IPC
  + resmgr + supervision + crash containment on QNX 8.0, fail-closed gate,
  blind AI ladder with published raws, 55 docs-consistency pins (VERIFIED
  FACT, high — §2 award case citations). K1 adds a genuinely composed
  CLI+API+Studio feature with red-first tests, verified live this session.
- *Remaining weakness (why not higher).* QEMU-only; single build host;
  BUILD-ONLY native CI; author-machine-only provenance with the second-host
  record unfilled; arm-physics aliasing ships; stale control unsealed
  (VERIFIED FACT, high — §2 reject/reject citations). A rival with
  hardware-backed native CI takes this cell.
- *Best improvement.* Fill the second-host provenance record (owner rebuild +
  re-verify on a second machine/SDP install, dated note with two host
  fingerprints + matching pack hashes) — the cheapest second signal for every
  native claim (per
  [backlog.md](./backlog.md#L199-L216)).

### Criterion 2 — Design (weight 25%)

**INTERNAL hostile score: 6.5/10** (self: 8; reviewer: 7).

- *Supporting evidence.* Studio is a complete 13-tab workbench (Overview,
  7-stage guided Judge Mode with real run/inspect actions, Designer, C views,
  target runner, Fault Lab, passport, Before/After, graph, twin, CLI index)
  over one shared orchestrator with no mock runs, plus a dependency-free
  dashboard and a node-tested shared verify core; K1's one-click verdict card
  (CLI + Studio Prove button) turns the flagship differentiator into the front
  door (VERIFIED FACT, high:
  [recon.md](./recon.md#L129-L143);
  change.py + cli.py:560 + api.py:487 + studio.html Prove wiring verified this
  session). The new one-page glossary directly attacks the steepest
  comprehension wall (VERIFIED FACT, high:
  [GLOSSARY.md](../../../docs/jury/GLOSSARY.md#L1-L87)).
- *Remaining weakness (why not higher).* "Complete, coherent product
  experience, not just a technical proof of concept" is the criterion text —
  and the self-assessed residual is still "dense single page," no
  screen-reader session (axe scans in CI only), no video, and no cold-reader
  proof that Judge Mode carries a first contact (VERIFIED FACT, high:
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L21)).
  The GLOSSARY exists but its cold-read test needs an owner-recruited human
  who does not exist yet. A rival with a sparse, guided, tested first-run
  experience wins this cell even with 1/10th the features.
- *Best improvement.* Cold-start walkthrough proof: one non-author human goes
  land → Judge Mode → PASS verdict in <5 min, with and without backend, and
  every stumbled term gets fixed in the glossary/Devpost text (backlog B-29 +
  B-14 verification). Design points come from witnessed usability, not from
  tab counts.

### Criterion 3 — Potential Impact (weight 25%)

**INTERNAL hostile score: 4.5/10** (self: 5; reviewer: 5).

- *Supporting evidence.* The case is specific and credible on paper: QNX teams
  shipping requirement changes get reproducible native evidence, stale-binary
  rejection, and offline third-party verification instead of screenshots; the
  complements-not-replaces framing names the incumbents and the seat at the
  table (VERIFIED FACT, high:
  [DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L185-L199)).
  The paired pilot kit (6-task + 3-task tiers, consent + anonymization
  enforced, validated tooling) is ready to measure benefit honestly.
- *Remaining weakness (why lower than self-score).* The criterion demands "a
  credible, specific case for a real problem in a QNX market; why real-time
  QNX is the right choice" — and this entry has zero users, zero invitations,
  unmeasured benefit, AND an inconclusive RT result where the "why real-time
  QNX" argument should be (VERIFIED FACT, high — §1/§3 citations). A hostile
  judge reads the Impact section as "a bet on the evidence loop," i.e. a
  promise, in a criterion that rewards demonstrated or at minimum
  tightly-argued real-world consequence. Any rival with one named beneficiary
  and one measured outcome beats a 4.5. Winners-delta DP2/DP4/DP5 all point
  the same way: validity-scored awards go to named beneficiaries + real-world
  fidelity (per
  [backlog.md](./backlog.md#L93-L95)).
- *Best improvement.* The quick-tier paired pilot with dated raws (see §1).
  Nothing else moves this cell; more prose does not score.

### Criterion 4 — Innovation & AI Creativity (weight 25%)

**INTERNAL hostile score: 7.5/10** (self: 8.5; reviewer: 8).

- *Supporting evidence.* Genuine non-obvious core: contract-aware oracles with
  expectations derived per run from the validated IR, stale-binary behavioral
  refusal, stranger-replayable offline passports, counterfactual `compare` /
  `verify-change` as first-class commands — none of which appears in any
  inspected competitor body (Momentics/Parasoft/LDRA/VectorCAST pages;
  OBSERVATION, high bounded to inspected bodies, per
  [competitors.md](./competitors.md#L262-L372)).
  The AI side is creatively honest rather than creatively applied: a blind,
  frozen, no-format-example eval loop where wrong-kind accepts went 4/3 → 0
  via a registry and every residual is classed and published (VERIFIED FACT,
  high:
  [README.md](../../../README.md#L58-L71)).
  Winners-delta DP4 ("non-AI cores still win… method-fit over fashion") favors
  the deterministic-evidence core over AI theatre (per
  [winners-delta.md](./winners-delta.md#L384)).
- *Remaining weakness (why not higher).* "Creative, non-obvious use of QNX"
  and "genuine understanding of the problem space" cut both ways: the 5
  unsafe accepts / 112 + 14 explained consultation mismatches are open on the
  current blind set with no post-fix measurement on a new frozen set, so the
  AI-creativity half of the cell carries a published failure rate a rival
  judge can quote (VERIFIED FACT, high:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L28-L35)).
  The model path is also narrow (keyword planner + optional LLM consults,
  validator decides) — defensible architecture, but a rival with a genuinely
  novel model-native loop (e.g. spec repair, counterexample-guided synthesis)
  out-narrates "model proposes, gate disposes" on the *creativity* half of
  the label.
- *Best improvement.* Deterministic-layer fix with red-green tests, measured
  on a NEW frozen holdout (v10, separately authored, frozen-before-fix) — on
  a branch, merged only if green well before filing, else ship v9 honestly
  (per
  [backlog.md](./backlog.md#L132-L148)).
  Never rerun v9 on changed code; the freeze policy is load-bearing for the
  whole AI story.

### Hostile total: 26.5/40 (INTERNAL, deflated)

8.0 + 6.5 + 4.5 + 7.5 = **26.5/40**, vs self 31 and reviewer 29. The gap is
concentrated where it hurts most: Impact (−0.5 vs self on a 25%-weight cell
with zero users) and Design (−1.5 vs self for unproven first-contact UX).
Tie-break order (criterion 1 first) means Tech strength only helps ties — it
does not rescue Impact. OBSERVATION (high): even under hostile scoring the
entry's floor is its honesty architecture — every deduction above is armed by
the project's own disclosures, which is exactly why a judge can trust the
remaining points.

## 5. Verdict simulation — would it win?

- **As a branch (today): no.** No video, no filing, no entry. Current award
  probability is exactly zero for administrative reasons, and every day the
  video slips compresses the recording-plus-filing window against an
  unmovable 15 Dec 2026 14:00 ET stop (VERIFIED FACT, high — qnx-forensics
  timeline).
- **As a filed entry (video + Devpost done, nothing else changed): competitive
  finalist, not a safe winner.** The hostile 26.5/40 reflects a real profile:
  elite engineering honesty and QNX depth, a memorable one-metric identity
  ("the wrong binary cannot pass"), and a credible B2 bonus shape — against a
  hollow Impact cell, unproven first-contact design, and single-host native
  provenance. It beats entries that are thinner or less honest; it loses to
  any entry that pairs comparable depth with one measured user outcome or
  hardware-backed RT numbers. The most likely winning rival archetype from
  this evidence: a narrower QNX-native tool with a named beneficiary and a
  measured before/after on real hardware (DP2 + DP4 pattern).
- **Single highest-leverage week (owner-gated):** (1) record + upload the
  video; (2) file Devpost early per the filing checklist; (3) run the
  quick-tier paired pilot; (4) fill the second-host provenance record; (5) get
  one cold reader through Judge Mode. Items 1–2 create the entry; 3–5 attack
  the three lowest hostile cells in weight order. All five need the owner —
  no agent action substitutes.

## 6. Evidence log + unresolved

*Bodies opened this session (branch read via scratch worktree at `8b35839`,
content-identical to shared checkout at same commit; citations use stable
`genesis-rt/` paths):*
`README.md` (L1-120), `docs/jury/JUDGE_SCORECARD.md` (L1-120),
`host/genesis_rt/change.py` (full), `host/genesis_rt/facts.py` (full),
`docs/jury/GLOSSARY.md` (full), `docs/submission/FILING_DAY_CHECKLIST.md`
(full), `docs/submission/SECOND_HOST_PROVENANCE.md` (full),
`docs/jury/KNOWN_LIMITATIONS.md` (full), `docs/jury/WHY_QNX.md` (full),
`docs/jury/WHY_GENESIS_RT.md` (full), `docs/jury/START_HERE.md` (L1-60),
`docs/submission/DEVPOST_FINAL_DRAFT.md` (L180-239),
`docs/limitations-and-safety.md` (L1-40),
`docs/submission/VIDEO_STORYBOARD_DEFERRED.md` (L1-71),
`docs/jury/COMPLIANCE.md` (L1-20); K1 wiring grepped in `cli.py` (L192-196,
L560-571), `api.py` (L487, L587), `studio.html` (L462-469, L1042, L2180-2190);
`tests/integration/test_change.py` + `test_changes_api.py` presence confirmed.
*v3-research inputs opened:* `qnx-forensics.md`, `demo-story.md`, `recon.md`,
`backlog.md`, `competitors.md` (§§1-3), `killer-feature.md`,
`winners-delta.md` (patterns §, L360-405). *Prior-result handoff index read in
full* (284 lines, no truncation); 8 prior summaries reused as discovery
pointers, all claims above re-grounded in the bodies listed here.
*Commands executed:* scratch worktree create (detached `8b35839`) + remove;
`test_change.py` → 8 passed; live `verify-change` on cell broken→fixed →
FAIL→PASS card with knob table + 3 fixed + chains valid (see §1); worktree +
shared checkout both verified clean afterward.

*Unresolved / not verified this session:*
U1: full 1395-test suite execution (prior implementer result reports 1395
passed EXIT 0; this session ran the 8 K1 integration tests + 1 live CLI run
only). U2: browser E2E / Studio Prove-button click path (wiring grepped, not
clicked). U3: native QNX campaign re-run (needs SDP 8.0 + QEMU). U4: AI-eval
reproduction (forbidden by freeze policy). U5: pack file-count wording B-19
(recon-era observation, not re-checked on this branch). U6: exact Devpost form
fields (login-gated); owner §3 eligibility; live judge roster / participant
count (re-check near filing). U7: all owner-human acts (video, filing, pilots,
cold read, SR session, second host).


