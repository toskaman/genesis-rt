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
| Whole suite | `python -m pytest tests/ -q` | green, 1166 tests (all run w/ SDK; SDK-free 7 Nov 2026: 1161 + 5 honest skips: 3 QNX-build + 1 SDK-only codelab + 1 real-build target op; +1 cksum-conformance where coreutils is absent) |
| QNX SDK probe | `PYTHONPATH=host python scripts/qnx_env_check.py` | JSON, `sdk_present` honest |
| **QNX native build (needs SDK)** | `source ~/qnx800/qnxsdp-env.sh` then generate + `make -f genesis_build_gen.mk qnx` | 6 `genesis_*` binaries per machine build (7 for cell: + `genesis_cellcheck`), 0 warnings (9 staged on target: bound set + `genesis_guard_conv` + `genesis_guard_v2`) |
| **QNX run (needs SDK+QEMU)** | `python scripts/qnx_target.py put <bins>` then `verify` | 16/16 matrix PASS, `qnx_verified: true` |
| Native BEFORE/AFTER packs (no SDK, canonical) | `python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before` then the same for `qnx8-x86_64-w11-after` | both `VERIFY OK`, 16/16, 1000 samples; 1.5 m/s probe DENY (1.2 limit) → ALLOW (1.6 limit), see `evidence/w11-before-after/COMPARISON.md` |
| Legacy native pack (historical, b22cea1) | `python evidence/qnx8-x86_64-verified-b22cea1/verify.py` | `VERIFY OK`, 16/16 (kept as historical record) |

`PYTHONPATH=host` is unnecessary after `pip install -e .`.

