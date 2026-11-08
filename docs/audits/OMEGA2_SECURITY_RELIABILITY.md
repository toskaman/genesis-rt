# Omega2 audit 6/7: security + reliability posture

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c`. Status:
ASSESSED — no new holes opened; known residual items listed.

## Held in Omega2

- Secrets: target password exclusively via
  `GENESIS_TARGET_PASSWORD` env, never argv/log; the literal
  default password was removed from codelab docs
  (placeholder instead).
- No secrets, SDK materials, or binaries committed: packs
  carry transcripts + manifests; the QNX SDP and images stay
  outside the repo (`E:\qnx800`, `E:\VMs\qemu`).
- Campaign lock closes the concurrent-run interleaving hole
  (§3.1); stale locks fail closed (`TargetBusy`).
- Single-SSH-at-a-time discipline kept throughout (the
  target penalty-boxes concurrent sessions).
- Fail-closed defaults kept: release eligibility, verify rc,
  evidence gating (external adapter has no gate import —
  pinned by test).

## Audited but NOT fixed (residual)

- M1–M5 / M9–M11 and H4–H7 race conditions: reviewed during
  the Titan/Omega2 audits; fixes deferred as
  disproportionate to judging/product value before the
  deadline. No fix was attempted, so no regression risk was
  introduced either.
- QNX image still uses the DEFAULT password (`qnxuser`);
  recommend the owner change it (guest banner says so too).
- Native CI remains build-only (`.github/workflows/qnx.yml`
  carries NOT EXECUTED / BUILD-ONLY markers, pinned by
  test); no self-hosted runner was configured (licensing +
  secret-exfiltration risk).
- No production hardening claim: localhost API has no auth
  boundary review; dependency CVEs not re-scanned in
  Omega2; soak coverage is Wave-10/11 era.

## Verdict

Safe to merge and demo. Not production-certified; the
limitations above are the honest boundary.
