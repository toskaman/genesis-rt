# Omega2 audit 5/7: codelab + developer experience (P1c)

Date: 8 Nov 2026. Branch: `omega2` @ `33d361c`. Status: CLOSED.

## Fixes (every added command executed on this box)

- README: exact determinism compare (header-only `cmp` — the
  `.mk` embeds `GENESIS_SRC` relative to `--out` by design);
  step-6 PowerShell block; `PYTHONPATH` rule documented
  (`genesis_rt.cli` needs it, `scripts/*.py` self-insert);
  PS cleanup; executed-against `b5a278f`.
- EXTERNAL-BUILD: hand-runner `export PYTHONPATH=host`
  (the harness presets it, hands did not — steps 2–3 failed
  in Git `sh`); single-session note; step-1 PS run line;
  step-5 PS variant (6/6 MATCH, zero qcc warnings);
  Windows qcc troubleshooting; `sdk-manifest.json` cleanup.
- ADVANCED: literal default password replaced with a
  placeholder; Lab-5 PS variant; git-bash setup note.
- Verified live: steps 1–4 + 6 outputs match the doc
  byte-for-byte (incl. codegen shas, 8/8 faults, 14-record
  passport, step-3 STALE exit 2); codelab tests 6/6.

## Competitive tags

Repo topics: developer-tools, embedded-systems, evidence,
qnx, qnx8, real-time, robotics, verification + qemu (added
Omega2). No invented demo URL; homepage unset (honest).

## Count sync

Codelab cites 16-step matrix + 9 staged files (both current
per the Omega2 campaign) and no test totals. Suite total
unchanged at 1293 collected by P1c (docs-only).

## Not done

Lab 6 target transcript stays the 2026-11-05 live run
(re-running target labs adds no new information; the
acceptance checklist marks Labs 5–6 manual). No
third-party reader review was available.
