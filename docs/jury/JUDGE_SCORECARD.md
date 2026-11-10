# Judge scorecard (internal self-assessment)

> **Internal development assessment — not official judge scores.**
> Current scores are in the first table; everything below the line is
> historical and kept for traceability.

## Current internal assessment — 10 Nov 2026 (OMEGA7 + wow batch + causal slice, unmerged)

Causal slice (10 Nov 2026, branch `titan/omega7-causal-engine` —
unmerged, draft PR pending, no re-assessment of scores below):
incident → hypotheses → experiments → sealed dossier → K1 fix
proof; flagship estop 5.5 s incident-to-proof (n=1, host,
archived grounding); deterministic only; live path unexecuted;
human benefit still NOT YET MEASURED.

## Prior assessment — 10 Nov 2026 (OMEGA7 + wow batch)

1610 host tests green on the owner machine (SDK+axe: 1610 passed,
0 skips; SDK-only: 1608 + 2 honest axe skips).
SDK-free: 1604 + 6 honest skips (SDK-gated).
65 documentation-consistency tests
green, 113 planning unit tests green, E2E 44/44 with axe-core
(42 + 2 skips without it), Omega2 packs re-verified VERIFY OK
16/16 on the final tree (no target/ C changes, so no native
re-run required).

OMEGA7 delta (10 Nov 2026, branch `titan/omega7-v10-stale-arm` —
reported here, scores above held with no re-assessment): planner
contract v1.4 (Greifer tier-1, Roboter fleet forms, 4
safety-vocabulary additions, 4-kind multilingual unsupported
veto, rule-18-literal consult policy) measured on blind v10
(184 cases, d550b802): 159/165/165 with 15 unsafe accepts of
136 (same 15 on all providers), 0 wrong-kind, 29/26 consults
+ 3 explained mismatches; arm verdicts quarantined at the
release gate (FAIL + PHYSICS WARNING banner, native verdicts
byte-identical). Counts above re-synced to the OMEGA7 tree.

| Criterion | Omega4 | **Now** | New OMEGA5 evidence | Remaining gap | Independent attack |
|---|---|---|---|---|---|
| Technological Implementation | 9.5 | **9.5** | contract v1.3 (semantic frames, scoped negation, kind-evidence boundary) + 12 red-green planner cases + v9-overlap pin + exit-1 wiring test; `expect_consult` harness enforcement + v7/v8 consultation audit; 6 new doc pins; facts 1434/1428; packs re-verified offline | no native CI runner; TCG-only timing; one build host; cross-SDP unverified; local crypto still 43.0.3 (owner upgrade pending) | 9 (reviewer: v1.3 + enforcement + audit verified, packs re-verified; −1 QEMU-only + single host + no native CI + crypto residual) |
| Design | 8 | **8** | no UX changes this milestone (no redesign without evidence) | dense single page; no screen-reader session; video deferred | 7 (reviewer: unchanged since Omega4 — axe in CI, no SR session, no video) |
| Potential Impact | 5 | **5** | owner handoff refreshed (`OMEGA5_OWNER_ACTIONS.md`); nothing sent, nothing faked | `HUMAN USER BENEFIT NOT YET MEASURED`; zero participants, zero invitations | 5 (reviewer agrees) |
| Innovation & AI Creativity | 8.5 | **8.5** | blind v9 (160, 54e08384, no format example): 142/150/150; wrong-kind 4/3 → 0 via registry; 5 unsafe accepts of 112 (4 safety + 1 fleet, all deterministic-layer, classed); 34/36 consults with 14 explained consultation mismatches; consultation audit pins v7/v8 gaps; raws published | 5 unsafe/112 open; 14 v9 consultation mismatches (explained, not hidden); v9 targeted (no broad-robustness claim) | 8 (reviewer: genuine no-example blind loop, wrong-kind 4/3 → 0 recomputed, enforcement fires; −0.5 open 5/112 + rule-18 + targeted scope) |

