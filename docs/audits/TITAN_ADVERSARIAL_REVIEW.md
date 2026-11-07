# TITAN adversarial review — 50 questions + simulated jury (7 Nov 2026)

Two inputs: (1) an independent read-only judge-panel agent that did not
write the code (scores and findings below are its own, lightly
condensed); (2) the 50-question self-audit. Every row says what was
**done** about it in this wave, or why not.

## 1. Simulated jury (independent agent)

| Judge | Score | Strongest evidence | Top weaknesses |
|---|---|---|---|
| QNX principal engineer | 7/10 | Real `name_attach`/`MsgReceive`/`MsgReply` loops (`genesis_device.c`, `genesis_guard.c`), real `resmgr_attach` + `io_read` (`genesis_status.c`), bounded supervisor; both packs `VERIFY OK` | TCG-only timing, no priority/`SchedSet` scenario; Windows-only quickstart paths; garbled toolchain/identity lines in pack EXPECTED_RESULTS |
| Product design director | 6/10 | Honest BEFORE/AFTER hero, labelled ARCHIVED | Nav overload above the fold; default tab was an empty Projects view; long caveat paragraph |
| Industrial buyer | 4/10 | Candour: zero pilots/interviews stated plainly | No measured benefit; buyer persona/budget line unnamed; simulation-only, own IR, no import path |
| Innovation reviewer | 6/10 | Contract→binary→behaviour→passport binding + stale-build rejection | AI is a regex planner by default; LLM path has no sealed evidence; regex blocklist oversold as safety |

**Hardest question (agent's answer):** the Innovation & AI criterion —
the default "AI" is a deterministic keyword planner and the LLM path has
no sealed evidence; second, zero measured user benefit.

### Acted on in this wave

| Finding | Action |
|---|---|
| Default tab empty | Studio now opens on the **Guided tour** for first-time visitors |
| Caveat paragraph above the fold | Collapsed into a `What needs the backend?` disclosure |
| Nav reflects internal names | Regrouped by task: Start · Machines · Build & Run · Verify · Evidence · Explore, plainer labels |
| Windows-only quickstart | Added a Windows↔Linux path map (§0b) |
| Regex blocklist oversold | `planning.py` now states it is a courtesy pre-filter; `validate_ir` + gate are the boundary |
| No real AI path | Opt-in OpenAI-compatible `llm` provider (`--provider llm`), 13 adversarial tests with a fake endpoint |
| Fresh native run missing | Re-run attempted on the owner's box (see `TITAN_FINAL_READINESS.md`) |

### Open (needs owner or external input)

- Sealed run of a **real** LLM proposing IR (needs a model: e.g. start
  the local Ollama and pull a model — a multi-GB download not done
  without asking).
- Measured benefit: 2–3 interviews or one timed internal task.
- KVM/hardware latency run + priority/deadline-miss scenario.
- Clean toolchain/identity capture in the committed packs (the packs are
  sealed: fixing them means a new campaign, not editing sealed files).

## 2. Fifty questions (condensed)

Status: **OK** holds with evidence · **FIXED** this wave · **OPEN**.

| # | Question | Status | Evidence / note |
|---|---|---|---|
| 1 | Needlessly complicated component? | OPEN | `ui/studio.html` ~3.9k-line single file; deliberate (offline, no build) but hard to maintain |
| 2 | Unclear ownership? | OK | host/target/ui split; `facts.py` owns numbers |
| 3 | Duplicated state? | OPEN | guard policy exists in C and Python by design; pinned by conformance vectors |
| 4 | Implicit contracts? | OK | JSON schemas under `schemas/`, IR validator |
| 5 | Removable deps? | OK | runtime stdlib + optional extras only |
| 6 | Concurrency failures? | OK | admission 429 + stress tests; target lock shared CLI↔API |
| 7 | Cancellation? | OK | E2E cancel/refresh paths; runner cleanup stops QEMU on failure (seen live: `qemu_stop` ran after the failed op this wave) |
| 8 | Unchecked input? | OK | IR validator, path checks on generated-file endpoint (`api.py`) |
| 9 | Stale data accepted? | OK | stale-binary negative control; RFC 1982 seq freshness |
| 10 | False success? | FIXED | `qnx.yml` no longer looks like a target run |
| 11 | Native matches contract? | OK | 16/16 both packs, probe DENY→ALLOW |
| 12 | IPC errors exhaustive? | OK (judge) | MsgReceive loops skip pulses, reply with codes |
| 13 | Crash → unsafe state? | OK | supervisor GIVE_UP halt, crash-containment tests |
| 14 | Timing measured correctly? | OPEN | TCG only; documented as relative |
| 15 | Native claims reproducible? | OK/OPEN | packs verify offline; fresh campaign needs SDK + image |
| 16 | Forged result passes? | OK | tamper + verdict-flip rejected (exit 2) |
| 17 | Foreign passport reused? | OK | cross-op swap rejected |
| 18 | Artifacts bound to binary? | OK | guard sha256 in pack, IR digest binding |
| 19 | Incomplete results rejected? | OK | no-test ⇒ no-pass gate tests |
| 20 | Independent reproduction? | OK | stdlib `verify.py`, `python -S` test |
| 21 | API input escapes scope? | OK | path containment on gen files |
| 22 | Secrets leak? | FIXED | LLM key never echoed (test); target password env-only |
| 23 | Endpoint exposed? | OK | loopback bind, Origin guard (`docs/local-security-model.md`) |
| 24 | Resource exhaustion? | OK | 64 KiB LLM cap, preview size cap, admission control |
| 25 | Dependency reproducibility? | OK | axe pinned 4.10.2; actions pinned to majors |
| 26 | Beginner understands first screen? | FIXED | hero + guided tour default + plain-language trust lines |
| 27 | Judge finds strongest proof? | OK | BEFORE/AFTER table at top |
| 28 | Errors understandable? | FIXED | `trustSentence()` beside technical fields |
| 29 | Next action clear? | OK | two CTAs + guided stages |
| 30 | Nav reflects goals? | FIXED | task-based groups |
| 31 | Visually consistent? | FIXED | token design system |
| 32 | Density? | OPEN | judge still finds above-the-fold busy |
| 33 | Colors meaningful? | OK | status always paired with words |
| 34 | Hierarchy? | OK | — |
| 35 | Credible product look? | OPEN | clean but not yet "premium"; single-page layout |
| 36 | Keyboard completeness? | OK | tabs pattern, skip link (E2E) |
| 37 | Screen readers? | OPEN | landmarks/labels fixed; no SR session |
| 38 | Colour-only info? | OK | axe clean |
| 39 | Zoom/reflow? | OK | 320 px test per tab |
| 40 | Dynamic updates accessible? | OK/OPEN | `role=status` live region; long-job wording unreviewed |
| 41 | Precise customer pain? | OK | change verification for QNX control code |
| 42 | Why not existing tools? | FIXED | §9 of COMPETITIVE_LANDSCAPE: complement, not replace |
| 43 | Measured benefits? | OPEN | none yet |
| 44 | What blocks deployment? | OK | simulation-only, own IR, no certification (documented) |
| 45 | Most valuable feature? | OK | stale-build rejection + offline replay |
| 46 | Every rule addressed? | OK | rules re-fetched; license visible on GitHub |
| 47 | QNX-specific? | OK | native IPC, resmgr, QEMU target |
| 48 | Judge reproduces strongest claim? | OK | `verify.py` both packs, no SDK |
| 49 | Evidence per criterion? | OK/OPEN | Impact weakest |
| 50 | Single weakness costing the Grand Prize? | OPEN | AI depth + measured impact (see §1) |
