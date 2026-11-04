# Judges: start here (5 minutes)

GENESIS RT turns a constrained machine description into a native QNX 8.0
controller plus a hash-linked evidence passport. Category: **Developer
Tooling & Host Tools**. Everything below runs without a QNX SDK; the SDK
path is documented and honestly reported as pending.

## 1. Fastest proof (2 min)

```sh
git clone https://github.com/toskaman/genesis-rt.git && cd genesis-rt
pip install pytest pyyaml          # only test deps; core is stdlib-only
PYTHONPATH=host python scripts/run_verified_demo.py
PYTHONPATH=host python scripts/replay.py artifacts/runs/*/passport.json
```

Expect: `verdict: PASS`, `qnx_verified: false`, `chain: valid`, `gate: PASS`.
Open `ui/dashboard.html`, load the passport, and every verdict links to data.

## 2. Full test suite (3 min)

```sh
python -m pytest tests/ -q
```

Expect green with exactly one skip: `test_qnx_build` (needs a real SDK —
a skip is reported as a skip, never as a QNX pass).

## 3. What to read next

- `REPRODUCE.md` — reproduce every claim step by step.
- `TECHNICAL_EVIDENCE.md` — where each QNX/honesty claim lives in code.
- `KNOWN_LIMITATIONS.md` — what we do NOT claim.
- `COMPLIANCE.md` — rules checklist, license decision, original-work note.

## 4. QNX-native substance (no SDK needed to inspect)

- `target/qnx8/include/genesis_ipc.h` — fixed protocol (magic/version/seq).
- `target/qnx8/guard`, `controller` — native `MsgReceive`/`MsgReply`/`MsgSend`.
- `target/qnx8/status` — `/dev/genesis/status` resource manager.
- `target/qnx8/common/guard_policy.c` — shared policy, proven identical to
  the Python mirror by `tests/integration/test_c_conformance.py`.
