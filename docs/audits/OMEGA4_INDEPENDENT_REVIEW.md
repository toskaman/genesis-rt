# OMEGA4 independent review record

Date: 9 Nov 2026. Reviewer: separate agent (`omega4-attack`) that
implemented nothing. Target: `titan-omega4` @ `144c693`
(HEAD moved to `5de0e0b` mid-review — one docs-only file, verified
via diff; code verdicts unaffected). Base `main` @ `f93399a`.
Method: every verdict below rests on a command the reviewer ran;
raw notes in the review transcript (session artifacts).

## Verdicts per area

- Test counts: HOLDS. Canonical collect 1346 (at review time);
  43/43 consistency green; full suite exit 0, zero fail/skip
  markers on the SDK+axe box.
- AI claims: HOLDS core, WEAK reporting. Digests recomputed
  (`d91e3956`, `cb3820fd`); freeze→measured diffs results-only;
  scores/consults/residuals recomputed from raws; v8-038 scored
  FAIL with dated correction; v8 zero verbatim overlap; fix-1
  predates v8 freeze. Reporting nicks found (see fixes).
- QNX-native: HOLDS core, WEAK sub-claim. Both packs VERIFY OK
  exit 0 via both verifiers, 16/16; `target/` empty diff vs main
  AND vs pack commit `318d46b` ("(current source)" holds).
  STALE 14/16 prose-only (see fixes).
- README + Devpost: WEAK — one real error (Devpost 52/52 vs 60
  collected; no pin test covered it). README first screen holds.
- Pilot/human: HOLDS. NOT YET MEASURED pinned by tests; zero
  invitations; bench REPORT is machine-time counts with explicit
  no-savings scope; no fake records.
- Security: WEAK — residuals disclosed but open: floor
  `cryptography>=49` unmet on the evidence box (43.0.3), lock
  pinned 43.0.3, no pin test, "CI scans enforced" overstated
  (no secret-scanner CI job). No committed secrets, no SDK
  binaries, UNSIGNED exit-2 verified.
- Accessibility: HOLDS. No conformance claim; axe 3/3 verified;
  screen-reader explicitly NOT YET EXECUTED.
- Bonus: HOLDS. Codelab in-period from `a2bde91`, re-executed,
  6/6 anti-rot green incl. Linux CI; QNX API mapping genuine
  (`name_attach`, `MsgSend/MsgReceive/MsgReply`,
  `resmgr_attach`, `CLOCK_MONOTONIC`, `TimerTimeout`).

## Findings fixed (each with a test or artifact)

1. Devpost "Planning unit tests 52/52" → 60/60, plus NEW pin test
   `test_devpost_planning_count_matches_collected` (was RED,
   now green). Submission-facing error closed.
2. AI-report FR clash: report now defines `false_rejects`
   (true rejects only), explains the valid-column gap, and names
   the 4 wrong-kind parcel-coinage→conveyor model accepts
   (v8-007/010/012/014; llama gets v8-010 right). Artifact: the
   report text, checkable against raw rows.
3. "No v7 string in code/tests" corrected: v7 case IDs appear in
   9 code comments (failure-class citations) — disclosed; the
   convergent guard phrasing was reworded ("commission a
   conveyor for the test cell"). v7 never rerun (scoring
   unaffected).
4. Crypto floor: `requirements.lock` bumped 43.0.3 → 50.0.2
   (abi3 wheels verified for CI cp312-manylinux and owner
   cp314-win via `pip download`); NEW pin test
   `test_requirements_lock_meets_crypto_floor` (was RED, now
   green); Devpost "CI scans enforced" softened to the truth
   (redaction/no-leak tests run; no dedicated scanner job).
   Local box still 43.0.3 — owner upgrade command in
   `OMEGA4_OWNER_ACTIONS.md`; CI proof pending merge checks.
5. STALE 14/16 scoped to prose-grade in README, Devpost draft,
   and CLAIMS ("operator-recorded, no sealed transcript ships;
   sealing is future work"). Scorecard gained its Omega4 row
   (was stale at v6).

Cosmetic: lock header "1293-test suite" → 1348. Devpost v6
"ZERO times" now carries the latency-inferred hedge.

## Scores

Independent reviewer: **28/40** (Implementation 9, Design 7,
Impact 5, Innovation/AI 7). Self-assessment after fixes:
**31/40** (9.5/8/5/8.5) — see `docs/jury/JUDGE_SCORECARD.md`.
Neither is an official judging prediction.
