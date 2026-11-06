# Wave 11 extended soak — 100 jobs (2026-11-06)

One-shot measurement, NOT in the default suite (the suite keeps the
24-job tripwire in `tests/unit/test_soak.py`). Method: one warmup job,
then 100 mixed jobs (nominal / fail-fast invalid IR) through the real
`JobManager` + pipeline on this box. Driver: `/tmp/soak100.py`
(scratch, not committed).

| metric | warmup | after 100 jobs |
| ------ | ------ | -------------- |
| states | — | 90 succeeded, 10 failed (invalid IR, by design) |
| wall time | — | 108.1 s |
| threads | 2 | 2 (no leak) |
| Python heap growth (tracemalloc) | — | +202 KiB (< 8 MiB tripwire) |
| runs.db (+wal/shm) | 57 KiB | 2.9 MiB (~30 KiB/job) |
| artifact files | — | 920 |

DB and artifact growth is linear in job count because passports are
retained per job by design (same as Wave 10: +18 KiB heap, 1.1 MiB DB
for 25 jobs). No unbounded growth observed beyond that linear term.

Covered elsewhere in Phase D (committed tests):

- `tests/integration/test_sse_storm.py` — 50 sequential + 5
  concurrent SSE reconnects replay the full ordered history; worker
  thread count unchanged, total threads bounded.
- `tests/unit/test_store_pressure.py` — unusable artifact store fails
  the job honestly with the cause attached; a healthy manager keeps
  serving (contained stand-in for disk pressure; no destructive fill
  of real volumes was run).

Not covered (honest gaps): no 24-hour wall-clock run, no full-disk
fill, no API restart mid-SSE (restart recovery is unit-tested at the
`JobManager` level only), no multi-day retention aging.
