# GENESIS RT — Local security model (Wave 8 §6)

Local-first developer tool. Loopback is the trust boundary; localhost is
NOT assumed secure against the browser (drive-by sites) or malicious inputs.

## Enforced controls (verified in code + tests)

- **Origin guard** (`api.py:_origin_guard`): every POST/PUT/PATCH/DELETE with
  a non-loopback `Origin` is rejected 403. Loopback = `localhost`,
  `127.0.0.1`, `::1` (`_loopback_origin`). Negative tests:
  `test_origin_guard_rejects_foreign_writes`,
  `test_cross_origin_project_write_rejected`,
  `test_cross_origin_project_put_rejected`.
- **ID validation**: run/job ids (`_valid_run_id`) and project ids
  (`valid_project_id`) rejected 400 when malformed, before any I/O.
- **Path containment**: example files must resolve under `examples/`;
  job artifact dirs must resolve under `ARTIFACTS` (`_job_gen_dir`);
  unknown ids → 404, escapes → 409. No raw filesystem paths accepted.
- **Payload bounds**: scenario count capped (`MAX_SCENARIOS`), scenario ids
  allowlisted (`SCENARIO_IDS`), posted passport text capped at 3 MiB
  (`MAX_PASSPORT_TEXT`), graph inputs size-capped (`GraphTooLarge`).
- **Job lifecycle**: cancel is idempotent; terminal states are sticky; a
  cancelled/failed/crashed/interrupted job never carries a success verdict.
- **SSE**: streaming requires an existing job id (404 otherwise); resume via
  `Last-Event-ID` only replays that job's ordered rows; heartbeats bound
  idle connections.

## Target-operation rules (required for the §5 Target Runner)

- Frontend never submits shell commands; every native op maps to the
  server-side allowlist in `target.py` with per-op param schemas.
- No shell interpolation; guest writes confined to `/tmp/genesis`;
  bounded time/output/concurrency per step; single campaign lock.
- QNX credentials live in server-side config, never reach Studio JS.

## Residual risks / not verified in this pass

- `Host`-header validation and DNS-rebinding posture unaudited here.
- No operator authentication: any local process/user can call the API.
  Appropriate for a local dev tool; do not expose the port beyond loopback.
- JSON body depth/nesting limits rely on framework defaults.
