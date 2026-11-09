# GENESIS RT — Demonstration + Storytelling Strategy (v3 research)

> DOCS ONLY. No media produced, no contact, no submission, no release/tag,
> no secrets, no history rewrites. Frozen evals untouched
> (`genesis-rt/evals/*.json`, `evals/results/*` — not opened, not cited by value).
> Reader posture on `genesis-rt`: this file lives under `v3-research/` only.
>
> Method: every factual claim reuses a body opened in this session (see §10).
> Search output located candidates only. Labels:
> **VERIFIED FACT** (read in the cited body) / **OBSERVATION** (synthesis) /
> **ASSUMPTION** (inference, flagged), with confidence high/med/low.
> No metrics, scores, feedback, or testimonials invented. Numbers are quoted
> from cited bodies only.
>
> Rule anchor: final video **DEFERRED BY OWNER**, Devpost **NOT submitted**
> (VERIFIED FACT, high:
> [README.md](../../../README.md#L52-L54),
> [DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L1-L6)).
> Competition rules: video <180 s (treat as mandatory), must show the project
> on the target (QEMU), public YouTube only
> (per [qnx-forensics.md](./qnx-forensics.md#L65-L70)).

## 0. The ONE memorable moment

**"The wrong binary cannot pass."**

The stale control: v2 contract run against the v1-built binary fails **14/16**,
exactly on `estop_target` + `v2_transitions` — the changed behavior and nothing
else. VERIFIED FACT (high):
[README.md](../../../README.md#L29-L39),
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L112-L115).

Why this moment (OBSERVATION, high):

- It is the only beat competitors cannot mirror with a slide: it proves the
  oracle derives expectations from the validated IR per run, not from fixed
  thresholds (per [competitors.md](./competitors.md#L331-L336)).
- It maps to the winners-delta pattern DP3 "one-metric identities travel"
  (per [winners-delta.md](./winners-delta.md#L376-L387)):
  risk index, no-loss rule, dead-man's switch, 45-minute patch — ours is
  "14/16 on exactly the changed steps."
- It survives the judging pile as one sentence, and it is honest: the control
  is operator-recorded, prose-grade, no sealed transcript ships in the packs
  (VERIFIED FACT, high: same README lines). Say so on camera in one line —
  refusal-first honesty is the brand
  (per [WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L40-L48)).

Every timed cut below builds to this moment and lands it before the end card.

## 1. Pitch ladder

### One sentence (memorability statement)

> GENESIS RT doesn't merely generate code. It generates inspectable evidence
> about the behavior of the code.

VERIFIED FACT (high — quoted):
[WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L50-L53).

### 15-second pitch (~35 words)

> Embedded test evidence is usually screenshots. GENESIS RT compiles a machine
> contract into native QNX software plus a hash-linked evidence passport —
> and the wrong binary cannot pass: stale code fails exactly the changed
> checks. Replayable by anyone, no SDK needed.

Claim grounding: "screenshots" pain per
[WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L3-L9);
passport + stale control per README lines above; SDK-free replay per
[START_HERE.md](../../../docs/jury/START_HERE.md#L10-L22).

### 30-second pitch (~70 words)

> When a requirement changes — say a mobile robot gains a guarded safe-stop —
> teams must prove the target matches. GENESIS RT turns that contract into a
> native QNX 8.0 multi-process controller, runs a 16-check matrix on QEMU,
> breaks it on purpose with seeded faults, and seals a hash-linked passport.
> Change v1 to v2 and both pass 16/16 under their own contract — but the old
> binary against the new contract fails exactly the changed steps. Proof, not
> promises.

Grounding: AMR v1→v2 safe-stop per
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L26-L34);
16/16 + packs per README L29-39; fault campaign per
[DEMO_WALKTHROUGH.md](../../../docs/jury/DEMO_WALKTHROUGH.md#L24-L46).

### 60-second pitch (use the README pitch, verbatim-adjacent)

> Embedded control prototypes are slow to build and their test evidence is
> usually a pile of screenshots. GENESIS RT turns a constrained machine
> description into a typed, inspectable specification (Machine IR), generates
> a native QNX 8.0 multi-process controller, runs it, breaks it on purpose
> with seeded fault injection, and produces a hash-linked evidence passport
> where every green verdict links to a real execution trace. One convincing
> proof-driven demo beats twenty speculative features.

VERIFIED FACT (high — quoted):
[README.md](../../../README.md#L17-L25).

## 2. Full-length demo beats (live / judge-guided, ~5 min)

Chain: hook → pain → interaction → intelligence → result → verification →
transformation → differentiation → impact. Each beat names the exact command
or screen; all commands exist on the current tree
(VERIFIED FACT, high: storyboard §"Exact commands",
[VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L41-L54)).

| # | Beat | What the judge sees | Evidence it rests on |
|---|---|---|---|
| 1 | HOOK (0:00) | "A requirement changed — prove the target matches." Studio overview screenshot with BEFORE/AFTER proof cards. | README hero image line 15; storyboard beat 1 |
| 2 | PAIN (0:30) | Folklore evidence: hand-wired IPC glue, hand-run fault checks, screenshots that rot. "Nobody can say what broke or whether green means anything." | WHY_GENESIS_RT problem § (L3-9) |
| 3 | INTERACTION (1:00) | Judge path, 2 commands, no SDK: `run_verified_demo.py` → `verdict: PASS`; `replay.py <passport>` → `chain: valid, gate: PASS`; load passport in `ui/dashboard.html`, every verdict links to data. | START_HERE §1 (L10-22); DEMO_WALKTHROUGH Demo A |
| 4 | INTELLIGENCE (1:45) | The contract-aware oracle: expectations (ALLOW/DENY/SAFE_STOP) derive from the validated IR per run — show AMR v2 guarded safe-stop lines, then the native matrix transcript 16/16. Optional: model proposes, deterministic gate disposes (v9: 150/160, 5 unsafe disclosed). | DEVPOST_FINAL_DRAFT "How we built it" + "AI disclosure" (L64-80, L120-142); WHY_QNX native § |
| 5 | RESULT (2:30) | BEFORE/AFTER side by side: v1 and v2 contracts, each 16/16 PASS sealed under its own contract; `compare` shows the contract knob, regenerated C, changed binary hashes, fixed scenarios. | README L29-39; DEMO_WALKTHROUGH Demo C; storyboard beat 6 |
| 6 | VERIFICATION (3:15) | Offline stranger replay: `verify.py <pack>` → VERIFY OK on both Omega2 packs; state hash-only UNSIGNED honestly in one line; `qnx_verified: true` on target packs vs `false` on host. | README L37-39; START_HERE L19; storyboard beat 7 |
| 7 | TRANSFORMATION (3:45) | **THE MOMENT.** Stale control: v2 contract + v1 binary → 14/16 FAIL exactly on `estop_target` + `v2_transitions`. "The wrong binary cannot pass." One-line honesty: operator-recorded, prose-grade, no sealed transcript. | README L35-37; DEVPOST_FINAL_DRAFT L112-115; storyboard beat 8 |
| 8 | DIFFERENTIATION (4:15) | "It complements Momentics, Parasoft, LDRA, VectorCAST — never replaces them." They do standards/coverage/profiling; GENESIS RT does change-level behavioral verdicts + stale refusal + offline passports. Fail-closed gate: missing/skipped/crashed/tampered ⇒ FAIL. | DEVPOST_FINAL_DRAFT L187-189; WHY_GENESIS_RT L31-33; competitors.md §4-6 |
| 9 | IMPACT (4:45) | Who it serves: QNX teams shipping requirement changes on prototypes; reviewer/auditor gets a dossier ZIP (report + raw + offline verify) instead of screenshots. Honest close: QEMU-only, no cert, human benefit not yet measured — the bet is the evidence loop. | DEVPOST_FINAL_DRAFT L185-199; START_HERE §3 dossier refs; WHY_QNX bonus § |

OBSERVATION (med): this 9-beat arc doubles as the live-judge tour (Studio
Guided demo tab has 7 stages; VERIFIED FACT, high per
[recon.md](./recon.md#L129-L134))
and as the narration spine for the recorded cut — same beats, tighter words.

## 3. Timed video cuts (owner records; DOCS ONLY here)

Hard constraints (all VERIFIED FACT, high, per qnx-forensics §Video rules):

- Duration STRICTLY under 3:00 — target **2:45 + 15 s buffer**; judges need not
  watch beyond 3:00, so treat <180 s as mandatory.
- Must show the project functioning on the intended target: **QEMU/QNX 8.0
  terminal visible** (boot marker, `identity` output, native matrix transcript).
- **Public YouTube only**; link on the Devpost form.
- English narration or captions throughout; no third-party marks/music/footage
  (all visuals: owner's terminal + Studio + QEMU console).
- Record AFTER the final merge; state the commit SHA in the description.
- If the target is unavailable on recording day: show sealed transcripts +
  `verify.py` replay and say so on camera — **never fake a live run**.

Source for all of the above: the deferred storyboard
([VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L1-L25),
[VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L56-L61)).

### 15-second cut (~35 words)

> [0:00 Studio BEFORE/AFTER cards] "A requirement changed. Does the target
> match?" [0:05 terminal: verify.py → VERIFY OK] "GENESIS RT proves it on
> QNX." [0:10 stale result 14/16] "The wrong binary cannot pass."
> [0:13 title card + repo URL]

### 30-second cut (~70 words)

> [0:00–0:08 pain: screenshots rot] "Test evidence is usually screenshots."
> [0:08–0:16 QEMU identity + matrix 16/16] "GENESIS RT compiles the contract
> into native QNX software and runs it." [0:16–0:24 BEFORE/AFTER + verify.py
> OK] "Both contracts pass — sealed, replayable." [0:24–0:30 stale 14/16]
> "And the wrong binary cannot pass." [title card]

### 60-second cut (~140 words)

> 0:00–0:10 hook: "A requirement changed — prove the target matches."
> 0:10–0:20 contract excerpt (AMR v2 safe-stop lines).
> 0:20–0:35 QEMU: probe → identity (`QNX qnxqemu 8.0.0 x86_64`) → matrix 16/16.
> 0:35–0:45 BEFORE/AFTER compare side by side, both 16/16.
> 0:45–0:55 verify.py → VERIFY OK; "hash-only, unsigned — honestly labeled."
> 0:55–1:00 THE MOMENT: stale 14/16, "the wrong binary cannot pass." Title card.

### 90-second cut (~210 words)

60-second cut plus: 10 s fault-lab tail (injected faults caught, oracle
verdicts), 10 s `/dev/genesis/status` resmgr telemetry on target, 10 s
release-decision panel (fail-closed verdict) before the closing line:
"change-verification and evidence for QNX — replayable by anyone."

### Full 2:45 cut (narrative authority: the deferred storyboard)

Follow the 9-shot timed narrative in
[VIDEO_STORYBOARD_DEFERRED.md](../../../docs/submission/VIDEO_STORYBOARD_DEFERRED.md#L27-L39)
verbatim (problem → requirement → compile → QNX execution → faults →
BEFORE/AFTER → passport → stale rejection → value prop, ≈380 words at
140 wpm). Do not improvise a different arc — the storyboard is already
verified against the tree's real commands and the compliance checklist.
Recording notes (1080p, font ≥18pt, hide personal paths, never show the
target password): same file, L63-71.

OBSERVATION (high): the historical W12 cut
(`docs/demo/genesis-rt-demo-w12.mp4`, 154.664 s) predates Studio and is
explicitly NOT the submission video (VERIFIED FACT, high:
[README.md](../../../README.md#L52-L54)).
Never upload it as the entry.

## 4. FAQ (short answers, all evidence-linked)

1. **What is GENESIS RT?** A contract-aware change-verification and evidence
   layer for QNX: machine contract → validated IR → deterministic native QNX
   8.0 controller → seeded faults → hash-linked evidence passport + fail-closed
   gate. ([README.md](../../../README.md#L17-L25),
   [WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L11-L22))
2. **What do I need to verify it?** A clone + Python + `pytest`/`pyyaml`;
   two commands, no SDK: `run_verified_demo.py`, then `replay.py <passport>`.
   ([START_HERE.md](../../../docs/jury/START_HERE.md#L10-L22))
3. **Where is the QNX-native proof?** Omega2 BEFORE/AFTER packs, 16/16 PASS
   sealed on both contracts, `qnx_verified: true`, offline `verify.py`.
   ([README.md](../../../README.md#L29-L39))
4. **What is genuinely new?** Not codegen — the evidence loop: IR-derived
   oracles, stale-binary refusal, stranger-replayable passports, `compare`
   as a first-class command.
   ([WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L24-L38))
5. **Does it replace Momentics / Parasoft / LDRA / VectorCAST?** No — it
   complements them; no static analysis, coverage, MISRA, or qualification
   story is claimed.
   ([DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L185-L199),
   [competitors.md](./competitors.md#L368-L372))
6. **What role does AI play?** Optional planner; model proposes, deterministic
   validator disposes; measured on blind holdouts (v9: 142/150/150, 5 unsafe
   disclosed), never authorizes safety or release.
   ([README.md](../../../README.md#L58-L71))
7. **What are the limits?** QEMU-only, no safety certification, host faults
   simulated (labeled `qnx_verified`), packs UNSIGNED hash-only, no pilots,
   human benefit unmeasured, video pending.
   ([README.md](../../../README.md#L8-L13),
   [competitors.md](./competitors.md#L79-L85))
8. **What is the license?** Apache-2.0; core stdlib-only.
   ([START_HERE.md](../../../docs/jury/START_HERE.md#L10-L16),
   [recon.md](./recon.md#L25-L28))

## 5. The 10 hardest judge questions (evidence-backed answers)

**Q1. "Isn't this just a code generator with extra steps?"**
No. The generator is the boring part; the product is the evidence loop
around it: strictly validated contracts whose limits provably drive runtime
behavior, a fail-closed gate (missing/skipped/crashed/tampered/recycled ⇒
FAIL), stranger-replayable passports, and counterfactual `compare` as a
first-class command. VERIFIED FACT (high):
[WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L24-L38).
A generator shows you source; GENESIS RT shows you the contract knob, the
regenerated files, the changed binary hashes, and the fixed scenarios side
by side (Demo C,
[DEMO_WALKTHROUGH.md](../../../docs/jury/DEMO_WALKTHROUGH.md#L48-L69)).

**Q2. "Why QNX — why not Linux + sockets?"**
Because the generated system is shaped by Neutrino primitives and the
evidence is about those primitives behaving: synchronous message passing
with a fixed versioned protocol and `NONGUARD=0` asserted every step,
`/dev/genesis/status` resmgr telemetry, `CLOCK_MONOTONIC` RFC-1982
wrap-safe arithmetic, bounded supervision, and crash-containment matrix
steps whose blast radius is small and checkable *because* of microkernel
isolation. The C policy is proven identical to its Python mirror by
compiled conformance vectors; the 16-step matrix runs on QNX 8.0
(`qcc -Vgcc_ntox86_64`, 0 warnings). VERIFIED FACT (high):
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L1-L49).

**Q3. "QEMU-only, no hardware — is the 'native' claim real?"**
"Native" means QNX 8.0 binaries built with `qcc` running on a QNX 8.0
kernel (QEMU x86_64) — verified: 0-warning native build, 16/16 on-target
matrix, `qnx_verified: true`. QEMU-only is disclosed, not hidden; no
physical hardware, no HAM, no attestation, and TCG timing is explicitly a
regression aid, not a guarantee (the RT-scheduling experiment reported
**inconclusive** rather than claim a speedup). VERIFIED FACT (high):
[README.md](../../../README.md#L8-L13),
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L19-L32).
QEMU is explicitly allowed by the rules (per qnx-forensics §Sponsor/tech).

**Q4. "The stale control is prose-grade — why should I trust your headline moment?"**
You should trust it exactly as far as labeled: operator-recorded negative
control, no sealed transcript in the packs — and we say so in the README,
the draft, and (planned) on camera. What *is* sealed is everything around
it: both 16/16 contracts, the IR-derived oracle mechanism, and the offline
replay. The prose-grade label is the point: a team that marks its own best
moment as unsealed can be believed about what it marks sealed. VERIFIED
FACT (high):
[README.md](../../../README.md#L29-L39),
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L112-L115).
Sealing the stale transcript is future work (per recon §10).

**Q5. "5 unsafe accepts out of 112 — isn't your AI dangerous?"**
The 5 unsafe accepts (same 5 deterministic-layer cases on all providers, 0
wrong-kind) are disclosed with per-case raws and a consultation audit —
and the architecture makes them non-shippable: the model proposes, the
deterministic validator disposes; the model can never authorize safety,
mark a build verified, or grant release eligibility (regression-pinned).
Default planner is the offline deterministic keyword planner; no LLM is
bundled. VERIFIED FACT (high):
[README.md](../../../README.md#L58-L71),
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L120-L142).
OBSERVATION (high): publishing failures with layer attribution is the
cheapest credibility available (transferable-principles argument, per
competitors.md §1).

**Q6. "Passports are UNSIGNED hash-only — can't evidence be forged?"**
Hash-only UNSIGNED is stated, with the exact `--trust local → exit 2`
behavior — and forgery is tested, not theorized: 13+ forgery classes
refused, 24 adversarial passport tests, tampered/version-unknown passports
raising `InvalidPassport`, `no-test ⇒ no-pass`. VERIFIED FACT (high):
[WHY_GENESIS_RT.md](../../../docs/jury/WHY_GENESIS_RT.md#L31-L36),
competitors.md §6.3. The trust claim is tamper-*evident* offline replay by
a stranger, not signed provenance — signatures exist as CLI (`sign-pack` /
`verify-pack`) but packs ship unsigned, disclosed as such (per recon §8).

**Q7. "No pilots, no measured human benefit — where is the impact?"**
There is none measured, and we do not imply any: `HUMAN USER BENEFIT NOT
YET MEASURED` governs; the paired pilot kit (6-task + 3-task tiers, consent
+ anonymization enforced) is ready with zero invitations sent. Internal
self-score holds Potential Impact at 5/10 for exactly this reason.
VERIFIED FACT (high):
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L185-L199),
[JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L18-L23).
The demonstrable impact today is reproducible native evidence,
stale-binary rejection, and offline third-party verification — a bet on the
evidence loop, not on production readiness.

**Q8. "How is this different from Parasoft / VectorCAST / LDRA / Momentics?"**
Those do standards-shaped verification (MISRA/AUTOSAR/CERT, MC/DC,
TÜV-backed qualification), live runtime profiling (Momentics instrumented
kernel), and management-grade trending/ALM traceability — all credited as
their edge. None of their inspected bodies describes contract-aware oracles
derived per run from a validated spec, a before/after native comparison
with stale-binary refusal, or a stranger-replayable offline passport.
GENESIS RT claims no static analysis, coverage, MISRA, qualification, or
ALM integration. OBSERVATION (high, bounded to inspected bodies) + VERIFIED
FACT non-claims: [competitors.md](./competitors.md#L262-L372).

**Q9. "1376 tests — isn't that a vanity number?"**
It is a collected count with honest skips, not a pass-fabrication: 1376
collected SDK+axe (0 skips on the owner box), 1370 + 6 honest SDK-gated
skips SDK-free; without an SDK, QNX steps report blocked/skipped, never
passed. The suite includes 24 adversarial, 73 planning-unit, 32 real-browser
E2E, and 51 docs-consistency pins (each tracing to a past incident), plus
16/16 on-target + 1000 perf samples + 9/9 native fault-injection over IPC.
VERIFIED FACT (high):
[START_HERE.md](../../../docs/jury/START_HERE.md#L24-L36),
[recon.md](./recon.md#L167-L201),
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L64-L80).

**Q10. "Judges may never run the project — does the submission stand alone?"**
Yes by design: the Devpost text names exact QNX files/functions/output/demo,
the <180 s public-YouTube video shows QEMU execution, both Omega2 packs
verify offline with stdlib-only `verify.py`, the dossier ZIP carries report
+ raw data + offline verify, and `ui/dashboard.html` inspects any passport
from disk with no backend. The 2-minute SDK-free path exists for judges who
do run it. VERIFIED FACT (high): text+video requirements per qnx-forensics
§§Video/Submission-fields; dossier per recon §4; dashboard per
[START_HERE.md](../../../docs/jury/START_HERE.md#L10-L22).
Unresolved: judges-may-not-run is carried as U3 in qnx-forensics — the
mitigation is stand-alone text + video, not persuasion.

## 6. Differentiation / memorability statement (submission-ready prose)

> Every toolchain generates code; GENESIS RT generates the proof that the
> code matches the requirement — on QNX, under a contract-aware oracle, with
> the wrong binary provably unable to pass. Change one requirement, re-verify
> natively, and hand any stranger a passport they can replay offline in
> minutes. It complements the established verification suites instead of
> replacing them, refuses to impress dishonestly (inconclusive RT result,
> disclosed unsafe accepts, prose-grade stale label, UNSIGNED trust, zero
> pilots — all published), and stays forkable after judging under Apache-2.0.

Grounding: each clause traces to §4/Q&A citations above; "complements, never
replaces" per
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L185-L189);
forkability per competitors.md §7.5. OBSERVATION (med): this paragraph is the
answer to "why pick it" in Developer Tooling & Host Tools, compressed from
competitors.md §7.

## 7. Optimized submission-field TEXT (NEVER submit — owner files)

Derived from
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L1-L23)
(form fields) with storytelling tightening. Field list per qnx-forensics
§Submission fields. **Do not paste anywhere; the owner completes the form.**

- **Title:** GENESIS RT — The Physical World Compiler
- **Tagline:** From machine intent to QNX-native software — with verifiable
  proof. (Keep: names the category promise + the differentiator in 11 words.)
- **Category:** Developer Tooling & Host Tools.
- **Repository:** https://github.com/toskaman/genesis-rt (must stay public
  through 29 Jan 2027; re-check at filing.)
- **Codelab URL (B1 bonus box):**
  https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/README.md
- **Video URL:** PENDING — owner publishes the final cut (public YouTube,
  strictly <3:00, QEMU footage on screen, English, clean rights) then pastes
  the link. Storyboard: `docs/submission/VIDEO_STORYBOARD_DEFERRED.md`.
- **Build/run instructions (QNX version + target + toolchain):** QNX SDP 8.0,
  `qcc` 12.2.0 (`gcc_ntox86_64`), QEMU x86_64; judge path per §4 Q2 above;
  full SDK path in `docs/quickstart-qnx8-qemu.md`. (Versions VERIFIED FACT,
  high, per DEVPOST_FINAL_DRAFT L92-94.)
- **Text description:** use the Devpost draft sections (Inspiration → What it
  does → How we built it → How we use QNX → Technical proof → AI disclosure
  → Potential impact → Try it), ending every claim-heavy paragraph with its
  evidence path. Mandatory inclusions: exact QNX files/functions/output/demo
  (rules require it); the one-line stale honesty note; the one-line UNSIGNED
  note; `HUMAN USER BENEFIT NOT YET MEASURED`. (Requirements per
  qnx-forensics §§Sponsor-tech/Submission-fields.)
- **B2 surfacing (no extra field — from the Submission itself):** name message
  passing, resmgr, monotonic timers, RT experiments, supervision, crash
  containment in "How we use QNX" AND show at least two on screen in the
  video (matrix transcript + `/dev/genesis/status` read). Candidacy per
  [WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L51-L56).

## 8. Story risks + mitigations

| Risk | Mitigation (docs-side) |
|---|---|
| Judge watches only the video (U3) | Video carries hook→moment→proof alone; text repeats every number with paths |
| "Another code generator" dismissal | Open with the stale moment, not the pipeline; Q1 answer ready |
| AI-safety suspicion from 5/112 | Lead with "model proposes, gate disposes" + regression pin; never bury the 5 |
| Over-claiming temptation | Every boast paired with its bound (QEMU-only, UNSIGNED, prose-grade, no pilots) — the honesty IS the pitch |
| Production drift (owner records late) | Record after final merge; state commit SHA in description; storyboard L23-25 |
| Faked-live-run temptation | Storyboard fallback: sealed transcripts + verify.py replay, said on camera |

## 9. Unresolved / owner-deferred

- U1: final video recording, YouTube upload, URL paste — OWNER action
  (BLOCKED item M8, per qnx-forensics §3). Nothing in this file substitutes.
- U2: Devpost form field labels/validation (login-gated) — re-check at filing
  (carried from qnx-forensics U1).
- U3: owner §3 eligibility self-confirmation (carried from qnx-forensics U4).
- U4: judge roster / participant count are live values (carried from
  qnx-forensics U5).
- U5: stale-transcript sealing (future work) — until then, "prose-grade" stays
  in every telling of the moment.

## 10. Evidence log (bodies opened this session)

- `genesis-rt/README.md` (L1-120 window) → pitch, Omega2 proof, AI v9, status.
- `genesis-rt/docs/jury/WHY_GENESIS_RT.md` (full) → pain, approach, novelty,
  boundaries, one-line memory statement.
- `genesis-rt/docs/jury/START_HERE.md` (full) → 2-min judge path, suite counts,
  native file pointers.
- `genesis-rt/docs/submission/VIDEO_STORYBOARD_DEFERRED.md` (full) → timed
  narrative, exact commands, compliance checklist, recording notes.
- `genesis-rt/docs/jury/DEMO_WALKTHROUGH.md` (L1-100) → Demos A/B/C with exact
  outputs.
- `genesis-rt/docs/jury/WHY_QNX.md` (L1-80, full file) → native substance,
  inconclusive RT, bonus candidacy.
- `genesis-rt/docs/submission/DEVPOST_FINAL_DRAFT.md` (L1-219) → form fields,
  proof table, AI disclosure, impact, judge path.
- `genesis-rt/docs/jury/JUDGE_SCORECARD.md` (L1-80) → internal self-scores
  (31/40; reviewer 29/40), residuals.
- `v3-research/recon.md`, `v3-research/winners-delta.md`,
  `v3-research/qnx-forensics.md`, `v3-research/competitors.md` (full reads) →
  counts, patterns DP1-DP5, rules/constraints, positioning wedge.
- Prior-result handoff index (full read, 143 lines, no "(more lines below)") →
  4 prior summaries reused as discovery pointers; all claims above re-grounded
  in the bodies listed here.
