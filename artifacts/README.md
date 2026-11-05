# Artifacts

- `runs/<run-id>/passport.json` — evidence passports from local runs
  (git-ignored; reproduce with `genesis-rt demo`).
- `runs/<run-id>/generated/` — per-run codegen output (git-ignored).
- `samples/` — explicitly committed example passports. These are
  **host-simulated** records, never QNX execution evidence, and are
  labelled as such inside the file
  (`environment.qnx.environment.sdk_present=false`,
  `environment.qnx.verified_on_target=false`, `qnx_verified=false`).
