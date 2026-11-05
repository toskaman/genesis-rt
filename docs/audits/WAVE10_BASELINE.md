# Wave 10 baseline (2026-11-05, HEAD 37acc81, CI success)

Fresh re-verification: **856/856 host tests green, 0 skips**
(602 unit + 254 rest), SDK-less CI 851 + 5 skips. Tree clean.
No open PRs inspected (direct-to-main flow this session).
Prior waves complete: Target Runner + seal/replay, formal
campaign op-dc74 (MEASURED), §8 audit, retention, Judge Mode,
bench + pilot kit, red-team round 1, advanced codelab +
harness, competitive dossier.

Per-change table (§6 format: state → deficiency → impact →
risk → competition value → verification → priority).

## F1 — Portable native evidence (Sprint A, P0)

- State: op-dc74 records exist only in git-ignored
  `artifacts/runs/`; committed samples are host-only
  (`artifacts/README.md` says so explicitly).
- Deficiency (confirmed): a judge cloning the repo cannot
  obtain raw native QNX evidence. Major reproducibility gap.
- User impact: judges must trust transcripts quoted in docs.
- Risk: low (curation + redaction review, no product change).
- Competition: very high — turns "trust us" into "verify
  yourself" for Technology + Impact.
- Verify: clean-room replay on SDK-less machine (CI job or
  documented manual run) + tampered-bundle rejection test.
- Priority: P0 first.

## F2 — Final video (Sprint C, P0)

- State: Studio-first storyboard only
  (`docs/demo-video-plan.md`); compliance matrix marks
  YouTube pending.
- Deficiency (confirmed): no recording, narration, subtitles,
  or edit project exist.
- User impact: submission-incomplete without it.
- Risk: medium (capture tooling on Windows, voice track
  authorization, editing time).
- Competition: decisive — the video IS the first impression.
- Verify: shot-to-evidence mapping, < 3:00, subtitle file
  present; publication itself stays an owner handoff.
- Priority: P0, after evidence pack + dossier exist to film.

## F3 — Judge Mode browser E2E (Sprint B, P0)

- State: Judge tab + 5 node-harness tests (render/nav only,
  mocked DOM).
- Deficiency (confirmed): no real-browser journey test.
- User impact: wiring regressions (the `judgeRunJob` path)
  escape CI.
- Risk: medium (Playwright availability on this box + CI
  ubuntu; flaky timing).
- Competition: high — proves the flagship flow is real.
- Verify: Playwright journey (job run → passport → release
  banner) green locally; CI-gated if the runner supports it.
- Priority: P0.

## F4 — Jury doc contradictions (Sprint A, P0)

- State: scorecard/limitations say "no guided Judge Mode"
  (stale — tab shipped); A/B twin comparison claim needs a
  code check; sample passports host-only (true until F1).
- Deficiency (confirmed): contradictions a judge will spot.
- User impact: credibility loss at reading time.
- Risk: low (audit + extend docs-consistency guard).
- Competition: high — cheap to fix, costly to leave.
- Verify: guard tests + manual read-through.
- Priority: P0, with F1 (evidence-pack claims interact).

## F5 — Synthetic commercial evidence (Sprint D, P1)

- State: reproducible bench (synthetic ref, honestly
  labeled) + pilot kit, zero pilots conducted.
- Deficiency (confirmed): no real-team measurements.
- User impact: Impact score capped at plausible-but-unproven.
- Risk: high to fix properly (needs external teams + time);
  low to improve honestly (fairer reference, invitation
  package ready).
- Competition: medium — honesty here beats invented numbers.
- Verify: pilot invitation handoff prepared; no fabricated
  participants (guarded by review, not code).
- Priority: P1.

## F6 — Evidence dossier export (Sprint B, P0)

- State: passports + records exist; no one-click dossier.
- Deficiency (confirmed): review package is manual assembly.
- User impact: engineering-lead review flow missing.
- Risk: medium (HTML escaping, size caps, path safety —
  all standard, testable).
- Competition: high — the "take it to your boss" artifact.
- Verify: export E2E test (build → verify contents → no
  hidden failures), red-team filename/escape tests.
- Priority: P0.

## F7 — Real AI provider (Sprint E, P1 optional)

- State: offline keyword planner, 28/28 eval, honestly
  labeled everywhere.
- Deficiency: none confirmed — optional uplift only.
- User impact: nil if skipped (no promise made).
- Risk: high (credentials, cost, hallucination eval).
- Competition: low-medium — only if genuinely useful.
- Verify: 28-case + unseen eval, safety boundaries tested.
- Priority: P1 optional, last. Do not block on it.

## F8 — Second industrial scenario (Sprint E, P1)

- State: AMR/conveyor cell flagship (+conv/v2/cell IRs as
  build-set secondaries, not standalone stories).
- Deficiency: none confirmed — breadth is a choice.
- User impact: extensibility story weaker with one hero.
- Risk: high (full test + native + passport per scenario).
- Competition: medium — depth beats breadth for judges.
- Verify: same bar as flagship (IR→passport→counterexample).
- Priority: P1, only if flagship quality stays intact.

## F9 — Competitive matrix substantiation (Sprint D, P1)

- State: `COMPETITIVE_LANDSCAPE.md` labels assessments, but
  learning-curve/integration-burden cells read quantitative.
- Deficiency (confirmed on re-read): unmeasured comparisons
  presented in matrix form.
- User impact: a skeptical judge discounts the whole table.
- Risk: low (reword + source-grade labels).
- Competition: medium — fairness is persuasive.
- Verify: each cell carries evidence grade
  (vendor-doc / assessment / hypothesis); guard test pins
  the grading vocabulary.
- Priority: P1.

## Sprint order (from §27, confirmed)

A (F1 pack → F4 docs → CI) → B (F6 dossier → F3 E2E →
before/after + release explanation) → C (F2 video) →
D (F5/F9) → E (F7/F8 if viable) → F (gates + report).
