# Omega2 audit 1/7: P0 native correctness (§3–§4)

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c` (fixes landed
P0a–P0d, before `318d46b`). Status: CLOSED — all four items
fixed, tested, and proven on the live target.

## §3.1 Campaign concurrency → TargetLock + atomic staging

Concurrent `qnx_target.py` invocations could interleave SSH/SFTP
operations against one target (single-session penalty box) and
race staged binaries. Fix: a filesystem lock
(`scripts/qnx_target.py`, `TargetLock`) serializes target
commands; `probe` splits nonce/auth from state queries;
uploads stage atomically with a read-back manifest; a stale
lock yields `TargetBusy`, never silent interleaving. Tests:
21/21 lock tests incl. race (`≥1 won + ≥1 busy`) and
unlink-mock cases.

## §3.2 Device handshake → supervisor-passed pid + set-restart

The supervisor respawned children without proving the new
process was the one it tracked. Fix: the supervisor passes the
child pid explicitly and the handshake requires the
`PRE/REBIND/POST/SETTLED` chain plus `set-restart` before the
respawn counts. Proven natively in the BEFORE/AFTER campaign
(see `CAMPAIGN_OMEGA2_2026-11-08.md`): respawn REBIND chain
observed in both ops.

## §3.3 Supervisor reset_armed + faultinject rc + 2³¹−1 vector

`reset_armed` handling hardened in the supervisor; faultinject
now exits fatal-rc on failures (no silent pass); a 2³¹−1
wraparound vector added to the guard conformance set (RFC 1982
boundary). All red-then-green with focused suites green
(guard + conformance + qemu_argv + consistency: 98/98).

## §4 Sched contradiction → claim withdrawn

The 5 Nov RT-priority speedup did not replicate on 8 Nov
(p50 231–256µs across configs, no separation). The ~45%/~65%
generalization was withdrawn from all three current-facing
docs (`WHY_QNX.md`, `TECHNICAL_EVIDENCE.md`,
`perf-baseline.md`); the inconclusive reading is pinned by
`test_sched_speedup_claim_withdrawn`. QEMU timing stays a
regression aid, never real-time evidence.

## Verdict

No known P0 native-correctness defect remains. Residual risks
(M1–M5/M9–M11, H4–H7 races) were audited but intentionally not
fixed in Omega2; see audit 6/7.
