# Known limitations (jury copy)

Short version of `docs/limitations-and-safety.md` — the full text governs.

- Host fault results are **simulated**; on-target QNX replay is implemented
  and documented but awaits SDK setup. Passports always show `qnx_verified`.
- No safety certification, no formal verification, no production timing
  guarantees; QEMU numbers are regression aids only.
- Millisecond clocks are `uint32` (wrap documented, not yet wrap-safe).
- UI is an MVP passport inspector; the full workspace is roadmap.
- API is local-first with no auth; not for exposed deployment.

Anything presented as measured comes with method + raw artifacts; anything
pending is labelled pending. That distinction is the point of the project.
