# Known limitations (jury copy)

Short version of `docs/limitations-and-safety.md` — the full text governs.

- Host fault results are **simulated**; the C policy is proven identical
  by conformance vectors, and the on-target 13-step matrix (9/9 IPC checks,
  live telemetry, supervision, guarded device chain) passes on QNX 8.0/QEMU. Passports always
  show `qnx_verified` explicitly.
- No safety certification, no formal verification, no production timing
  guarantees; QEMU numbers are regression aids only.
- Millisecond clocks are `uint32` (wrap documented, not yet wrap-safe).
- UI is static pages (`dashboard.html`, `studio.html`): artifact
  inspection + trace replay, no live pipeline execution from the page.
- API is local-first with no auth; not for exposed deployment.
- No QNX HAM integration: the QSTI image ships no `ham` binary, so
  supervision is our own tested RESPAWN/GIVE_UP process (matrix
  steps `supervisor_respawn`/`supervisor_giveup`).

Anything presented as measured comes with method + raw artifacts; anything
pending is labelled pending. That distinction is the point of the project.