Total **31 / 40** (Omega4: 31; independent reviewer: 29/40 =
9/7/5/8). The total holds: wrong-kind accepts are eliminated on
a blind set and consultation is now enforced and audited, but
unsafe accepts move 4 → 5 across a larger/harder reject pool
(rate 6.2% → 4.5%) with 14 explained consultation mismatches —
methodology strengthened, no broader claim earned. The reviewer
docked Tech/AI for structural residuals (QEMU-only, open 5/112)
and Design for no screen-reader session; all P0/P1 findings
(uncommitted state, 11-vs-12, stale limitations, Devpost raw
pointer) were fixed with tests before merge. Internal
assessment, not official judging. No criterion is claimed at
10/10. Final video DEFERRED BY OWNER; submission pending the
video.

---

## Historical assessment — 9 Nov 2026 (Omega4)

1348 host tests green on the owner machine (SDK+axe: 1348 passed,
0 skips; SDK-only: 1346 + 2 honest axe skips).
SDK-free: 1342 + 6 honest skips (SDK-gated).
45 documentation-consistency tests
green, 60 planning unit tests green, E2E 32/32 with axe-core
(30 + 2 skips without it), Omega2 packs re-verified VERIFY OK
16/16 on the final tree (no target/ C changes, so no native
re-run required).

| Criterion | Omega3 | **Now** | New Omega4 evidence | Remaining gap | Independent attack |
|---|---|---|---|---|---|
| Technological Implementation | 9.5 | **9.5** | CLAIMS/README drift fixes + 8 semantic pins (frozen-only latest-eval, Devpost planning pin, crypto-floor lock pin); requirements.lock cryptography 43.0.3 → 50.0.2 (floor met where CI installs); STALE 14/16 scoped to prose-grade; packs re-verified offline | no native CI runner; TCG-only timing; one build host; cross-SDP unverified; lock bump awaits CI proof | 9 (reviewer: sealed packs on current source hold; −1 QEMU-only + single host + crypto residual) |
| Design | 8 | **8** | screen-reader checklist protocol (prepared, NOT executed); keyboard/320px/390px/1366px/zoom review; no redesign without evidence | dense single page; no screen-reader session; video deferred | 7 (reviewer: axe 3/3 verified; −3 density + no SR + no video) |
| Potential Impact | 5 | **5** | pilot tooling validated on fixtures; owner handoff written; nothing sent, nothing faked | `HUMAN USER BENEFIT NOT YET MEASURED`; zero participants, zero invitations | 5 (reviewer agrees) |
| Innovation & AI Creativity | 8 | **8.5** | blind v7 (120, d91e3956): 83/82/79, 20 consults, 30 shared unsafe; fix-1 under contract v1.2 (6 red-green tests, fresh phrasings); blind v8 (100, cb3820fd): 82/90/92, 25 consults, 4 residuals (1 dispute + 3 subclasses); over-mapping 7-9 → 0; FR/wrong-kind metrics defined; raws published | 4 unsafe/100 open; v8 targeted (no broad-robustness claim); parcel-coinage→conveyor model bias; v6 zero-consult latency-inferred | 7 (reviewer: genuine v7→fix→v8 loop with frozen proof; −3 open residuals + no broad claim + report nicks, since fixed) |

Total **31 / 40** (Omega3: 30.5; independent reviewer: 28/40 =
9/7/5/7). The AI cell moves up half a point: the model path is
now exercised and measured (20-25 direct consults), the veto is
proven on a blind set (generic nouns 8/8, zero consults), and
residuals are 4 named cases instead of 26 classes — but v8 is a
targeted instrument, so no broader claim is made. Internal
assessment, not official judging. No criterion is claimed at
10/10. Final video DEFERRED BY OWNER; submission pending the
video.

---

## Historical assessment — 8 Nov 2026 (Omega3)

(Counts below were kept in sync through Omega4 P0; the evidence
cells are Omega3-era.)

1346 host tests green on the owner machine (SDK: 1344 passed + 2
honest axe skips; SDK-free: 1340 + 6 honest skips), 24-test adversarial
suite green, 28-case planning eval at 28/28, 60 planning unit tests
green, E2E 30 + 2 skips / 32, Omega2 packs re-verified VERIFY OK
16/16 on the final tree.

