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
  browser E2E is pending (current Judge tests are node/DOM-level).
- API is local-first with no auth; not for exposed deployment.
- No QNX HAM integration: the QSTI image ships no `ham` binary, so
  supervision is our own tested RESPAWN/GIVE_UP process (matrix
  steps `supervisor_respawn`/`supervisor_giveup`).

Anything presented as measured comes with method + raw artifacts; anything
pending is labelled pending. That distinction is the point of the project.
