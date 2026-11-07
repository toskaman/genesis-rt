# Limitations and safety (read before judging or deploying)

1. **Prototype, not a certified system.** No formal verification, no
   functional-safety qualification, no real-world robot safety claim.
2. **Simulation only.** All actuation targets are virtual. The IR requires
   `simulation_only: true`; physical outputs are out of scope by design.
3. **Host results are not QNX results.** Fault campaigns run against a host
   mirror of the guard; the C policy is proven identical by conformance
   vectors, and the on-target 16-step matrix passes on QNX 8.0/QEMU — but a
   host-only passport still never implies target verification.
   Passports always carry `qnx_verified` explicitly.
4. **QEMU timing is relative.** Emulator measurements support regression
   comparison and reproducibility, not production timing guarantees.
5. **uint32 millisecond clocks wrap** (~49.7 days) and are handled with
   RFC 1982 serial-number arithmetic in both the C guard
   (`target/qnx8/common/guard_policy.c`) and the host mirror
   (`host/genesis_rt/guard_policy.py`): sequence and deadline deltas are
   accepted iff `1 <= delta < 2^31`, so counters stay correct across the
   2^32 wraparound (`tests/unit/test_guard_policy.py::test_seq_wraparound_accepted`,
   `tests/unit/test_time_wrap.py`). Residual limits: values 2^31 apart are
   ambiguous by construction, and the wrap path is host- and
   conformance-tested only; no native vector crosses 2^32 on target yet.
6. **NaN/Inf rejected, floats otherwise trusted** within bounds; no fixed-point
   or interval arithmetic in the MVP.
7. **Supervisor recovery is bounded, not autonomous**: 3 RESPAWN attempts
   with backoff, then a loud GIVE_UP halt with no orphaned survivors.
   Fleet/HAM policy integration is documented but not automated.
8. **Security posture** is hackathon-grade: local-first, no auth, no sandbox
   beyond timeouts and argv lists. See `SECURITY.md`.
9. **v2 has no cell semantics.** `industrial_cell` stays on the v1 path:
   v2 validation and v1→v2 migration reject it loudly instead of dropping
   the `cell` block or crashing.
10. **No arm kinematics.** `robotic_arm_virtual` passes schema validation but
    the host mirror runs it on the differential-drive corridor; no
    arm-specific physics exists on host or target yet. Since Wave 10
    Sprint E, scenario records carry `physics` (+ `physics_note` when
    aliased), so the aliasing is visible in the evidence itself.

If any of these is a surprise, the submission has failed its honesty goal —
please file an issue.
