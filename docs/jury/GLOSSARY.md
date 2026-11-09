# Plain-language glossary

One page for a cold reader: what GENESIS RT is, and what its
most confusing terms mean. Numbers live in the linked reports,
not here — this page defines vocabulary only.

**One line.** GENESIS RT generates inspectable evidence about
the behavior of the code: you describe a machine, it builds a
QNX controller for it, runs it against fault scenarios, and
seals everything into a replayable evidence pack.

## The product in five nouns

- **Machine IR** — a strict JSON description of your machine
  (actuators, sensors, control limits, safety contracts,
  scenarios). Strict means: unknown keys are rejected, never
  guessed.
- **Pipeline** — validate → generate C → build → run fault
  scenarios → seal evidence → gate verdict. One command
  (`genesis-rt demo`) or one Studio button.
- **Passport** — the sealed result of one pipeline run: a
  hash-chained JSON document (each record links to the
  previous, so tampering breaks the chain). Re-verify offline
  with `verify.py` or by opening it in the dashboard.
- **Gate verdict** — PASS only when every required scenario
  passed and the evidence is complete. Missing, skipped, or
  tampered evidence yields FAIL (`no-test => no-pass`).
- **BEFORE/AFTER** — run the pipeline on two revisions, diff
  them: which contract knob moved, which scenarios flipped,
  what the gate says. `genesis-rt verify-change` does both
  runs plus the diff in one step.

## The AI vocabulary (the steepest wall)

The optional planner turns short English into draft IRs. The
model proposes; the deterministic validator disposes. Three
failure kinds are tracked separately — never folded into one
accuracy number:

- **Unsafe accept** — the planner produced an IR for a request
  that should have been refused (a reject case). The scary one.
- **Wrong-kind accept** — the request was valid, but the IR
  describes the wrong machine kind. A different mistake from
  unsafe; counted separately.
- **True false reject** — a valid request the planner refused.
  Annoying, not dangerous.
- **Consult** — cases where the expected behavior is to ask
  the user (ambiguous input) instead of guessing. A
  **consultation mismatch** means the harness expected a
  consult but got an IR (or vice versa); each is explained in
  the consultation audit.

How the planner is measured:

- **Blind holdout** — a frozen set of cases authored
  separately from (and before) the code under test, so the
  code cannot have memorized them. Newest sets first; older
  sets are history, never re-run on changed code.
- **Qualified-blind (v8)** — the v8 set had format-preview
  exposure during authoring, so it is never called "blind"
  without that qualification in the same paragraph.
- **Frozen vs regression** — frozen sets are sealed and never
  re-run after a code change; regression sets may be re-run.
  Current numbers: `docs/CLAIMS.md` → "AI evaluation (current)".

## Trust vocabulary

- **hash-only / UNSIGNED** — packs prove integrity (nothing
  was modified) via SHA-256, not identity (no signature says
  who produced them). Verification answers "was it modified",
  not "who attests this".
- **`qnx_verified`** — a passport field that is true only when
  the evidence includes a genuine native QNX run. Host-only
  runs say false, loudly.
- **Stale-binary control** — the negative control: a contract
  change run against the OLD binary must fail, exactly on the
  changed behavior. If the old binary passed the new contract,
  the oracle would be vacuous. Currently operator-recorded
  (prose-grade), not a sealed transcript.
- **SDK-free replay** — re-verifying a pack with no QNX SDK:
  two commands, works anywhere. Re-running the native matrix
  needs SDP 8.0 + QEMU.

Pointers: AI numbers → `docs/CLAIMS.md` and
`docs/audits/OMEGA5_AI_EVALUATION.md`; native proof →
`docs/jury/TECHNICAL_EVIDENCE.md`; honest limits →
`docs/jury/KNOWN_LIMITATIONS.md`.
