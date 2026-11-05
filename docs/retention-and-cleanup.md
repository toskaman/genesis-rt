# Retention, bounds & cleanup (Wave 8 §7/§17 remainder)

Policy: user evidence (passports, run dirs, op records, project
revisions) is NEVER auto-deleted. Transients are bounded or removed
by the worker that created them. Growth figures measured 2026-11-05.

## Measured growth (this box)

| Item | Size | Notes |
|---|---|---|
| Full target op workdir (`op-dc74…`) | ~321 KiB | 9 binaries + transcripts + records |
| Target op record JSON | ~7 KiB | params + steps + artifacts |
| Target op events jsonl | ~4 KiB | ~2 rows/step, 200-char cap |
| Host pipeline run (`run-conv-task4`) | ~167 KiB | 6 binaries + passport |
| `runs.db` (whole history) | 1.3 MiB | jobs + events + runs tables |

100 full campaigns ≈ 35 MiB. No auto-purge exists by design.

## Enforced caps (code)

| Cap | Value | Where |
|---|---|---|
| Live jobs (queued+running) | 50, else 429 | `jobs.py:MAX_LIVE_JOBS` |
| Pool workers | 2 | `jobs.py:MAX_WORKERS` |
| Events stored / job | 1000 × 2000 chars | `jobs.py:MAX_EVENTS_PER_JOB/CHARS` |
| Tracked completion events | 200 terminal | `jobs.py:MAX_TRACKED_JOBS` |
| Job list / events read | 200 / 500 rows | `jobs.py:list_jobs/events` |
| Target campaign lock | 1 live op | `TargetRunner` + `TargetLock` |
| Target op list | 100 rows | `target.py:list_ops` |
| Step detail / reason / event | 500 / 500 / 200 chars | `target.py:_set_step/_finish/_emit` |
| QEMU stop reap | `wait(timeout=5)` | `target.py:_step_qemu_stop` |
| Project revisions | 200 | `projects.py:MAX_REVISIONS` |
| IR payload | 256 KiB | `api.py:MAX_IR_BYTES` |
| Posted passport/record text | 3 MiB | `api.py:MAX_PASSPORT_TEXT` |
| Twin frames / input events | 20000 / 100000 | `twin.py` |
| Explorer budgets | ticks 3000, scripts 5000, 300 s… | `explorer.py:MAX_*_HARD` |

## Cleanup done by workers

- Tmp IR uploads: deleted by the job worker on settle
  (`jobs.py:_work … cleanup.unlink`); submitters delete on refusal.
- QEMU: stopped by `qemu_stop` step AND bounded `_cleanup_qemu` on
  any failure path; child reaped via `wait`, never `os.kill(self)`.
- SSE streams end on terminal events/state; ~15 s heartbeat bounds
  idle connections (`api.py:job_events`).

## Operator purge (manual, explicit)

No endpoint deletes evidence. To reclaim disk, stop the server and
remove whole directories (never single files inside a run/op —
that breaks provenance):

```
# drop old host runs (keeps DB rows; re-adds nothing)
rm -rf artifacts/runs/run-<id>
# drop old target ops (record + workdir + events share the op id)
rm -rf artifacts/runs/target-ops/op-<id>*
# vacuum the job/event history (sqlite3 CLI)
sqlite3 artifacts/runs/runs.db \
  "DELETE FROM events WHERE job_id IN \
     (SELECT job_id FROM jobs WHERE state IN \
      ('succeeded','failed','cancelled','interrupted') \
      ORDER BY updated DESC LIMIT -1 OFFSET 200); \
   DELETE FROM jobs WHERE state IN \
     ('succeeded','failed','cancelled','interrupted') \
     AND job_id NOT IN (SELECT job_id FROM jobs \
      ORDER BY updated DESC LIMIT 200); VACUUM;"
```

Keeping the newest 200 terminal jobs matches `MAX_TRACKED_JOBS`
(validated on a DB copy 2026-11-05: 15 jobs kept, SQL runs clean).

Note: the `runs` table (sync facade) keeps one passport TEXT per
sync run with no timestamp column; it grows only via `POST /runs`
and is left untouched by the purge above. Truncate by explicit
`run_id` if ever needed.
