# Codelab: stale-binary detection for your own QNX build (15 min)

> Authored during the hackathon entry period. Follows the bonus-prize shape
> (task on/for QNX 8.0); usable with or without the GENESIS entry itself.
> Every command below was executed on 2026-11-08 (Windows 11; the
> same host blocks run on Linux CI with every push); host blocks are enforced by
> `tests/integration/test_codelab_external.py`, SDK blocks run only
> with a QNX SDP installed.
>
> Companion to [`README.md`](README.md) (the 45-minute native IPC
> controller lab) and [`ADVANCED-QNX.md`](ADVANCED-QNX.md) (guard
> internals, provenance, replay).

## Goal

In ~15 minutes you will: compile a real binary from this repo's QNX C
sources, fingerprint the build directory into a manifest, verify it is
unchanged, then flip one byte and watch the checker name the stale
binary. No GENESIS rewrite of your project, no Machine IR — this is
the one GENESIS capability that drops onto an existing build.

## Prerequisites

- This repo cloned; Python ≥3.12; a host C compiler (`cc`/`gcc`).
- For step 5 only: QNX SDP 8.0 with `qcc` on PATH
  (`source ~/qnx800/qnxsdp-env.sh`). Steps 1–4 need no SDK.
- Shells: Linux/macOS use `sh`; Windows uses PowerShell or Git `sh`.
  Run host commands from the repo root, in ONE session per shell:
  the `PYTHONPATH`/`CODELAB_TMP` exports below do not survive a
  new terminal.
- The `sh` steps below use `$CODELAB_TMP` as a scratch directory (the
  test harness provides it, with `PYTHONPATH` preset). Running by
  hand? Export both first:
  `export CODELAB_TMP=/tmp/codelab-ext PYTHONPATH=host &&
  mkdir -p $CODELAB_TMP` (Linux/macOS/Git `sh`). The PowerShell
  blocks use `$env:TEMP` directly and set `$env:PYTHONPATH='host'`
  inline in step 2 (it persists for later steps in the same
  session).

## Step 1 — Build one real binary (3 min, no SDK)

Compile the shipped guard-policy conformance binary — the same C file
that runs on the QNX target in the main codelab:

```sh-harness
CC_BIN=$(command -v cc || command -v gcc)
$CC_BIN -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common \
  -o $CODELAB_TMP/guard_vector target/qnx8/common/guard_policy.c \
  target/qnx8/host_tests/guard_vector.c
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 5.0 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q 'DENY SPEED_OVER_LIMIT 1'
```

```powershell
gcc -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common `
  -o $env:TEMP/guard_vector target/qnx8/common/guard_policy.c target/qnx8/host_tests/guard_vector.c
'LIMITS 1.2 1.0 100', '47454E31 1 1 1 0 50 5.0 0.0 1 0 1 0 1' | & $env:TEMP/guard_vector.exe
# expect: DENY SPEED_OVER_LIMIT 1
```

This is your "existing project's build output": one directory, one
binary. Everything below treats it as opaque bytes.

## Step 2 — Fingerprint the build (2 min, no SDK)

Hash the build directory into an external manifest (schema v1):

```sh-harness
mkdir -p $CODELAB_TMP/build-out
cp $CODELAB_TMP/guard_vector* $CODELAB_TMP/build-out/
python -m genesis_rt.cli external-write-manifest \
  --workspace $CODELAB_TMP/build-out --project codelab-ext \
  --toolchain "host cc (recorded, not verified)" \
  --out $CODELAB_TMP/manifest.json
python -m genesis_rt.cli external-check $CODELAB_TMP/manifest.json \
  --workspace $CODELAB_TMP/build-out | grep -q 'verdict: CONSISTENT'
