# GENESIS RT — Wave 8 baseline (Wave 0 audit, 2026-11-05)

Short factual source-of-truth. Prior reference: `docs/baseline-2026-11-05.md` (758-test baseline).

## Repository state

- HEAD == `origin/main` == `24e0171` (Wave 7 M4 §15). Nothing newer to fetch.
- Remote CI: `host-ci success` @ 24e0171 (2026-11-05 06:48 UTC, confirmed via `gh`).
- Uncommitted WIP at audit start: `scripts/qnx_target.py` (+339: TargetLock,
  staging manifest, `stop` QEMU) + `tests/unit/test_qemu_stop.py` (9) +
  `tests/unit/test_target_isolation.py` (17). Tested and kept (see below).

## Test baseline (local, this Windows host)

- Full suite: **784/784 green** (758 baseline + 26 WIP), 0 failures, 0 skips,
  0 orphans — run in bounded micro-runs (`python -u`, one statement, log file).
- Environment: QNX SDP 8.0 present (qnx 6/6 incl. native qcc build, 0 skips),
  node present (ui 37/37), gcc present (C behavior 26/26).
- CI-equivalent steps: verified demo `PASS` (host, 1.36 s) + anchored replay
  `gate: PASS (qnx_verified=False)` + C policy compile clean (gcc for CI's `cc`).

## Crash incident (resolved during audit)

- Symptom: every run touching `tests/unit/test_qemu_stop.py` or
  `test_target_isolation.py` killed the shell+pytest tree (exit 1, 0 bytes
  even with `-u`, deterministic).
- Root cause (bisected to single calls): `os.kill()` on the process's OWN pid
  is treated as hostile by the sandboxed Windows runner and kills the tree.
  Signaling a child or bogus pid, and `tasklist`, are fine.
- Second bug (probe): `os.kill(pid, 0)` reports Windows zombies as alive
  (open handle) → `_wait_pid_gone` would burn 20+10 s and fail.
- Fix (`scripts/qnx_target.py`, `tests/unit/test_qemu_stop.py`): never signal
  where observation suffices — `_pid_is_qemu` drops the kill-0 probe,
  `TargetLock._pid_alive` reuses `_pid_is_gone`, `_wait_pid_gone` uses
  tasklist (Windows) / `/proc` zombie-state (POSIX, kill-0 only without
  procfs). Durable rule: **never `os.kill()` a pid that may be self**
  (critical for the §5 in-process Target Runner).

## Gaps verified firsthand (§4 file inspection)

| Prompt § | Finding |
|---|---|
| §6 P0 | `PUT /projects/{pid}` exists (`api.py:643`, the only PUT, no PATCH) and is **not** covered by the Origin guard (POST/DELETE only, `api.py:187`). |
| §7 P0 | `JobManager.submit` has **no admission bound**: every submit inserts a DB row + unbounded `ThreadPoolExecutor` queue; only completion-Event tracking is capped (`_evict_done_locked`). |
| §5 P0 | No Studio Target Runner: `studio.html` shows raw `qnx_target.py boot/put/verify` CLI hints only; no target state machine, no op API. |
| §9 P1 | No Judge Mode in Studio. |
| §8 P0 | Prior 16/16 native matrix predates wrap-safe clock changes; fresh campaign required before claiming reverification. |

## Docs state (spot-checked)

- `docs/PROGRESS.md` current through Wave 7 M4. `docs/demo-video-plan.md`
  still terminal-centric (rewrite required, §14). Devpost draft + scorecard
  predate Wave 8 features (refresh in Phase E).
