# GENESIS RT — The Physical World Compiler

**From human intent to tested QNX-native machine software.**

GENESIS RT generates inspectable evidence about the behavior of
the code — a requirement change goes in, a verdict anyone can
re-verify offline comes out.

> **30-second cold start** (no SDK, no QNX target) — product-time budget:
> `pip install -e .` (one-time setup, unmeasured) →
> `genesis-rt validate examples/cell-demo/cell-ir.json` →
> `genesis-rt demo --ir examples/cell-demo/cell-ir.json`
> (PASS verdict + offline passport in ~2 s of product runtime after setup;
> install/clone/first-boot excluded — see `docs/jury/REPRODUCE.md`).

[![host-ci](https://github.com/toskaman/genesis-rt/actions/workflows/host-ci.yml/badge.svg)](https://github.com/toskaman/genesis-rt/actions/workflows/host-ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> Status: functional alpha for the [QNX Global Hackathon](https://qnx.devpost.com/)
> (Developer Tooling & Host Tools), built 4 Nov 2026 onward. Host verification
> is fully working; QNX on-target execution is verified (native `qcc`
> build with 0 warnings, 16/16 on-target matrix, `qnx_verified: true`).
> QEMU x86_64 only — no physical hardware. No safety certification is claimed.
> Human benefit is not yet measured (no pilots run).

![GENESIS RT Studio overview: one requirement change verified natively twice, with archived BEFORE/AFTER/stale-binary proof cards](docs/ascension/screens/after-light-1440.png)

## 60-second pitch

Embedded control prototypes are slow to build and their test evidence is
usually a pile of screenshots. GENESIS RT turns a **constrained machine
description** into a **typed, inspectable specification (Machine IR)**,
generates a **native QNX 8.0 multi-process controller**, runs it, breaks it
on purpose with **seeded fault injection**, and produces a **hash-linked
evidence passport** where every green verdict links to a real execution
trace. One convincing proof-driven demo beats twenty speculative features.

## What's proven

- **Contract-aware native verification (current source)**: the
  Omega2 BEFORE/AFTER pair
  (`evidence/qnx8-x86_64-omega2-before/`,
  `evidence/qnx8-x86_64-omega2-after/`) verifies one valid
  requirement change natively twice — AMR v1 → v2 guarded
  safe-stop transitions, 16/16 PASS sealed on both contracts,
  and a stale control failing 14/16 exactly on the changed
  behavior (operator-recorded negative control — prose-grade,
  no sealed transcript ships in the packs). Verify offline
  with no SDK:
  `python evidence/qnx8-x86_64-omega2-after/verify.py evidence/qnx8-x86_64-omega2-after`.
- **Native IPC execution timeline** from real QNX `CLOCK_MONOTONIC`
  timestamps (`evidence/ipc-timeline/`).
- **CI IR impact bridge** (`scripts/ci_ir_check.py`): changed-IR
  validation and impact reports on every push/PR.
- **Professional review dossier**: one-click ZIP export (report +
  raw data + offline verify) from any target operation.
- **Historical proof** (7 Nov 2026, superseded for current claims):
  limit change 1.2 → 1.6 m/s flipping the 1.5 m/s probe
  DENY → ALLOW, three BEFORE/AFTER packs
  (`evidence/qnx8-x86_64-w11-before/`, `...-after/`,
  `...-after-rerun/`), 15-link passport chains, tamper control,
  18/18 bit-for-bit `qcc` rebuilds.
- **Final submission video: DEFERRED BY OWNER.** The historical cut
  `docs/demo/genesis-rt-demo-w12.mp4` (154.664 s) predates the current
  Studio and is **not** the final video; see `submission/VIDEO_DEFERRED.md`.

Canonical numbers live in [docs/CLAIMS.md](docs/CLAIMS.md).

## AI planner: measured, not marketed

Latest blind holdout **v10** (184 cases, 48 valid + 136 reject,
agent-authored against contract v1.3 + failure classes only, frozen
before the v1.4 code): offline **159/184**, Qwen 2.5 7B and Llama
3.1 8B **165/184** each — **15 unsafe accepts of 136** reject cases
(same 15 deterministic-layer cases on all providers), **0 wrong-kind
accepts**, 29 of 26 expected model consults per model (0 missing,
3 explained mismatches). v9/v10 unsafe rates are NOT comparable
(harder instrument). A consultation audit
(`docs/audits/OMEGA5_CONSULTATION_AUDIT.md`) pins the v7/v8
expectation mismatches, and the harness now enforces
`expect_consult` per case. The model proposes; the deterministic
validator decides. Full per-case raws: `evals/results/2026-11-10-omega7-v10/`;
report: [docs/audits/OMEGA7_AI_EVALUATION.md](docs/audits/OMEGA7_AI_EVALUATION.md).

## Architecture

```
[CLI / Web API / GENESIS Studio]        genesis-rt demo
         |
[Planner] -> [Machine IR v1 | v2] -> [strict per-version VALIDATION]
             (AMR, conveyor,               |
              industrial cell)   [Deterministic codegen v1 / v2]
                                           |
                       [Multi-build provenance: host mirror + qcc x86_64]       
                                           |
                                 [QNX 8.0 target (QEMU)]
                                  guard/controller/device/status/
                                  supervisor/faultinject/cellcheck
                                  (C, native MsgSend/MsgReceive/MsgReply)
                                           |
[Simulator + Fault Lab] <-- host mirror --> [16-step target matrix + traces]
         |
[Compare: broken vs fixed]
         |
[Evidence passport + fail-closed release gate]
```

See [docs/architecture.md](docs/architecture.md).

## Quickstart (no QNX SDK needed)

```sh
git clone https://github.com/toskaman/genesis-rt.git
cd genesis-rt
pip install -e '.[dev]'        # or: PYTHONPATH=host
python -m pytest tests/ -q     # host suite, incl. C/Python conformance
python scripts/run_verified_demo.py
python scripts/replay.py artifacts/runs/*/passport.json
```

(With several runs present, pass the exact passport path the demo
printed instead of the glob.)

Then start the live workbench (`genesis-rt serve`) and open
http://127.0.0.1:8077/ — Studio Live: projects with
revision history, a Machine IR designer with state graphs, and an SSE
pipeline runner (validate → generate → run → passport → diff), plus the
trace/passport/diff inspectors. `ui/dashboard.html` stays a dependency-free
passport inspector that also works straight from disk.

Full install reference (prerequisites, Windows + Linux, environment
variables, troubleshooting, uninstall): [docs/INSTALL.md](docs/INSTALL.md).

With a QNX SDP 8.0 SDK installed: [docs/quickstart-qnx8-qemu.md](docs/quickstart-qnx8-qemu.md)
(`scripts/qnx_env_check.py` probes your setup; without an SDK the pipeline
records QNX steps as `blocked`, never as passed).

## Commands

| Command | What it does |
|---|---|
| `genesis-rt validate <ir>` | strict Machine IR validation |
| `genesis-rt plan "<request>"` | constrained intent → validated IR proposal |
| `genesis-rt generate <ir> --out <dir>` | deterministic QNX C build files |
| `genesis-rt simulate <ir> [--scenario id]` | nominal (or named) scenario for AMR / conveyor / cell, v1 or v2 |
| `genesis-rt faults <ir>` | declared fault campaign with oracles (AMR 8, conveyor 5, cell 4) |
| `genesis-rt demo` | full pipeline → evidence passport + gate verdict |
| `genesis-rt verify-change --before A --after B` | BEFORE/AFTER in one step → `verdict.json` card |
| `genesis-rt demo-break` | seal → mutate → STALE refusal in seconds |
| `genesis-rt quickstart [--example cell]` | validate + run + card in one command |
| `genesis-rt watch <ir> [--once]` | re-validate on every save, 1-line verdict |
| `genesis-rt new --kind cell --id ID --out FILE` | first Machine IR from an example, validated |
| `genesis-rt external-write-manifest` | hash an existing build dir into a manifest |
| `genesis-rt external-check` | stale-binary check of a build dir vs its manifest |
| `genesis-rt check-env` | probe for QNX SDK toolchain |
| `genesis-rt serve` | local web API (needs `api` extra) |

## QNX evidence for judges

- Native IPC: `target/qnx8/guard` + `controller` (`name_attach`/`MsgReceive`/
  `MsgReply`/`MsgSend`), fixed protocol in `target/qnx8/include/genesis_ipc.h`.
- Resource manager `/dev/genesis/status`, supervisor with reset authority.
- Shared guard policy proven identical in C and Python by
  `tests/integration/test_c_conformance.py` via `guard_vector`.
- Codelabs: [native IPC controller in 45 min](docs/codelab/README.md),
  [advanced QNX deep-dive](docs/codelab/ADVANCED-QNX.md),
  [stale-binary detection for your own build in 15 min](docs/codelab/EXTERNAL-BUILD.md).
- Start here: [docs/jury/START_HERE.md](docs/jury/START_HERE.md).

## Honest known limitations

- Host fault results are **simulated**; QNX on-target runs are verified by
  the authors (16/16 matrix) and reproducible with an SDK + QEMU setup
  ([docs/PROGRESS.md](docs/PROGRESS.md)).
- QEMU timing is for regression comparison, not production guarantees.
- Prototype only: no functional-safety qualification, simulation-only outputs.
- Full detail: [docs/limitations-and-safety.md](docs/limitations-and-safety.md).

## FAQ

**Is this original work?** Yes — created during the hackathon entry period for
this submission; see [docs/jury/COMPLIANCE.md](docs/jury/COMPLIANCE.md).

**Why Apache-2.0?** The project brief asked to match the OpenBridge license if
possible. The referenced OpenBridge project uses PolyForm Strict 1.0.0, which
is not an open-source license and would violate the Devpost requirement for a
public open-source repository — so Apache-2.0 (OSI-approved, GitHub-detectable,
also the license the OpenBridge design system converges to) was chosen instead.
Details in [docs/jury/COMPLIANCE.md](docs/jury/COMPLIANCE.md).

**Does the gate ever pass without tests?** No — `no-test => no-pass` is tested
(`tests/unit/test_evidence_gate.py`): missing, skipped, crashed or tampered
evidence always yields FAIL.

## License

Apache-2.0, see [LICENSE](LICENSE).
