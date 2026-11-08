# Omega2 audit 2/7: evidence trust (H9/M6/H8 + packs)

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c`. Status: CLOSED.

## H9: verify exit code is fatal on explicit-but-broken input

`verify --ir/--build-set` with an absent file soft-capped the
result instead of failing. Now: absent optional input caps,
explicit-but-broken input is fatal (nonzero rc). Real-op
dossiers re-checked: 17 → 0 suspect hits, chain still verifies.

## M6: release defaults closed

A passport without a release field was readable as eligible.
Now: absent field = closed. All 6 shipped packs carry the
field; the `None`-flag fixture (auto/None) pins the default.

## H8: home paths redacted to ~ in display copies

Real-op dossiers leaked the operator's home path in 17 hits
(`target-op.json`). `_normalize_paths` rewrites home → `~` in
display copies only; sealed bytes are untouched and the chain
still verifies.

## Fourth evidence round (§5)

BEFORE (`op-d91bd4133590`) and AFTER (`op-6840da0e9f69`)
on current source, both COMPLETED, sealed PASS,
qnx_verified=True, replay matches. First end-to-end drive of
the v2 machine. STALE negative control 14/16, failing exactly
on `estop_target` + `v2_transitions` as designed. Packs:
`evidence/qnx8-x86_64-omega2-before` (34 files) and
`-after` (36 files); `verify-pack --trust local`:
UNSIGNED exit 2, hash-only parity with the W11 packs (W11 —
no signer infrastructure in repo, honestly labeled).

## Natively found bugs (all red-then-green + native proof)

v1-only codegen dispatch, v1-only `verify --ir` binding,
hardcoded `probe state` seq=1, v1-centric estop/v2transitions
matrix, build-set alias refusal on identical bytes. Full
record: `CAMPAIGN_OMEGA2_2026-11-08.md`.

## Verdict

Trust boundaries hold: fail-closed release, fatal verify,
redacted display, hash-only packs labeled as such. No
cryptographic attestation is claimed.
