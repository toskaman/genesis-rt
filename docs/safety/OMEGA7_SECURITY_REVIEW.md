# OMEGA7 Security Review — Causal Slice

Date: 10 Nov 2026. Scope: incident.py, causal.py, causal_run.py,
causal CLI/API, Judge stage H, flagship endpoint. No planner,
target C, or auth changes in this cycle.

## Threat model & dispositions

- Prompt/log injection → execution: intake vocabulary is
  allowlisted (`OBSERVED_KINDS`); ranking is substring matching
  with no eval/exec; experiments come only from the bounded
  hypothesis table (fixed scenario ids); the LLM is not consulted
  anywhere in this slice. No natural-language string ever reaches
  a shell, however indirectly.
- Path traversal (incident IR, dossier ids, API payloads):
  incident/machine paths resolve against repo root only when
  relative; absolute paths allowed for CLI operators (local tool
  posture, unchanged). Dossier GET/fix validate ids
  (`valid_incident_id`) and resolve inside the dossiers base with
  the same parent-guard as `/changes/{id}` (tested: 404 unknown,
  400 on escape-shaped ids via validation).
- Arbitrary native commands: live grounding runs only the fixed
  `verify-only` workflow with caller params validated by
  `TargetRunner`; no incident content flows into op params.
- Payload bombs: API IR/incident payloads capped at
  `MAX_IR_BYTES` (256 KiB), mirroring `/changes`.
- Secret leakage: passports/dossiers never embed credentials;
  temp uploads are dropped after use (finally blocks).
- Evidence substitution: seal + incident digest + before-IR hash
  + per-passport chain re-verification; `verify_fix` refuses
  tampered dossiers before spending K1 legs.
- Target races: one live op at a time via the existing target
  lock; `TargetBusy` surfaces as honest `start-failed` grounding.
  Timeout path cancels the op (fake-runner pinned).
- UI injection: Judge H render escapes every dossier value
  (`esc()`), mirroring stage G; seal truncated for display only.
- DoS via long runs: live poll is time-bounded (default 900 s);
  host repro inherits pipeline admission/cancel semantics.

## Residuals (unchanged from baseline)

Local API stays single-user loopback without auth (disclosed
tool posture); packs/dossiers UNSIGNED; QEMU target password
rotation remains owner-only; live causal path unexecuted here.
No new network listeners, no new permissions, no dependency added.
