# Omega3 P1a/P1d: impact readiness (pilot kit ready, humans: zero)

Date: 8 Nov 2026. Branch: `titan-omega3` (`1eb8722` P1a +
P1d docs). Status: KIT READY — methodology, timers,
analyzer, consent, and outreach drafts are implemented
and tested; **zero participants, zero invitations sent**,
`HUMAN USER BENEFIT NOT YET MEASURED` governs.

## What exists (implemented + tested)

- Protocol: `docs/business/pilot-study.md` (§2.1:
  low-friction quick tier) — paired tasks, randomized
  lane order, real timing, command counts, manual
  steps, fault-detection outcomes, evidence-verification
  time, consent, anonymization.
- Two tiers, honestly separated by the analyzer
  (`bench/productivity/analyze_pilot.py`):
  - Full 6-task study (unchanged completion threshold —
    never redefined for a better label).
  - Quick 3-task tier: `QUICK_PAIRED_PILOT` =
    (change + generate, fault campaign, evidence +
    tamper verification). QUICK can never report
    COMPLETE as a full study.
  - States: `OWNER_ONLY_EXPLORATORY`,
    quick-paired, partial, full independent,
    incomplete-paired, insufficient-sample.
- Timer: `bench/productivity/pilot_timer.py` (`--quick`
  via `build_parser`), JSONL recording, abandonment
  handling, consent enforcement, anonymized reports.
- Outreach kit (prepared, NEVER sent):
  `docs/business/pilot-outreach.md` — embedded/QNX
  engineer + verification-lead variants, community
  research, time/privacy/prerequisite terms.

## Dry-run measurements (8 Nov 2026, owner machine)

Machine-execution floor for the quick-3 core (NOT human
time): generate 0.17 s, fault campaign 0.18 s,
verify-pack 0.18 s. Human quick-pilot target ≈ 60–90
min paired total *including setup and feedback* is a
planning target, explicitly NOT yet measured with any
human (not even the owner). Full-lane duration
reconciled in P0a: no 45-minute full-pilot claim
remains anywhere.

## Evidence ladder position (see `COMMERCIAL_VISION.md` §13)

- Level 1 (author-operated): codelab ~45 min hands-on,
  re-executed 8 Nov 2026; pilot machine floor above.
- Level 2 (deterministic benchmark): 8 vs 30+10
  commands/steps, 5/5 vs 3/5 faults — tool property.
- Level 3 (new-user onboarding): UNMEASURED.
- Level 4 (independent pilots): NONE.

## Gate F verdict

Methodology consistent, timer verified, consent
enforced, analysis reproducible, owner-only vs
independent evidence separated in code and prose.
Impact evidence awaits genuine owner + independent
human sessions (owner action list, P1d commit).
