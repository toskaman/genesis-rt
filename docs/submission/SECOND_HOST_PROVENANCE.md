# Second-host provenance record (B-17)

Status: TEMPLATE — unfilled. Native provenance is currently
author-machine only: one build host, cross-SDP reproducibility
unverified. This file is the procedure + record the owner fills
when a second machine reproduces the packs. Do NOT register a
self-hosted CI runner casually (licensed SDK + untrusted PR code
= exfiltration risk); a dated owner-executed note is the
pre-deadline mitigation.

## Procedure (owner, on the second host)

1. Install QNX SDP 8.0 (note the exact installer/version below)
   and clone the repo at the same commit as the packs'
   `manifest.json` (`commit` field).
2. Re-verify both Omega2 packs offline (no SDK needed for this
   step — proves the sealed bytes, not the toolchain):
   `python evidence/qnx8-x86_64-omega2-before/verify.py` and
   `python evidence/qnx8-x86_64-omega2-after/verify.py`.
   Expect `VERIFY OK` on both.
3. Re-run the bit-for-bit rebuild check (needs the SDK):
   `python scripts/qnx_rebuild_check.py
   evidence/qnx8-x86_64-omega2-before` and the same for
   `-after`. Expect exit 0 (every binary digest matches).
4. Fill the record below, commit it with the date.

## Record (fill on the second host)

- Date:
- Host A fingerprint (original build host): hostname / OS /
  `qcc -V` output / SDP install path:
- Host B fingerprint (this reproduction): hostname / OS /
  `qcc -V` output / SDP install path:
- Repo commit reproduced:
- `verify.py` BEFORE result (paste the VERIFY line):
- `verify.py` AFTER result (paste the VERIFY line):
- `qnx_rebuild_check.py` BEFORE exit code:
- `qnx_rebuild_check.py` AFTER exit code:
- Pack hashes match Host A (yes/no + sha256 of each pack's
  `manifest.json` on both hosts):
- Operator signature (name + date):

Until this record is filled, every native claim reduces to
"trust the author's machine plus a hash" — stated here so no
reader has to discover it.