| Criterion | Omega2 | **Now** | New Omega3 evidence | Remaining gap | Independent attack |
|---|---|---|---|---|---|
| Technological Implementation | 9.5 | **9.5** | doc-drift fixes §4.1-4.7 + semantic pins; GET-36 re-audit + prose pin; cryptography floor >=49 verified; model-consult counter red-then-green; packs re-verified offline (no C changes, so no native re-run required) | no native CI runner; TCG-only timing; one build host; cross-SDP unverified | 9 (reviewer caps on QEMU-only + build-only CI; native claims held) |
| Design | 8 | **8** | first-proof Omega2 strip + stage-A copy fix + Playwright pin (green); 3-persona review with honest deferrals; probe 13 tabs x 2 widths, 0 errors | designer/graph/runner still a dense single page; no screen-reader session | 7 (reviewer stresses page density; no fake states found) |
| Potential Impact | 5 | **5** | quick-tier pilot + outreach kit + buyer brief + final Devpost draft — all infrastructure, held out of the score | `HUMAN USER BENEFIT NOT YET MEASURED`; zero participants, zero invitations | 5 (agrees) |
| Innovation & AI Creativity | 8.5 | **8** | blind v6 (separately agent-authored, frozen-before-fix): 46/72 x3 identical, 0 false rejects; v5 classes fixed (v4/v5 postfix 36/36 regression-only); consult counter; raw JSON published | 26 v6 unsafe-accept classes open; model consulted 0x (deterministic short-circuit); v7 required for the next honest claim | 7 (reviewer stresses 26/48 unsafe + unexercised model path) |

Total **30.5 / 40** (Omega2: 31.5). The total moves down
because blind v6 data showed the generalization problem is
harder than v5 suggested — methodology strengthened, measured
safety honesty reduced the AI cell. Internal assessment, not
official judging. No criterion is claimed at 10/10. Final video
DEFERRED BY OWNER; submission pending the video.

---

## Historical assessment — 8 Nov 2026 (Omega2)

| Criterion | 7 Nov | **Now** | New Omega2 evidence | Remaining gap |
|---|---|---|---|---|
| Technological Implementation | 9 | **9.5** | 4th native pack on current source (BEFORE/AFTER 16/16 ×2, v2 machine end-to-end first time, 14/16 STALE-as-designed); campaign lock + atomic staging; supervisor-passed pid + set-restart handshake with native proof; 5 native bugs found natively and fixed red-then-green; H9/M6/H8 trust fixes; 1346-test suite green (SDK: 1344+2; SDK-free 1340+6) | no native CI runner; TCG-only timing; one build host; cross-SDP reproducibility unverified |
| Design | 7.5 | **8** | Studio honesty pass (shared-core passport classifier, terminal phase banner, runner hint); E2E 29+2 green incl. axe clean × 2 themes; 48 control names verified | designer/graph/runner still form-heavy (scoped fixes, no full redesign); no screen-reader session |
| Potential Impact | 5 | **5** | pilot kit ready, zero invitations sent — unchanged | `HUMAN USER BENEFIT NOT YET MEASURED` |
| Innovation & AI Creativity | 8 | **8.5** | v4 rerun identical (no regression); v5 second frozen set (agent-authored, frozen-before-run) measured 24/36 × 3 identical, 0 false rejects; r14-class fix confirmed on fresh phrasings (2/2 deterministic) | 12 v5 unsafe-accept classes open; 72 cases still small and same-author; model refusal reasons unreliable |

Total **31.5 / 40** (7 Nov: 29.5). Internal assessment, not official
judging. No criterion is claimed at 10/10. Final video DEFERRED BY
OWNER; submission pending the video.

---

## Historical assessment — 7 Nov 2026 (Ascension)

