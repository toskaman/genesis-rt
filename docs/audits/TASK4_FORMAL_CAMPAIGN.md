# Task 4 — Formal native QNX campaign record (Wave 8 §8)

Date: 2026-11-05. Code: `c3c6e4b` (tree clean, CI success on the
seal/replay parent `4dcbe3f`). Runner: TargetRunner via Studio API
(Task 3 Step 6 doubles as this campaign). Suite at campaign time:
826/826 green (589 unit + 237 rest).

## Environment (pinned)

- Host: Windows, QNX SDP `E:/qnx800`, qcc 12.2.0
  (`gcc_ntox86_64` default), zero build warnings.
- QEMU: `E:\VMs\qemu\qemu-system-x86_64.exe`, 11.1.0
  (v11.1.0-12130-ge470268ff4).
- Image: `E:\qnx800\images\qemu\qemu` (ifs.bin + disk-qemu),
  accel=tcg, cpu=max, ssh_port=2222, wait=300.
- Target: `QNX qnxqemu 8.0.0 2026/06/05 x86pc x86_64`.
- WHPX still broken on this host (needs reboot); campaign ran on TCG.
- Target password via `GENESIS_TARGET_PASSWORD` env (never in params).

## Source pipelines (fresh, this box)

| run_id | IR | verdict | level |
|---|---|---|---|
| run-conv-task4 | examples/conveyor-demo/machine-ir.json (conveyor v1) | PASS | QNX_COMPILED |
| run-amrv2-task4 | examples/amr-demo/machine-ir-v2.json (diff-drive v2) | PASS | QNX_COMPILED |
| run-cell-task4 | examples/cell-demo/cell-ir.json (industrial_cell v1) | PASS | QNX_COMPILED |

Command each: `run_pipeline(<ir>, "artifacts/runs", run_id=<id>)`.

## Build set (fresh)

```
python scripts/build_set.py create \
  -o artifacts/runs/task4-formal/build-set-task4.json \
  --entry genesis_guard_conv=genesis_guard:artifacts/runs/run-conv-task4/passport.json \
  --entry genesis_guard_v2=genesis_guard:artifacts/runs/run-amrv2-task4/passport.json \
  --entry genesis_cellcheck=genesis_cellcheck:artifacts/runs/run-cell-task4/passport.json
```

Entries chain-verify their source passport at creation. Origins:
conv (conveyor v1), v2 (differential_drive_robot v2), cell
(industrial_cell v1). sha256: `b22aaf9730c1d299…`.

Secondary binaries copied byte-identical to
`artifacts/runs/task4-formal/` under their staged names.

## Formal op: op-dc74546f8fa2

```
POST /target/ops {"workflow": "full", "params": {
  "ir": <examples/amr-demo/machine-ir.json>,
  "image_dir": "E:\\qnx800\\images\\qemu\\qemu",
  "accel": "tcg", "cpu": "max", "wait": 300,
  "extra_src": [<3 secondaries>],
  "build_set": <build-set-task4.json>}}
```

Result: COMPLETED 13/13 in ~197 s, `reason: all steps done`.

- normalize → generate → build → stage → execute → verify →
  measure → seal → replay (full 13-step workflow; per-step
  detail lost — see repair note below)

## Repair note (2026-11-05, Wave 10 Sprint D)

This record was committed truncated: commit `bfa549e` ends
mid-list with a pasted model-output truncation marker
(2744 chars dropped). The per-step breakdown after
`- normalize` never reached git and is unrecoverable —
it is NOT reconstructed here.

Salvaged result summary (from `docs/PROGRESS.md`, same campaign):

- Formal op `op-dc74546f8fa2`: 13/13 COMPLETED.
- Fresh qcc 12.2.0 build, hermetic staging of 9 binaries
  (6 primary + 3 attributed secondaries).
- 16/16 verification matrix PASS on QNX 8.0.0 (TCG).
- 1000-sample perf bound, verdict PASS, replay PASS.
- Level `QNX_PERFORMANCE_MEASURED`, `release_eligible: true`.
- Negative tamper control refused.
- Honest gap: no explicit 2^32 wrap vector on target.

Status: HISTORICAL. Wave 8 evidence is superseded by the fresh
Wave 10 campaign (see `docs/audits/WAVE10_BASELINE.md`); this
file is kept for provenance, not cited as current proof.