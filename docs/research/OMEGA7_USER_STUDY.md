# OMEGA7 User Study — Causal Dossier Protocol

Status: protocol ready, `HUMAN USER BENEFIT NOT YET MEASURED`.
Zero participants, zero invitations sent (owner-only outreach).

## Protocol (paired, counterbalanced)

Task: given the flagship estop incident file, (1) name the most
likely cause, (2) reproduce it, (3) verify a fix, (4) hand a
second engineer something independently checkable.

- Lane A (baseline): repo + docs + today's CLI (`demo`,
  `compare`, `verify-change`), no causal commands.
- Lane B (causal): `causal-repro` + `causal-fix` + dossier.
- Order counterbalanced; onboarding separated from task time;
  think-aloud optional with consent.

## Measures

Primary: time to correct independently-verified verdict;
correctness of named cause; missed-fault rate; second-engineer
verification time. Secondary: commands run, tools touched,
clarification requests, confidence (1–5), willingness to adopt.

## Validity rules

Real consented participants only; paired data required (both
lanes per participant); abandoned tasks recorded, never dropped;
raw records append-only; small samples reported with explicit
non-generalization limits. No agent may recruit, contact, or
fabricate participants.

## Handoff

Recruitment kit: one-paragraph invite + consent + 5-minute
onboarding + incident file + recording procedure + anonymization
rules — to be sent by the owner only. Results template lives in
`docs/benchmarks/OMEGA7_WORKFLOW_COMPARISON.md` (human section).
