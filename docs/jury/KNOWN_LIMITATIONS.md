# Known limitations (jury copy)

Short version of `docs/limitations-and-safety.md` — the full text governs.

- Host fault results are **simulated**; the C policy is proven identical
  by conformance vectors, and the on-target 16-step matrix (9/9 IPC checks,
  live telemetry, supervision, guarded device chain, crash containment x3) passes on QNX 8.0/QEMU. Passports always
  show `qnx_verified` explicitly.
- No safety certification, no formal verification, no production timing
  guarantees; QEMU numbers are regression aids only.
- Millisecond clocks are `uint32` with RFC 1982 serial arithmetic for
  seq and deadlines (§16, C/Python conformance-tested): correct across
  the ~49.7-day wrap. Pairs 2^31+ ms apart are ambiguous by
  construction and read as "deadline in the future" — unreachable
  for near-term deadlines, but a 64-bit clock would remove the caveat.
- Studio Live (`studio.html` + local API) runs host pipelines and
  native target ops from the page (SSE progress, cancel, evidence
  inspection, Target tab with phase checklist, guided 7-stage Judge
  Mode tab with real run/inspect actions, synchronized A/B twin
  replay of two passports on one time cursor). There is no
  multi-user/team workflow — single local operator. Judge Mode
  real-browser E2E runs in CI (headless Chromium + live backend, 2
  real jobs); the CI path covers host only, no QEMU.
- API is local-first with no auth; not for exposed deployment.
- No QNX HAM integration: the QSTI image ships no `ham` binary, so
  supervision is our own tested RESPAWN/GIVE_UP process (matrix
  steps `supervisor_respawn`/`supervisor_giveup`).
- AI planner: blind v9 (160 cases, no format example) measured
  5 reject→IR accepts / 112 (4 safety-semantic + 1 fleet-count,
  all deterministic-layer) with 34/36 consults + 14 explained
  consultation mismatches per model; wrong-kind 0. Previous
  blind v8 (qualified provenance: limited prior-set
  format-preview exposure): 4 unsafe / 100. Post-fix v4/v5
  36/36 is regression-only; v7/v8/v9 are never rerun on
  changed code. Trigger (v10 rule): any planner or
  deterministic-layer change requires a separately-authored,
  frozen-before-fix blind set (v10) before any improved
  number may be claimed. No general AI-safety claim.
- Evidence packs are hash-only (UNSIGNED): SHA-256 integrity +
  offline replay, not signer authentication or attestation.
- Accessibility: automated axe scans in CI only; full
  screen-reader verification is outstanding, not claimed.
- Human benefit is not yet measured: zero pilots, zero
  invitations sent; no productivity claim exists.

Anything presented as measured comes with method + raw artifacts; anything
pending is labelled pending. That distinction is the point of the project.