```

```powershell
New-Item -ItemType Directory -Force -Path $env:TEMP/build-out | Out-Null
Copy-Item $env:TEMP/guard_vector.exe $env:TEMP/build-out/
$env:PYTHONPATH='host'; python -m genesis_rt.cli external-write-manifest `
  --workspace $env:TEMP/build-out --project codelab-ext `
  --toolchain "host cc (recorded, not verified)" --out $env:TEMP/manifest.json
python -m genesis_rt.cli external-check $env:TEMP/manifest.json `
  --workspace $env:TEMP/build-out
# expect: MATCH guard_vector.exe ... verdict: CONSISTENT
```

Expect `MATCH guard_vector` (`guard_vector.exe` on Windows) and
`verdict: CONSISTENT` (exit 0).

## Step 3 — Tamper, then catch it (3 min, no SDK)

Flip one byte and re-check. The checker must name the binary:

```sh-harness
python -c "import sys, glob; p = glob.glob(sys.argv[1] + '/build-out/guard_vector*')[0]; b = bytearray(open(p, 'rb').read()); b[100] ^= 1; open(p, 'wb').write(bytes(b))" "$CODELAB_TMP"
if python -m genesis_rt.cli external-check $CODELAB_TMP/manifest.json \
  --workspace $CODELAB_TMP/build-out 2>/dev/null; then
  echo "expected STALE, got CONSISTENT"; exit 1
fi
python -m genesis_rt.cli external-check $CODELAB_TMP/manifest.json \
  --workspace $CODELAB_TMP/build-out --json \
  | grep -q '"verdict": "STALE"'
```

```powershell
$bytes = [IO.File]::ReadAllBytes("$env:TEMP/build-out/guard_vector.exe")
$bytes[100] = $bytes[100] -bxor 1
[IO.File]::WriteAllBytes("$env:TEMP/build-out/guard_vector.exe", $bytes)
python -m genesis_rt.cli external-check $env:TEMP/manifest.json `
  --workspace $env:TEMP/build-out
# expect: MISMATCH guard_vector.exe (expected <sha>..., observed <sha>...)
# verdict: STALE, exit code 2, release_eligible: False
```

## Step 4 — Read the trust boundary (2 min, no SDK)

What just happened, precisely:

- The checker re-hashed bytes and compared digests. That is ALL it
  does: `MATCH` / `MISMATCH` / `ABSENT` per binary.
- The toolchain string is recorded, never verified. A manifest can
  claim any toolchain; the verdict does not depend on it.
- A manifest may carry `test_claims` ("smoke: pass"). These are
  counted and labelled `UNVERIFIED_CLAIM` — never evaluated, never
  trusted. There is no code path from `host/genesis_rt/external.py`
  to the release gate (enforced by
  `test_adapter_has_no_gate_or_target_imports`).
- `release_eligible` is always `False`. CONSISTENT means "not
  stale", never "verified".

This is the honest minimum a tool can say about a build it did not
supervise — and it is exactly the check that catches "deployed last
month's binary with this month's config".

## Step 5 — Same flow on real qcc output (5 min, needs SDK)

The mechanics are byte-identical for cross-compiled binaries.
Generate a target build, compile with `qcc`, manifest, check:

```sh-harness-sdk
PYTHONPATH=host python -m genesis_rt.cli generate \
  examples/amr-demo/machine-ir.json --out $CODELAB_TMP/sdk-build >/dev/null
make -C $CODELAB_TMP/sdk-build -f genesis_build_gen.mk qnx >/dev/null
mkdir -p $CODELAB_TMP/sdk-out
cp $CODELAB_TMP/sdk-build/genesis_guard $CODELAB_TMP/sdk-build/genesis_controller $CODELAB_TMP/sdk-build/genesis_device $CODELAB_TMP/sdk-build/genesis_status $CODELAB_TMP/sdk-build/genesis_supervisor $CODELAB_TMP/sdk-build/genesis_faultinject $CODELAB_TMP/sdk-out/
python -m genesis_rt.cli external-write-manifest \
  --workspace $CODELAB_TMP/sdk-out --project codelab-qcc \
  --toolchain "qcc 12.2.0 gcc_ntox86_64 (recorded, not verified)" \
  --out $CODELAB_TMP/sdk-manifest.json >/dev/null
