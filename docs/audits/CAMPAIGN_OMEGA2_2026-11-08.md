# Omega2 native campaign — 8 Nov 2026 (afternoon, UTC+1)

Fourth native evidence round: BEFORE/AFTER/STALE on current `omega2` source,
driving the v2 machine end to end for the first time.

## Environment

- Host: Windows 11, QNX SDP 8.0.0 (`E:\qnx800`), qcc 12.2.0 `gcc_ntox86_64`.
- QEMU 11.1.0 (`E:\VMs\qemu`), `--boot disk --accel tcg --cpu max -m 4G -smp 4`.
- Target: `QNX qnxqemu 8.0.0 x86_64`, user `qnxuser`.
- Auth note: the image still uses its DEFAULT password (`qnxuser`); the
  owner's recalled candidates were never set on this disk. The morning
  "candidate #1" was the default all along. Recommend changing it
  (the guest banner says so too); all access stayed via
  `GENESIS_TARGET_PASSWORD` env, never argv/log.
- Code: `omega2` @ `318d46b` (P0c/P0d + estop-timeline + v2-matrix fixes).

## Ops (all via TargetRunner; QEMU owned per-op, 2222 sequential)

| Op | IR | Result |
|---|---|---|
| `op-820b5e4b69ad` build-only | amr v1 | PASS (passport for v1 guard) |
| `op-8ac1391676d6` build-only | amr v2 | PASS (passport for v2 guard; rebuilt after the generate-dispatch fix) |
| `op-8c770693e16f` build-only | conv v1 | PASS (passport for conv guard) |
| `op-ca0ca1d8edd6` build-only | cell v1 | PASS (passport for cellcheck) |
| `op-d91bd4133590` full BEFORE | amr v1 | COMPLETED, sealed PASS, **qnx_verified=True**, replay matches |
| `op-6840da0e9f69` full AFTER | amr v2 | COMPLETED, sealed PASS, **qnx_verified=True**, replay matches |
| `op-f178fd5a1b64` build-only (v2, poisoned) | amr v2 | PASS but built with v1 codegen (generate bug); passport DISCARDED, never used |
| `op-3ece2561cd61`, `op-3a2b01c6ae88`, `op-287a41d33712` full AFTER attempts | amr v2 | FAILED/CAPPED during diagnosis (binding refusal, v1-centric matrix, alias rule); superseded by `op-6840da0e9f69` |

## Matrix / perf / sched (BEFORE2 + AFTER4, current source)

- 16/16 matrix PASS in both ops, incl. the stricter P0d proofs:
  respawn REBIND chain (`PRE/REBIND/POST/SETTLED`) and the estop
  SIGUSR1 reset wire (v1: motion ALLOW; v2: declared safe_stop→init
  transition then motion ALLOW).
- Direct-CLI parity runs (same binaries): 16/16 unattested, 16/16
  IR-attested (BEFORE IR), perf 1000/1000
  (p50 249.5µs, p95 404.2µs, p99 509.7µs, max 878.0µs),
  sched 4×200/200 recorded (p50 231–256µs across configs — no
  separation claimed; consistent with the withdrawn speedup claim).
- qcc rebuild of all four machines: 0 warnings.

## STALE negative control (direct CLI)

v1-primary staging verified against the v2 IR + v1 build-set:
14/16, FAILs exactly on `estop_target` (v1 cannot take the v2
declared reset edge) and `v2_transitions` (DIFF_BIN where the v2
binding requires SAME_BIN). `limits_differ` passes on both revisions
because the v1→v2 change is governance (guarded transitions), not
limits (1.2/1.0 mps both) — stale is caught behaviorally, as designed.

## Bugs found natively and fixed (all red-then-green + native proof)

1. Op generate always ran v1 codegen (v2 guards built without the
   machine module). Fixed: schema dispatch in `_step_generate`.
2. `verify --ir` used the v1 loader only (v2 refused as unknown
   keys). Fixed: version-aware binding + `schema_version` in binding.
3. `probe state` hardcoded seq=1 (STALE_SEQ on a live guard). Fixed:
   optional `[seq]` argv.
4. estop/v2transitions matrix v1-centric. Fixed: sequenced state
   probe in RESET, V1BIN fallback, bound-aware parsers.
5. buildset refused the legitimate v2 alias (same IR + identical
   bytes) as reused provenance. Fixed: byte-equality alias
   exception; same-IR/different-bytes still refused.

## Packs

- `evidence/qnx8-x86_64-omega2-before` (34 files, op-d91bd4133590).
- `evidence/qnx8-x86_64-omega2-after` (36 files, op-6840da0e9f69).
- Both `verify-pack --trust local`: UNSIGNED exit 2, hash-only —
  same status as the W11 packs (no signer infrastructure in repo).
- Host suite at this commit (measured, this box, SDK present):
  **1286 passed + 2 skipped of 1288**, zero failures.
