# GENESIS RT — The Physical World Compiler

**From human intent to tested QNX-native machine software.**

GENESIS RT generates inspectable evidence about the behavior of
the code — a requirement change goes in, a verdict anyone can
re-verify offline comes out.

**In plain words:** you describe a machine (a mobile robot, a conveyor,
a robot cell) in one JSON file. GENESIS RT generates its QNX 8.0
controller in C, runs it, breaks it on purpose with injected faults,
and seals what happened into a file a reviewer can re-check on their
own laptop — no SDK and no trust in the author required. Change one
requirement and it shows which behavior changed, and it refuses a
binary that was not rebuilt.

**Try it in 30 seconds** (Python ≥ 3.12; no QNX SDK, no target):

```sh
git clone https://github.com/toskaman/genesis-rt.git && cd genesis-rt
pip install -e .
genesis-rt demo --ir examples/cell-demo/cell-ir.json      # 4 fault scenarios -> verdict: PASS + passport
genesis-rt demo-break                                      # tamper with a sealed binary -> STALE, refused
python evidence/t10-causal-live-dossier/verify_causal.py   # re-check a real QNX 8.0 run offline -> VERIFY OK
```

Each command returns in about a second of product runtime (clean
Linux clone, Python 3.13, 13 Nov 2026: `demo` 0.4 s; clone and
install excluded — see `docs/jury/REPRODUCE.md`). Without an SDK the
demo reports `qnx_verified: False`, never a QNX pass; the native QNX
runs are the sealed packs under `evidence/`.

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

Each item is a file you can re-check yourself. Canonical numbers live
in [docs/CLAIMS.md](docs/CLAIMS.md); the four judging criteria are
mapped to files in
[docs/jury/CRITERIA_EVIDENCE.md](docs/jury/CRITERIA_EVIDENCE.md).

- **Contract-aware native verification**: one requirement change — a
  mobile robot gains guarded safe-stop transitions (contract v1 → v2)
  — verified natively on QNX 8.0 twice. 16/16 PASS sealed on both
  contracts, and a stale control failing 14/16 exactly on the changed
  behavior (operator-recorded negative control — prose-grade, no
  sealed transcript ships in the packs). Packs:
  `evidence/qnx8-x86_64-omega2-before/`,
  `evidence/qnx8-x86_64-omega2-after/`. Verify offline with no SDK:
  `python evidence/qnx8-x86_64-omega2-after/verify.py evidence/qnx8-x86_64-omega2-after`.
- **Incident → cause, grounded live on QNX** (12 Nov 2026):
  `genesis-rt causal-repro --target live` turned a "cell halts,
  ESTOP latched" incident into a sealed dossier in one command. The
  host reproduction ranks the emergency-stop hypothesis first, and
  one hermetic native run on the cell's own `qcc` binaries passed
  16/16 on QNX 8.0 (`qnx_verified=True`), its `estop_target`
  transcript hash-bound into the dossier (234 s, n=1, QEMU TCG).
  Verify offline:
  `python evidence/t10-causal-live-dossier/verify_causal.py`.
- **Native IPC execution timeline** from real QNX `CLOCK_MONOTONIC`
  timestamps (`evidence/ipc-timeline/`).
- **Contract changes checked in CI** (`scripts/ci_ir_check.py`):
  validation and an impact report on every push and pull request.
- **Professional review dossier**: one-click ZIP export (report +
  raw data + offline verify) from any target operation.
- **Earlier proof** (7 Nov 2026, superseded for current claims): a
  speed limit raised from 1.2 to 1.6 m/s flips the 1.5 m/s probe
  from DENY to ALLOW; three BEFORE/AFTER packs
  (`evidence/qnx8-x86_64-w11-before/`, `...-after/`,
  `...-after-rerun/`), 15-link passport chains, tamper control,
  18/18 bit-for-bit `qcc` rebuilds.
- **Final submission video: DEFERRED BY OWNER.** All cuts WITHDRAWN
  2026-11-12 for an owner remake — no video file is shipped;
  see `submission/VIDEO_DEFERRED.md`.

## AI planner: measured, not marketed

