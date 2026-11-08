# Advanced QNX codelab: message passing, guards, supervision, provenance

> Companion to the base codelab (`README.md`, do its steps 1–3
> first). Every host command below was executed against commit
> `88fc772` on 2026-11-05; every target command was executed live
> on QNX 8.0.0 QEMU the same day (transcripts in Lab 6).
> Fenced `sh-harness` blocks are executed by
> `tests/integration/test_codelab_advanced.py` — if they rot, CI
> fails. `sh-harness-sdk` needs an SDP 8.0; `sh-target` runs on
> the target over SSH (read Lab 6 setup first).
>
> Setup (host, repo root): `export CODELAB_TMP=/tmp/qlab-adv &&
> mkdir -p $CODELAB_TMP`. Windows: run the `sh` blocks in the QNX
> SDP shell or git-bash (PowerShell variants where `printf` is
> used). No physical hardware is involved anywhere below.

You will learn, by running: the guard policy (including its
wraparound-safe clock arithmetic), deterministic codegen and its
provenance header, passport anatomy, independent replay and
tamper-evidence, the native `qcc` build, and on-target IPC,
supervision, telemetry, and latency measurement.

- [Lab 1 — Guard policy microscope](#lab-1--guard-policy-microscope-host-no-sdk) (host, no SDK)
- [Lab 2 — Deterministic codegen](#lab-2--deterministic-codegen-and-provenance-host-no-sdk) (host, no SDK)
- [Lab 3 — Passport anatomy](#lab-3--passport-anatomy-host-no-sdk) (host, no SDK)
- [Lab 4 — Independent replay](#lab-4--independent-replay-and-tamper-evidence-host-no-sdk) (host, no SDK)
- [Lab 5 — Native build anatomy](#lab-5--native-build-anatomy-host-needs-sdp-80) (host, needs SDP 8.0)
- [Lab 6 — On target](#lab-6--on-target-ipc-supervision-telemetry-latency) (needs QEMU target)
- [Acceptance checklist — Labs 5–6](#acceptance-checklist--labs-56-manual-needs-sdk--target)

## Lab 1 — Guard policy microscope (host, no SDK)

Build the host vector harness (same `guard_policy.c` that ships
on the target) and feed it decision vectors. Vector fields:
`magic version size_ok seq now_ms deadline_ms linear angular
req_state sensor_age sim_connected reset_armed state_in`.
Output: `DECISION REASON STATE_OUT`.

```sh-harness
CC=$(command -v cc || command -v gcc)  # whichever host compiler exists
$CC -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common \
  -o $CODELAB_TMP/guard_vector target/qnx8/common/guard_policy.c \
  target/qnx8/host_tests/guard_vector.c
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 100 100 0.5 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q "ALLOW OK 1"
```

Nominal: 0.5 m/s under the 1.2 limit → `ALLOW OK 1`. Now the
wraparound boundary — `SEQ <last>` arms the previous sequence
counter, and millisecond clocks are `uint32` (RFC 1982 serial
arithmetic: a delta is fresh iff `1 <= delta < 2^31`):

```sh-harness
printf 'LIMITS 1.2 1.0 100\nSEQ 4294967295\n47454E31 1 1 0 100 100 0.5 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q "ALLOW OK 1"
printf 'LIMITS 1.2 1.0 100\nSEQ 100\n47454E31 1 1 100 100 100 0.5 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q "DENY STALE_SEQ 1"
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 101 5 4294967290 0.5 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q "DENY OVERDUE_DEADLINE 1"
printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 102 4294967290 5 0.5 0.0 1 0 1 0 1\n' \
  | $CODELAB_TMP/guard_vector | grep -q "ALLOW OK 1"
```

Read them: seq `2^32-1 → 0` is delta 1, accepted; replaying
seq 100 is delta 0, denied `STALE_SEQ`; `now=5` past
`deadline=2^32-6` is 11 ms overdue across the wrap, denied;
`now=2^32-6` with `deadline=5` is a deadline in the future
across the wrap, allowed. The ~49.7-day wrap is a non-event
by construction; pairs 2^31+ ms apart are ambiguous by
design and read as "deadline in the future".

Windows (PowerShell, file-based — no `printf`):

```powershell
gcc -O1 -Wall -Wextra -Itarget/qnx8/include -Itarget/qnx8/common `
  -o $env:TEMP/guard_vector target/qnx8/common/guard_policy.c target/qnx8/host_tests/guard_vector.c
@'
LIMITS 1.2 1.0 100
SEQ 4294967295
47454E31 1 1 0 100 100 0.5 0.0 1 0 1 0 1
'@ | Set-Content $env:TEMP/wrap.txt
Get-Content $env:TEMP/wrap.txt | & $env:TEMP/guard_vector.exe
# expect: SEQ-ARMED 4294967295, then ALLOW OK 1
```

## Lab 2 — Deterministic codegen and provenance (host, no SDK)

Generate twice into two directories: byte-identical output.
Then verify the printed `sha256` of the config header
independently — trust the hash, not the log line:

```sh-harness
PYTHONPATH=host python -m genesis_rt.cli generate examples/amr-demo/machine-ir.json --out $CODELAB_TMP/lab-a
PYTHONPATH=host python -m genesis_rt.cli generate examples/amr-demo/machine-ir.json --out $CODELAB_TMP/lab-b
python -c "import hashlib,os; t=os.environ['CODELAB_TMP']; a=[open(t+'/lab-a/genesis_config_gen.h','rb').read(),open(t+'/lab-a/genesis_build_gen.mk','rb').read()]; b=[open(t+'/lab-b/genesis_config_gen.h','rb').read(),open(t+'/lab-b/genesis_build_gen.mk','rb').read()]; assert a==b, 'codegen not deterministic'; print('config sha256:', hashlib.sha256(a[0]).hexdigest()[:16])"
```

Example from the author's run: `config sha256:
cd74fc72635d736c` (stable across machines — the header
carries no paths). The `.mk` embeds `GENESIS_SRC` relative
to the output directory, so its bytes (and sha) legitimately
differ when `--out` moves; same inputs → same bytes still
holds. Inspect the provenance header:

```sh-harness
grep -q "IR sha256:" $CODELAB_TMP/lab-a/genesis_config_gen.h
grep -q "GENESIS RT codegen" $CODELAB_TMP/lab-a/genesis_config_gen.h
grep -q "GENESIS_MAX_LINEAR_MPS 1.2" $CODELAB_TMP/lab-a/genesis_config_gen.h
```

Every generated file names the IR digest and generator
version that produced it — the seed of the passport chain.

## Lab 3 — Passport anatomy (host, no SDK)

Run the verified demo pipeline, then dissect its passport
(14 hash-chained records on the author's run):

```sh-harness
PYTHONPATH=host python scripts/run_verified_demo.py > $CODELAB_TMP/demo.json
python -c "import json,os; d=json.load(open(os.environ['CODELAB_TMP']+'/demo.json')); print(d['verdict'], 'qnx_verified=' + str(d['qnx_verified']))"
```

Expect `PASS qnx_verified=False` — host-only evidence is
labeled as such; nothing here claims a target run. The JSON
also prints the passport path. Inspect the chain:

```sh-harness
python -c "
import json, glob
pp = sorted(glob.glob('artifacts/runs/run-*/passport.json'), key=lambda p: __import__('os').stat(p).st_mtime)[-1]
p = json.load(open(pp))
print('records:', len(p['chain']), '| kinds:', [r['kind'] for r in p['chain']][:4], '...')
g = [r['body'] for r in p['chain'] if r['kind']=='gate_verdict'][0]
print('level:', g['level'], '| release_eligible:', g['release_eligible'])
assert g['level'] in ('QNX_COMPILED', 'HOST_TESTED'), g['level']
assert g['release_eligible'] is False
"
```

`QNX_COMPILED` (built, never ran on target — or `HOST_TESTED`
without an SDK) with `release_eligible: False`: the release
policy from `docs/limitations-and-safety.md` in one line — no
target binding, no release.

## Lab 4 — Independent replay and tamper-evidence (host, no SDK)

Replay the demo passport with the standalone verifier (no
pipeline state — just the file), then flip one byte in a
copy and watch the chain refuse it:

```sh-harness
python -c "
import json, glob, os
pp = sorted(glob.glob('artifacts/runs/run-*/passport.json'), key=lambda p: os.stat(p).st_mtime)[-1]
open(os.environ['CODELAB_TMP']+'/which.txt','w').write(pp)
"
PYTHONPATH=host python scripts/replay.py $(cat $CODELAB_TMP/which.txt) | grep -q "chain: valid"
python -c "
import json, os
t = os.environ['CODELAB_TMP']
pp = open(t+'/which.txt').read().strip()
p = json.load(open(pp))
p['chain'][4]['body']['verdict'] = 'PASS'
open(t+'/tampered.json','w').write(json.dumps(p))
"
PYTHONPATH=host python scripts/replay.py $CODELAB_TMP/tampered.json > $CODELAB_TMP/tamper.log || test $? -eq 1
grep -q "hash mismatch" $CODELAB_TMP/tamper.log
grep -q "gate: FAIL" $CODELAB_TMP/tamper.log
```

The author's tamper flipped `chain[4]`
(`scenario:corrupted_message`) → `record 4
(...): hash mismatch`, `gate: FAIL`, exit 1. Any byte,
any record, same refusal.

## Lab 5 — Native build anatomy (host, needs SDP 8.0)

Compile Lab 2's output with `qcc` (Linux: source the env
script first; Windows: wrap in `cmd /c "call
E:\qnx800\qnxsdp-env.bat ..."` with your SDK path). The
harness runs this block only when the SDK probes present:

```sh-harness-sdk
PYTHONPATH=host python -m genesis_rt.cli generate examples/amr-demo/machine-ir.json --out $CODELAB_TMP/lab-a
make -C $CODELAB_TMP/lab-a -f genesis_build_gen.mk qnx > $CODELAB_TMP/make.log 2>&1
grep -q "qcc -Vgcc_ntox86_64" $CODELAB_TMP/make.log
test $(grep -c "warning" $CODELAB_TMP/make.log) -eq 0
ls $CODELAB_TMP/lab-a/genesis_controller $CODELAB_TMP/lab-a/genesis_device $CODELAB_TMP/lab-a/genesis_faultinject $CODELAB_TMP/lab-a/genesis_guard $CODELAB_TMP/lab-a/genesis_status $CODELAB_TMP/lab-a/genesis_supervisor
```

Expect 6 `genesis_*` binaries, `-O2 -Wall -Wextra`, zero
warnings. Note what links what: guard+faultinject share
`guard_policy.c` (the exact file from Lab 1), the device
links `device_model.c`, the supervisor stands alone.

## Lab 6 — ON TARGET: IPC, supervision, telemetry, latency

Target: QNX 8.0.0 QEMU x86_64 (see
`docs/quickstart-qnx8-qemu.md` for image setup). Boot and
stage the Lab 5 binaries from the host (adjust the image
dir to your install):

```sh-target
python scripts/qnx_target.py boot E:/qnx800/images/qemu/qemu --accel tcg --cpu max --ssh-port 2222
python scripts/qnx_target.py wait-ssh --ssh-port 2222 --wait 300
export GENESIS_TARGET_PASSWORD=qnxuser
python scripts/qnx_target.py put $CODELAB_TMP/lab-a/genesis_* --user qnxuser
```

Then SSH (`ssh qnxuser@localhost -p 2222`) and run each
section below. Outputs are from the author's live run on
2026-11-05 (see note at the end of the lab).

### 6.1 Process isolation: two address spaces, one channel

```sh-target
cd /tmp/genesis
./genesis_device > lab-dev.log 2>&1 & ./genesis_guard > lab-guard.log 2>&1 &
sleep 3
pidin 2>/dev/null | grep genesis
```

```text
1622043   1 ./genesis_device              10r RECEIVE        1
1622044   1 ./genesis_guard               10r RECEIVE        1
```

Distinct PIDs, both blocked in `RECEIVE`: each process owns
its address space (a wild pointer in the device cannot touch
the guard), and all coordination flows through the kernel
surrogate — `MsgSend`/`MsgReceive`/`MsgReply` on a channel
(see `target/qnx8/include/genesis_ipc.h` for the wire
structs, `*_VERSION`/`magic` checked on every message).

### 6.2 Resource manager telemetry: BEFORE vs AFTER

```sh-target
sudo -n ./genesis_status > lab-status.log 2>&1 & sleep 2
cat /dev/genesis/status
./genesis_faultinject; echo FI_EXIT=$?
cat /dev/genesis/status
```

```text
state=1 allows=0 denies=0 last_reason=OK last_seq=0 dropped=0 fwd_ok=0 fwd_fail=0 dev_x=0.000 dev_theta=0.000 dev_v=0.000 dev_applied=0 dev_seq=0
PASS nominal            decision=0 reason=0 state=1 (want 0/0/1)
PASS over_limit         decision=1 reason=8 state=1 (want 1/8/1)
PASS replay_seq         decision=1 reason=4 state=1 (want 1/4/1)
PASS overdue            decision=1 reason=5 state=1 (want 1/5/1)
PASS bad_version        decision=1 reason=2 state=3 (want 1/2/3)
PASS nan_linear         decision=1 reason=11 state=3 (want 1/11/3)
PASS bad_magic          decision=1 reason=1 state=3 (want 1/1/3)
PASS short_frame        decision=1 reason=3 state=3 (want 1/3/3)
PASS locked_nominal     decision=1 reason=10 state=3 (want 1/10/3)
faultinject: ALL 9 CHECKS PASS
FI_EXIT=0
state=3 allows=1 denies=8 last_reason=BAD_TRANSITION last_seq=1 dropped=4 fwd_ok=1 fwd_fail=0 dev_x=0.000 dev_theta=0.000 dev_v=0.000 dev_applied=1 dev_seq=1
```

Nine adversarial checks through real IPC, and the telemetry
node (`/dev/genesis/status`, served by `genesis_status` via
`resmgr_attach`) moves accordingly: the SAFE_STOP latch
(`state=3`), 1 allow against 8 denies, 1 forwarded apply.
`sudo -n` is required: attaching at an absolute path needs
root, otherwise `EPERM` and no node appears.

### 6.3 Latency visibility (QEMU numbers, regression use only)

```sh-target
./genesis_faultinject bench 200; echo BENCH_EXIT=$?
```

```text
SAMPLE 112.126
SAMPLE 131.207
SAMPLE 273.014
...
SAMPLE 128.051
SAMPLE 130.556
PERF_DONE n=200
BENCH_EXIT=0
```

200 IPC round-trips in microseconds. These numbers compare
runs against each other (the `target_perf` matrix step and
the `qemu_perf` campaign stage do exactly that); they are
not physical hard-real-time evidence — QEMU on a desktop
cannot provide that, and the passport never claims it.

### 6.4 Supervision: RESPAWN, then GIVE_UP

```sh-target
./genesis_supervisor > lab-sup.log 2>&1 & sleep 4
slay genesis_device; sleep 6
grep -c RESPAWN lab-sup.log
```

```text
4
```

The supervisor notices the dead child and respawns it (4
RESPAWN lines cover the respawned chain settling). Kill the
guard 4 times in a row and policy flips to giving up:

```sh-target
./genesis_supervisor > lab-sup2.log 2>&1 & sleep 4
for i in 1 2 3 4; do slay genesis_guard; sleep 6; done; sleep 2
grep -c GIVE_UP lab-sup2.log
```

```text
1
```

(`slay: Unable to find process` noise between kills is
harmless — it means a previous kill already landed.) Respawn
forever on a flapping guard would wedge the machine;
GIVE_UP says so in the log instead of looping silently.

### 6.5 Failure containment: SIGKILL the controller mid-chain

```sh-target
./genesis_guard > lab-ccx-g.log 2>&1 & sleep 2
./genesis_device > lab-ccx-d.log 2>&1 & sleep 1
./genesis_controller 100 > lab-ccx-c.log 2>&1 & sleep 6
GBEFORE=$(grep -c decision lab-ccx-g.log)
slay -9 genesis_controller; sleep 3
echo GBEFORE=$GBEFORE GAFTER=$(grep -c decision lab-ccx-g.log)
echo CALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_controller)
echo GALIVE=$(pidin -F %n 2>/dev/null | grep -c genesis_guard)
```

```text
GBEFORE=61 GAFTER=61
CALIVE=0
GALIVE=1
```

The guard log freezes the moment the source dies (61 → 61:
no phantom traffic), the controller is gone from `pidin`,
and the guard survives. Containment is per-process because
isolation is per-process (§6.1).

### 6.6 Cleanup and stop

```sh-target
slay genesis_supervisor 2>/dev/null; slay genesis_guard 2>/dev/null
slay genesis_controller 2>/dev/null; slay genesis_device 2>/dev/null
sudo -n slay genesis_status 2>/dev/null
rm -f lab-*.log
```

On the host: `python scripts/qnx_target.py stop
E:/qnx800/images/qemu/qemu` (your image dir), which clears
the pidfile.

> Lab 6 transcript note: PIDs, SAMPLE values, and counts
> (61 decisions, 4 RESPAWNs) vary run to run — assert shapes,
> not literals. QNX 8.0.0 QEMU x86_64, TCG+cpu max,
> 2026-11-05.

## Acceptance checklist — Labs 5–6 (manual, needs SDK + target)

Labs 1–4 are executed by CI (`sh-harness`); Labs 5–6 need an
SDP and a live target, so confirm them by hand. Tick every box
before calling the codelab done — shapes, not literals:

- [ ] Lab 5: `make.log` shows `qcc -Vgcc_ntox86_64`, zero
  `warning` lines, and all 6 `genesis_*` binaries exist.
- [ ] Lab 6.1: two distinct PIDs, both in `RECEIVE` state.
- [ ] Lab 6.2: `faultinject: ALL 9 CHECKS PASS`, `FI_EXIT=0`,
  and `/dev/genesis/status` shows the `state=3` latch with
  1 allow against 8 denies.
- [ ] Lab 6.3: `PERF_DONE n=200` with `BENCH_EXIT=0` (SAMPLE
  values vary; the shape `SAMPLE <µs>` × 200 is what matters).
- [ ] Lab 6.4: `grep -c RESPAWN` ≥ 1 after killing the device;
  `grep -c GIVE_UP` = 1 after 4 guard kills.
- [ ] Lab 6.5: guard log count frozen (`GAFTER` = `GBEFORE`),
  `CALIVE=0`, `GALIVE=1` after SIGKILLing the controller.
- [ ] Lab 6.6: no `genesis_*` left in `pidin`, scratch
  `lab-*.log` removed, QEMU stopped from the host.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `cc: not found` (Lab 1) | No host C compiler | Install gcc/clang (Windows: MinGW via scoop, or the QNX SDP shell) |
| `sh: printf` missing newlines | Non-POSIX shell | Run `sh` blocks in sh/bash, not PowerShell (variants given in Lab 1) |
| `grep -q` fails on Lab 2 | Edited example IR | Re-copy `examples/amr-demo/machine-ir.json`; the doc's shas assume it |
| `replay.py` says `chain: valid` on your tamper copy | Edited the original path, not the copy | Re-copy the passport, flip, re-run |
| `make: qcc: No such file` (Lab 5) | SDK env not in this shell | Source `qnxsdp-env` in the **same** shell (Linux `source`, Windows `cmd /c "call ... && make ..."`) |
| `wait-ssh` never opens | Boot still starting (TCG is slow) or a stale QEMU holds 2222 | Wait up to 300 s; `tasklist`/`ps` for a stale `qemu-system`, `stop` it, re-boot |
| `status: EPERM` (Lab 6.2) | Resource manager needs root | `sudo -n ./genesis_status` (NOPASSWD sudo, as on the QSTI image) |
| `slay: Unable to find process` | Already dead | Harmless |

## Cleanup (host)

Remove the scratch outputs — including the Lab 3 demo run, so a
later `artifacts/runs/*/passport.json` glob still matches exactly
one file:

```sh-harness
python -c "import json,os,shutil; d=json.load(open(os.environ['CODELAB_TMP']+'/demo.json')); shutil.rmtree('artifacts/runs/'+d['run_id'])"
rm -rf $CODELAB_TMP/lab-a $CODELAB_TMP/lab-b $CODELAB_TMP/demo.json $CODELAB_TMP/which.txt $CODELAB_TMP/tampered.json $CODELAB_TMP/tamper.log $CODELAB_TMP/guard_vector $CODELAB_TMP/make.log
```

## Safety and scope limitations

Same as the base codelab: simulation only, prototype
not certified, QEMU timing is regression aid only (see
`docs/jury/KNOWN_LIMITATIONS.md`, which governs).

## Takeaway

A measured guard policy, byte-identical codegen, a passport
you replayed and tampered with, a native `qcc` build, and
on-target IPC, supervision, and containment you watched
happen. Same loop as the base codelab — specify → compile →
run → break → prove — now with the inside of every step
visible.

> Final URL for the Devpost bonus box:
> `https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/ADVANCED-QNX.md`