| Criterion | Self (before review) | Independent agent | **Then** | Evidence | Remaining gap |
|---|---|---|---|---|---|
| Technological Implementation | 9.5 | 8.5 | **9** | real QNX IPC, resmgr, supervisor; 3 native packs 16/16; 18/18 published binaries rebuild bit-for-bit (`docs/ascension/QNX_REPRODUCIBILITY.md`); rebuild checker hardened after the review (no vacuous pass) | no native CI runner; one build host; TCG-only timing |
| Design | 8.5 | 7 | **7.5** | application shell, Overview, breadcrumbs, deep links/history, mobile menu, page intros, target-readiness line, ≥ 3:1 control borders, axe clean on 13 pages × 2 themes, 320 px + zoom tests | Machine designer, Evidence graph and Target runner still form-heavy; no screen-reader session |
| Potential Impact | 5 | 5 | **5** | sourced positioning; pilot kit + session timer | `HUMAN USER BENEFIT NOT YET MEASURED` |
| Innovation & AI Creativity | 8.5 | 7.5 | **8** | contract → binary → behaviour → passport binding visible in rebuilt binaries; 2-model, 98-case holdout; measured gaps fixed deterministically; 6 false refusals found by the review fixed with tests | no post-fix model run; holdout v2 written by the same author |

Total **29.5 / 40** (start of Ascension: 29). The independent agent is an
internal AI reviewer, not a human judge. No criterion is claimed at 10/10.

---

## Historical assessments


Internal target only — never a claim about official judging. Scores
are against the four published criteria; every cell links to
verifiable evidence or a named weakness.

| Criterion | Score | Evidence | Weakness | Improvement | Verified result |
|---|---|---|---|---|---|
| A. Technological Implementation | 9/10 | Native guard/controller/device/status/supervisor/faultinject + cellcheck in C (`qcc` 0 warnings, incl. env-gated IPC trace); contract-aware native oracle (IR-derived EXPECTED_DENY/ALLOW/SAFE_STOP/ERROR, float32 wire fidelity, mutation + flipped-verdict anti-cheating); 16/16 on-target matrix; two valid W11 before/after passports + genuine negative; native IPC timeline from real CLOCK_MONOTONIC stamps; 1346 host tests (SDK outcome per-machine; SDK-free: 1340 + 6 honest skips, Omega4 fix-1); C/Python conformance harness; red-team rounds 1–2; soak 100 jobs zero thread leak | QEMU-only (no real hardware); no HAM (absent from image); no HW attestation; uint32 ms clocks wrap-safe RFC1982 | ARM/real-board campaign; HAM integration when image ships it; 64-bit clocks | 16/16 matrix PASS + replay + tamper control; W11 packs VERIFY OK; fresh rerun op-24fecbf11df8 16/16 (7 Nov 2026, `evidence/qnx8-x86_64-w11-after-rerun/`) |
| B. Design | 9/10 | CLI + local API + Studio Live (projects/designer/SSE pipeline + Target Runner tab with phase checklist + inspection tabs incl. evidence graph); guided 7-stage Judge Mode tab with real run/inspect actions; coherent machine→native-QNX→passport flow from the page; verified 45-min codelab (Win+Linux); precise errors (exit 2 + reason); judge path is 2 commands; one-click dossier ZIP export (`/target/ops/{id}/dossier`: report.html + TOC/coverage/print CSS + manifest + VERIFY.md); inline release-decision panel (`/target/ops/{id}/decision`); change-proof before/after view (contract→code→binary→behavior→passports); real-browser E2E in CI (Judge A→G + 19 negative paths: guidance/cancel/refresh/navigation/tamper/outage/3 viewports, zero console errors); final video DEFERRED BY OWNER (historical w12 cut is not the submission video) | E2E covers the host path only in CI (no QEMU/SDK); final video deferred by owner; YouTube publication pending | Self-hosted SDK/QEMU CI lane; YouTube publish; dossier PDF export | E2E 32/32 (incl. axe WCAG 2.2 scan, both themes, + 320 px reflow) in CI; fresh-clone judge path green (suite 1324 + 6 SDK skips + pack verify OK) |
| C. Potential Impact | 8/10 | Industrial-cell flagship demo; `docs/business/COMMERCIAL_VISION.md` (users, 8 use cases, landscape, models, roadmap); honest QNX-licensing note; ~45-min onboarding measured; pilot-study kit (task set, both-lane templates, survey, privacy, repro scripts); bench v2 refreshed 2026-11-06 (8 vs 30+10, faults 5/5 vs 3/5, reproducible); CI IR-check bridge (per-push validate + impact + retest verdict + report artifact); dossier review UX | No pilot teams yet; human gains unmeasured (machine-time only, labeled as such) | 2–3 pilots with before/after numbers | Cell Demo C broken→fixed with causal delta; bench REPORT.json |
| D. Innovation & AI Creativity | 9/10 | Evidence passport + fail-closed gate + counterfactual compare (contract knob → verdict move); contract-aware oracle (distinguishes a changed expectation from a safety regression); native IPC timeline (SEND→RECV→REPLY→DONE waterfall from real target stamps); 24-test adversarial suite; pinned ce-001 counterexample + before/after regression; 28-case planning eval at 28/28 behind the strict gate | Bundled AI is a keyword planner, not an LLM (labeled as such); no real provider adapter | LLM provider adapter measured on the same 28-case set (if a provider becomes available) | `compare` output + eval + oracle mutation results, all replayable |

