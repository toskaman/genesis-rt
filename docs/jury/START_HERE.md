# Judges: start here (5 minutes)

GENESIS RT turns a constrained machine description into a native QNX 8.0
controller plus a hash-linked evidence passport. Category: **Developer
Tooling & Host Tools**. Everything below runs without a QNX SDK; the SDK
path is verified by the authors (native `qcc` build + on-target 16/16 matrix)
and reproducible per `docs/quickstart-qnx8-qemu.md`. Without an SDK the
suite reports QNX steps as blocked/skipped, never as passed.

## 1. Fastest proof (2 min)

```sh
git clone https://github.com/toskaman/genesis-rt.git && cd genesis-rt
pip install pytest pyyaml          # only test deps; core is stdlib-only
PYTHONPATH=host python scripts/run_verified_demo.py
PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json
```

Expect: `verdict: PASS`, `qnx_verified: false`, `chain: valid`, `gate: PASS`.
Open `ui/dashboard.html`, load the passport, and every verdict links to data.
On Windows PowerShell, prefix the two commands with
`$env:PYTHONPATH='host';` instead of `PYTHONPATH=host`.

## 2. Full test suite (3 min)

```sh
python -m pytest tests/ -q
```

Expect green (1251 tests, SDK outcome per-machine;
SDK-free, 8 Nov 2026: 1245 passed + 6 honest skips — 3 QNX-build + 2 SDK-only codelab + 1 real-build target op — without an
SDK; +1 cksum-conformance where coreutils is absent). With an SDK the
QNX build test compiles the 6 native binaries per machine build for
real (7 for the cell, 9 staged on target: bound set +
`genesis_guard_conv` + `genesis_guard_v2`); without one it reports
an honest skip — never a QNX pass.

## 3. What to read next

- `REPRODUCE.md` — reproduce every claim step by step.
- `TECHNICAL_EVIDENCE.md` — where each QNX/honesty claim lives in code.
- `KNOWN_LIMITATIONS.md` — what we do NOT claim.
- `COMPLIANCE.md` — rules checklist, license decision, original-work note.
- `DEMO_WALKTHROUGH.md` — the three demo paths with exact outputs.
- `WHY_QNX.md` / `WHY_GENESIS_RT.md` — the two one-page pitches.
- `JUDGE_SCORECARD.md` — internal self-assessment with evidence links.

## 4. QNX-native substance (no SDK needed to inspect)

- `target/qnx8/include/genesis_ipc.h` — fixed protocol (magic/version/seq).
- `target/qnx8/guard`, `controller` — native `MsgReceive`/`MsgReply`/`MsgSend`.
- `target/qnx8/status` — `/dev/genesis/status` resource manager.
- `target/qnx8/common/guard_policy.c` — shared policy, proven identical to
  the Python mirror by `tests/integration/test_c_conformance.py`.