Free text can be turned into a machine contract by a local model, but
the model only proposes: the same deterministic validator decides,
and anything it cannot prove safe is rejected.

Latest blind holdout (184 cases: 48 valid, 136 that must be
rejected; written by an AI agent from the contract and its failure
classes only, frozen before the code they test): offline rules
**159/184**, Qwen 2.5 7B and Llama 3.1 8B **165/184** each. **15
unsafe accepts of 136** reject cases — the same 15 on every provider,
all in the deterministic layer — and **0 wrong-kind accepts**. Each
model was consulted 29 times against 26 expected (0 missing, 3
unexpected, each explained). Results across holdout versions are not
comparable (each one is a harder instrument).

Per-case raw results: `evals/results/2026-11-10-omega7-v10/`;
report: [docs/audits/OMEGA7_AI_EVALUATION.md](docs/audits/OMEGA7_AI_EVALUATION.md);
consultation audit: `docs/audits/OMEGA5_CONSULTATION_AUDIT.md`.

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

Expect green. How many tests run depends on what is installed, and
every skip names its reason: `.[dev]` alone runs everything except
the real-browser lane (clean Linux clone, Python 3.13, 13 Nov 2026:
1577 passed, 14 skipped); the full pinned total needs
`pip install -e '.[dev,e2e]'` plus `python -m playwright install chromium`,
as CI does. A missing QNX SDK is a skip, never a QNX pass.

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

Four commands carry the product:

| Command | What it does |
|---|---|
| `genesis-rt demo` | full pipeline → evidence passport + gate verdict |
| `genesis-rt verify-change --before A --after B` | BEFORE/AFTER in one step → `verdict.json` card |
| `genesis-rt causal-repro --incident FILE` | incident → hypotheses → sealed causal dossier |
| `genesis-rt demo-break` | seal → mutate → STALE refusal in seconds |

<details>
<summary>All other commands</summary>

| Command | What it does |
|---|---|
| `genesis-rt validate <ir>` | strict Machine IR validation |
| `genesis-rt plan "<request>"` | constrained intent → validated IR proposal |
| `genesis-rt generate <ir> --out <dir>` | deterministic QNX C build files |
| `genesis-rt simulate <ir> [--scenario id]` | nominal (or named) scenario for AMR / conveyor / cell, v1 or v2 |
| `genesis-rt faults <ir>` | declared fault campaign with oracles (AMR 8, conveyor 5, cell 4) |
| `genesis-rt causal-fix --dossier DIR --after-ir FILE` | fix proof appended + dossier resealed |
| `genesis-rt quickstart [--example cell]` | validate + run + card in one command |
| `genesis-rt watch <ir> [--once]` | re-validate on every save, 1-line verdict |
| `genesis-rt new --kind cell --id ID --out FILE` | first Machine IR from an example, validated |
| `genesis-rt external-write-manifest` | hash an existing build dir into a manifest |
| `genesis-rt external-check` | stale-binary check of a build dir vs its manifest |
| `genesis-rt check-env` | probe for QNX SDK toolchain |
| `genesis-rt serve` | local web API (needs `api` extra) |

</details>

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
  ([docs/quickstart-qnx8-qemu.md](docs/quickstart-qnx8-qemu.md)).
- QEMU timing is for regression comparison, not production guarantees.
- Prototype only: no functional-safety qualification, simulation-only outputs.
- Full detail: [docs/limitations-and-safety.md](docs/limitations-and-safety.md).

## FAQ

**Is this original work?** Yes — created during the hackathon entry period for
this submission; see [docs/jury/COMPLIANCE.md](docs/jury/COMPLIANCE.md).

**Why Apache-2.0?** The hackathon requires a public repository under an
open-source license that the hosting site detects. Apache-2.0 is
OSI-approved, shows in this repository's About box, and carries a patent
grant. Details in [docs/jury/COMPLIANCE.md](docs/jury/COMPLIANCE.md).

**Does the gate ever pass without tests?** No — `no-test => no-pass` is tested
(`tests/unit/test_evidence_gate.py`): missing, skipped, crashed or tampered
evidence always yields FAIL.

## License

Apache-2.0, see [LICENSE](LICENSE).