python -m genesis_rt.cli external-check $CODELAB_TMP/sdk-manifest.json \
  --workspace $CODELAB_TMP/sdk-out | grep -q 'verdict: CONSISTENT'
```

Windows (PowerShell, adjust the SDK path to your install —
same session as step 2 so `$env:PYTHONPATH` persists):

```powershell
$env:PYTHONPATH='host'
python -m genesis_rt.cli generate examples/amr-demo/machine-ir.json --out $env:TEMP/sdk-build
cmd /c "call E:\qnx800\qnxsdp-env.bat >NUL 2>&1 && make -C $env:TEMP/sdk-build -f genesis_build_gen.mk qnx"
New-Item -ItemType Directory -Force -Path $env:TEMP/sdk-out | Out-Null
Copy-Item $env:TEMP/sdk-build/genesis_guard, $env:TEMP/sdk-build/genesis_controller, `
  $env:TEMP/sdk-build/genesis_device, $env:TEMP/sdk-build/genesis_status, `
  $env:TEMP/sdk-build/genesis_supervisor, $env:TEMP/sdk-build/genesis_faultinject $env:TEMP/sdk-out/
python -m genesis_rt.cli external-write-manifest --workspace $env:TEMP/sdk-out `
  --project codelab-qcc --toolchain "qcc 12.2.0 gcc_ntox86_64 (recorded, not verified)" `
  --out $env:TEMP/sdk-manifest.json
python -m genesis_rt.cli external-check $env:TEMP/sdk-manifest.json --workspace $env:TEMP/sdk-out
# expect: 6 MATCH lines, verdict: CONSISTENT
```

Verified 8 Nov 2026 on Windows (qcc 12.2.0, 6/6 MATCH both
shells, then a planted 1-byte tamper detected as STALE naming
`genesis_guard`).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `binary ... escapes the workspace` | Manifest names an absolute path or `..` | Keep names relative inside the build dir |
| `workspace has no files to cover` | Empty `--workspace` | Point at the directory holding the binaries |
| `test_claims[i] verdict must be pass/fail` | Hand-written claim typo | Claims take only `pass`/`fail` (and stay unverified) |
| CONSISTENT after a rebuild | You re-manifested after rebuilding | Manifest once per release candidate; check copies, not the fresh build |
| `qcc: not found` | SDK env not sourced | `source ~/qnx800/qnxsdp-env.sh` in the same shell (Linux) or `cmd /c "call E:\qnx800\qnxsdp-env.bat ... && make ..."` (Windows) |

## Cleanup

```sh
rm -rf $CODELAB_TMP/build-out $CODELAB_TMP/manifest.json \
  $CODELAB_TMP/guard_vector $CODELAB_TMP/sdk-build $CODELAB_TMP/sdk-out \
  $CODELAB_TMP/sdk-manifest.json
```

```powershell
Remove-Item -Recurse -Force $env:TEMP/build-out, $env:TEMP/manifest.json, `
  $env:TEMP/guard_vector.exe, $env:TEMP/sdk-build, $env:TEMP/sdk-out, $env:TEMP/sdk-manifest.json
```

## Safety and scope limitations

- Digest equality is not execution evidence. This adapter cannot tell
  you the binary behaves correctly — only that it is the binary you
  fingerprinted.
- No functional-safety qualification; see
  `docs/jury/KNOWN_LIMITATIONS.md`, which governs.
- QEMU/host timing is not real-time evidence.

## Takeaway

Two commands give an existing QNX build a tamper-evident seal:
fingerprint once, check everywhere the bits travel. When you also
want supervised execution with a sealed passport, continue with
[`README.md`](README.md).