## Bonus coverage

- **Best Use of QNX-specific Technologies:** message passing,
  resmgr, RT scheduling experiments, supervision, crash containment —
  see `WHY_QNX.md` + `TECHNICAL_EVIDENCE.md`.
- **Best Codelab/Tutorial:** `docs/codelab/README.md` — every host
  command re-executed 2026-11-08 on `omega2` (target transcript
  from the 2026-11-05 live run), PowerShell variants for every
  step, troubleshooting, cleanup, limitations, final Devpost URL
  inside. Companions `docs/codelab/ADVANCED-QNX.md` (guards,
  supervision, provenance, replay — CI-harnessed) and
  `docs/codelab/EXTERNAL-BUILD.md` (15-min stale-binary lab for
  existing builds — CI-harnessed).

(Rules allow one general + one bonus prize per project; both tracks
are prepared without assuming they combine.)



## Internal re-assessment — 7 Nov 2026 (TITAN waves 1–3)

The table above is the earlier self-assessment. Re-scored from current
evidence, with an independent judge-panel agent's scores alongside
(`docs/audits/TITAN_ADVERSARIAL_REVIEW.md`; the agent reviewed before
waves 2–3 landed).

| Criterion | Earlier self | Agent (pre-wave 2) | Now | Why (evidence) | Main gap |
|---|---|---|---|---|---|
| Technological Implementation | 9 | 7 | **9** | real QNX IPC + resmgr + supervisor; BEFORE/AFTER packs + fresh native rerun 16/16 (op-24fecbf11df8); 1192-test suite (7 Nov pre-Ascension count) green on Windows+SDK and Linux CI | QEMU/TCG only; qcc believed non-reproducible at the time (corrected same day: 18/18 bit-for-bit, see QNX_REPRODUCIBILITY.md); native CI lane build-only |
| Design | 9 | 6 | **7** | task-based nav, guided tour default, themes + tokens, plain-language trust lines, axe WCAG 2.2 clean in CI | single 3.9k-line page; still dense above the fold; no screen-reader session |
| Potential Impact | 8 | 4 | **5** | narrowed, sourced positioning as a complement to Parasoft/LDRA/VectorCAST | zero pilots, zero interviews, no measured user benefit |
| Innovation & AI Creativity | 9 | 6 | **8** | contract→binary→behaviour→passport binding + stale-binary rejection; LLM intent architecture measured: 28/28, 8/8 vs 3/8 paraphrases, 0 unsafe accepts | one model, small eval sets |

No 10/10 is claimed. Video quality is not scored (deferred by owner).

> Correction 8 Nov 2026 (Omega3 INT jury attack): the "0 unsafe
> accepts" in the 7-Nov "Now" cell above was scoped to the 28-case
> eval of that date. Blind holdouts measured later (v5: 12, v6:
> 26 unsafe accepts) supersede it for any general safety reading —
> see the current assessment. The historical cell is preserved.
