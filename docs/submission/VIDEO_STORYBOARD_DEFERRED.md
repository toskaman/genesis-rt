# Final video storyboard (DEFERRED — owner produces the cut)

> `VIDEO_STATUS = DEFERRED_BY_OWNER`. Nothing here is
> rendered, recorded, or published. The owner records the
> real product per this shot list, keeps the cut STRICTLY
> under 3:00 (target 2:45 + 15 s buffer), uploads it
> public to YouTube, and pastes the link into the Devpost
> form. No third-party music, footage, or images anywhere
> (all visuals are the owner's terminal + Studio + QEMU
> console). All produced cuts were WITHDRAWN 2026-11-10
> for an owner remake; no video file is shipped and no
> cut is the submission video.

## Compliance checklist (official rules, re-verified 8 Nov 2026)

- [ ] Duration < 3:00 (judges need not watch beyond).
- [ ] Shows the project running on the intended device:
      QEMU/QNX 8.0 target terminal visible (boot marker,
      `identity` output, native matrix transcript).
- [ ] Public on YouTube; link on the Devpost form.
- [ ] English narration or English captions throughout.
- [ ] No copyrighted third-party material.
- [ ] Functionality shown matches the repo state
      (record AFTER the Omega3 merge; state the commit
      SHA in the description).

## Timed narrative (2:45 total)

| # | Time | Beat | Visual (genuine runs only) |
|---|------|------|----------------------------|
| 1 | 0:00–0:20 | The problem | Studio overview + voiceover: "a requirement changed — prove the target matches." No typing yet. |
| 2 | 0:20–0:40 | Machine requirement | AMR v2 contract excerpt on screen; highlight the guarded safe-stop lines. |
| 3 | 0:40–1:00 | Deterministic compile | Terminal: `PYTHONPATH=host python scripts/run_verified_demo.py` (or generate step); show byte-identical digest line. |
| 4 | 1:00–1:25 | Actual QNX execution | QEMU console + terminal: `python scripts/qnx_target.py probe --ssh-port 2222`, `identity --ssh-port 2222` (`QNX qnxqemu 8.0.0 x86_64`), then the native matrix transcript excerpt (16/16). Final 5 s: `cat /dev/genesis/status` (resource-manager telemetry) + the `pidin` process list with the supervisor visible — the named QNX primitives on screen (B2 surface). |
| 5 | 1:25–1:45 | Fault campaign | Studio Fault Lab or terminal fault tail: injected faults caught, oracle verdicts ALLOW/DENY/SAFE_STOP. |
| 6 | 1:45–2:05 | BEFORE/AFTER | Studio Compare Workspace side-by-side: v1 vs v2 contract diff + behavior delta; voiceover states both 16/16 under their own contract. |
| 7 | 2:05–2:20 | Evidence passport | Terminal: `python evidence/qnx8-x86_64-omega2-after/verify.py evidence/qnx8-x86_64-omega2-after` → VERIFY OK; passport excerpt; state hash-only UNSIGNED honestly in one line. |
| 8 | 2:20–2:35 | Stale-binary rejection | Show the stale control result: v2 contract + v1 binary → 14/16 FAIL on `estop_target` + `v2_transitions`. One line: "the wrong binary cannot pass." |
| 9 | 2:35–2:45 | Value proposition | Studio release-decision panel: FAIL-CLOSED verdict; closing line: "change-verification and evidence for QNX — replayable by anyone." Title card with repo URL. |

## Exact commands used on camera

All commands exist on the current tree (verified 8 Nov
2026 against `scripts/qnx_target.py` subparsers):

```powershell
$env:PYTHONPATH='host'
python scripts/run_verified_demo.py
python scripts/qnx_target.py probe --ssh-port 2222
python scripts/qnx_target.py identity --ssh-port 2222
python evidence/qnx8-x86_64-omega2-after/verify.py `
  evidence/qnx8-x86_64-omega2-after
python -m genesis_rt.cli serve   # Studio http://127.0.0.1:8077/
```

QEMU must already be booted per
`docs/quickstart-qnx8-qemu.md` §4 before recording
(boot time is NOT part of the 2:45). If the target is
unavailable on recording day: show the sealed
transcripts + `verify.py` replay instead, and say so on
camera — never fake a live run.

## Recording notes

- 1080p, terminal font ≥ 18 pt, dark theme; hide
  personal paths/tabs; never type or display the QNX
  password (env var is already exported off-camera).
- Narration script = the "Beat" column expanded to one
  sentence per shot; total ≈ 380 words at 140 wpm.
- Description box: repo URL, commit SHA, pack paths,
  "Recorded <date> on QNX SDP 8.0 / QEMU x86_64".
