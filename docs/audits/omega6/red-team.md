# GENESIS RT (titan/omega6-product-proof) — OMEGA6 Red-Team Audit

> READ-ONLY on the repo. No contact, no submission, no media produced, no
> releases/tags, no secrets, no force-push, no history rewrite, no
> planner/validator/IR/target-C/eval changes (frozen evals untouched —
> `evals/*.json`, `evals/results/*` never opened, never cited by value).
> Branch read via a PRIVATE scratch worktree
> (`$env:TEMP\omega6-redteam-scratch`, detached HEAD `fa9aeb7`), read-only;
> shared checkout untouched (verified clean before and after); worktree
> removed after reading. This file under `omega6-research/` is the only write.
>
> Method: every factual claim reuses a body opened in this session (see §7)
> or a command executed in the scratch worktree this session. Search output
> located candidates only. Labels: **VERIFIED FACT** (read in the cited body
> and/or executed this session, confidence high/med/low) / **OBSERVATION**
> (synthesis) / **ASSUMPTION** (inference, flagged). No metrics invented. All
> numbers are quoted from cited bodies or from commands executed this
> session. Scores in §4 are **INTERNAL** hostile simulations, deliberately
> deflated, not predictions of official judging.
>
> Rule anchor: final video **DEFERRED BY OWNER**, Devpost **NOT submitted**
> (VERIFIED FACT, high:
> [FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L10-L13)).
> Official criteria: four **equally weighted** (25% each) — Technological
> Implementation, Design, Potential Impact, Innovation & AI Creativity — plus
> a Stage-One pass/fail gate and criterion-1-first tie-breaks (VERIFIED FACT,
> high: [qnx-forensics.md](../titanv3/qnx-forensics.md#L32-L41)).
> Branch under review: `origin/titan/omega6-product-proof` = `fa9aeb7`
> "OMEGA6 count sync: 1431 collected (1425+6 SDK-free, 41 E2E, 61 pins)"
> (VERIFIED FACT, high — worktree HEAD read this session; 19 commits ahead
> of `origin/main@cdd70da`).
> Prior baselines: v3 red-team hostile INTERNAL 26.5/40, self 31/40,
> independent reviewer 29/40 (VERIFIED FACT, high:
> [red-team.md](../titanv3/red-team.md#L270-L278));
> OMEGA6 self-delta draft claims 31.5/40 (+0.5 Design only,
> VERIFIED FACT, high:
> [SCORECARD_DELTA_OMEGA6.md](../../../docs/jury/SCORECARD_DELTA_OMEGA6.md#L12-L21)).

## 1. Perspective A — Product / impact judge ("who is this for, and does it matter?")

**Strongest reason to award first place.**
The flagship loop is now demonstrable end to end in seconds by three
independent paths: a scripted host stale-refusal (STALE, exit 0),
a one-click browser verdict card, and a CLI FAIL→PASS card — all re-ran in
this session (VERIFIED FACT, high: `scripts/demo_stale_refusal.py` → STALE
in 0.0 s product time, exit 0;
[demo_stale_refusal.py](../../../scripts/demo_stale_refusal.py#L39-L70);
live `verify-change` on cell broken→fixed → FAIL→PASS with knob table
`max_linear_speed_mps: 0.3 → 1.2`, 3 fixed scenarios, both chains valid,
2.47 s wall, exit 0). The landing page now front-doors the value
proposition (hero line + 30 s card + one-click change-proof card) instead
of burying it in tabs (VERIFIED FACT, high:
[studio.html](../../../ui/studio.html#L219-L244)).
OBSERVATION (med): the product finally has a 60-second stranger path that
is measured, budgeted, and rehearsed — the single biggest product delta of
OMEGA6.

**Strongest reason to reject.**
No human has ever used it for real work, and OMEGA6 added zero humans:
`HUMAN USER BENEFIT NOT YET MEASURED` still governs, zero pilots, zero
invitations, zero buyer conversations, zero cold readers, zero
screen-reader sessions (VERIFIED FACT, high:
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L201-L206);
[HARDEST_QA_LIVE.md](../../../docs/jury/HARDEST_QA_LIVE.md#L8-L13)).
The new persona/buyer/win-loss/bit-rebuild prose is explicitly labeled
hypothesis/unvalidated (VERIFIED FACT, high:
[DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L208-L229)).
A product judge comparing this against any entry with one named user and
one measured outcome files GENESIS RT under "impressive prototype, no
evidence of use" — OMEGA6 narrowed the demo gap, not the evidence gap.
OBSERVATION (high): candor about zero users earns trust but zero points;
the criterion scores impact, not honesty about its absence.

**Most serious weakness.**
The "30-second cold start" front-door promise is timed only in its cheapest
segment. The timed portion is product runtime (~2 s); the unmeasured
portion is everything a cold judge actually waits for — `pip install -e
".[dev]"`, repo clone, first backend boot — which is not timed anywhere
and can exceed 30 s on a cold box by itself (VERIFIED FACT, high: the
README chain
[README.md](../../../README.md#L9-L14)
lists install→validate→demo but
[REPRODUCE.md](../../../docs/jury/REPRODUCE.md#L25-L34)
times only the demo+replay steps). OBSERVATION (high): a judge who times
the literal README chain from zero and lands past 30 s will read the
headline as marketing — the one thing this entry cannot afford.

**Most memorable part.**
"The wrong binary cannot pass" — now demonstrated live in 0.0 s by the
stale script with the archived 14/16 behavioral refusal one replay away,
and the hero line front-doored on README + Studio + Devpost (VERIFIED
FACT, high: [DEMO_BEATS_TIMED.md](../../../docs/jury/DEMO_BEATS_TIMED.md#L8-L14);
hero pin
[test_docs_consistency.py](../../../tests/unit/test_docs_consistency.py#L806-L813),
re-ran green inside the 61-pin suite). OBSERVATION (high): the one-metric
identity survived productization intact — still one sentence, still sticky,
now clickable.

**Missing evidence.**
Any external human signal: one pilot record, one cold-reader note, one
screen-reader session log, one second-host provenance fill. All four
protocols/templates exist and all four remain unfilled/unexecuted after
OMEGA6 (VERIFIED FACT, high: SR K1-path script is explicitly "NOT
executed",
[SCREEN_READER_CHECKLIST.md](../../../docs/design/SCREEN_READER_CHECKLIST.md#L39);
pilot kit zero invitations,
[HARDEST_QA_LIVE.md](../../../docs/jury/HARDEST_QA_LIVE.md#L8-L13)).
The product judge's file still contains zero lines written by anyone but
the author and agents.

**Recommended final improvement.**
Run the quick-tier paired pilot exactly per protocol and publish dated
raws — the only move that adds Impact points rather than Impact prose.
If owner bandwidth allows exactly one human act before filing, the pilot
beats the video-adjacent work on criterion weight: video creates the
entry, but the pilot is the only rescue for a 25%-weight cell sitting at
~half marks (OBSERVATION, high — unchanged from v3, still binding).

## 2. Perspective B — Technical expert ("is it real engineering, and is it sound?")

**Strongest reason to award first place.**
Claims that survived hostile re-execution this session, in a scratch
worktree the implementer never touched: 17/17 K1 integration tests,
46/46 dossier+stale tests, 61/61 docs-consistency pins, 9/9 real-browser
Prove tests (30.3 s wall), A1 race test 10× with 0 fails, both Omega2
packs VERIFY OK 16/16 with recursive counts 35/37, vulture clean at 80%,
and — the strongest single verification — a from-scratch `qcc -O2`
rebuild of all 6 native binaries reproducing the published footprint
table **bit-exact** (text/data/bss/file-bytes, 0 warnings) (VERIFIED
FACT, high: all commands §7; footprint source
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L51-L71)).
The A3 traversal fix is genuine fail-closed hardening (`valid_op_id`
before any disk read;
[dossier.py](../../../host/genesis_rt/dossier.py#L129-L146),
regex `op-[0-9a-f]{12}`,
[target.py](../../../host/genesis_rt/target.py#L71-L92)),
covered by 7 dossier + 8 change-id hostile params (VERIFIED FACT, high:
[test_dossier.py](../../../tests/integration/test_dossier.py#L164-L178);
[test_change.py](../../../tests/integration/test_change.py#L95-L109)).
OBSERVATION (high): this is the rare branch where the auditor's best
falsification attempt (independent native rebuild) returned an exact
match — that is what engineering evidence is supposed to look like.

**Strongest reason to reject.**
Every native claim still funnels through one unverified choke point:
author-machine provenance. The QNX CI lane is BUILD-ONLY by design, the
second-host record is still an unfilled template, cross-SDP
reproducibility is unverified, and packs remain hash-only UNSIGNED
(VERIFIED FACT, high — unchanged since v3; single-host gap restated in
[HARDEST_QA_LIVE.md](../../../docs/jury/HARDEST_QA_LIVE.md#L15-L21)).
My bit-exact rebuild used the same box and toolchain — it verifies the
method, not independence (OBSERVATION, high). A hostile expert still
reads the native story as "trust the author's laptop plus a hash."

**Most serious weakness.**
Two findings, one old and one new. (1) `robotic_arm_virtual` still
passes schema validation while host and target run it on
differential-drive corridor physics — arm verdicts computed by car
physics, one hostile skim from "fabricated results" (VERIFIED FACT,
high — unchanged since v3:
[limitations-and-safety.md](../../../docs/limitations-and-safety.md#L33-L37)).
(2, NEW) The OMEGA6 "XSS audit" does not survive inspection of its own
framing: the handoff claims "25 innerHTML sinks" but `ui/studio.html`
alone contains **156** `innerHTML` lines (147 assignments + 9 concats,
counted this session); the static guard
`test_all_interpolations_escaped` checks only `${…}` interpolations, and
studio.html contains **zero** `${` — the guard is vacuous for the file
where the K1 card lives (all renderers use `+` concatenation); and
`esc()` does not escape single quotes (VERIFIED FACT, high:
[test_dashboard_verify.py](../../../tests/ui/test_dashboard_verify.py#L119-L130);
[genesis_verify.js](../../../ui/genesis_verify.js#L294-L297)).
The five runtime hostile-name tests (including the new K1 card test) all
pass and are real evidence — but "all Studio sinks escape-by-default" is
an assertion with no audit artifact, not a verified claim (OBSERVATION,
high). No live XSS was demonstrated either way (see U10).

**Most memorable part.**
The repo that tests its README now tests its counts, its hero line, its
footprint table, its cold-start copy, and its own audit vocabulary: 61
docs-consistency pins, all green on re-run (VERIFIED FACT, high:
61/61 `test_docs_consistency.py`, EXIT 0 this session; pins include hero
L806, footprint L816, E2E count L225, total count L262, A5 hygiene
L776–790). OBSERVATION (med): process-theatre-shaped, but the pins bit
twice this branch (6 A5 offenders red-then-green; stale 1330 count
synced) — the gate keeps biting rather than decorating.

**Missing evidence.**
(1) A sealed STALE transcript — the credibility keystone (negative
control 14/16) is still operator-recorded prose-grade; the new live
script demonstrates the *host digest* refusal, not the native behavioral
one, and says so honestly (VERIFIED FACT, high:
[demo_stale_refusal.py](../../../scripts/demo_stale_refusal.py#L61-L66)).
(2) The `qnx_verified=true` → "QNX 8.0 target" ran-where branch has no
test anywhere (this session: zero hits for the string in `tests/`) —
every runnable path renders host/host, so the sponsor-relevant label is
the untested one (VERIFIED FACT, high; renderer at
[studio.html](../../../ui/studio.html#L1091-L1100)).
(3) A native 2^32 clock-crossing vector and a v10 fix-then-measure cycle
— still open, correctly (VERIFIED FACT, high:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L11-L15);
v10 rule pinned L35-38).

**Recommended final improvement.**
Seal the STALE transcript into the evidence pack with hash-chain +
offline verify (backlog B-13, unchanged) — it converts the headline
moment from the strongest claim with the weakest artifact into a sealed
negative control. Second, within one hour: extend the XSS static guard
to concatenation-style sinks (or enumerate the 147 assignment sites into
a pinned audit) — the current guard's hole is exactly the kind of thing
a technical judge's `grep` finds in 30 seconds (OBSERVATION, high).

## 3. Perspective C — Sponsor / competition evaluator ("does this serve QNX and the rules?")

**Strongest reason to award first place.**
Genuine, specific, QNX-native substance, now with measured numbers an
auditor reproduced: 6 binaries via `qcc -Vgcc_ntox86_64 -O2` at 0
warnings with a bit-exact footprint table, synchronous message passing
with `NONGUARD=0` asserted every step, a `/dev/genesis/status` resource
manager, bounded RESPAWN/GIVE_UP supervision, crash-containment steps,
and a 16/16 on-target matrix in committed packs — in Developer Tooling
& Host Tools, where the tool *builds for* QNX (VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L7-L78);
packs re-verified this session). QEMU is explicitly allowed and no
hardware is required (VERIFIED FACT, high:
[qnx-forensics.md](../titanv3/qnx-forensics.md#L48-L52)).
The B2 bonus candidacy is first-class and the ran-where labels now
surface per-leg host-vs-target provenance on the verdict card itself
(VERIFIED FACT, high:
[studio.html](../../../ui/studio.html#L1091-L1100)).
OBSERVATION (high): this remains a credible Overall + B2 shape, and the
complements-not-replaces framing flatters the ecosystem.

**Strongest reason to reject.**
There is still no entry. Video DEFERRED BY OWNER, Devpost NOT submitted,
hard stop 15 Dec 2026 14:00 ET with no edits after (VERIFIED FACT,
high: [FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L10-L13);
[qnx-forensics.md](../titanv3/qnx-forensics.md#L25-L30)).
OMEGA6 added a dry run, a freeze note, and a canonical-text pointer —
all preparation, none of it a filing (VERIFIED FACT, high:
[FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L26-L33)).
Worse, the rules re-check is explicitly NOT VERIFIED (403 to automation;
owner must re-open in a real browser) (VERIFIED FACT, high:
[FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L21-L25)).
OBSERVATION (high): at this moment the project's biggest competitor is
still its own calendar — 36 days at branch date, all owner-gated items
open.

**Most serious weakness.**
The scored criterion "Potential Impact" explicitly asks "why real-time
QNX is the right choice" — and the RT-scheduling headline is still
*inconclusive* (5 Nov speedup not reproduced 8 Nov; no speedup claimed)
(VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L19-L28)).
Correct honesty, weak ammunition, unchanged by OMEGA6. A
hardware-backed rival with measured deterministic-latency numbers wins
this cell outright. Combined with QEMU-only + TCG-timing-as-regression-
aid (VERIFIED FACT, high:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L9-L10))
and an honestly-unmeasured RSS column (VERIFIED FACT, high:
[WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L67-L71)),
the QNX story is deep on IPC/architecture and empty on real-time
performance — half the sponsor's love language.

**Most memorable part.**
The one-page honesty contract — "Anything presented as measured comes
with method + raw artifacts; anything pending is labelled pending. That
distinction is the point of the project." (VERIFIED FACT, high — quoted:
[KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L46-L47)).
OMEGA6 extended the pattern: the dry run records its own unverified
boxes, the triage note dates its risk acceptance, the demo ladder
forbids presenting archived rungs as live (VERIFIED FACT, high:
[DEMO_FALLBACK_LADDER.md](../../../docs/jury/DEMO_FALLBACK_LADDER.md#L1-L4)).
OBSERVATION (med): sponsor evaluators read hundreds of entries that blur
measured and claimed; this team publishes its gaps in the submission
draft itself.

**Missing evidence.**
(1) The filed submission itself (live URL + committed copy of filed
text). (2) The final video (public YouTube, <180 s, QEMU visible).
(3) Owner §3 eligibility self-confirmation (not research-verifiable).
(4) A rules + homepage re-check near filing for §11.5 amendments
(VERIFIED FACT, high: all four open per
[FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L8-L33)).
All four are owner-gated; the checklist and dry run exist to catch them
but catch nothing by themselves.

**Recommended final improvement.**
Record the video BEFORE the final code freeze window against a tagged
candidate commit, with the storyboard's B2 shot (`cat
/dev/genesis/status` + `pidin`) and the stale-moment honesty line locked
— and keep a sealed-transcript-plus-`verify.py` fallback segment in the
can (the storyboard authorizes this fallback and forbids faking a live
run) (VERIFIED FACT, high — storyboard terms unchanged since v3).
Filing early with a good video beats filing late with a perfect tree —
the deadline is the only undefeated rival (OBSERVATION, high).

## 4. Official QNX criteria — hostile INTERNAL scoring (prefer the competitor)

Weights exact: four equally-weighted criteria (25% each), Stage-One
pass/fail gate, tie-breaks in criterion order 1→4 (VERIFIED FACT, high:
[qnx-forensics.md](../titanv3/qnx-forensics.md#L32-L41)).
Scores below are **INTERNAL** red-team simulations, deliberately
deflated, scored as a judge hunting for reasons to prefer a rival. Not
predictions. Contrast: self 31.5 (9.5/8.5/5/8.5 per the OMEGA6 delta
draft), v3 hostile 26.5 (8.0/6.5/4.5/7.5).

### Stage-One gate (pass/fail, unweighted)

**Simulated verdict: PASS** (OBSERVATION, high). Theme fit is direct (a
tool that builds/tests QNX 8.0 software) and the required SDK/API
application is genuine (`qcc` native build re-verified bit-exact this
session; on-target matrix; QEMU explicitly allowed). No plausible gate
failure — unless the entry is never filed, which fails louder than any
gate.

### Criterion 1 — Technological Implementation (weight 25%)

**INTERNAL hostile score: 8.0/10** (v3 hostile: 8.0; self: 9.5). HOLD.

- *Supporting evidence.* Depth that survives hostile re-execution:
  1431-test suite with 61 docs pins re-ran green in a scratch worktree;
  genuine traversal hardening (A3); bounded SSE paging (D2); deflaked
  race test with a documented mechanism (A1); non-blocking pip-audit +
  dated triage (D5); and a natively-measured footprint table the auditor
  reproduced bit-exact (D4) (VERIFIED FACT, high — §2 award case +
  §6/§7). K1 remains composition of green paths, AST-pinned
  ([test_change.py](../../../tests/integration/test_change.py#L148-L174)).
- *Remaining weakness (why not higher).* QEMU-only; single build host;
  BUILD-ONLY native CI; author-machine-only provenance with the second-
  host record unfilled; arm-physics aliasing ships; stale control
  unsealed (VERIFIED FACT, high — §2 citations). The traversal fix also
  proves a genuine ZipSlip *shipped* — a hostile judge counts the
  pre-fix exposure against the "sound engineering" half of the cell
  (OBSERVATION, med). A rival with hardware-backed native CI takes this
  cell.
- *Best improvement.* Fill the second-host provenance record (owner
  rebuild + re-verify on a second machine/SDP install, dated note with
  two host fingerprints + matching pack hashes) — the cheapest second
  signal for every native claim.

### Criterion 2 — Design (weight 25%)

**INTERNAL hostile score: 7.0/10** (v3 hostile: 6.5; self: 8.5). +0.5 —
the only cell that moves, and only halfway to self.

- *Supporting evidence.* The B2 acceptance gap is genuinely CLOSED with
  demonstrated evidence: first real Prove click in Chromium, honest
  empty/error/dead-backend states, 320/390/1366 no-overflow, keyboard-
  only path, 200/400% zoom, per-leg ran-where labels — 9/9 re-ran green
  in the scratch worktree (VERIFIED FACT, high: §6 row B2). K1 hero card
  + Prove CTA landed additively on the Overview (tabs kept) (VERIFIED
  FACT, high:
  [studio.html](../../../ui/studio.html#L230-L244));
  hero line + 30 s card pinned on all three front doors (VERIFIED FACT,
  high: hero pin green). Validate errors now carry `file:line` spans —
  demonstrated live (`omega6-bad-ir.json:21: …`, exit 2) (VERIFIED FACT,
  high: [cli.py](../../../host/genesis_rt/cli.py#L19-L40)).
- *Remaining weakness (why not higher).* "Complete, coherent product
  experience, not just a technical proof of concept" is the criterion
  text — and the residue is still: dense single page, no screen-reader
  session (protocol ready, human pending), no cold-read proof that a
  first contact survives Judge Mode, no video, and a "30-second" label
  whose install chain is unmeasured (VERIFIED FACT, high — §1/§3
  citations). The QNX-target ran-where branch is untested, so the
  sponsor-relevant label is display-only until proven (VERIFIED FACT,
  high — §2). A rival with a sparse, guided, *tested-with-humans*
  first-run wins this cell even with 1/10th the features.
- *Best improvement.* Cold-start walkthrough proof: one non-author human
  goes land → Judge Mode → PASS verdict in <5 min, with and without
  backend, timed wall-from-zero *including install*; every stumbled
  term gets fixed in the glossary/Devpost text. Design points come from
  witnessed usability, not from tab counts or headless-browser counts.

### Criterion 3 — Potential Impact (weight 25%)

**INTERNAL hostile score: 4.5/10** (v3 hostile: 4.5; self: 5). HOLD.

- *Supporting evidence.* The case is specific and credible on paper, and
  OMEGA6 sharpened the positioning: named persona (controls/
  verification lead), explicit buyer hypothesis, an honest win/loss
  table that concedes qualification/coverage/hardware-timing turf, and
  an 18/18 bit-rebuild receipt — all labeled prose, none overclaimed
  (VERIFIED FACT, high:
  [DEVPOST_FINAL_DRAFT.md](../../../docs/submission/DEVPOST_FINAL_DRAFT.md#L192-L229)).
  The paired pilot kit is ready to measure benefit honestly.
- *Remaining weakness (why lower than self-score).* The criterion
  demands "a credible, specific case for a real problem in a QNX
  market; why real-time QNX is the right choice" — and this entry has
  zero users, zero invitations, unmeasured benefit, AND an inconclusive
  RT result where the "why real-time QNX" argument should be (VERIFIED
  FACT, high — §1/§3 citations). E3 added positioning, not evidence;
  positioning does not score (OBSERVATION, high). Any rival with one
  named beneficiary and one measured outcome beats a 4.5.
- *Best improvement.* The quick-tier paired pilot with dated raws (see
  §1). Nothing else moves this cell; more prose does not score.

### Criterion 4 — Innovation & AI Creativity (weight 25%)

**INTERNAL hostile score: 7.5/10** (v3 hostile: 7.5; self: 8.5). HOLD.

- *Supporting evidence.* Genuine non-obvious core, now demonstrable in
  one click: contract-aware oracles, stale-binary behavioral refusal,
  stranger-replayable offline passports, counterfactual
  `compare`/`verify-change` as first-class commands — none in any
  inspected competitor body (OBSERVATION, high bounded to inspected
  bodies, per v3 competitors survey). The v10 trigger rule is now
  pinned as process (any planner/deterministic-layer change requires a
  separately-authored frozen-before-fix v10) (VERIFIED FACT, high:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L35-L38)).
- *Remaining weakness (why not higher).* No planner/validator change was
  allowed this branch, so the AI-creativity half still carries the
  published 5/112 unsafe accepts + 14 explained mismatches with no
  post-fix measurement on a new frozen set (VERIFIED FACT, high:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L28-L35)).
  The model path stays narrow (keyword planner + optional LLM consults,
  validator decides) — defensible architecture, but a rival with a
  genuinely novel model-native loop out-narrates "model proposes, gate
  disposes" on the *creativity* half of the label (OBSERVATION, med).
- *Best improvement.* Deterministic-layer fix with red-green tests,
  measured on a NEW frozen holdout (v10, separately authored,
  frozen-before-fix) — on a branch, merged only if green well before
  filing, else ship v9 honestly. Never rerun v9 on changed code; the
  freeze policy is load-bearing for the whole AI story.

### Hostile total: 27.0/40 (INTERNAL, deflated)

8.0 + 7.0 + 4.5 + 7.5 = **27.0/40**, vs v3 hostile 26.5, reviewer 29,
self 31.5. The +0.5 concedes exactly what OMEGA6 demonstrated (browser
acceptance + front-door productization) and nothing it merely wrote.
Tie-break order (criterion 1 first) means Tech strength only helps ties
— it does not rescue Impact. OBSERVATION (high): even under hostile
scoring the entry's floor is its honesty architecture — nearly every
deduction above is armed by the project's own disclosures, which is
exactly why a judge can trust the remaining points.

## 5. Verdict simulation — would it win?

- **As a branch (today): no.** No video, no filing, no entry. Current
  award probability is exactly zero for administrative reasons, and the
  rules re-check sits explicitly unverified (403 to automation) against
  an unmovable 15 Dec 2026 14:00 ET stop (VERIFIED FACT, high:
  [FILING_DRY_RUN_OMEGA6.md](../../../docs/submission/FILING_DRY_RUN_OMEGA6.md#L8-L33)).
- **As a filed entry (video + Devpost done, nothing else changed):
  competitive finalist, not a safe winner.** The hostile 27.0/40
  reflects a real profile: elite engineering honesty and QNX depth, a
  memorable one-metric identity now clickable in 5.7 s, a measured
  footprint, and a credible B2 bonus shape — against a hollow Impact
  cell, human-unproven first-contact design, and single-host native
  provenance. It beats entries that are thinner or less honest; it
  loses to any entry that pairs comparable depth with one measured user
  outcome or hardware-backed RT numbers. The most likely winning rival
  archetype from this evidence is unchanged: a narrower QNX-native tool
  with a named beneficiary and a measured before/after on real
  hardware (OBSERVATION, high).
- **Single highest-leverage week (owner-gated):** (1) record + upload
  the video; (2) re-open rules + homepage in a real browser, then file
  Devpost early per the checklist; (3) run the quick-tier paired pilot;
  (4) fill the second-host provenance record; (5) get one cold reader
  through Judge Mode wall-from-zero including install. Items 1–2 create
  the entry; 3–5 attack the three lowest hostile cells in weight order.
  All five need the owner — no agent action substitutes.

## 6. Falsification log — every new OMEGA6 claim attacked

Each row: the claim, the hostile attempt executed this session in the
scratch worktree, and the outcome. "SURVIVED" means the attempt failed
to falsify (claim holds); "WOUNDED" means the core holds but the
framing/number does not.

| # | claim | hostile attempt (this session) | outcome |
|---|---|---|---|
| A1 | race test deflaked (drop `busy>=1`); 20× green | ran `test_stale_reclaim_race_never_tracebacks` 10×: **0 fails**; read the mechanism docstring (partial-read unlink-steal) | SURVIVED. Residual, disclosed in the test body itself: the lock guarantee is now scoped to multi-process campaigns seconds apart — the narrowed guarantee fits the test, but the narrowing is published, not hidden ([test_target_lock.py](../../../tests/unit/test_target_lock.py#L60-L95)) |
| A2/XSS | hostile-name card test + "25 sinks audited, all escape-by-default" | re-ran the K1 hostile test + 3 sibling escape tests (4/4 green); counted sinks: **156** `innerHTML` lines in studio.html, not 25; counted `${` in studio.html: **0** (static guard vacuous there); read `esc()`: no single-quote escape | WOUNDED. The runtime tests are real and green; the audit framing is not: the "25" is irreproducible, the guard has a concatenation-shaped hole, no audit artifact exists. No live XSS demonstrated either way (U10) |
| B2 click | FIRST real Prove click, 9 browser tests green | re-ran full `test_prove_browser.py` in scratch worktree: **9/9 green, 30.3 s wall** | SURVIVED. Nuance: 6 test functions parametrized to 9 cases ([test_prove_browser.py](../../../tests/e2e/test_prove_browser.py#L157-L296)); the 5.7 s single-click figure was not isolated (U5); headless Chromium only — no AT/human |
| cold-start | `demo --ir` PASS ~1.17 s; "~2 s on a cold box"; "30-second cold start" | ran `demo --ir` 3×: **1.36/1.38/1.36 s** (within ±30% of 1.2); README chain install step has no timing anywhere | WOUNDED. Product runtime holds (~2 s honest); the "30-second" label is unmeasured end to end — `pip install` alone can break it ([README.md](../../../README.md#L9-L14)) |
| Demo-A | 1.2/1.2/1.2 s + 0.2/0.1/0.1 s | ran `run_verified_demo.py` (1.3 s wall, `elapsed_s` 1.13) + `replay.py` 3× (**0.15–0.16 s**) | SURVIVED. All inside the ±30% budgets ([REPRODUCE.md](../../../docs/jury/REPRODUCE.md#L25-L34)) |
| footprint | `qcc -O2` table via `ntox86_64-size` (6641/800/56 … 8136/680/8), 0 warnings | independent from-scratch rebuild of **all 6** binaries in `$env:TEMP` (auditor-invoked `qcc`, not branch artifacts) + `ntox86_64-size -B`: **text/data/bss/file-bytes exact on all 6, 0 warnings** | SURVIVED — strongest verification this session. RSS honestly unmeasured, as labeled ([WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L51-L71)) |
| pip-audit | non-blocking CI step + dated triage (pytest PYSEC-2026-1845 ACCEPT) | read the CI step (`continue-on-error: true`) + triage doc; confirmed `pytest==7.4.0` in `requirements.lock` (matches triage); checked CI status observability | SURVIVED as wiring + prose; UNVERIFIED as execution — no CI run was observable from here (U2), and non-blocking means a future finding cannot fail the build by design ([host-ci.yml](../../../.github/workflows/host-ci.yml#L25-L29); [SUPPLY_CHAIN_TRIAGE.md](../../../docs/security/SUPPLY_CHAIN_TRIAGE.md#L1-L24)) |
| A6/B-19 | packs 35/37 on disk = 34/36 payload + verify.py; exclusion stated | recursive file counts (**35/37**) + both `verify.py` re-ran (**VERIFY OK**, 16/16, exit 0) | SURVIVED ([CLAIMS.md](../../../docs/CLAIMS.md#L62-L64)) |
| A3 | traversal fail-closed (dossier + change-id) | re-ran dossier+stale suites (**46/46**); read `valid_op_id` gate before any disk read | SURVIVED. `build_set` path handling past `dossier.py:199` not fully inspected (U4) |
| C3 | validate errors carry `file:line` | live run on crafted invalid IR: `omega6-bad-ir.json:21: control.max_linear_speed_mps must be a number…`, exit 2 | SURVIVED. Best-effort heuristic (longest-identifier match), honestly documented as such ([cli.py](../../../host/genesis_rt/cli.py#L19-L40)) |
| D2 | op `events()` bounded (limit 200) | re-ran slow-consumer paging test (green); read the page-bound code | SURVIVED ([target.py](../../../host/genesis_rt/target.py#L303-L327)) |
| counts | 1431 / 1425+6 / 41 E2E / 61 pins | re-ran all 61 docs pins (**green**, incl. count, E2E-collect, hero, footprint pins); full 1431 suite not executed | SURVIVED as pins; full-suite green is implementer-reported (U1) |

Report-H objection tracker: O5 flaky-fix proof → CLOSED (A1 + loops);
O6 browser-click acceptance → CLOSED (9/9 re-ran); O3 cold-start proof →
PARTLY (product time measured, wall-from-zero + human missing); O4 SR
session, O1 pilots, O2 video → OPEN (owner); O7 arm-aliasing → OPEN,
ships (OBSERVATION, high — against
`v4-output/report-H-jury.md (L120-125)`).

## 7. Evidence log + unresolved

*Bodies opened this session (branch read via scratch worktree at
`fa9aeb7`, content-identical to shared checkout at same commit; citations
use stable `genesis-rt/` paths):* `README.md` (L1-45),
`docs/jury/SCORECARD_DELTA_OMEGA6.md` (full),
`docs/jury/DEMO_BEATS_TIMED.md` (full),
`docs/jury/DEMO_FALLBACK_LADDER.md` (full),
`docs/jury/HARDEST_QA_LIVE.md` (full),
`docs/submission/FILING_DRY_RUN_OMEGA6.md` (full),
`docs/jury/WHY_QNX.md` (L1-78), `docs/security/SUPPLY_CHAIN_TRIAGE.md`
(full), `docs/jury/REPRODUCE.md` (full),
`docs/jury/KNOWN_LIMITATIONS.md` (full),
`tests/unit/test_target_lock.py` (L1-120),
`tests/e2e/test_prove_browser.py` (L1-150 + test-name/parametrize map),
`scripts/demo_stale_refusal.py` (full),
`.github/workflows/host-ci.yml` (L1-44),
`host/genesis_rt/dossier.py` (L1-85, L120-199),
`host/genesis_rt/cli.py` (L1-90), `host/genesis_rt/target.py` (L71-92
regex, L280-327 events, L329-354 recover),
`host/genesis_rt/facts.py` (full),
`tests/ui/test_dashboard_verify.py` (L1-160, L315-360),
`tests/integration/test_change.py` (L90-175),
`tests/integration/test_dossier.py` (L130-199),
`ui/studio.html` (L200-244 hero/K1, L1075-1102 card renderer),
`ui/genesis_verify.js` (L285-297 esc),
`docs/submission/DEVPOST_FINAL_DRAFT.md` (L185-244),
`docs/CLAIMS.md` (B-19 lines), `host/genesis_rt/jobs.py` (recover),
`genesis_build_gen.mk` (generated header + qnx lines),
`tests/unit/test_docs_consistency.py` (pin spot-lines).
*External inputs opened:* `v4-output/report-H-jury.md` (full),
`v3-research/red-team.md` (full), `v3-research/qnx-forensics.md` (§§1–4
+ judging/bonus/video rules). *Prior-result handoff index read in full*
(35 lines, no truncation); implementer evidence reused as discovery
pointers, every claim above re-grounded in the bodies listed here.
*Commands executed (all in the scratch worktree unless noted):*
worktree create (detached `fa9aeb7`) + remove (exit 0, path gone);
`test_change.py` → 17 passed; `test_dossier.py` + `test_stale_demo.py`
→ 46 passed; `test_dashboard_verify.py -k "change_card or
escapes_hostile or all_interpolations"` → 4 passed;
`test_docs_consistency.py` → 61 passed; `test_prove_browser.py` full →
9 passed, 30.3 s; A1 race test 10× → 0 fails; D2 paging test → pass;
`vulture host scripts tests --min-confidence 80` → clean, exit 0; live
`demo_stale_refusal.py` → STALE exit 0 (0.0 s product); live
`verify-change` cell broken→fixed → FAIL→PASS, 2.47 s wall, exit 0;
live `demo --ir` 3× → 1.36–1.38 s; live `run_verified_demo.py` →
1.3 s wall; live `replay.py` 3× → 0.15–0.16 s; live `validate` on
crafted bad IR → `file:21:` span, exit 2; both pack `verify.py` →
VERIFY OK exit 0; recursive pack counts 35/37; full 6-binary `qcc`
rebuild + `ntox86_64-size -B` → bit-exact table, 0 warnings;
`innerHTML` counts (156 studio.html / 3 dashboard); `${` counts (0
studio / 9 dashboard); `pytest==7.4.0` lock grep; `QNX 8.0 target`
zero-hit grep over `tests/`; shared checkout + worktree `status`
verified clean before removal.

*Unresolved / not verified this session:*
U1: full 1431-test suite execution (pins re-verified; full green is
implementer-reported EXIT 0). U2: `pip-audit` actual CI execution + CI
status on the branch (no gh auth; non-blocking by design). U3: repo-
public 200 + rules-403 re-fetch (implementer-observed, not re-checked).
U4: dossier `build_set` path handling past `dossier.py:199` (not fully
inspected). U5: exact 5.7 s single-click figure (full file 30.3 s; per-
test wall not isolated). U6: `qnx_verified=true` label branch untested
anywhere (zero test hits). U7: all owner-human acts (video, filing,
pilots, cold read, SR session, second host, eligibility, crypto
upgrade). U8: native QEMU re-run (packs replayed, never re-executed).
U9: AI-eval reproduction (frozen, forbidden). U10: single-quote
attribute contexts across the 147 concat sinks (no sink audit artifact;
no live XSS demonstrated either way).
