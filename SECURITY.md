# Security policy

## Scope

GENESIS RT is a hackathon prototype. It is **simulation-only**: no component
commands physical actuators, and nothing in this repository is qualified for
production control of machinery.

## Boundaries we enforce

- The browser/UI and any AI planner output are **never on the actuation path**:
  they produce untrusted proposals that must pass strict schema validation.
- The QNX-side guard (`target/qnx8`) applies fail-closed policy independent of
  host and simulator: unknown/malformed/stale/out-of-range input is denied.
- Host orchestrator: safe subprocess argv lists (no shell interpolation),
  fixed timeouts, output caps, one local pipeline at a time, SQLite WAL.
- No arbitrary code execution from the public API: only validated IR documents.

## Reporting

For the hackathon period, please open a GitHub issue with `[security]` in the
title. Do not include secrets, credentials or private infrastructure details.

## What we will not accept

- Real-motor drivers or removal of `simulation_only`.
- Network-exposed actuation endpoints.
- Committed secrets, SDK binaries, or proprietary headers (see `.gitignore`).
