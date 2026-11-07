# Ascension baseline (7 Nov 2026)

- HEAD `400da70` (PR #9), host CI green: run 42392322226.
- Tests: 1166 collected; Windows + QNX SDK 1164 passed + 2 skipped (axe
  scans, no axe-core locally); Linux SDK-free CI 1161 passed + 5 skipped.
- UX: grouped horizontal tabs; hero + proof table repeated above every
  page; 64 rem layout; dark/light themes; axe WCAG 2.2 clean in CI.
- QNX evidence: BEFORE/AFTER packs + AFTER rerun op-24fecbf11df8, all
  16/16 on QEMU x86_64 (TCG); native CI lane build-only.
- AI: qwen2.5:7b, 28/28 published eval, 8/8 paraphrases (8 cases);
  offline planner 28/28 and 3/8.
- Commercial evidence: none measured; pilot protocol only.
- Known limitations at start: no human user data; no screen-reader
  session; TCG-only timing; "qcc not byte-reproducible" (claimed — see
  `QNX_REPRODUCIBILITY.md`, this turned out to be wrong); small AI
  datasets; scorecard showing two score sets side by side.
