# Devpost submission draft (prepared, NOT submitted)

Category: **Developer Tooling & Host Tools**.
Video: `PENDING — FINAL VIDEO DEFERRED BY USER`. Final video production:
deferred by user. A historical cut exists (`docs/demo/genesis-rt-demo-w12.mp4`,
154.664 s; see `docs/demo/PUBLICATION_HANDOFF_W12.md`) but it predates the
current Studio and is **not** the submission video. Rules reminder: the
final video must show the project running on the intended device (QEMU
target), be public on YouTube and under 3 minutes.
Repo: https://github.com/toskaman/genesis-rt
Codelab (bonus box): https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/README.md

## Title

GENESIS RT — The Physical World Compiler

## Tagline

From machine intent to QNX-native software — with verifiable proof.

## Inspiration

When a requirement changes on embedded control software — say a robot's
speed limit goes from 1.2 to 1.6 m/s — teams have to answer three
questions before shipping: did the code actually change, does the binary
on the target match the new requirement, and can someone else check the
evidence without trusting us? In practice the answers live in chat logs
and people's heads. We wanted a tool where the answer is a file anyone can
verify offline.

## What it does

1. **Specify** — a machine is described as a strictly validated Machine IR
   contract (fixed kinds, units, limits, safety contracts; unknown input is
   rejected, never guessed). Optional AI planning turns free text into that
   contract — but only through the same gate (see below).
2. **Compile** — deterministic codegen emits QNX C build files with hashed
   provenance; identical IR always yields byte-identical source.
3. **Run natively** — `qcc` builds six QNX processes that run on QNX 8.0
   (QEMU x86_64): guard server, periodic controller, device endpoint,
   `/dev/genesis/status` resource manager, supervisor, fault-injection client.
4. **Break** — an 8-scenario fault lab on the host and a 16-check on-target
   matrix including 9/9 native fault-injection checks over real IPC.
5. **Prove** — a hash-linked evidence passport and a fail-closed release
   gate; missing, skipped, crashed or tampered evidence yields FAIL. Packs
   verify offline with a stdlib-only `verify.py`.
6. **Explain** — GENESIS Studio (local web UI) with a guided tour, a
   before/after view, an evidence graph, a release-decision panel in plain
   language, light/dark themes and an automated WCAG 2.2 scan in CI.

## How it works

Machine IR → strict validation → deterministic codegen → `qcc` build with
binary digests → staged to the QNX target over SSH → contract-aware native
oracle (expected ALLOW / DENY / SAFE_STOP derived from the validated IR, not
hard-coded) → transcripts sealed into a 15-link passport bound to the IR
digest and op id → in-op replay → release decision.

## How we use QNX (paste-ready)

The generated controller is QNX-native C: guard and controller communicate
over Neutrino synchronous message passing (`name_attach`/`name_open`,
`MsgSend`/`MsgReceive`/`MsgReply`), telemetry is served by a resource
manager (`resmgr_attach`, `io_read`) at `/dev/genesis/status`, control
timing uses `CLOCK_MONOTONIC` with RFC 1982 wrap-safe sequence/deadline
arithmetic, and a custom supervisor owns bounded respawn and GIVE_UP
(QNX HAM is not used — it is absent from the image). Target: QNX SDP 8.0,
`qcc` 12.2.0 (`gcc_ntox86_64`), QEMU x86_64. Key files:
`target/qnx8/include/genesis_ipc.h`, `target/qnx8/guard/`,
`target/qnx8/controller/`, `target/qnx8/status/`,
`target/qnx8/supervisor/`, `target/qnx8/common/guard_policy.c`.

## Technical innovation: contract-to-proof change verification

The flagship proof is one valid requirement change, verified natively twice:

| | BEFORE | AFTER |
|---|---|---|
| Contract `max_linear_speed_mps` | 1.2 | 1.6 |
| Probe 1.5 m/s on QNX | DENY `SPEED_OVER_LIMIT` | ALLOW |
| Native matrix | 16/16 | 16/16 |
| Pack | `evidence/qnx8-x86_64-w11-before/` | `evidence/qnx8-x86_64-w11-after/` |

