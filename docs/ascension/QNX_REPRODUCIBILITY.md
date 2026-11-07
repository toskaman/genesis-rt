# qcc build reproducibility (7 Nov 2026)

## Question

The AFTER rerun (op-24fecbf11df8) produced guard sha256 `f92f5e66…`
while the AFTER pack has `b65afcb4…` for the same IR. Wave 2 recorded
this as "qcc builds are not byte-reproducible". Is that true?

## Experiments (owner's Windows box, QNX SDP 8.0, qcc 12.2.0 gcc_ntox86_64)

1. **Same sources, two output folders** (`repro.ps1`): guard binaries
   identical, 0 differing bytes of 14 432.
2. **Sources of each commit, two worktrees at different paths**
   (`repro2.ps1`, my own flag order): run 1 = run 2 for each commit, but
   neither matched the published hash → my command differed from the
   runner's (`-lm` placement).
3. **Exact recorded command** from `qnx-build-record.json` (`repro3.ps1`):
   `a465e7f` → `b65afcb4…` (AFTER pack) twice; `e439276` → `f92f5e66…`
   (rerun) twice. **Both match.**
4. **All binaries, all packs** with `scripts/qnx_rebuild_check.py`
   (fresh `git worktree` in a temp dir, config header regenerated from
   the pack's `ir.json`, recorded qcc command replayed):

| Pack | Commit | Result |
|---|---|---|
| `qnx8-x86_64-w11-before` | `a465e7f` | 6/6 MATCH |
| `qnx8-x86_64-w11-after` | `a465e7f` | 6/6 MATCH |
| `qnx8-x86_64-w11-after-rerun` | `5cbc458` | 6/6 MATCH |

## Conclusion

- The guard hash difference is caused by a **source change**:
  `target/qnx8/guard/genesis_guard.c` gained the IPC-timeline trace in
  commit `805ef7b`, between the AFTER pack (`a465e7f`) and the rerun.
- With this toolchain and these flags, qcc output was **bit-identical
  across checkout paths and repeated builds** for all 18 binaries tested.
- Between BEFORE and AFTER (same commit `a465e7f`, contract 1.2 → 1.6)
  exactly three binaries change — `genesis_guard`, `genesis_controller`,
  `genesis_faultinject`, the ones that compile in the generated limits —
  while `genesis_device`, `genesis_status` and `genesis_supervisor` are
  byte-identical. The contract change is visible in exactly the binaries
  that depend on it.

## Limits

One host (Windows 11), one SDP install, one qcc version. Not tested:
Linux host builds, other SDP patch levels, `-g` debug builds. Reproduce:

```sh
QNX_HOST=<sdp>/host/<os>/x86_64 python scripts/qnx_rebuild_check.py evidence/qnx8-x86_64-w11-after
```
