# OMEGA7 B-13: STALE-seal blocked — owner handoff

Date: 2026-11-10. Branch: `titan/omega7-v10-stale-arm` (pushed
`549eab6..7cb64d7`). Scout verdict was FEASIBLE; Phase A (host-only
sealing code) is implemented, tested, and pushed. Phase B (fresh QEMU
re-execution) is blocked on exactly one owner-only input.

## The missing piece

`GENESIS_TARGET_PASSWORD` is **unset** in the executing session
(probed, value never printed). Steps `put` + `verify` SSH into the
QNX guest as `qnxuser`; without the password no fresh matrix can be
captured, and backdating a passport for the 8-Nov operator-recorded
transcript would be fabrication — so no sealed pack was produced.

Nothing else is missing: SDK (qcc 12.2.0, gcc_ntox86_64 default),
QEMU 11.1.0, QSTI image, v2 IR, build-sets, stage binaries, and the
new `stale-control` workflow are all present and verified (see below).

## What is already done (pushed, no PR, no merge)

- `f4862ef` — `stale-control` runner workflow + sealed FAIL
  (`host/genesis_rt/target.py`, `evidence.append_record`) + 35 tests.
- `14310a2` — control pack builder + `verify.py` stale coverage
  (`scripts/build_evidence_pack.py`, `scripts/verify_evidence_pack.py`).
- `d28fb68` — Studio workflow option (`ui/studio.html`).
- `7cb64d7` — count sync: 1525 collected (1519+6 SDK-free), facts + 7 docs.
- Verified: full suite green both lanes (SDK 1525 exit 0; SDK-free
  1519+6 exit 0), ruff gate clean, Omega2 BEFORE/AFTER packs still
  VERIFY OK (16/16), read-only preflight
  `python scripts/qnx_env_check.py` → `sdk_present: true`,
  `qemu.present: true`.
- Resolved scout open item: bind `--build-set
  artifacts/campaign-omega2/build-set.json` (byte-identical,
  sha-prefix `b487eea82b98a7c5`, to the 8-Nov stale record's embedded
  build_set; `build-set-after.json` carries an extra `genesis_guard_v1`
  entry and is the wrong binding).
- Untouched as required: `evals/*`, `target/` (0 commits since
  `318d46b` — no C changes, no re-campaign needed), frozen pack bytes.

## Owner handoff commands (exclusive target time ~15 min, single instance)

From `genesis-rt/` on branch `titan/omega7-v10-stale-arm`, PowerShell:

```powershell
$env:GENESIS_TARGET_PASSWORD = '...'   # owner-supplied, never committed
# 0. preflight (read-only): expect sdk_present=true + qemu.present=true
python scripts/qnx_env_check.py
# 1. rebuild current sources per docs/quickstart-qnx8-qemu.md §3 (all four
#    machines); expect 0 warnings and sha256 == stale-manifest.json pins
# 2. run the stale control through the new sealing path (polls to terminal)
$env:PYTHONPATH = 'host'
python -c "import json,time,sys
from genesis_rt.target import TargetRunner
from genesis_rt.ir_v2 import load_ir_v2_file
ir = load_ir_v2_file('examples/amr-demo/machine-ir-v2.json')
bins = ['genesis_cellcheck','genesis_controller','genesis_device','genesis_faultinject','genesis_guard','genesis_guard_conv','genesis_guard_v2','genesis_status','genesis_supervisor']
src = ['artifacts/campaign-omega2/stage/'+b for b in bins]
r = TargetRunner('artifacts/runs/target-ops')
rec = r.start('stale-control', params={'ir': ir, 'image_dir': 'E:/qnx800/images/qemu/qemu', 'build_set': 'artifacts/campaign-omega2/build-set.json', 'src': src, 'expect_refusal': ['estop_target','v2_transitions']})
op = rec['op_id']; print('op:', op)
import time as t
while True:
    cur = r.get(op)
    if cur['state'] in ('COMPLETED','FAILED','CANCELLED','BLOCKED','INTERRUPTED'): print(cur['state'], cur['reason']); break
    t.sleep(10)
"
# expect: COMPLETED, sealed control refusal ['estop_target', 'v2_transitions'] (14/16, gate FAIL as designed)
# any other shape FAILEDs by design — diagnose before sealing, never force
# 3. build the control pack + offline verify (host-only, seconds)
python scripts/build_evidence_pack.py --op <op-id> --out evidence/qnx8-x86_64-stale-control
python evidence/qnx8-x86_64-stale-control/verify.py evidence/qnx8-x86_64-stale-control
# expect: VERIFY OK + refusal=['estop_target', 'v2_transitions'] matching EXPECTED_RESULTS.md
# 4. close the docs loop (B-13 verify clause): update the STALE wording in
#    docs/CLAIMS.md:50-54 (+ mirrored DevPost/demo-story lines) from
#    "prose-grade, no sealed transcript" to the sealed pack path, and mark
#    B-13 done in docs/audits/titanv3/backlog.md; commit + push (no PR)
```

Risks (from the scout): SSH `PerSourcePenalties` bans on rapid
retries (run serially); single instance only (`/tmp/genesis` wipe
races); TCG timing variance (seal matrix + refusal only, never timing).

## Return state

`complete=true`, `unresolved=["GENESIS_TARGET_PASSWORD (owner-only) +
exclusive ~15 min target run per the handoff above; sealed pack +
docs-pin updates pending that run"]`. No fabrication performed: no
sealed transcript exists yet, and no doc claims a sealed pack.
