# Omega3 P1c: security review (residuals triage + local API + deps + rotation + signing)

Date: 8 Nov 2026. Branch: `titan-omega3` @ `bc8abc8` + P1c
working tree. Base: `main` @ `cee9c9d` (PR #11 merged).
Status: REVIEWED — 1 dependency floor raised (verified), 1
prose-drift pin test added, rotation procedure published, no
exploitable trust-boundary defect found, residuals documented.

## Evidence commands (owner machine, Windows, Python 3.14, SDK present)

- `python -m pytest tests/unit/test_docs_consistency.py -q`
  → 37/37 passed, EXIT=0 (8 Nov 2026, includes the new
  `test_security_model_get_inventory_count_current`).
- `python -m pytest tests/integration/test_rebinding_posture.py -q`
  → EXIT=0 (36-route GET inventory pin green).
- `python -m pytest` (full suite) → **1328 passed, 2 skipped,
  0 failures, 329.55s, EXIT=0** (8 Nov 2026; the 2 skips are
  the axe-core scans without `node_modules/axe-core`).
- `pip-audit --format=json --local` → 177 vulns in 27
  environment packages; `cryptography 43.0.3`: 10 vulns,
  highest fix version `49.0.0` (re-run 8 Nov 2026,
  identical totals to the earlier same-day run).
- Throwaway venv with `cryptography 50.0.2`: signing subset
  12/12 green, `pip-audit` reports 0 vulns for
  `cryptography` (8 Nov 2026, prior P1c session).

## §8.1 Residual triage (M1–M5 / M9–M11 / H4–H7 races)

Honest finding first: the M/H identifiers have **no
committed per-ID definitions**. A repo-wide search returns
exactly three mentions, all collective labels with no
reproduction attached:

- `docs/audits/OMEGA2_SECURITY_RELIABILITY.md:25`
  ("M1–M5 / M9–M11 and H4–H7 race conditions: reviewed…
  fixes deferred"),
- `docs/audits/OMEGA2_P0_NATIVE_CORRECTNESS.md:50`
  ("audited but intentionally not fixed"),
- `docs/audits/OMEGA3_BASELINE.md:61` (same collective line).

Per-ID reproduction is therefore impossible: there is no
per-ID claim to reproduce. Claiming "M4 fixed" against an
undefined M4 would be fabrication. Classification:
**unactionable-as-specified** (not Critical/High/Medium —
those ratings require a defined defect).

Substituted fresh surface review (8 Nov 2026, static +
test-pinned, no live target):

- Campaign interleave: `host/genesis_rt/target.py:372`
  raises `TargetBusy("another target op is live")`; stale
  locks fail closed; callers re-raise (`target.py:378-379`,
  `api.py:598`, `runner.py:301`).
- Single-SSH-at-a-time discipline unchanged; the target
  penalty-boxes parallel sessions (rotation doc §4).
- Local API serves one worker
  (`host/genesis_rt/cli.py:320`, `workers=1`); target ops
  serialize through the campaign lock, never overlapping
  SSH sessions.
- Fail-closed gates kept: release eligibility, verify rc,
  evidence gating (external adapter has no gate import —
  pinned by test).

Verdict: no *defined* race defect reproduced; the
concurrency controls above are the audited boundary.
Accepted limitation: a full adversarial concurrency soak
was not re-run in Omega3 (Wave-10/11 era coverage stands).

## §8.2 Local API trust boundary

Reviewed `host/genesis_rt/api.py` guards against the live
source (line refs current at P1c):

- Loopback-only serve: `cli.py:320`
  (`host="127.0.0.1"`, `workers=1`) — the service cannot
  accidentally bind to the LAN.
- Origin guard: `_origin_guard` (`api.py:207`) rejects
  non-loopback `Origin` values (`_loopback_origin`,
  `api.py:147-155`); JSON-only writes die at body
  validation (422) before any job/op exists.
- Payload caps: `MAX_BODY_BYTES` 8 MiB, `MAX_IR_BYTES`
  256 KiB, `MAX_PLAN_BYTES` 256 KiB, `MAX_PASSPORT_TEXT`
  3 MiB, `MAX_SCENARIOS` 32 (`api.py:104-111` + call
  sites) — resource-exhaustion via giant payloads is
  bounded.
- GET inventory re-audit: the prose count drifted (31 vs
  the 36-entry `AUDITED_GET_ROUTES` list). Provenance via
  Wave-8→now diff: 5 routes added, 0 removed
  (`/ipc-timeline`, `/target/ops/compare`,
  `/target/ops/compare/dossier`,
  `/target/ops/{op_id}/decision`,
  `/target/ops/{op_id}/dossier`). All five re-checked
  read-only (op-id validated 400-first, zips built
  in-memory in `dossier.py`, timeline serves a fixed
  committed path with no user input). Fixed by documenting
  36 + adding `test_security_model_get_inventory_count_current`
  so prose and list cannot drift again.
- `Host` header deliberately NOT validated (documented in
  `docs/local-security-model.md` with rationale: with the
  layers above, no browser vector reaches a state change).

Verdict: no exploitable trust-boundary defect found.
Accepted limitation (unchanged from Omega2): the localhost
API has no authentication boundary — it is a local-user
tool, not a multi-user network service. Do not expose it
beyond loopback.

## §8.3 Dependency vulnerability audit

Python (`pip-audit --local`, 8 Nov 2026, fresh re-run):

- Environment-wide: 177 vulns in 27 installed packages.
  Almost all are **not project dependencies** (owner
  machine site-packages); only one project-reachable
  package is affected: `cryptography 43.0.3` (10 vulns).
- Reachability: project use is local-only Ed25519
  sign/verify (`host/genesis_rt/signing.py`) plus TLS via
  `httpx`/`paramiko` transitive use — no remote-attacker
  controlled input reaches crypto primitives directly.
  Still remediated rather than waived.
- Remediation: `pyproject.toml` `dev` floor raised
  `cryptography>=41` → `cryptography>=49`. `49` is the
  **lowest** version clearing all 10 (highest fix version
  in the audit is `49.0.0`), verified in a throwaway venv
  on `50.0.2` (signing 12/12 green, audit 0 vulns) — not
  a blind upgrade. Full 1330 suite green on the owner env
  after the change.
- Owner-env note: the owner machine still has `43.0.3`
  installed (this review changed the declared floor, not
  the owner's global environment); CI installs fresh and
  picks up `>=49` automatically.

JavaScript: the repo contains **no `package.json` and no
committed JS dependencies** (verified by tree search);
`axe-core` is loaded from `node_modules` at test time
only (its absence produces the 2 honest E2E skips).
Nothing committed to audit on the JS side.

## §8.4 QNX password rotation

`docs/security/QNX_PASSWORD_ROTATION.md`: procedure
published, NOT executed. Covers exposure, interactive
change (~10 min), env-only credential update, reconnect +
verify (`probe`/`identity`, port 2222), console-based
failure recovery, and no-logging-of-secrets rules.
Statically verified 8 Nov 2026 that `probe`/`identity`
exist in `scripts/qnx_target.py` with `--ssh-port`
(default 2222) and read `GENESIS_TARGET_PASSWORD` first.
Owner-only action; the image still uses its default
credential configuration.

## §8.5 Signing decision (assessment, not implementation)

Signing already exists: `host/genesis_rt/signing.py`
(Wave 12 §9) implements optional Ed25519
`manifest.sig.json` envelopes with a documented trust
model (origin + integrity-at-rest only, no truth/safety
claim, no trusted timestamping), a pinned-trust-store
verifier, and rotation via `supersedes` + trust-store
update. Assessed against the §8.5 criteria:

- Public-key trust relationship: only meaningful when
  the *verifier* pins a key out-of-band (supported).
- Private-key custody / rotation / revocation: keypair
  generation + unencrypted-PEM custody warning + rotation
  procedure exist; no project-wide key ceremony exists
  for hackathon artifacts.
- Correct-signature validation + exact-pack binding:
  verifier fails closed (`SignatureError` on any error),
  signature covers the canonical envelope body including
  `manifest_sha256` of the stored manifest bytes.

Decision: **keep the official evidence packs hash-only
(UNSIGNED)** and document it. A self-generated ephemeral
key would add no authorship trust a judge could rely on;
signing stays available for teams that pin their own
trust root. No code change; no signature-status claim
changed. `verify-pack --trust local` → UNSIGNED exit 2
remains the expected, documented outcome.

## Accepted residuals (Omega3 P1c)

1. M/H race IDs undefined → unactionable-as-specified;
   concurrency boundary = campaign lock + single worker +
   single-SSH discipline (see §8.1).
2. Localhost API without auth boundary — local-user tool
   only, loopback-bound (see §8.2).
3. Owner machine still on `cryptography 43.0.3` until the
   owner upgrades; declared floor is `>=49`.
4. QNX image on default credentials until the owner runs
   the rotation procedure.
5. No trusted timestamp authority, no hardware
   attestation, no native CI runner (unchanged, honest
   limitations — QEMU remains an accepted target).
6. Official packs hash-only UNSIGNED (deliberate, §8.5).

## Verdict

Safe to demo and to merge via reviewed PR. Not
production-certified; the six residuals above are the
honest boundary. Gate G (security) is satisfied: no
high-severity exploitable issue open, medium residuals
classified, dependency review completed with a verified
remediation, local API trust boundary reviewed, rotation
instructions ready.
