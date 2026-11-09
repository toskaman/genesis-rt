# Supply-chain triage (pip-audit, non-blocking)

CI runs `pip-audit -r requirements.lock` on every push/PR
(`host-ci.yml`, `continue-on-error`: findings never block the
build — they land here as dated triage notes instead).

## 2026-11-09 — pytest 7.4.0 / PYSEC-2026-1845 (OMEGA6 D5)

- Finding: `pytest through 9.0.2 on UNIX relies on directories
  with the /tmp/pytest-of-{user} name pattern, which allows
  local users to cause a denial of service or possibly gain
  privileges.` Fix version: 9.0.3. (`pip-audit -r
  requirements.lock --desc`, 2 rows, same ID.)
- Exposure: test-only dependency; no shipped code path imports
  pytest. CI runners are ephemeral single-tenant GitHub-hosted
  VMs; the owner box is a single-user Windows machine
  (the advisory is UNIX-/tmp-specific).
- Decision: ACCEPT until post-filing. Bumping the lock 7.4.0 →
  9.0.3 days before the 15 Dec filing risks plugin churn
  (pytest-asyncio and friends) for a threat outside our
  deployment shape. Revisit with the next intentional lock
  refresh (re-run the suite; never float silently).
- Residual: same class as the 43.0.3 global-interpreter note
  in `OMEGA5_OWNER_ACTIONS.md` — tracked, not hidden.
