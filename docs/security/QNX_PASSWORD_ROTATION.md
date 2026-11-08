# QNX target password rotation (owner-operated)

Status: procedure published, NOT executed. The QNX 8.0 QEMU image
still uses its default credential configuration (see
`docs/audits/CAMPAIGN_OMEGA2_2026-11-08.md` env notes). Only the
owner changes it, interactively, on the owner machine.

Verified 8 Nov 2026 (Omega3 P1c, static): `probe` and
`identity` exist in `scripts/qnx_target.py` with `--ssh-port`
(default 2222, the established forward port); both read the
password from `GENESIS_TARGET_PASSWORD` first and only fall
back to `--password`. No live-target execution was performed
for this review.

## 1. Exposure

- The default password is the same on every fresh QSTI-derived
  image. Anyone with the image and the default can SSH in.
- Current mitigation: the target is reachable only via a
  localhost-forwarded port while QEMU runs; GENESIS tooling
  reads the password exclusively from the
  `GENESIS_TARGET_PASSWORD` environment variable (never
  argv, logs, or files).

## 2. Interactive change (owner, ~10 min)

1. Boot the target per `docs/quickstart-qnx8-qemu.md` §4 and
   wait for the `login:` marker.
2. SSH in as usual (`ssh qnxuser@localhost -p 2222`).
3. Run `passwd`, enter the current password, then the new one
   twice. The terminal never echoes passwords.
4. Log out. Do NOT paste the new password anywhere except the
   password prompt and step 3.

## 3. Safe credential update

- PowerShell (current session only, never in a script file):
  `$env:GENESIS_TARGET_PASSWORD = '<new-password>'`
- For persistence across reboots, store it in the OS
  credential manager and re-export it per session. Never
  commit it, never put it in `.env` files inside the repo.

## 4. Reconnection + verification

```powershell
$env:PYTHONPATH='host'
python scripts/qnx_target.py probe --ssh-port 2222
python scripts/qnx_target.py identity --ssh-port 2222
```

Expect: auth OK, `QNX qnxqemu 8.0.0 x86_64`. If `probe`
reports auth failure, the env var is stale — fix step 3,
do not retry blindly (the target penalty-boxes parallel
or rapid auth attempts; one SSH session at a time).

## 5. Failure recovery

- Locked out: stop QEMU, reboot the image, log in on the
  QEMU console (no network auth involved) and repeat §2.
- Forgotten new password: same console path. There is no
  remote reset; physical (console) access is the recovery.
- Campaign in flight: rotation invalidates nothing on disk
  (packs carry no credentials); in-flight ops fail closed
  on auth and can be re-run after step 4.

## 6. No logging of secrets

- Never `echo` the password, never pass `--password` on a
  command line, never screenshot a terminal containing it.
- `qnx_target.py` redacts auth material from transcripts;
  verify with `grep -ri password artifacts/` after any
  campaign and delete accidental captures.
