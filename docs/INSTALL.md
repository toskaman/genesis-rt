# Installing GENESIS RT

Tested hosts: Windows 10/11 (dev box) and Linux (Ubuntu 22.04 via
`host-ci`, which is a fresh clone + full suite on every push).
macOS is untested — the pure-Python path should work, the QNX
target loop is not covered there.

No installer, no services, no registry keys: a git clone plus a
virtualenv. Everything runs locally; nothing phones home.

## Prerequisites

| Need | Notes |
|---|---|
| Python 3.12+ | `pyproject.toml` requires `>=3.12`; check with `python --version` |
| git, pip | any recent version |
| A C compiler | `cc`, `gcc`, or `clang` on `PATH` — needed only for the host C conformance checks and the `generate` benchmark lane (`build_adapter.py`, `explorer_conformance.py` probe in that order); the pure-Python suite runs without one |
| QNX SDP 8.0 | OPTIONAL — host-only mode is fully functional without it; without an SDK the pipeline records QNX steps as `blocked`, never as passed |
| QEMU | OPTIONAL — only for the native target loop (`qemu-system-x86_64` on `PATH`) |
| Chromium | OPTIONAL — only for the real-browser E2E tests (`python -m playwright install chromium`, as CI does) |

## Install (both platforms)

```sh
git clone https://github.com/toskaman/genesis-rt.git
cd genesis-rt
python -m venv .venv
# Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

`.[dev]` is `pytest, pyyaml, fastapi, uvicorn, httpx, jsonschema`
(see `pyproject.toml`). The API server needs the `fastapi` /
`uvicorn` pair (`genesis-rt serve` fails with an actionable
message without them).

## Verify the install

```sh
python -m pytest tests/unit -q          # fast host subset
python scripts/run_verified_demo.py     # end-to-end host pipeline
python scripts/replay.py artifacts/runs/*/passport.json
PYTHONPATH=host python -m genesis_rt.cli check-env   # QNX probe
```

`check-env` reports what it finds (SDK toolchain, QEMU) and marks
missing pieces `blocked`. A green unit subset + a verified demo
passport means the install is good.

## Run

```sh
PYTHONPATH=host python -m genesis_rt.cli serve   # Studio API
```

Then open http://127.0.0.1:8077/ (`--port` overrides the default
8077). For the native target loop, continue with
[docs/quickstart-qnx8-qemu.md](quickstart-qnx8-qemu.md).

Useful next commands: `genesis-rt validate|generate|faults|demo`,
`genesis-rt bench --out DIR` (productivity benchmark, see
`bench/productivity/METHODOLOGY.md`).

## Environment variables

Only one is ever required, and only for the native target loop:

- `GENESIS_TARGET_PASSWORD` — target SSH password, read by
  `scripts/qnx_target.py`. Prefer it over `--password` so the
  secret never lands in shell history. It is never written to
  passports, dossiers, or the evidence pack.

QNX SDK layout (`QNX_HOST`, `QNX_TARGET`, `QNX_CONFIGURATION`)
follows your SDP installation; GENESIS RT probes the toolchain
with `shutil.which("qcc")` plus the standard variables and tells
you what is missing instead of guessing.

## Security model

Local developer tool: localhost-only API with same-origin/Host
protections, allowlisted target operations (no generic shell for
the browser), bounded job queues. Details and trust assumptions:
[docs/local-security-model.md](local-security-model.md).

## Troubleshooting

- `qcc not found` / QNX steps `blocked` → expected without an
  SDK; host-only mode still runs everything else. See
  [docs/quickstart-qnx8-qemu.md](quickstart-qnx8-qemu.md).
- `No module named genesis_rt` → activate the venv, or run with
  `PYTHONPATH=host` / `pip install -e .` from the repo root.
- `serve` fails on import → `pip install -e ".[api]"` (fastapi +
  uvicorn).
- Browser E2E failures → `python -m playwright install chromium`
  (CI runs the same step).
- Stale `artifacts/runs/*` confusing a diff → runs are
  git-ignored scratch; delete the ones you do not need (see
  [docs/retention-and-cleanup.md](retention-and-cleanup.md)).

## Uninstall

```sh
pip uninstall genesis-rt
cd .. && rm -rf genesis-rt .venv   # or Remove-Item on Windows
```

Runs, caches, and virtualenvs live inside the clone (plus your
`.venv`); removing both removes everything. No system-wide state
is created.
