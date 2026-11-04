# Limitations and safety (read before judging or deploying)

1. **Prototype, not a certified system.** No formal verification, no
   functional-safety qualification, no real-world robot safety claim.
2. **Simulation only.** All actuation targets are virtual. The IR requires
   `simulation_only: true`; physical outputs are out of scope by design.
3. **Host results are not QNX results.** Fault campaigns run against a host
   mirror of the guard; the C policy is proven identical by conformance
   vectors, and the on-target 8-step matrix passes on QNX 8.0/QEMU — but a
   host-only passport still never implies target verification.
   Passports always carry `qnx_verified` explicitly.
4. **QEMU timing is relative.** Emulator measurements support regression
   comparison and reproducibility, not production timing guarantees.
5. **uint32 millisecond clocks wrap** (~49.7 days). Long-running deployments
   need wrap-safe arithmetic; the MVP documents the boundary instead.
6. **NaN/Inf rejected, floats otherwise trusted** within bounds; no fixed-point
   or interval arithmetic in the MVP.
7. **Supervisor recovery is bounded, not autonomous**: 3 RESPAWN attempts
   with backoff, then a loud GIVE_UP halt with no orphaned survivors.
   Fleet/HAM policy integration is documented but not automated.
8. **Security posture** is hackathon-grade: local-first, no auth, no sandbox
   beyond timeouts and argv lists. See `SECURITY.md`.

If any of these is a surprise, the submission has failed its honesty goal —
please file an issue.
