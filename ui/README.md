# UI (static, dependency-free)

Open the pages directly in a browser (`file://` works, script tags
only — no `fetch`, no network, no build step).

- `dashboard.html`: Proof Passport inspector. Load a `passport.json`;
  the hash chain is re-verified live and a stored PASS is shown only
  when valid.
- `studio.html`: six-tab workspace — Intent (IR + live sha256),
  Source (generated C provenance pinned vs the IR), Twin (canvas
  trace replay), Lab (scenario/seeds/checks), Passport (same live
  verification as the dashboard), Diff (broken-vs-fixed delta),
  Run (exact pipeline commands).
  Every tab loads real artifacts from disk; Lab/Twin stay empty
  unless the passport chain verifies.
- `genesis_verify.js`: shared pure core (SHA-256, raw JSON,
  canonical form, chain verify, escaping), node-tested from
  `tests/ui/test_dashboard_verify.py` against the Python toolchain.

Nothing here executes a pipeline or a target run: run the commands
from the Run tab, then drop the fresh outputs back into the tabs.
