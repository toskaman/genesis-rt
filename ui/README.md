# UI (dependency-free pages + live backend)

Start the workbench:

```sh
PYTHONPATH=host python -m genesis_rt.cli serve   # http://127.0.0.1:8077/
```

- `studio.html`: Studio Live. Projects (create/import/examples/save/
  duplicate/history/diff/export), Designer (JSON editor, authoritative
  backend validation, read-only v2 state graph, error locate), Pipeline
  (example/project → scenarios → SSE-streamed run → generated files →
  passport → diff), plus the file-based inspectors: Source (generated C
  provenance pinned vs the IR), Twin (canvas trace replay), Lab
  (scenario/seeds/checks), Passport (live chain re-verification),
  Diff (broken-vs-fixed delta), Run (exact CLI/target commands).
  Without the backend, Projects/Designer/Pipeline show an offline
  banner while the six inspector tabs keep working on local files.
- `dashboard.html`: Proof Passport inspector. Load a `passport.json`;
  the hash chain is re-verified live and a stored PASS is shown only
  when valid. Works straight from disk (`file://`).
- `genesis_verify.js`: shared pure core (SHA-256, raw JSON,
  canonical form, chain verify, escaping), node-tested from
  `tests/ui/test_dashboard_verify.py` against the Python toolchain
  together with the Studio render/reducer core.

No build step, no npm, no mock runs: every verdict is recomputed
from real artifacts, and every pipeline step executes the same
orchestrator the CLI uses.
