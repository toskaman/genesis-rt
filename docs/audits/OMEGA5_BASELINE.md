# OMEGA5 baseline (Wave 0, 9 Nov 2026)

Base: `main` @ `eacab88` (PR #13 merged, OMEGA4). Verified via fetch:
no advance beyond the directive's SHA. Branch `titan-omega5` from
`origin/main`. Tree clean. No `target/` changes pending.

## Carried-over verified state (OMEGA4, unchanged)

- Host suite: 1348 collected / 1348 passed / 0 skipped (SDK+axe box).
- Planning 60/60; consistency 45/45; E2E 32/32; axe 3/3; adversarial 24.
- v7 `d91e3956…` (120): offline 83, qwen 82 (20 consults), llama 79 (20).
- v8 `cb3820fd…` (100): offline 82, qwen 90 (25), llama 92 (25).
- 4 v8 unsafe accepts (1 dispute + 3 subclasses); parcel-coinage
  wrong-kind bias (qwen 4, llama 3); v8-025 negation FP.
- Scorecard: self 31/40, independent 28/40. Impact 5/10 (no humans).

## Newly noted at Wave 0

- Ollama daemon NOT running (`ollama list` connection refused on
  127.0.0.1:11434). Models were present in OMEGA4; daemon must be
  started before v9 measurement. No new downloads planned.
- Local `cryptography` still 43.0.3 (global interpreter; owner
  upgrade to lock's 50.0.2 pending). CI installs the lock.
- QNX image default password rotation still pending (owner).
- Packs UNSIGNED; QNX CI BUILD-ONLY; QEMU-only evidence.
- Video DEFERRED_BY_OWNER; Devpost PENDING_FINAL_VIDEO; no
  pilot data; no release/tag.

## OMEGA5 work order (frozen by the directive)

1. Consult-audit script + OMEGA4 addendum + harness enforcement.
2. Prospective contract v1.3 (BEFORE v9 authoring).
3. Blind v9 (contract + schema prose only — NO format example),
   freeze + pin BEFORE any planner change.
4. Planner implementation (frames, negation, Förderband,
   kind-evidence boundary), red-then-green, fresh phrasings.
5. v9 once per provider. Docs, attack, scorecard, PR→CI→merge.
