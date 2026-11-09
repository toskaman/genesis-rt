# GENESIS RT — UX reinvention + killer feature (v3 research)

Date: 2026-11-09. Scope: strategy + spec only (READ-ONLY on `genesis-rt/`; this file is the only write).
Inputs read in full: [recon.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/recon.md:1),
[winners-delta.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/winners-delta.md:1),
[qnx-forensics.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/qnx-forensics.md:1),
[competitors.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/competitors.md:1),
plus every code/doc body cited below (opened; search output only located candidates).
Labels: **VERIFIED FACT** (opened body) / **OBSERVATION** (measured or reasoned, needs interpretation) /
**ASSUMPTION** (low confidence). No metrics, scores, feedback, or testimonials invented.

Rubric anchor (**VERIFIED FACT**, high — [qnx-forensics.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/qnx-forensics.md:32-41)):
four equally-weighted criteria — Technological Implementation, Design ("complete, coherent product
experience, not just a technical proof of concept"), Potential Impact, Innovation & AI Creativity —
plus Stage-One gate and criterion-1-first tie-breaks. Internal self-score is 31/40 with Design at 8
(dense single page, no screen-reader session, video deferred) and Impact at 5 (no pilots)
(**VERIFIED FACT**, high — [JUDGE_SCORECARD.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/JUDGE_SCORECARD.md:18-24)).

---

## 1. Most painful workflow + friction-removal plan

### 1.1 The workflow: "my first custom machine" (idea → valid IR → first green passport)

**VERIFIED FACT** (high): GENESIS RT requires expressing the machine in its IR first — a real adoption
tax for anyone not starting from an example
([competitors.md §4.4](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/competitors.md:281-285)).
The smallest real IR is 45 lines of strict hand-written JSON (whitelist, fail-closed,
`simulation_only: true` required)
([cell-ir.json](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/examples/cell-demo/cell-ir.json:1-45),
[architecture.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/architecture.md:42-46)).
A planner (NL→IR) exists, but the model proposes and the deterministic validator disposes, with
5 unsafe accepts of 112 reject cases still open on blind v9
(**VERIFIED FACT**, high — [README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/README.md:58-71)).
The Studio Designer already has JSON editing + authoritative backend validation + error locate
(**VERIFIED FACT**, high — [ui/README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/README.md:9-18)).

**OBSERVATION** (high): this is the most painful workflow because it is the *entry* workflow every
new user, judge-experimenter, and pilot must survive, and every error in it surfaces as a raw
validator message the user must manually map back to a line, fix, and re-run. The judge happy path
(Demo A, 2 min) never touches it — it runs a canned script
([START_HERE.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/START_HERE.md:10-22)) —
so the pain is invisible in the demo but dominant in real use. Winners-delta DP5 ("designing for
the non-user") and D11's "remove a real footgun" lesson both point at exactly this class of fix
([winners-delta.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/winners-delta.md:214-226)).

### 1.2 Before: 13 actions (CLI + editor, grounded in opened bodies)

Counted from [DEMO_WALKTHROUGH.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/DEMO_WALKTHROUGH.md:1-69),
[START_HERE.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/START_HERE.md:10-22), and the Designer description:

| # | Action | Source |
|---|---|---|
| 1 | Browse `examples/` to find the closest machine kind | examples dir (recon §2) |
| 2 | Copy the example IR to a working file | — (manual step) |
| 3 | Open it in an external editor | — (manual step) |
| 4 | Hand-edit N fields (actuators, sensors, control knobs, contracts) | cell-ir.json:9-29 |
| 5 | Run `genesis-rt validate <file>` (1 of 22 subcommands) | cli.py:494-612 (recon §3) |
| 6 | Read the raw validator error text | PLANNER_CONTRACT / validator behavior |
| 7 | Manually locate the offending line/field | no CLI locate (Designer has it; CLI does not) |
| 8 | Fix in editor | — (manual step) |
| 9 | Re-run validate | repeat of 5 |
| 10–11 | Repeat 6–9 for the next error class (strict whitelist ⇒ errors arrive one family at a time) | strict per-version loaders, architecture.md:42-46 |
| 12 | Run `genesis-rt demo --ir <file>` and note the printed run id | DEMO_WALKTHROUGH.md:54-58 |
| 13 | Run `replay.py <passport>` / open `dashboard.html` and load the passport | START_HERE.md:15-20 |

**OBSERVATION** (med): realistic first-machine cost is 13+ actions with 2–4 validate-fix loops;
each loop crosses three surfaces (terminal → editor → terminal).

### 1.3 After: 5 actions (Studio "New machine" guided flow — all additive)

| # | Action | Mechanism (existing substrate) |
|---|---|---|
| 1 | Type intent in one box ("AMR, 1.2 m/s, e-stop freezes drive") | existing planner endpoint; validator still decides |
| 2 | Review the drafted IR in the Designer (state graph + JSON side by side) | existing Designer tab |
| 3 | Press Validate → each error arrives with line-locate + one-click suggested fix | existing error-locate + new fix-suggestion renderer (validator messages already structured) |
| 4 | Press Run pipeline (validate → generate → run → passport → diff) | existing SSE pipeline runner |
| 5 | Passport auto-opens, chain re-verified live | existing Passport tab |

**OBSERVATION** (med): 13 → 5 actions (−62%), three surfaces → one, and the unsafe-planner risk is
contained by the existing "model proposes, validator decides" architecture — the flow can only
narrow the funnel, never widen the gate. Effort: days (a Studio tab composition + fix-suggestion
renderer over existing APIs; no pipeline, schema, or gate changes).

---

## 2. Five killer-feature candidates (scored /10)

Scoring dimensions: pain solved (P), workflow improvement (W), time saved (T), demo impact (D),
originality (O), differentiation vs inspected competitors (Df), rubric alignment (R), feasibility
before 15 Dec 2026 (F), reliability (Rl), evidence potential (E). Scores are **OBSERVATION** (med):
reasoned judgments against the four opened research files, not measurements. All candidates are
additive, need no video production, and reuse existing subsystems (constraint compliance per
candidate).

### K1. "Prove my change" — one-click BEFORE/AFTER verdict card (CLI `verify-change` + Studio button)

Old Demo C takes 3 CLI commands + manual run-id plumbing + a separate diff surface
([DEMO_WALKTHROUGH.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/DEMO_WALKTHROUGH.md:48-69)).
K1 collapses it: point at two IRs (or one IR + one knob edit), get one card — contract knob,
regenerated files, binary hashes, fixed/broken scenarios, gate verdict — backed by the existing
`compare` + gate machinery. One-sentence identity in the D4/D10/D12 pattern ("change one number,
get a verdict, not a log pile").

| P | W | T | D | O | Df | R | F | Rl | E | Σ/100 |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 9 | 8 | 9 | 7 | 10 | 10 | 9 | 9 | 10 | **90** |

Effort: S–M (2–4 days: CLI wrapper + Studio card over `POST /runs` ×2 + `POST /compare`; zero gate
changes). Risk: low — read-only composition of green paths; failure mode is "falls back to today's
3-command flow." Df=10 because no inspected competitor body describes contract-knob → verdict moves
([competitors.md §5.1](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/competitors.md:296-300)).

### K2. Guided IR co-author — NL draft + deterministic repair loop (Studio "New machine" flow, §1.3)

NL intent → drafted IR → validate → line-located errors with one-click fixes → run. Directly
removes the §1 adoption tax; D11 "remove a real footgun" pattern.

| P | W | T | D | O | Df | R | F | Rl | E | Σ/100 |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 9 | 9 | 7 | 6 | 7 | 9 | 7 | 7 | 7 | **78** |

Effort: M (4–7 days: prompt-to-planner wiring, fix-suggestion renderer, loop tests). Risk: medium —
planner has 5 open unsafe accepts on v9; the validator gate must remain the sole decider (it
already is), and every NL-drafted IR must carry a "drafted, validator-decided" label to avoid
implying model authority. Rl=7 reflects that new UI surface area near a safety-relevant gate.

### K3. One-file proof capsule — double-clickable offline evidence bundle

Extends the dependency-free `dashboard.html` + `genesis_verify.js` + stdlib `verify.py` story
(**VERIFIED FACT**, high — [ui/README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/README.md:18-28)):
`genesis-rt export-proof <run>` emits a single self-contained HTML capsule (passport + chain +
timeline + dossier summary + embedded verifier) that opens from disk with zero install. D12
"works for people who never touch the tech" pattern — a reviewer verifies without cloning.

| P | W | T | D | O | Df | R | F | Rl | E | Σ/100 |
|---|---|---|---|---|---|---|---|---|---|---|
| 7 | 7 | 7 | 8 | 6 | 9 | 8 | 9 | 10 | 9 | **80** |

Effort: S (2–3 days: exporter composing existing dossier + verify core; node-tested like today).
Risk: very low — pure read path, no pipeline contact. Df=9: no fetched competitor body describes a
stranger-replayable offline artifact ([competitors.md §5.2](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/competitors.md:301-306)).

### K4. "Green board" — one-button native matrix re-run with live progress (Studio target runner)

Wraps `qnx_target.py` probe → boot → run → verify into one Studio button with per-step progress and
the stale-refusal display, degrading to archived-pack replay without an SDK (today the QNX lane is
build-only with no runner, and native reproduction is the documented high-friction path —
**VERIFIED FACT**, high: recon §7/§11; [quickstart §1](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/quickstart-qnx8-qemu.md:44-58)
needs a myQNX account no automation can remove).

| P | W | T | D | O | Df | R | F | Rl | E | Σ/100 |
|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 8 | 6 | 9 | 5 | 8 | 9 | 5 | 6 | 8 | **72** |

Effort: M–L (5–10 days: SSE streaming of a long SSH/QEMU campaign, timeouts, pidfile safety).
Risk: medium-high — live QEMU/SSH in a demo is flaky by nature; F=5 because the irreducible myQNX
+ image-unpack steps cap what "one button" can honestly claim before 15 Dec.

### K5. Fault Lab "chaos dial" — one-click seeded campaign presets with verdict strip

Preset dial (Nominal / Rough / Hostile) over the existing simulator + Fault Lab + seeded fault
injection (**VERIFIED FACT**, high — recon §3): one click runs the campaign, renders a per-scenario
verdict strip with DENY reasons (`SPEED_OVER_LIMIT`, `STALE_SEQ`, `ESTOP` — machine-readable today
per [DEMO_WALKTHROUGH.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/docs/jury/DEMO_WALKTHROUGH.md:43-46)),
exports the transcript. D13 "live-playable beats describable" pattern.

| P | W | T | D | O | Df | R | F | Rl | E | Σ/100 |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 7 | 6 | 9 | 5 | 6 | 7 | 9 | 9 | 8 | **72** |

Effort: S (2–3 days: preset definitions + strip renderer over existing `faults` CLI/API). Risk:
low — host-only, deterministic seeds. Df=6: fault injection exists elsewhere; the contract-aware
oracle framing is the only moat.

### Ranking

1. **K1 Prove-my-change (90)** — highest rubric alignment + differentiation at low risk.
2. K3 Proof capsule (80) — best reliability/effort ratio; ideal second slice if time permits.
3. K2 Guided co-author (78) — biggest pain solved, but touches the safety-gate neighborhood.
4. K4 Green board = K5 Chaos dial (72) — strong demos, weaker feasibility (K4) / moat (K5).

**SELECTED: K1.** It turns the project's proven differentiator (contract-aware BEFORE/AFTER with
stale refusal — Omega2 16/16 + STALE 14/16 failing exactly on changed behavior, recon §8) into the
product's front door, directly answers Design's "complete, coherent experience" (the current Diff
experience spans CLI + run ids + Studio tab), and is pure composition of green, tested paths.

---

## 3. Selected feature spec: K1 "Prove my change"

- **User.** Embedded prototyper / controls reviewer iterating on a machine contract, and the
  hackathon judge replaying the change story. (**OBSERVATION**, med — same persona as
  [competitors.md §3-user row](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/competitors.md:247-259).)
- **Problem.** Proving that a requirement change did what was intended — and nothing else — today
  requires running two pipelines by hand, plumbing run ids between commands, and assembling the
  verdict from three surfaces (terminal, Studio Diff tab, dashboard). Demo C's own script shows the
  seams: two `demo` runs with `<broken>`/`<fixed>` placeholders the user must fill in, then a
  separate `compare` (**VERIFIED FACT**, high — DEMO_WALKTHROUGH.md:48-69).
- **Old process (7 actions).** (1) Run pipeline on IR-A → copy run id. (2) Edit IR → IR-B.
  (3) Run pipeline on IR-B → copy run id. (4) Run `compare <idA> <idB>`. (5) Read terminal delta.
  (6) Open Studio Diff tab to see it graphically. (7) Open dashboard to confirm passport chains.
  (**OBSERVATION**, med — assembled from DEMO_WALKTHROUGH.md:48-69 + START_HERE.md:10-22.)
- **New process (2 actions).** (1) `genesis-rt verify-change --before IR-A --after IR-B`
  (or: open Studio → Before/After tab → pick A and B → Prove). (2) Read the single verdict card.
  (**OBSERVATION**, med — proposed.)
- **Interaction.** CLI prints a compact card and writes `artifacts/change/<id>/verdict.json`; Studio
  renders the same JSON as a card: knob table (`max_linear_speed_mps: 0.3 → 1.2`), scenario flips
  (fixed/broken lists), regenerated-file + binary-hash chips, gate verdict banner (PASS/FAIL), and
  "open passports" links. On any sub-step failure the card shows which leg failed and falls back to
  printing the equivalent manual commands (no dead ends). (**OBSERVATION**, med — proposed; visual
  vocabulary reuses the existing proof-card pattern in
  [studio.html](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/studio.html:231-239).)
- **Visible outcome.** One screen proving causation: "this knob moved, these scenarios flipped,
  everything else held, gate says PASS, both chains valid." The Omega2 narrative (same 16/16
  harness, STALE failing exactly the changed steps) becomes reproducible on any user-supplied pair,
  not just the shipped packs. (**OBSERVATION**, med.)
- **Technical mechanism (additive only).** New thin orchestrator `host/genesis_rt/change.py`
  (~150 lines): calls the existing run orchestrator twice (same function the CLI and Studio
  pipeline already share — "every pipeline step executes the same orchestrator the CLI uses,"
  [ui/README.md](C:/Users/TheBox/Desktop/QNX-hackaton/genesis-rt/ui/README.md:27-28)), then the
  existing `compare` + `gate` + `replay` logic; new CLI subcommand `verify-change` (23rd, same
  argparse pattern as the 22 in cli.py:494-612); new `POST /changes` + `GET /changes/{id}` routes
  beside `POST /compare` (api.py:289-1097); Studio Before/After tab gains a "Prove" button
  rendering `verdict.json`. No schema, validator, codegen, gate-semantics, or target changes; no
  frozen-eval contact. (**OBSERVATION**, med — proposed; all touch-points VERIFIED FACT per recon
  §3/§6.)
- **Verification method.** (1) New tests: golden `verdict.json` for the cell broken→fixed pair
  (contract knob + fixed-scenario list asserted, mirroring DEMO_WALKTHROUGH.md:59-62 expectations);
  failure-leg tests (broken leg fails ⇒ card shows leg failure + manual-command fallback, exit
  non-zero); API round-trip test for `POST /changes`. (2) Existing gates must stay green:
  `tests/unit/test_docs_consistency.py` (51 tests) plus a new pin that Demo C's documented outputs
  still match (docs-consistency pattern, recon §7). (3) Manual: run on Omega2 IR pair and confirm
  the card's knob table matches the sealed packs' known delta. (**OBSERVATION**, med — proposed.)
- **Expected benefit.** Change-verification loop 7 → 2 actions; the flagship differentiator becomes
  the first thing a judge/reviewer touches instead of a 3-command recipe; Design criterion gains a
  coherent story ("complete experience") without any redesign risk; every future BEFORE/AFTER claim
  ships as a re-runnable artifact (`verdict.json` + two passports) instead of prose.
  (**OBSERVATION**, med. No user benefit measured yet anywhere in the repo — Impact stays honestly
  at 5 until a pilot runs.)
- **Demo sequence (live, no video production, SDK-free, ~90 seconds).**
  1. Studio Before/After tab: A = `cell-ir-broken.json`, B = `cell-ir.json` → press Prove (~10 s).
  2. Card appears: `max_linear_speed_mps: 0.3 → 1.2`, three scenarios flip FAIL→PASS, gate PASS
     (mirrors DEMO_WALKTHROUGH.md:54-62, now in one surface) (~20 s).
  3. Click "open passports" → both chains re-verify live in the dashboard core (~15 s).
  4. Terminal encore: same result from `genesis-rt verify-change --before … --after …` (~20 s).
  5. Closer (one sentence, D4/D10 pattern): "Change one number, get a verdict — not a log pile."
     (~10 s + questions.)

### Constraints check

Additive (new module + subcommand + routes + button; no existing behavior altered) / low-risk
(composition of green paths with manual-command fallback; full existing suite + docs pins must stay
green) / no video production (live demo only) / days not weeks (2–4 days per §2 estimate; ~5 weeks
remain to 15 Dec 2026 per [qnx-forensics.md](C:/Users/TheBox/Desktop/QNX-hackaton/v3-research/qnx-forensics.md:25-30)).

## 4. Unresolved / explicitly not claimed

- U1: No prototype built — action counts and day estimates are reasoned, not measured.
- U2: Whether judges value the one-click story over raw CLI transparency — no judge feedback exists
  anywhere in the inputs (winners-delta unresolved, qnx-forensics U3).
- U3: K2's fix-suggestion quality and K4's live-QEMU flakiness are unprobed; K1 selected partly to
  avoid both unknowns.
- U4: Human-productivity gain remains UNKNOWN by the project's own admission (zero pilots).
