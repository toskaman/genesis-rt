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

## DNS-rebinding posture (audited 2026-11-05, Wave 8 §8 remainder)

Drive-by page reaching the loopback API via a rebond name is blocked
in layers (each pinned by a test):

- **Loopback bind** (`cli.py:_cmd_serve`): `127.0.0.1`, 1 worker.
  Pinned: `tests/unit/test_serve_bind.py`.
- **No CORS middleware**: a preflighted cross-origin `fetch` earns no
  `access-control-allow-origin`, so the browser blocks the write.
  Pinned: `test_preflight_earns_no_cors_allowance`.
- **Origin guard** (above): simple cross-origin writes rejected 403.
- **JSON-only writes**: an Origin-less form POST dies at body
  validation (422) before any job/op exists.
  Pinned: `test_form_post_rejected_without_execution`.
- **GET inventory** (`test_get_route_inventory_matches_audit`, 39
  routes incl. FastAPI docs): audited side-effect free. The only
  writes reachable from a GET are idempotent store init
  (`_db()`: sqlite file + additive migrations, no attacker data).
  Adding a GET route fails the test until the audit list grows.
  (Omega3 P1c re-audit, 8 Nov 2026: the five routes added since
  the Wave-8 audit — `/ipc-timeline`, `/target/ops/compare`,
  `/target/ops/compare/dossier`, `/target/ops/{op_id}/decision`,
  `/target/ops/{op_id}/dossier` — were re-checked read-only:
  op-id validated 400-first, zips built in memory, the
  timeline serves a fixed committed path with no user input.)
  (Titan v3 re-audit, 9 Nov 2026: `/changes/{change_id}` serves
  one stored `verdict.json` — id validated 400-first, resolved
  path containment-checked against the change store, no writes.)
  (Causal slice re-audit, 10 Nov 2026:
  `/causal/dossiers/{incident_id}` serves one stored `dossier.json`
  plus re-verification — id validated 400-first, containment-checked
  against the dossier store, no writes; `/causal/flagship` serves
  two fixed committed files with no user input.)
- **Host header**: deliberately NOT validated. With the five layers
  above, no browser vector reaches a state change; `Host` checking
  would only constrain already-trusted local callers.

## Residual risks / trust assumptions

- No operator authentication: any local process/user can call the API.
  Appropriate for a local dev tool; do not expose the port beyond loopback.
- JSON body depth/nesting limits rely on framework defaults for
  missing-Origin (local) callers; foreign-Origin bodies are rejected
  pre-parse by the middleware.
