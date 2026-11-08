# qcc reproducibility experiments 1–3 (7 Nov 2026, owner's Windows box)

Companion scripts for `docs/ascension/QNX_REPRODUCIBILITY.md`. Experiment 4
(all 18 binaries) is `scripts/qnx_rebuild_check.py`.

- `exp1-same-sources-two-dirs.ps1` — same sources, two output folders:
  guard binaries identical, 0 differing bytes.
- `exp2-per-commit-worktrees.ps1` — per-commit sources in worktrees at
  different paths: run 1 = run 2 per commit, but neither matched the
  published hash (own flag order differed from the runner's `-lm`
  placement).
- `exp3-exact-recorded-command.ps1` — exact recorded qcc command from
  `qnx-build-record.json`: both commits reproduce their published
  guard hash twice.

Paths are hardcoded to the original machine (`E:\qnx800`, repo
checkout, `artifacts/runs/op-24fecbf11df8/gen`); adjust the `$repo`,
`$qcc`, `$gen`, `$root` variables to rerun elsewhere. No QNX materials
are redistributed — only the operator's own commands.
