# Pilot outreach kit (Omega3 §6.5, 8 Nov 2026)

Status: DRAFTS ONLY — zero invitations sent. The owner sends
these, or nobody does.

Both variants offer the quick tier (§2.1 of `pilot-study.md`,
~60–90 min total) with the full six-task study as an option.
Consent (`pilot-consent.md`), anonymization (§6) and the
no-source-code rule apply to both.

## Variant A — embedded / QNX engineer

> Subject: 60–90 min pilot — evidence-driven QNX verification
> workflow (open-source, local-only)
>
> Hi — I'm trialling GENESIS RT (Apache-2.0), a tool that
> turns a machine requirement into QNX C code, runs a fault
> campaign on QNX 8.0 (QEMU ok, host-only ok), and seals the
> result into an independently verifiable evidence package.
>
> Ask: ~60–90 min of your time for three paired tasks —
> (1) change a requirement and regenerate the build files,
> (2) run an 8-scenario fault campaign, (3) hand a reviewer
> a package that proves the verdict (incl. tamper detection)
> — once with your current practice, once with GENESIS RT
> (randomized order). Host-only is fine; nothing leaves your
> machines except anonymized timings + a 5-min survey.
>
> You keep: the tool, your evidence dossiers, the benchmark
> scripts. I ask for: anonymized task rows + survey answers
> (protocol: `docs/business/pilot-study.md` §§2–6, 10).
> Interested? Reply with "host-only" or your SDP/QEMU setup
> and two candidate slots.

## Variant B — engineering manager / verification lead

> Subject: pilot your change-verification workflow (60–90 min,
> no install on your infra required)
>
> We're validating whether an evidence-driven workflow cuts
> the review cost of QNX control-software changes: one
> engineer changes a requirement, regenerates the software,
> runs a fault campaign, and produces a package a second
> engineer can verify without asking questions.
>
> Ask: lend one engineer for 60–90 min (quick tier) or two
> half-days (full six-task study). Local-only, Apache-2.0,
> no source code or SDK material shared, anonymized results.
> Deliverable back to you: the filled measurement templates,
> the evidence dossiers, and a summary of where review time
> went in each lane.
>
> Protocol: `docs/business/pilot-study.md`. Consent and
> anonymization guaranteed in writing before we start.

## Target communities (research, not contacted)

| Community | Why relevant | What they get |
|---|---|---|
| QNX community forums / QNX Everywhere | QNX 8.0 developers; the project's natural users | Free tooling + codelab; early pilot results |
| Embedded Rust/C++ meetups (local, Paris/EU) | Verification pain is universal in embedded | Talk/demo slot; benchmark data |
| University robotics/controls labs | Real QNX curricula; students are willing timed subjects | Open-source teaching material |
| Indie robotics / ROS 2 builders | Safety-review burden without enterprise tooling | Lightweight evidence workflow |

Rules: no spam, no cross-posting, no vote/adoption promises;
one maintainer-approved post per community max; disclose
hackathon context; link the protocol, never a tracking URL.