Both verdicts are correct under their own contract. Pairing the 1.6
contract with the stale 1.2-built binary is rejected by the gate. The AFTER
campaign was re-executed from scratch on 7 Nov 2026 (op-24fecbf11df8, 16/16,
`evidence/qnx8-x86_64-w11-after-rerun/`).
Every published native binary (18 across the three packs) rebuilds
bit-for-bit from its commit with `scripts/qnx_rebuild_check.py`; between BEFORE and AFTER exactly the three binaries that compile in the
limits change and the other three are byte-identical.

**AI, without AI theatre.** The optional LLM planner never writes the
contract: the model extracts a structured intent, deterministic code checks
units/ranges/ambiguity first and builds the IR from templates, and the same
validation gate applies. Measured with `qwen2.5:7b-instruct` and
`llama3.1:8b-instruct` (CPU, local Ollama): 28/28 on the published eval
with 0 unsafe accepts, and 8/8 (Qwen) on unseen paraphrases where the
keyword planner gets 3/8. On a harder 98-case holdout the models first
scored 87 and 81 with 11-14 accepted-should-refuse cases each — real
failures, fixed deterministically; both models are now rerun post-fix at
98/98 plus 30/30 on a second holdout. Because those sets are
development-touched, a fourth frozen 36-case set is the honest final
word: 32 (Qwen), 31 (Llama), 32 (offline), with every miss a
pre-registered adversarial probe except one Llama overreach (raw logs
`evals/results/2026-11-07-holdout-2models/`,
`evals/results/2026-11-08-finalcode-2models/`,
`evals/results/2026-11-08-v3v4-final/`,
`docs/ascension/AI_EVALUATION.md`). The default remains the offline,
deterministic keyword planner.

## Potential impact

GENESIS RT is a change-verification and evidence layer for teams building
control software on QNX: it complements Momentics and established test
suites (Parasoft, LDRA, VectorCAST) rather than replacing them. The value
we can demonstrate today is technical: reproducible native evidence, a
stale-binary rejection, offline third-party verification. **No pilots or
customer measurements exist yet**; a pilot protocol is in
`docs/business/pilot-study.md`.

## Testing instructions (paste-ready)

Without a QNX SDK (about 5 minutes):

```sh
git clone https://github.com/toskaman/genesis-rt.git && cd genesis-rt
pip install -e ".[dev]"
python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before
python evidence/qnx8-x86_64-w11-after/verify.py evidence/qnx8-x86_64-w11-after
PYTHONPATH=host python scripts/run_verified_demo.py
PYTHONPATH=host python -m genesis_rt.cli serve   # Studio at http://127.0.0.1:8077/
python -m pytest tests/ -q   # 1251 collected; SDK run outcome is per-machine (the 2 axe scans skip without node_modules/axe-core); SDK-less CI: 1245 passed + 6 honest skips (measured 8 Nov 2026) (3 QNX-build + 2 SDK-only codelab + 1 real-build target op)
```

With an SDK: `python scripts/qnx_env_check.py`, then
`docs/quickstart-qnx8-qemu.md` (Windows and Linux path map included).

## Limitations

QEMU only (no real hardware), TCG timing is relative, simulation-only
machines, no safety certification, no hardware attestation, the native CI lane is
build-only (target campaigns run on the author's machine and ship as
evidence packs), and no external user study yet. Full list:
`docs/jury/KNOWN_LIMITATIONS.md`.

## Links

- Start here: `docs/jury/START_HERE.md`
- Canonical numbers: `docs/CLAIMS.md`
- Evidence packs: `evidence/`
- Codelabs: `docs/codelab/README.md`, `docs/codelab/ADVANCED-QNX.md`
- Readiness report: `docs/release/TITAN_FINAL_READINESS.md`
