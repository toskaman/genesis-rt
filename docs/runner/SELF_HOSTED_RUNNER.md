# Self-hosted QNX verification runner (reference, Wave 12 §8)

Status: reference implementation, functional. Code:
`host/genesis_rt/runner.py`, CLI `runner-submit` / `runner-status` /
`runner-cancel`, tests `tests/unit/test_runner.py` (14) +
`tests/integration/test_runner_cli.py` (4).

This is a **reference**, not a hosted service: no live runner is
operated for this repository. Any team can run it on a licensed
self-hosted machine that holds the QNX SDK + QEMU image. Nothing
proprietary ever touches a public GitHub runner.

## 1. Workflow

```
developer push / PR
  -> public CI: scripts/ci_ir_check.py validates changed IRs,
     builds a ProofOS plan (host only, no secrets)
  -> operator deploys the trusted revision on the runner host
  -> signed job {job_id, operation, revision, ir, plan?} submitted
  -> runner: HMAC auth -> allowlist -> revision pin -> IR + plan
     validation -> exclusive target lease -> native execution
  -> job record + target op record + evidence artifacts
  -> reviewer: verify-pack / Studio review brief / dossier
```

## 2. Threat model (how each §8 item is handled)

- **Untrusted PR code**: the runner never checks out a job's
  revision; it only runs jobs pinned to its own deployed `HEAD`.
  IR and plan arrive inline and are strictly validated.
- **Credential theft**: the only credential is
  `GENESIS_RUNNER_TOKEN` (HMAC-SHA256, env-only, never in jobs
  or logs). Narrow by construction: it authorizes verification
  jobs, nothing else.
- **Runner persistence / target compromise**: out of scope for
  the reference — the guide assumes a trusted host; per-job
  isolation is per-job op dirs + the exclusive lease, not a
  sandbox. Stated, not solved.
- **Replay attacks**: HMAC covers the whole body; `job_id`
  dedupe makes duplicate delivery return the stored record
  instead of re-running. Cross-pack plan replay is blocked by
  the plan/IR digest binding.
- **Stale binary deployment / build substitution**: the job IR
  is rebuilt from source on every run (`generate` + `build`
  steps); artifacts record `ir_sha256`, and `verify-only`
  refuses stale build sets (existing `TargetRunner` behavior).
- **Job ID collisions**: `job_id` charset is restricted and the
  store is keyed by id; a colliding redelivery replays the
  stored record, never forks a second execution.
- **Target lease loss**: `TargetLock` file lease + in-process
  exclusivity; a second job while leased gets `BLOCKED`
  (exit 2), never queue-jumping.
- **Cancelled workflows**: `runner-cancel` cancels the target
  op and settles the job `CANCELLED`; terminal states are
  sticky; the waiter enforces `timeout_s` then cancels.
- **Duplicate job delivery**: idempotent by `job_id`
  (tested, including while RUNNING).
- **Evidence tampering**: job records reference target op
  records; packs can be signed (`sign-pack`, see
  `docs/evidence-trust.md`).
- **Misleading target identity**: records carry adapter name,
  `op_id`, and the honest `qnx_verified` flag (`false` for
  `fake` and for `build-only`, which never touches a target).

## 3. Operations

Allowlisted operations (server-side map, clients cannot add
steps): `native_build` -> `build-only`, `native_verify` ->
`verify-only`, `native_full` -> `full`. Only `timeout_s`
(capped) is client-tunable; QEMU paths, ports, and workflows
are server config.

```sh
export GENESIS_RUNNER_TOKEN="$(openssl rand -hex 32)"  # secret store in prod
# job.json: {job_id, operation, revision=<deployed HEAD>, ir={...}, plan?}
PYTHONPATH=host python -m genesis_rt.cli runner-submit --job job.json \
  --image-dir /path/to/qemu-image
# exit 0 COMPLETED (check qnx_verified), 1 failed/rejected, 2 blocked/usage
PYTHONPATH=host python -m genesis_rt.cli runner-status --job-id <id>
PYTHONPATH=host python -m genesis_rt.cli runner-cancel --job-id <id>
```

Rotate the token by replacing it; in-flight jobs are
unaffected (auth happens once at submit). Keep the token out
of PR-visible CI: public CI builds plans, only the trusted
host submits jobs.

## 4. Functional demonstration (recorded 2026-11-06)

Environment: Windows 11, QNX SDP 8.0, qcc 12.2.0
(`gcc_ntox86_64`), QEMU 11.1.0 present. Repo pinned to
`f42b6ab`. Token: throwaway demo value.

Fake-adapter plumbing (`--adapter fake`):

```
job demo-fake-1 pinned to f42b6abebd81
"status": "COMPLETED", "adapter": "fake", "qnx_verified": false,
"note": "fake adapter: plumbing only, never a native verification verdict"
```

Real local path (`--adapter local`, `native_build`):

```
job demo-real-build-1 pinned to f42b6abebd81
"status": "COMPLETED", "adapter": "local", "op_id": "op-dd0b62f9d713",
"op_state": "COMPLETED", "qnx_verified": false,
"artifacts": {"binaries": [".../gen/genesis_controller",
  ".../genesis_device", ".../genesis_faultinject", ".../genesis_guard",
  ".../genesis_status", ".../genesis_supervisor"],
  "ir_sha256": "356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d",
  "machine_id": "amr-demo-01", "verdict": "PASS",
  "replay": {"verdict": "PASS", "qnx_verified": false},
  "sdk_present": true, "qemu_present": true}
```

Authenticity check on the produced binary: `genesis_guard`
starts with `7F 45 4C 46` (ELF), class 64-bit, machine
x86-64; `qnx-build-record.json` reports `status: ok`,
`returncode: 0`, compiler `qcc.EXE` 12.2.0. `qnx_verified`
is `false` because `build-only` compiles but never executes
on a target — the flag tells the truth.

A full `native_full` demo (QEMU boot + 16-check matrix) uses
the same command with `"operation": "native_full"` and
`--image-dir`; it was not re-run here because the Wave 11
campaign already proved the underlying `TargetRunner` path
(`op-ca900c25406f`, 16/16 PASS) and this reference adds no
new target steps — only auth, pinning, and job framing,
all covered by the tests above.

## 5. Residual risks

No sandboxing of the build (malicious IR-adjacent inputs are
validated, but qcc/make run as the runner user); no
multi-tenant isolation beyond the lease; token rotation is
manual; job store growth is unbounded (operator retention
policy needed); timestamps are host clocks. The `fake`
adapter exists so CI plumbing can be tested anywhere — it
must never be mistaken for verification, and its records
say so explicitly.
