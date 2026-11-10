# OMEGA7 Breakthrough Strategy — The Causal Failure Engine

Date: 10 Nov 2026. Branch: `titan/omega7-causal-engine` (unmerged).
Status: vertical slice implemented, draft PR pending. No merge without
owner authorization. Video deferred by owner; Devpost not submitted.

## Decision

Five concepts were scored against directive weights (Originality 15,
User impact 15, Workflow simplification 15, Technological breakthrough
15, QNX relevance 15, Demo memorability 10, Feasibility 10,
Reliability 5; scale 0–10 per criterion). Feasibility and QNX
relevance were grounded only in inspected repo bodies; originality
only in the competitive evidence
(`docs/strategy/OMEGA7_COMPETITIVE_INTELLIGENCE.md`).

| Concept | O | I | S | T | Q | D | F | R | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (1) Causal Failure Engine | 9 | 9 | 9 | 8 | 9 | 9 | 8 | 8 | **87.0** |
| (5) Adversarial Machine Lab | 7 | 8 | 7 | 8 | 7 | 8 | 6 | 5 | 72.0 |
| (3) Verification Scientist | 7 | 6 | 6 | 8 | 7 | 5 | 6 | 6 | 65.0 |
| (4) Proof-Carrying Change | 4 | 7 | 7 | 5 | 6 | 6 | 9 | 8 | 62.5 |
| (2) Time Machine | 5 | 6 | 5 | 7 | 5 | 6 | 5 | 6 | 56.0 |

Winner: **(1) Causal Failure Engine** — incident → hypotheses →
experiments → native execution → verified fix.

Why it won: no inspected tool closes incident → reproduction →
proof ON QNX with native artifacts (QNX gives manual trace/debug,
Parasoft/LDRA/Vector give host/CI change-evidence, Sentry/Jam/
Middleware give cloud/web telemetry-to-PR, Gremlin/FIS/ChaosMesh give
K8s/cloud fault scripts). Feasibility is high because K1, faultlab,
TargetRunner, passports, and the 16/16 native matrix are all reused
without rewrites, and estop/crash/stale-binary/IPC-replay are
natively supported mechanisms.

## Falsifications (strongest reason to reject)

- Winner (1): it is orchestration glue, not a breakthrough — a
  skeptic can fairly call it Sentry-Seer-Autofix plus Gremlin fault
  steps ported to QNX. One hallucinated causal claim on stage
  collapses trust, and without a live target the demo falls back to
  archived evidence, voiding the flagship "native execution" promise.
  Mitigations: deterministic-first hypotheses (no LLM in this
  slice), no probability percentages, explicit archived/live labels,
  fail-closed verdicts.
- Runner-up (5): nondeterministic discovery cannot guarantee a live
  find in the demo window and invites comparison with mature chaos
  libraries where superiority claims are forbidden; native injector
  gaps (stale-sensor/jam PARTIAL) risk host-only discoveries.

## Scope of this cycle

Minimal end-to-end slice only: estop flagship on the cell machine,
six-hypothesis table, host repro + archived native grounding, K1 fix
leg, sealed dossier, Judge stage H. Out of scope: LLM hypothesis
authoring, live-target maiden run (owner QEMU), pilot participants,
video, Devpost filing.
