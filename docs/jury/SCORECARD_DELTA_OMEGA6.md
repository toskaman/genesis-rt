# Scorecard delta, OMEGA6 product-proof (INTERNAL DRAFT — not a claim)

Date: 9 Nov 2026, branch `titan/omega6-product-proof` (unmerged).
Baseline: self 31/40 (9.5/8/5/8.5), independent 29/40,
hostile INTERNAL 26.5/40. This draft re-scores the SELF
column only, with evidence per cell. Nothing here is filed,
published, or shown to judges; the binding constraints
(pilots, video, second-host, cold-read, SR session) are all
still owner-open, so independent/hostile equivalents almost
certainly hold at 29/26.5.

| criterion | was (self) | now (self) | evidence / cap |
|---|---|---|---|
| Tech 9.5 | 9.5 | 9.5 (HOLD) | + traversal fix (was exploitable), SSE bound, A1 fix, C footprint, pip-audit CI. No new native evidence (still QEMU-only, single host) → no upward move. |
| Design 8 | 8 | 8.5 (+0.5) | + B2 acceptance DEMONSTRATED (9 browser tests: real Prove click, states, 320/390/1366, keyboard, zoom 200/400, ran-where labels) + K1 landing hero + hero/cold-start copy on all front doors. Capped: no SR session, no cold-read proof, no video. |
| Impact 5 | 5 | 5 (HOLD) | E3 persona/buyer/win-loss prose is positioning, not evidence. Zero pilots, zero buyer conversations → no move. Binding. |
| AI 8.5 | 8.5 | 8.5 (HOLD) | No planner/validator change (forbidden this branch); v10 rule pinned as process. 5 unsafe/112 still open on frozen v9 → no move. |

INTERNAL total: **31.5/40** (self-equivalent). The +0.5 sits
entirely in Design and dies if the SR session or cold-read
contradicts it. Do not quote this number anywhere juried.
