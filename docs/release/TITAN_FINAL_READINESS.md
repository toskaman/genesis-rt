# TITAN readiness (7 Nov 2026) — waves 1 and 2

Base `c0acdd3` (PR #4). Scope of this wave: honesty fixes found by
reproducing the brief's leads, the Studio design system (themes, tokens,
plain-language trust text) and an automated WCAG 2.2 scan in CI.
**No video work** (`submission/VIDEO_DEFERRED.md`).

## Leads from the brief — reproduced and resolved

| # | Lead | Reproduced? | Resolution |
|---|---|---|---|
| 1 | `qnx.yml` builds but advertises a target run | **Yes** (`name: qnx-target`, job `qnx-build-and-run`, no QEMU/verify step) | Renamed to `qnx-native-build`, stages numbered, explicit `Native target campaign: NOT EXECUTED` step; test `test_qnx_workflow_does_not_overclaim_target_run` |
| 2 | Native campaign not rerun | Yes | **Rerun in wave 2** (op-24fecbf11df8, see below). Wave 1 wrongly blamed the BIOS: virtualization is on; the Windows hypervisor is not running, and QEMU TCG never needed it. |
| 3 | W12 video presented as the final video | **Yes** (README, CLAIMS, scorecard) | All current-facing docs now say `DEFERRED BY OWNER`; test `test_video_status_deferred_everywhere` |
| 4 | Environment-dependent tests | Fixed in PR #4 (stdlib-verify test) | — |
| 5 | Limitations misdescribe RFC 1982 wrap | **Yes** ("documents the boundary instead") | Rewritten with code + test references and residual limits; test `test_limitations_match_rfc1982_implementation` |
| 6 | No WCAG 2.2 audit | Yes | axe-core scan in CI, fixes, `docs/design/ACCESSIBILITY_AUDIT.md` |
| 7 | Navigation / visuals | Partly | Token design system, light/dark/system theme, no-flash init, theme selector (`docs/design/DESIGN_SYSTEM.md`) |
| 8 | No external pilot | Yes | Unchanged; pilot kit exists (`docs/business/pilot-study.md`), zero participants |
| 9 | Planner is not an LLM | Yes | Unchanged and still disclosed |
| 10 | Native / host / archived labelling | Partly | Plain-language `trustSentence()` beside every `qnx_verified`/`release_eligible` display |

## Measured

| Check | Result |
|---|---|
| Full suite, Linux SDK-free (Py 3.13) | **1141 passed, 5 skipped** (1146 collected) |
| axe WCAG 2.2 A/AA, 12 tabs × 2 themes | 0 serious/critical; 0 at any level incl. best-practice (manual run) |
| 320 px reflow, 12 tabs | no horizontal page scroll |
| UI + browser E2E | green |

The Windows + QNX SDK run (1140/0 skips) belongs to PR #4; it was not
repeated for the three tests added here.

## Official rules re-check (fetched 7 Nov 2026)

Deadline 15 Dec 2026 2 pm EST; judging 15–29 Jan 2027; project must stay
testable until judging ends; one Overall + one Bonus + one Community
Choice max; build instructions must state QNX version, target (QEMU) and
toolchain (present: `docs/quickstart-qnx8-qemu.md`, qcc 12.2.0);
**license must be visible in the repo About section** — to confirm on
GitHub; **video must show the project running on the intended device**
(note for the deferred video: show the QEMU target, not only the host).

## Not done in this wave (honest)

Full IA rebuild into Machines / Build & Run / Verify / Evidence /
Explore pages, AI provider adapter, competitive re-research, 50-question
audit, jury simulation, fresh native campaign, screen-reader session.

## Wave 2 (same day)

### Fresh native QNX campaign — executed

`op-24fecbf11df8`, owner's Windows box, QNX SDP 8.0 (qcc 12.2.0,
gcc_ntox86_64), QEMU TCG `-cpu max`, AFTER contract (1.6 m/s):

| Step | Result |
|---|---|
| validate → generate | IR `fb2dbb3d…` (identical to the committed AFTER pack) |
| build | 6 binaries, qcc 12.2.0 |
| qemu_boot / wait_ssh / put | booted, SSH up, 9 files staged |
| qemu_verify | **16/16** on `QNX qnxqemu 8.0.0 x86_64` |
| qemu_perf | 1000 samples (TCG: relative only) |
| seal / replay | gate **PASS**, `qnx_verified=True`, replay matches |

Runtime 215 s. Packaged as `evidence/qnx8-x86_64-w11-after-rerun/`
(34/34 digests, `VERIFY OK`). A first attempt (op-08bfa36a6cfd) failed
honestly at `qemu_put` (no target password in the environment); QEMU was
cleaned up by the runner.

**Finding:** the rebuilt guard binary hash (`f92f5e66…`) differs from the
AFTER pack's (`b65afcb4…`) although the generated C is identical. Codegen
is deterministic; the qcc build is **not byte-reproducible** across runs
(likely embedded paths/timestamps). Behaviour and verdicts match. Not
fixed; recorded as a limitation.

### Also done in wave 2

- Studio nav regrouped by task (Start · Machines · Build & Run · Verify
  · Evidence · Explore); first visit opens the Guided tour; backend
  caveats folded into a disclosure. UI + E2E green.
- Opt-in `llm` planning provider (OpenAI-compatible, env-configured,
  stdlib HTTP, 64 KiB cap, key never echoed) — `genesis-rt plan
  --provider llm`. 12 adversarial tests against a fake endpoint. **No real
  model was called**; quality is unmeasured.
- Competitor re-check (§9 of `docs/business/COMPETITIVE_LANDSCAPE.md`):
  Parasoft already runs unit tests on QNX targets; positioning changed to
  "change-verification and evidence layer that complements" them.
- Independent judge-panel agent + 50-question audit:
  `docs/audits/TITAN_ADVERSARIAL_REVIEW.md` (agent scores: QNX 7,
  design 6, buyer 4, innovation 6).
- Quickstart Windows↔Linux path map; evidence-pack builder now prints
  clean target-identity / toolchain lines.
- Suite: 1158 collected; Linux SDK-free 1153 passed + 5 skipped.

### Still open

Measured user benefit (interviews / timed
task); KVM or hardware timing; byte-reproducible qcc builds; screen-reader
session; deeper visual redesign.

## Wave 3 — real-model evaluation (same day)

Owner-approved throwaway Vultr VM (12 vCPU, CPU only, ~45 min, est.
< 0.25 USD of credits, destroyed afterwards with its SSH key). Ollama +
`qwen2.5:7b-instruct`. Three measured rounds changed the architecture:

| Round | Design | 28-case eval | Unsafe accepts |
|---|---|---|---|
| 1 | model writes IR | 19/28 (valid 2/10) | 1 |
| 2 | model → intent → deterministic template | 24/28 | 4 |
| 3 | + deterministic unit/range/ambiguity guards before the model | **28/28** | **0** |

Paraphrase set (outside the keyword vocabulary): offline 3/8, llm **8/8**.
End-to-end: model-planned IR → generate → host pipeline → passport PASS,
replay valid (host-only evidence). Data:
`evals/results/2026-11-07-qwen2.5-7b/`.

## Verdicts

- Software: **`SOFTWARE_READY_WITH_LIMITATIONS`**
- Submission: **`SUBMISSION_PENDING_DEFERRED_VIDEO`**
