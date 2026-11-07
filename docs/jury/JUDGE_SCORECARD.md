# Judge scorecard (internal self-assessment)

Internal target only — never a claim about official judging. Scores
are against the four published criteria; every cell links to
verifiable evidence or a named weakness.

| Criterion | Score | Evidence | Weakness | Improvement | Verified result |
|---|---|---|---|---|---|
| A. Technological Implementation | 9/10 | Native guard/controller/device/status/supervisor/faultinject + cellcheck in C (`qcc` 0 warnings, incl. env-gated IPC trace); contract-aware native oracle (IR-derived EXPECTED_DENY/ALLOW/SAFE_STOP/ERROR, float32 wire fidelity, mutation + flipped-verdict anti-cheating); 16/16 on-target matrix; two valid W11 before/after passports + genuine negative; native IPC timeline from real CLOCK_MONOTONIC stamps; 1166 host tests (all run w/ SDK; SDK-free: 1161 + 5 honest skips, 7 Nov 2026); C/Python conformance harness; red-team rounds 1–2; soak 100 jobs zero thread leak | QEMU-only (no real hardware); no HAM (absent from image); no HW attestation; uint32 ms clocks wrap-safe RFC1982 | ARM/real-board campaign; HAM integration when image ships it; 64-bit clocks | 16/16 matrix PASS + replay + tamper control; W11 packs VERIFY OK; fresh rerun op-24fecbf11df8 16/16 (7 Nov 2026, `evidence/qnx8-x86_64-w11-after-rerun/`) |
| B. Design | 9/10 | CLI + local API + Studio Live (projects/designer/SSE pipeline + Target Runner tab with phase checklist + inspection tabs incl. evidence graph); guided 7-stage Judge Mode tab with real run/inspect actions; coherent machine→native-QNX→passport flow from the page; verified 45-min codelab (Win+Linux); precise errors (exit 2 + reason); judge path is 2 commands; one-click dossier ZIP export (`/target/ops/{id}/dossier`: report.html + TOC/coverage/print CSS + manifest + VERIFY.md); inline release-decision panel (`/target/ops/{id}/decision`); change-proof before/after view (contract→code→binary→behavior→passports); real-browser E2E in CI (Judge A→G + 19 negative paths: guidance/cancel/refresh/navigation/tamper/outage/3 viewports, zero console errors); final video DEFERRED BY OWNER (historical w12 cut is not the submission video) | E2E covers the host path only in CI (no QEMU/SDK); final video deferred by owner; YouTube publication pending | Self-hosted SDK/QEMU CI lane; YouTube publish; dossier PDF export | E2E 24/24 (incl. axe WCAG 2.2 scan, both themes, + 320 px reflow) in CI; fresh-clone judge path green (suite 1161 + 5 SDK skips + pack verify OK) |
| C. Potential Impact | 8/10 | Industrial-cell flagship demo; `docs/business/COMMERCIAL_VISION.md` (users, 8 use cases, landscape, models, roadmap); honest QNX-licensing note; ~45-min onboarding measured; pilot-study kit (task set, both-lane templates, survey, privacy, repro scripts); bench v2 refreshed 2026-11-06 (8 vs 30+10, faults 5/5 vs 3/5, reproducible); CI IR-check bridge (per-push validate + impact + retest verdict + report artifact); dossier review UX | No pilot teams yet; human gains unmeasured (machine-time only, labeled as such) | 2–3 pilots with before/after numbers | Cell Demo C broken→fixed with causal delta; bench REPORT.json |
| D. Innovation & AI Creativity | 9/10 | Evidence passport + fail-closed gate + counterfactual compare (contract knob → verdict move); contract-aware oracle (distinguishes a changed expectation from a safety regression); native IPC timeline (SEND→RECV→REPLY→DONE waterfall from real target stamps); 24-test adversarial suite; pinned ce-001 counterexample + before/after regression; 28-case planning eval at 28/28 behind the strict gate | Bundled AI is a keyword planner, not an LLM (labeled as such); no real provider adapter | LLM provider adapter measured on the same 28-case set (if a provider becomes available) | `compare` output + eval + oracle mutation results, all replayable |

## Bonus coverage

- **Best Use of QNX-specific Technologies:** message passing,
  resmgr, RT scheduling experiments, supervision, crash containment —
  see `WHY_QNX.md` + `TECHNICAL_EVIDENCE.md`.
- **Best Codelab/Tutorial:** `docs/codelab/README.md` — every command
  verified live 2026-11-05, Win+Linux, troubleshooting, cleanup,
  limitations, final Devpost URL inside. Companion
  `docs/codelab/ADVANCED-QNX.md` covers guards, supervision,
  provenance and replay (CI-harnessed).

(Rules allow one general + one bonus prize per project; both tracks
are prepared without assuming they combine.)



## Internal re-assessment — 7 Nov 2026 (TITAN waves 1–3)

The table above is the earlier self-assessment. Re-scored from current
evidence, with an independent judge-panel agent's scores alongside
(`docs/audits/TITAN_ADVERSARIAL_REVIEW.md`; the agent reviewed before
waves 2–3 landed).

| Criterion | Earlier self | Agent (pre-wave 2) | Now | Why (evidence) | Main gap |
|---|---|---|---|---|---|
| Technological Implementation | 9 | 7 | **9** | real QNX IPC + resmgr + supervisor; BEFORE/AFTER packs + fresh native rerun 16/16 (op-24fecbf11df8); 1166-test suite green on Windows+SDK and Linux CI | QEMU/TCG only; qcc not byte-reproducible; native CI lane build-only |
| Design | 9 | 6 | **7** | task-based nav, guided tour default, themes + tokens, plain-language trust lines, axe WCAG 2.2 clean in CI | single 3.9k-line page; still dense above the fold; no screen-reader session |
| Potential Impact | 8 | 4 | **5** | narrowed, sourced positioning as a complement to Parasoft/LDRA/VectorCAST | zero pilots, zero interviews, no measured user benefit |
| Innovation & AI Creativity | 9 | 6 | **8** | contract→binary→behaviour→passport binding + stale-binary rejection; LLM intent architecture measured: 28/28, 8/8 vs 3/8 paraphrases, 0 unsafe accepts | one model, small eval sets |

No 10/10 is claimed. Video quality is not scored (deferred by owner).
