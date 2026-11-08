# Impact study status (7 Nov 2026)

## `HUMAN USER BENEFIT NOT YET MEASURED`

No external participant has used GENESIS RT in a timed session. No
interviews have been held. Nothing in this repository claims a
productivity gain for people.

## What exists

| Asset | Status |
|---|---|
| Protocol, tasks, templates (`docs/business/pilot-study.md`) | published |
| Consent form, interview guide, decision-maker survey | published |
| `bench/productivity/analyze_pilot.py` | fail-closed aggregator; medians only; reports `comparative_claims: "insufficient"` under 2 teams |
| `bench/productivity/pilot_timer.py` (new) | interactive session timer: clock-measured durations, operator answers, appends analyzable JSON lines; tested |
| Machine benchmark (`bench/productivity/REPORT.json`) | command/step counts for scripted lanes — a property of the tool, not of users |

## How to produce the first real data (owner, ~2 × 60–90 min)

> Correction 8 Nov 2026 (Omega3 §4.5): this section previously
> said "~2 × 45 min", contradicting the protocol's 90–120
> min/lane. A timed expert dry run of the genesis lane (8 Nov
> 2026, operator knows the repo; machine time ≈ 6 s/lane,
> negligible) floors at ~40 min/lane excluding the reviewer
> loop (T1 5, T2 4, T3 5, T4 12, T5 8, T6 6 min: run, read,
> judge, record). Real participants add onboarding, learning
> and the reviewer checklist (~10–15 min), hence the
> protocol's 90–120 min/lane stands. The owner should budget
> 60–90 min/lane, not 45.

```sh
# lane 1: the way you would do it without GENESIS RT
python bench/productivity/pilot_timer.py --team OWNER --lane reference --out bench/productivity/data/owner.jsonl
# lane 2: with GENESIS RT (do the lanes in random order)
python bench/productivity/pilot_timer.py --team OWNER --lane genesis --out bench/productivity/data/owner.jsonl
python bench/productivity/analyze_pilot.py bench/productivity/data/owner.jsonl
```

Owner-operated results must be labelled "owner-operated, biased, n=1" and
can never be presented as independent validation. Two or three external
engineers (with consent, `docs/business/pilot-consent.md`) are needed
before any comparative claim.

## Effect on the impact score

Without human data, Potential Impact cannot reach a substantiated 10/10
under the Ascension rubric. This is the largest remaining gap.
