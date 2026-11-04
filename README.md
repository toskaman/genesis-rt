# GENESIS RT — The Physical World Compiler

**From human intent to tested QNX-native machine software.**

[![host-ci](https://github.com/toskaman/genesis-rt/actions/workflows/host-ci.yml/badge.svg)](https://github.com/toskaman/genesis-rt/actions/workflows/host-ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> Status: functional alpha for the [QNX Global Hackathon](https://qnx.devpost.com/)
> (Developer Tooling & Host Tools), built 4 Nov 2026 onward. Host verification
> is fully working; QNX on-target execution is verified (native `qcc`
> build with 0 warnings, 6/6 on-target matrix, `qnx_verified: true`).
> No safety certification is claimed.

## 60-second pitch

Embedded control prototypes are slow to build and their test evidence is
usually a pile of screenshots. GENESIS RT turns a **constrained machine
description** into a **typed, inspectable specification (Machine IR)**,
generates a **native QNX 8.0 multi-process controller**, runs it, breaks it
on purpose with **seeded fault injection**, and produces a **hash-linked
evidence passport** where every green verdict links to a real execution
trace. One convincing proof-driven demo beats twenty speculative features.

## Architecture

```
[CLI / Web API / dashboard]        genesis-rt demo
         |
[Planner] -> [Machine IR v1] -> [VALIDATION] -> [Deterministic codegen]
                                                        |
                                              [QNX 8.0 target (QEMU)]
                                               guard/controller/device/
                                               status/supervisor/faultinject
                                               (C, native MsgSend/MsgReceive)
                                                        |
[Simulator + Fault Lab] <-- host mirror --> [Telemetry + traces]
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

Then open `ui/dashboard.html` in a browser and load the passport.

With a QNX SDP 8.0 SDK installed: [docs/quickstart-qnx8-qemu.md](docs/quickstart-qnx8-qemu.md)
(`scripts/qnx_env_check.py` probes your setup; without an SDK the pipeline
records QNX steps as `blocked`, never as passed).

## Commands

| Command | What it does |
|---|---|
| `genesis-rt validate <ir>` | strict Machine IR validation |
| `genesis-rt plan "<request>"` | constrained intent → validated IR proposal |
| `genesis-rt generate <ir> --out <dir>` | deterministic QNX C build files |
| `genesis-rt simulate <ir>` | nominal 2D run |
| `genesis-rt faults <ir>` | 8-scenario fault campaign with oracles |
| `genesis-rt demo` | full pipeline → evidence passport + gate verdict |
| `genesis-rt check-env` | probe for QNX SDK toolchain |
| `genesis-rt serve` | local web API (needs `api` extra) |

## QNX evidence for judges

- Native IPC: `target/qnx8/guard` + `controller` (`name_attach`/`MsgReceive`/
  `MsgReply`/`MsgSend`), fixed protocol in `target/qnx8/include/genesis_ipc.h`.
- Resource manager `/dev/genesis/status`, supervisor with reset authority.
- Shared guard policy proven identical in C and Python by
  `tests/integration/test_c_conformance.py` via `guard_vector`.
- Start here: [docs/jury/START_HERE.md](docs/jury/START_HERE.md).

## Honest known limitations

- Host fault results are **simulated**; QNX on-target runs are verified by
  the authors (6/6 matrix) and reproducible with an SDK + QEMU setup
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
