# Pilot consent & confidentiality (GENESIS RT)

Status: template, no pilot conducted yet. The operator's employer
decides; this page is the starting point, not legal advice.

## What the participant agrees to

1. Two half-days (~90–120 min per lane) running the six tasks in
   `pilot-study.md` §2, once per lane, in randomized order.
2. Filling the measurement templates (§§3–4) and the survey (§5)
   honestly, including interruptions and tooling that misled them.
3. A 30-minute debrief call (notes shared back for correction).

## Confidentiality (both directions)

- All runs are local on the participant's machines. No source
  code, binaries, SDK material, images, or credentials are
  shared — ever. The anonymization protocol (`pilot-study.md`
  §6) is applied before anything leaves the team.
- GENESIS RT side receives only: anonymized templates, survey
  answers, benchmark REPORT.json files, and passport JSON files.
- Published results use team codes (T1, T2, …), never names,
  employers, or product details. Raw (non-anonymized) material
  is never published and never requested.
- Either side may stop the pilot at any time; already-shared
  anonymized data may be retained for the study unless the
  participant asks for deletion before publication.

## No Lock-in, no payment

Participation is unpaid and creates no obligation to adopt,
buy, or endorse anything. GENESIS RT stays Apache-2.0; the
participant keeps everything they produced.

## Sign-off

```
team code:        T_
operator:         <initials>   date: <UTC>
reviewer:         <initials>   date: <UTC>
genesis contact:  <initials>   date: <UTC>
lane order drawn: genesis-first | reference-first
notes:            <setup: host-only | SDP+QEMU, target id>
```
