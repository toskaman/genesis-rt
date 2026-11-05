# Why GENESIS RT (judge copy)

## The problem

Embedded control prototypes are slow to build, and their test
evidence is usually folklore: hand-wired IPC glue, hand-run fault
checks, screenshots in a slide deck that rot the next day. When the
spec changes, nobody can say what broke, what the fix changed, or
whether the green light means anything.

## The approach

GENESIS RT compiles a typed machine contract into three things at
once: native QNX software (guard + controller + device +
supervision), a seeded fault campaign with oracles that can genuinely
fail, and a hash-linked evidence passport where every verdict points
at the execution it came from. Change a limit, recompile, and the
target behavior changes the same day — with the before/after evidence
side by side (`compare`, Studio Diff tab, `POST /compare`).

The core loop: **specify → validate → compile → execute → break →
measure → prove → compare → improve.**

## What is genuinely new here

Not code generation — the evidence loop around it:

- A strictly validated contract language (unknown input rejected,
  never guessed) whose limits and transitions provably drive
  *runtime* behavior on the target, not just file diffs.
- A fail-closed release gate: missing, skipped, crashed, tampered,
  or recycled evidence always yields FAIL (adversarial suite:
  13+ forgery classes refused).
- Passports a stranger can replay offline (`scripts/replay.py`),
  with tamper-detection controls and an explicit `qnx_verified`
  label — host evidence is never dressed up as target evidence.
- Counterfactual engineering as a first-class command: broken vs
  fixed, contract knob to verdict move, in one screen.

## Honest boundaries

Prototype-grade, QEMU-only, no safety certification, no formal
verification, no production timing guarantees. AI assistance is a
keyword planner with a measured 28-case eval (28/28) behind the same
strict gate — useful, limited, and labeled as such; no LLM is
bundled and none is claimed. Everything measured ships method + raw
artifacts; everything pending is labeled pending. That distinction
is the point of the project — see `KNOWN_LIMITATIONS.md`.

## If you remember one line

**GENESIS RT doesn't merely generate code. It generates inspectable
evidence about the behavior of the code.**
