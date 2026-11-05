# GENESIS RT — demo narration (target 2:40–2:55, hard cap < 3:00)

English. ~380 words ≈ 2:45 at narration pace. Every line maps to a
captured or capturable authentic shot (see CAPTURE_PLAN.md and
SHOT_EVIDENCE.md). No mockups, no fake runs, no hardware claims:
QNX 8.0 runs virtualized under QEMU, labeled on screen.

## 0:00–0:12 — The hook

Embedded machines must behave predictably — especially when
something fails. GENESIS RT turns machine requirements into native
QNX software, then proves how that software behaves when things
go wrong.

## 0:12–0:30 — Machine design

Everything starts from a readable contract: sensors, actuators,
safety limits, state transitions. The tooling validates the
specification strictly — invalid input is rejected, never guessed.

## 0:30–0:52 — Native QNX generation

One click generates the native QNX controller: a guard server, a
periodic controller, a device endpoint, telemetry, and a
supervisor. Deterministic codegen — the same contract always
yields byte-identical sources.

## 0:52–1:15 — Real QNX execution

The controller compiles clean with qcc and runs natively on
QNX 8.0 — synchronous message passing, process isolation, a live
resource manager. Sixteen on-target checks pass, and a thousand
performance samples are recorded for regression.

## 1:15–1:38 — Break the system

Now we break it on purpose. A seeded fault — a stale proximity
reading — is injected. The guard denies the unsafe command and
the machine stops safe. Every run is reproducible from its seed.

## 1:38–2:00 — Explain the failure

The failure becomes evidence. The twin replays the exact trace,
and the evidence graph links the failed check back to the
requirement it violates. Cause, not vibes.

## 2:00–2:25 — Fix and verify

Change one limit in the contract, and watch behavior change on
the target: the probe that was denied is now allowed — and the
limit check fails closed, exactly as designed. Before and after,
side by side, from real campaigns.

## 2:25–2:43 — Prove independently

The evidence passport seals the run: hash-chained, replayable
without our servers. Modify one byte and replay rejects it.
Missing proof always fails closed — never silently green.

## 2:43–2:55 — The value

GENESIS RT: from machine intent to verifiable QNX behavior.
Specify, compile, run, break, prove — with evidence your whole
team can inspect.
