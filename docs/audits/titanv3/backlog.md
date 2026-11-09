# GENESIS RT — Brutal Audit Backlog (v3 research)

Date: 2026-11-09. Mission: disqualify GENESIS RT from first place — every
weakness below is a reason a judge, user, or rival could use against it.
READ-ONLY on `genesis-rt`; this file under `v3-research/` is the only write.
Frozen evals untouched. No metrics, scores, feedback, or testimonials invented:
every number is quoted from an opened body cited inline.

Labels: **VERIFIED FACT** (opened body) / **OBSERVATION** (synthesis) /
**ASSUMPTION** (inference, flagged). Confidence: High/Med/Low per item.
Effort scale: XS (<1h) / S (hours) / M (days) / L (1–2 wks) / XL (structural).
Ratio = judge-impact ÷ effort-weight (XS=1, S=2, M=4, L=8, XL=16); items are
ordered by ratio within each priority band. **HIGH-RISK** = destabilizing to a
submission-pending repo; do on a branch or defer past filing.

Inputs opened this session:
[v3 recon](recon.md),
[winners delta](winners-delta.md),
[QNX forensics](qnx-forensics.md),
[competitors](competitors.md),
plus genesis-rt bodies: `docs/jury/JUDGE_SCORECARD.md`,
`docs/jury/KNOWN_LIMITATIONS.md`, `docs/limitations-and-safety.md`,
`docs/jury/WHY_QNX.md`, `docs/submission/OMEGA5_OWNER_ACTIONS.md`,
`submission/VIDEO_DEFERRED.md`, `docs/business/pilot-study.md`,
`.github/workflows/qnx.yml`, `ui/README.md`, `host/genesis_rt/facts.py`
(all read-only, absolute links in each item).

## Scoreboard the audit attacks

