# Red-team round 2 — Wave 10 Sprint E3 (§18)

Date: 2026-11-05. Follows `RED_TEAM_ROUND1.md` (cross-operation passport
substitution, fixed). Five new attacks; three found real holes (fixed,
regression tests preserved), two confirmed existing defenses (pinned).

Method: each attack was written as a failing test FIRST, executed to
prove the hole, then fixed. Pre-fix failures were observed, not assumed.

## A1 — Provenance-version games (RESISTED, pinned)

Unknown `provenance_version` (99, missing, 0) on target/perf records:
already refused fail-closed (`provenance.validate_*_binding` early
return). A v1 downgrade is self-defeating: v1 records carry no build
set, so `check_build_set` caps them below the behavior tier anyway.
Pinned by `test_future_target_provenance_version_refused` and
`test_future_perf_provenance_version_capped`.

## A2 — Cross-target perf splice (FOUND + FIXED)

Hole: `validate_perf_binding` checked the perf record's build set,
staged binaries and identity *individually*, but never compared the
perf target block against the matrix run's. A bench from target Y
stapled to a matrix from target X earned `QNX_PERFORMANCE_MEASURED`.
Fix: `provenance.py` now refuses when the two target blocks differ.
Proven pre-fix by `test_cross_target_perf_splice_capped` (failed),
green post-fix. Severity: medium — same build set required, but
latency numbers from a faster machine could masquerade.

## A3 — Reused operation ID (FOUND + FIXED)

Hole: `TargetRunner.start()` generated `op-{uuid12}` with no
existence check — a collision (or a restored backup directory)
silently overwrote a finished operation's record and event log.
Fix: retry up to 8 candidates, refuse if none is fresh. Caller-chosen
IDs were never possible (server-generated); the jobs layer already
guards explicit `run_id` with `JobConflict`. Proven pre-fix by
`test_start_retries_on_op_id_collision` (failed), green post-fix.

## A4 — Unsupported requirement→evidence edges (FOUND + FIXED)

Hole: `evidence_graph.build_graph` emitted `verified_by` from every
requirement to its named scenario *unconditionally* — including
scenarios that never ran (dangling edge) or failed. Node status said
`unverified`/`failed` while the edge predicate claimed `verified_by`.
Fix: emit the edge only when the scenario status is `pass`, matching
the existing check-level convention (`verified_by if passed else
failed_by`). Proven pre-fix by `test_unrun_requirement_has_no_…
_verified_by_edge` and `test_failed_requirement_has_no_…
_verified_by_edge` (both failed), green post-fix, including a new
no-dangling-edges assertion on IR-attached graphs.

## A5 — Clock handling (RESISTED, pinned + one test correction)

`check_window` already refuses reversed, unparsable, timezone-naive,
zero-duration and far-future windows; perf windows are checked too.
Pinned at gate level by `test_incoherent_perf_window_capped` and
`test_ambiguous_target_window_refused`. During pinning, one new test
wrongly asserted `release_eligible is False` for a perf-only defect —
corrected: the top tier is optional for release by design
(`gate.RELEASE_MIN_LEVEL == QNX_BEHAVIOR_VERIFIED`, documented in
`gate.py`), and the cap + reason are the correct response.

## Trust-model notes (unchanged)

- Timestamps are operator-asserted; there is no trusted clock or
  timestamp authority, so clock checks catch accidents, not a
  malicious operator with a valid key to the store.
- No hardware attestation anywhere in this chain; "QNX verified"
  means bound target-observed records, not measured boot.
- Residuals from round 1 stand: point-in-time swap after verify,
  unsealed op-record files, no 2^32 wrap native vector.
