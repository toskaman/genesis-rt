# Reproduce every claim

Prereqs: Python ≥3.12, a C compiler (`cc`/`gcc`/`clang`), `make` optional.
No QNX SDK needed except where marked.

| Claim | Command | Expected |
|---|---|---|
| IR validates strictly | `PYTHONPATH=host python -m genesis_rt.cli validate examples/amr-demo/machine-ir.json` | `valid: amr-demo-01 …` |
| Codegen deterministic | `python -m pytest tests/unit/test_codegen_determinism.py -q` | green |
| Guard denies bad input | `python -m pytest tests/unit/test_guard_policy.py -q` | green |
| C == Python policy | `python -m pytest tests/integration/test_c_conformance.py -q` | green (builds `guard_vector`) |
| 8/8 fault scenarios | `PYTHONPATH=host python -m genesis_rt.cli faults examples/amr-demo/machine-ir.json` | `8/8 scenarios passed` |
| Full demo + passport | `PYTHONPATH=host python scripts/run_verified_demo.py` | `verdict: PASS` |
| Passport replays | `PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json` | `chain: valid`, `gate: PASS` |
| Gate blocks sabotage | `python -m pytest tests/integration/test_pipeline.py tests/acceptance/ -q` | green |
| Whole suite | `python -m pytest tests/ -q` | green + 1 QNX skip |
| QNX SDK probe | `PYTHONPATH=host python scripts/qnx_env_check.py` | JSON, `sdk_present` honest |
| **QNX native build (needs SDK)** | `source ~/qnx800/qnxsdp-env.sh` then generate + `make -f genesis_build_gen.mk qnx` | 5 `genesis_*` binaries |
| **QNX run (needs SDK+QEMU)** | on target: `./genesis_supervisor` | ALLOW/DENY log lines |

`PYTHONPATH=host` is unnecessary after `pip install -e .`.
