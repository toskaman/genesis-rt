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

## How to produce the first real data (owner, ~2 × 45 min)

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