Self-scores (internal, OMEGA5): 31/40 (9.5/8/5/8.5); independent reviewer 29/40
(9/7/5/8) — [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L18-L37).
Impact sits at 5/10 with zero pilots; Design is capped by density + no
screen-reader session + no video; Tech/AI carry QEMU-only + 5 open unsafe
accepts. The four Devpost criteria are equally weighted, so Impact at ~half
marks is a ~12.5% total-score hole no Tech polish can fill. Tie-breaks run
criterion 1→4 ([qnx-forensics.md](./qnx-forensics.md#L36)),
so Tech strength only helps ties — it does not rescue Impact.

## P0 — Submission blockers (no filing without these)

### B-01 Final video missing → no entry exists
- Severity: Critical. Judge 10/10, User 2/10. Effort M (owner-only).
  Regression risk: none (additive). Confidence High. Ratio 2.5.
- VERIFIED FACT: `SUBMISSION_STATUS = PENDING_FINAL_VIDEO`, video
  `DEFERRED_BY_OWNER` since 7 Nov; Devpost cannot be filed without a public
  YouTube <180 s video showing the project on its platform (QEMU).
  Sources: [VIDEO_DEFERRED.md](../../../submission/VIDEO_DEFERRED.md#L1-L18),
  [OMEGA5_OWNER_ACTIONS.md](../../../docs/submission/OMEGA5_OWNER_ACTIONS.md#L8-L14),
  [qnx-forensics.md](./qnx-forensics.md#L109).
- Why brutal: every other item is moot. Winners-delta DP2/DP3 show the demo
  artifact is scored work, not ceremony; a missing video is not a weak demo,
  it is absence from the pile.
- Fix: owner records <180 s (Studio + QEMU footage, English, clean rights),
  uploads PUBLIC to YouTube, commits URL in README + release asset same-day
  (never portal-only).
- Verify: file/URL exists; `duration < 180 s`; public YT; QEMU visible on
  screen; docs-consistency pin updated to the final cut.

### B-02 Devpost draft prepared but NOT submitted
- Severity: Critical. Judge 10/10, User 0/10. Effort S. Regression risk: none.
  Confidence High. Ratio 5.0.
- VERIFIED FACT: canonical text exists
  (`docs/submission/DEVPOST_FINAL_DRAFT.md`, v9-synced) but submission is
  pending the video; hard stop 15 Dec 2026 14:00 ET, no edits after.
  Sources: [OMEGA5_OWNER_ACTIONS.md](../../../docs/submission/OMEGA5_OWNER_ACTIONS.md#L16-L28),
  [qnx-forensics.md](./qnx-forensics.md#L27).
- Fix: after B-01, paste canonical text, select Developer Tooling & Host Tools,
  name exact QNX files/functions/output/demo in text, paste video + codelab
  URLs in the correct fields, submit early.
- Verify: live submission URL + committed copy of filed text.

### B-03 Submission-day checklist (public repo, eligibility, re-check rules)
- Severity: High. Judge 9/10 if violated else 0. Effort XS. Regression: none.
  Confidence High. Ratio 9.0.
- VERIFIED FACT: repo must stay public/free through 29 Jan 2027 (§4 Testing);
  owner §3 eligibility is self-confirm only; rules amendable anytime (§11.5).
  Source: [qnx-forensics.md](./qnx-forensics.md#L105-L136).
- Fix: day-of-filing checklist — visibility check, eligibility self-confirm,
  re-open S1+S2 in a browser, draft early.
- Verify: public-visibility screenshot at filing + calendar hold to 29 Jan 2027.

## P1 — First-place killers (fixable before the deadline)

### B-10 Potential Impact 5/10: zero pilots, zero invitations, benefit unmeasured
- Severity: Critical (for 1st). Judge 9/10, User 9/10. Effort L (owner-only:
  2 teams × ~2 h + analysis). Regression: none. Confidence High. Ratio 1.1.
- VERIFIED FACT: `HUMAN USER BENEFIT NOT YET MEASURED`; "zero participants,
  zero invitations sent, zero records in bench/"; protocol + timer + analyzer
  validated on fixtures only. Sources:
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L22),
  [pilot-study.md](../../../docs/business/pilot-study.md#L1-L6),
  [OMEGA5_OWNER_ACTIONS.md](../../../docs/submission/OMEGA5_OWNER_ACTIONS.md#L30-L42).
- Why brutal: 25% of the score is capped at half marks; winners-delta shows
  validity-scored awards go to named beneficiaries + real-world fidelity
  (D2/D5/D15). "Nothing sent, nothing faked" is honest — and currently worth 5.
- Fix: owner runs the quick-tier paired pilot exactly per protocol (2
  independent teams, 3 quick tasks, both lanes); publish dated raws. Earns
  `QUICK_PAIRED_PILOT` only — never claim independence or generalization.
- Verify: dated records under `bench/` + analyzer CSV + docs pin update;
  Devpost text cites the measured numbers with method.

### B-14 Judges may never run anything — text + video carry 100%
- Severity: High. Judge 7/10, User 3/10. Effort S. Regression: none.
  Confidence Med. Ratio 3.5.
- VERIFIED FACT: judges need not test (§4); submission must stand alone on
  text + video. OBSERVATION: the AI-ladder vocabulary (unsafe vs wrong-kind vs
  consults, blind vs qualified-blind, frozen vs regression) is the steepest
  comprehension wall in the repo. Sources:
  [qnx-forensics.md](./qnx-forensics.md#L138-L144),
  [recon.md](./recon.md#L301-L304).
- Why brutal: a 2-command SDK-free replay nobody runs scores zero; a confused
  judge scores the confusion. Winners-delta DP3: one-metric identities travel.
- Fix: one-page plain-language glossary + Devpost rewrite pass (one memorable
  line per subsystem, numbers with denominators); align video script to the
  same lines. Candidate identity line already exists
  ("generates inspectable evidence about the behavior of the code").
- Verify: cold-read test by one non-author human (owner-recruited); fix every
  term they stumble on; no agent contact involved.

### B-11 Design: no screen-reader session (protocol prepared, never executed)
- Severity: High. Judge 6/10, User 7/10. Effort S. Regression: none.
  Confidence High. Ratio 3.0.
- VERIFIED FACT: "automated axe scans in CI only; full screen-reader
  verification is outstanding, not claimed"; reviewer caps Design at 7/10 for
  density + no SR session + no video. Sources:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L38-L39),
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L21).
- Fix: execute the prepared SR checklist protocol, log the session, fix
  blockers only (no redesign pre-submission).
- Verify: dated session log + issue list + re-test; pin the log path in docs.

### B-12 AI residual: 5 unsafe accepts / 112 + 14 consultation mismatches open
- Severity: High. Judge 7/10, User 8/10. Effort M–L. **HIGH-RISK**
  (planner/gate changes near submission). Confidence High. Ratio ~1.0.
- VERIFIED FACT: blind v9 (160, no format example): 142/150/150, 5 unsafe of
  112 (4 safety + 1 fleet, all deterministic-layer, classed), 0 wrong-kind,
  34/36 consults with 14 explained mismatches; v9 targeted, no broad claim;
  v7/v8/v9 never rerun on changed code. Sources:
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L23-L30),
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L28-L35).
- Why brutal: an "unsafe accept" is the single scariest phrase a rival judge
  can quote; rate improved (6.2%→4.5%) but count rose (4→5) on a harder pool.
- Fix: fix at the deterministic layer with red-green tests, then measure on a
  NEW frozen holdout (v10, separately authored, frozen-before-fix). Never rerun
  v9 on changed code. Do on a branch; merge only if green well before filing,
  else ship v9 numbers honestly and defer.
- Verify: new frozen set file + hash recorded pre-fix + per-provider raws +
  updated CLAIMS/AI report; docs-consistency pin on the new set.

### B-15 `robotic_arm_virtual` runs on diff-drive physics (labeled aliasing)
- Severity: High. Judge 6/10, User 5/10. Effort M. **HIGH-RISK** if physics
  touched; XS if scoped out. Confidence High. Ratio 1.5 (scope-out path).
- VERIFIED FACT: arm kind passes schema but the host mirror runs the
  differential-drive corridor; no arm physics on host or target; scenario
  records carry `physics`/`physics_note` so aliasing is visible in evidence.
  Source: [limitations-and-safety.md](../../../docs/limitations-and-safety.md#L33-L37).
- Why brutal: labeled or not, a judge skimming evidence sees arm verdicts
  computed by car physics — one hostile read away from "fabricated results."
- Fix (pre-deadline): scope it out — validation rejects arm with a clear
  message, or quarantine the kind behind an explicit experimental flag;
  document as roadmap. Full arm physics is post-submission work.
- Verify: `validate` on an arm IR fails loudly (or flags experimental);
  no arm verdicts in shipped example passports; test pins the behavior.

### B-13 STALE 14/16 control is prose-grade (no sealed transcript in packs)
- Severity: High. Judge 6/10, User 4/10. Effort M (seal transcript; may need
  a QEMU rerun). Regression: low. Confidence High. Ratio 1.5.
- VERIFIED FACT: the stale-binary control (14/16 failing exactly on
  `estop_target` + `v2_transitions`) is operator-recorded; no sealed
  transcript ships in the packs; sealing is disclosed future work. Sources:
  [recon.md](./recon.md#L209),
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L54).
- Why brutal: the negative control is the credibility keystone (competitors
  §5.3: "cheapest credibility available") — prose-grade means the strongest
  claim has the weakest artifact.
- Fix: capture and seal the STALE transcript into the evidence pack with the
  same hash-chain + offline verify as BEFORE/AFTER.
- Verify: pack contains the sealed STALE transcript; `verify.py` covers it;
  docs pin its presence.

### B-16 QEMU-only + inconclusive RT result (no hardware, TCG timing)
- Severity: High. Judge 6/10, User 5/10. Effort XS (framing, done) / XL
  (hardware). Regression: none. Confidence High. Ratio n/a (do XS only).
- VERIFIED FACT: QEMU x86_64 only; no hardware, no HAM, no attestation; TCG
  timing is a regression aid, not a guarantee; the 5 Nov RT-priority speedup
  did not reproduce on 8 Nov jury-fixed sources — no speedup claimed.
  Sources: [WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L19-L28),
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L5-L10).
- Why brutal: "Potential Impact … why real-time QNX is the right choice" is a
  scored criterion, and the RT experiment's headline is *inconclusive* —
  correct honesty, weak ammunition. A hardware-backed rival wins this cell.
- Fix (pre-deadline): keep the disclosure prominent; frame Devpost Impact
  around verification-fidelity (what IS proven), not RT performance. Attempt a
  hardware run only if zero-risk and owner-executed; never weaken the
  disclosure to sharpen the pitch.
- Verify: Devpost text contains the QEMU-only + inconclusive-RT statements
  verbatim-adjacent to every perf-adjacent claim.

### B-17 Native provenance is author-machine only (no native CI runner)
- Severity: High. Judge 5/10, User 3/10. Effort XS (mitigation) / XL (runner).
  Regression: low. Confidence High. Ratio 5.0 (mitigation path).
- VERIFIED FACT: `qnx.yml` is BUILD-ONLY, `workflow_dispatch` only, needs an
  unregistered self-hosted `qnx` runner; it never boots QEMU or runs the
  16-step matrix — by design (licensed SDK + untrusted PR code = exfiltration
  risk). One build host; cross-SDP reproducibility unverified. Sources:
  [qnx.yml](../../../.github/workflows/qnx.yml#L1-L43),
  [JUDGE_SCORECARD.md](../../../docs/jury/JUDGE_SCORECARD.md#L20).
- Why brutal: every native claim reduces to "trust the author's laptop plus a
  hash." A judge who distrusts self-reported benchmarks has no independent
  signal.
- Fix (pre-deadline, no runner): second-host reproduction — owner rebuilds +
  re-verifies packs on a second machine/SDP install, commits a dated
  provenance note (host fingerprints, qcc version, pack hashes). Do NOT
  register a runner casually.
- Verify: provenance note in `docs/audits/` with two host fingerprints +
  matching pack hashes; `qnx_rebuild_check.py` green on both.

### B-18 Bonus strategy undecided in effect: only ONE bonus is winnable
- Severity: Medium. Judge 5/10 (bonus EV), User 1/10. Effort XS (decision +
  surfacing). Regression: none. Confidence High. Ratio 5.0.
- VERIFIED FACT: one Overall + one Bonus + one Community Choice max; only one
  Bonus winnable; B1 needs a codelab URL in the designated field, B2 is judged
  from the submission with no extra field. Owner actions name B2 primary +
  B1 second. Sources:
  [qnx-forensics.md](./qnx-forensics.md#L54-L58),
  [OMEGA5_OWNER_ACTIONS.md](../../../docs/submission/OMEGA5_OWNER_ACTIONS.md#L22-L26).
- Why brutal: split polish across both bonuses halves the winning surface;
  B2 silently fails if the Devpost text + video never name the QNX primitives.
- Fix: commit to B2-first; Devpost text names files/functions
  (`name_attach`/`MsgSend`/resmgr `/dev/genesis/status`/supervision) per
  [WHY_QNX.md](../../../docs/jury/WHY_QNX.md#L7-L38);
  video shows them on screen; B1 filed as the free second selection only.
- Verify: Devpost text grep for each primitive + file path; video shot list
  includes a QNX-primitive screen segment.

## P2 — High-value hardening (judge-impact per effort, in order)

### B-19 Pack file-count wording off by one (34/36 vs 35/37 on disk)
- Severity: Medium. Judge 2/10, User 1/10. Effort XS. Regression: none.
  Confidence Med. Ratio 2.0.
- OBSERVATION: on-disk counts include `verify.py` (35/37) while docs say
  34/36; no test pins file counts; both packs VERIFY OK so integrity holds.
  Source: [recon.md](./recon.md#L190-L194).
- Why brutal: trivially checkable mismatch — exactly the kind of nick a
  hostile reviewer can screenshot-circle to seed doubt about all other numbers.
- Fix: one-line wording fix ("34 payload files + verify.py") + docs-consistency
  pin on the counting rule.
- Verify: docs pin test green; `ls` count matches the documented rule.

### B-23 Owner security hygiene: default QNX password + crypto 43.0.3
- Severity: Medium. Judge 3/10, User 6/10. Effort XS (owner-only).
  Regression: none. Confidence High. Ratio 3.0.
- VERIFIED FACT: QNX image still boots with its DEFAULT password (rotation
  procedure exists); global interpreter runs `cryptography 43.0.3`
  (10 known vulns) vs lock 50.0.2; no project venv, so agents must not touch it.
  Source: [OMEGA5_OWNER_ACTIONS.md](../../../docs/submission/OMEGA5_OWNER_ACTIONS.md#L44-L64).
- Why brutal: "hash-only pack verification does not depend on it" is true and
  beside the point — default creds + known vulns on the build box undermine
  every provenance sentence.
- Fix: owner rotates the password per procedure; owner upgrades global
  cryptography to 50.0.2; record both as done with dates.
- Verify: dated owner confirmation; `cryptography.__version__ == 50.0.2`;
  no secret material in repo files.

### B-29 Dense 13-tab Studio first impression (Judge Mode exists — prove it carries)
- Severity: Medium. Judge 4/10, User 5/10. Effort S (verification + copy, no
  redesign). Regression: low. Confidence High. Ratio 2.0.
- VERIFIED FACT: `studio.html` (184 KB) has 13 tabs; self-assessed residual is
  "dense single page"; guided 7-stage Judge Mode tab exists with real
  run/inspect actions. Sources:
  [recon.md](./recon.md#L129-L143),
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L16-L23).
- Why brutal: Design rewards "complete, coherent product experience, not just
  a technical proof of concept" — density reads as the latter in the first
  30 seconds.
- Fix: no redesign without evidence (scorecard principle stands); verify Judge
  Mode carries a cold start end-to-end, tighten Overview copy, ensure the
  offline banner + 6 file inspectors degrade gracefully without backend
  ([ui/README.md](../../../ui/README.md#L9-L21)).
- Verify: cold-start walkthrough script (owner or owner-recruited human):
  land → Judge Mode → PASS verdict in <5 min, with and without backend.

### B-20 Evidence packs UNSIGNED (hash-only, no signer authentication)
- Severity: Medium. Judge 4/10, User 4/10. Effort M. Regression: low.
  Confidence High. Ratio 1.0.
- VERIFIED FACT: packs are hash-only UNSIGNED by design — SHA-256 integrity +
  offline replay, not signer authentication or attestation; `sign-pack` /
  `verify-pack` CLI exists but packs ship unsigned. Sources:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L36-L37),
  [recon.md](./recon.md#L221).
- Why brutal: "tamper-evident" without identity answers "was it modified" but
  not "who attests this ran on QNX" — the exact gap B-17 widens.
- Fix (post-filing preferred): sign release packs at tag time with a documented
  key + attestation note; keep hash-only verify as the stranger path.
  Pre-deadline: document the trust tiers explicitly in Devpost text
  (`--trust local → exit 2` behavior).
- Verify: signed pack verifies under `verify-pack`; unsigned packs still
  verify hash-only; docs pin the tier semantics.

### B-27 Narrow generality: 3 machine kinds, v1+v2 split, v2 has no cell semantics
- Severity: Medium. Judge 4/10, User 5/10. Effort XS (positioning) / XL (real).
  Regression: none for positioning. Confidence High. Ratio 4.0 (positioning).
- VERIFIED FACT: depth is narrow on AMR/conveyor/cell; `industrial_cell` stays
  v1-only — v2 validation and v1→v2 migration reject it loudly. Sources:
  [competitors.md](./competitors.md#L254),
  [limitations-and-safety.md](../../../docs/limitations-and-safety.md#L29-L32).
- Why brutal: "The Physical World Compiler" over-promises against 3 machine
  kinds; a generality-framed judge asks what the 4th kind costs.
- Fix (pre-deadline): scope statement in Devpost — "narrow + deep on N kinds;
  adding a kind = IR schema + codegen + oracles + matrix, no framework change"
  (only if true — verify against codegen structure first). v2 cell semantics
  is post-submission (**HIGH-RISK** now).
- Verify: Devpost scope paragraph present; no claim implies N+1 kinds work today.

### B-24 No native 2^32 clock-crossing vector (wrap path host-tested only)
- Severity: Low–Medium. Judge 3/10, User 4/10. Effort M (needs target run).
  Regression: low. Confidence High. Ratio 0.75.
- VERIFIED FACT: RFC 1982 serial arithmetic over uint32 in C + Python,
  conformance-tested; pairs 2^31+ ms apart ambiguous by construction;
  wrap path host- and conformance-tested only — no native vector crosses 2^32
  on target yet. Source:
  [limitations-and-safety.md](../../../docs/limitations-and-safety.md#L14-L22).
- Fix: add a native wrap-crossing matrix vector (or document why infeasible on
  QEMU time budget); 64-bit clock is the post-MVP cure.
- Verify: native vector green in a campaign transcript, or a dated infeasibility
  note with the host/conformance coverage cited.

### B-22 Local API has no auth (hackathon-grade security posture)
- Severity: Medium. Judge 3/10, User 5/10. Effort S (docs) / M (token).
  Regression: medium for code. Confidence High. Ratio 1.5 (docs path).
- VERIFIED FACT: "local-first, no auth, no sandbox beyond timeouts and argv
  lists"; loopback-only (`127.0.0.1:8077`) with foreign-Origin writes 403.
  Sources: [limitations-and-safety.md](../../../docs/limitations-and-safety.md#L28-L29),
  [recon.md](./recon.md#L63-L70).
- Why brutal: a network-exposed no-auth API running codegen/build pipelines is
  a one-line security dismissal — mitigated only if loopback-only is
  unmistakable in every doc.
- Fix (pre-deadline): docs only — SECURITY.md + Devpost state loopback-only +
  no-auth scope + "not for exposed deployment" prominently. Token auth is
  post-submission (**HIGH-RISK** now: touches every route + Studio + tests).
- Verify: grep shows the warning in SECURITY.md, api docs, and Studio footer;
  negative test: non-loopback bind refused or warned.

## P3 — Defer past filing (record, do not attempt now)

### B-21 v2 cell semantics missing — DEFER
- Severity: Medium. Judge 4/10, User 6/10. Effort L. **HIGH-RISK.**
  Confidence High.
- VERIFIED FACT: see B-27 source. Implementing v2 cell semantics touches
  schema + validator + migration + codegen + oracles + matrix weeks before a
  hard stop — classic destabilizer. Ship the loud rejection + scope statement.

### B-25 No QNX HAM integration — DEFER
- Severity: Medium. Judge 3/10 (+B2 surface), User 3/10. Effort L.
  **HIGH-RISK.** Confidence High.
- VERIFIED FACT: QSTI image ships no `ham` binary; supervision is the tested
  RESPAWN/GIVE_UP process with dedicated matrix steps; HAM documented as
  complementary. Source:
  [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L25-L27).
- Ship the documented position; HAM integration needs an image with HAM +
  new matrix steps + pack regeneration.

### B-26 Single local operator, no team workflow — DEFER
- Severity: Medium. Judge 3/10, User 6/10. Effort XL. Confidence High.
- VERIFIED FACT: "no multi-user/team workflow — single local operator."
  Source: [KNOWN_LIMITATIONS.md](../../../docs/jury/KNOWN_LIMITATIONS.md#L16-L23).
- Multi-user is a product generation, not a backlog item; state the scope.

### B-28 No static analysis / coverage / MISRA / qualification story — POSITION, don't build
- Severity: Low (out of scope). Judge 3/10, User 4/10. Effort —. Confidence High.
- VERIFIED FACT: commercial class (Parasoft/LDRA/VectorCAST) owns
  standards-shaped verification; GENESIS RT explicitly claims no functional
  safety qualification. Source:
  [competitors.md](./competitors.md#L262-L291).
- Never compete there; Devpost frames GENESIS RT as the change-verification +
  evidence loop that sits *before* qualification tooling.

### B-30 W12 historical video is confusable with a final cut — LABEL
- Severity: Low. Judge 2/10, User 1/10. Effort XS. Confidence High.
- VERIFIED FACT: `docs/demo/genesis-rt-demo-w12.mp4` (154.664 s) predates the
  7 Nov Studio nav change; explicitly NOT the final video; `facts.py` still
  pins it as `VIDEO_FILE`. Sources:
  [VIDEO_DEFERRED.md](../../../submission/VIDEO_DEFERRED.md#L11-L15),
  [facts.py](../../../host/genesis_rt/facts.py#L23-L24).
- Fix: rename or banner the file + directory README as HISTORICAL — do not
  present, do not link from new docs; re-pin `VIDEO_FILE` to the final cut
  once B-01 lands.

### B-31 Cosmetic: PROGRESS.md Nov-8 entries appended, not prepended — TRIVIAL
- Severity: Low. Judge 1/10, User 0/10. Effort XS. Confidence Med.
- OBSERVATION per [recon.md](./recon.md#L253-L255).
  Reorder when next touching the file; zero judge leverage either way.

### B-32 Community Choice: organic only, never game votes — NOTE
- Severity: Low. Judge 2/10 (non-cash), User 0/10. Effort XS. Confidence High.
- VERIFIED FACT: one vote per person per submission; circumvention/multiple
  emails/compensating voters → votes disqualified, maker possibly
  disqualified. Source:
  [qnx-forensics.md](./qnx-forensics.md#L90).
- No action except: announce the entry once through normal channels after
  filing; never incentivize votes.

## Priority × ratio summary (judge impact per effort)

| ID | Band | Judge/Effort | Ratio | One-line |
|---|---|---|---|---|
| B-03 | P0 | 9/XS | 9.0 | Filing-day checklist |
| B-02 | P0 | 10/S | 5.0 | Submit Devpost |
| B-01 | P0 | 10/M | 2.5 | Final video |
| B-17 | P1 | 5/XS-mit | 5.0 | Second-host provenance note |
| B-18 | P1 | 5/XS | 5.0 | Commit B2-first bonus surfacing |
| B-14 | P1 | 7/S | 3.5 | Plain-language glossary + Devpost pass |
| B-11 | P1 | 6/S | 3.0 | Execute screen-reader session |
| B-13 | P1 | 6/M | 1.5 | Seal the STALE transcript |
| B-15 | P1 | 6/M–XS | 1.5 | Scope out aliased arm physics |
| B-10 | P1 | 9/L | 1.1 | Run 2 quick paired pilots |
| B-12 | P1 | 7/M–L | ~1.0 | Fix unsafe accepts, measure on new v10 |
| B-16 | P1 | 6/XS–XL | n/a | Keep RT honesty; hardware only if free |
| B-27 | P2 | 4/XS-pos | 4.0 | Generality scope statement |
| B-23 | P2 | 3/XS | 3.0 | Rotate password + crypto floor |
| B-19 | P2 | 2/XS | 2.0 | Fix pack-count wording + pin |
| B-29 | P2 | 4/S | 2.0 | Prove Judge Mode carries cold start |
| B-22 | P2 | 3/S-doc | 1.5 | Auth-scope warnings in docs |
| B-20 | P2 | 4/M | 1.0 | Signed-release option / trust tiers |
| B-24 | P2 | 3/M | 0.75 | Native clock-wrap vector |
| B-21/25/26/28/30/31/32 | P3 | — | — | Deferred / labeled / noted |

Highest-leverage pre-deadline sequence: B-03 → B-02 → B-01 (existence) →
B-18 + B-14 (submission surface) → B-17 + B-19 + B-23 (credibility hygiene) →
B-11 + B-29 (Design cell) → B-10 (Impact cell, owner-bandwidth-gated) →
B-13 + B-15 (evidence honesty) → B-12 (only on a branch with spare runway) →
everything else deferred.

## Unresolved / explicitly not verified

- U1: full test-suite execution + browser E2E run (not run; recon collected
  only) — B-12/B-15 merges must be gated on the full green run.
- U2: native QNX campaign re-run (needs SDP 8.0 + QEMU; B-13/B-24 assume
  owner-machine access works as documented).
- U3: AI-eval reproduction forbidden by freeze policy — B-12's v10 must be a
  new frozen set, never a v9 rerun.
- U4: whether a 4th machine kind truly needs "no framework change" (B-27
  positioning claim) — verify against codegen before writing it in Devpost.
- U5: judge roster + participant count are live values; re-check near filing.
- U6: exact Devpost form fields (login-gated); owner confirms at filing.
- U7: cold-reader comprehension (B-14) and SR session (B-11) need owner-recruited
  humans — no agent may contact anyone.
