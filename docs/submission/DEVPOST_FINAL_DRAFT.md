# Devpost FINAL Draft (prepared 8 Nov 2026, NOT submitted)

> `SUBMISSION_STATUS = PENDING_FINAL_VIDEO`. The owner
> completes the form and submits. Video:
> `DEFERRED_BY_OWNER`. This draft supersedes
> `docs/devpost-draft.md` (working draft, kept for history).

## Form fields

- **Title:** GENESIS RT — The Physical World Compiler
- **Tagline:** From machine intent to QNX-native software —
  with verifiable proof.
- **Category:** Developer Tooling & Host Tools
  ("tools that make building for QNX easier, on the host
  or on the target").
- **Repository:** https://github.com/toskaman/genesis-rt
- **Codelab / tutorial URL (bonus box):**
  https://github.com/toskaman/genesis-rt/blob/main/docs/codelab/README.md
- **Video URL:** PENDING — owner publishes the final cut
  (public YouTube, strictly under 3:00) then pastes the
  link. Storyboard:
  `docs/submission/VIDEO_STORYBOARD_DEFERRED.md`.

## Inspiration

When a requirement changes on embedded control software —
say a mobile robot's controller gains a guarded safe-stop
transition (AMR v1 → v2) — teams must answer three
questions before shipping: did the code actually change,
does the binary on the target match the new requirement,
and can someone else check the evidence without trusting
us? In practice the answers live in chat logs and people's
heads. GENESIS RT makes the answer a file anyone can
verify offline.

## What it does

1. **Specify** — a machine is described as a strictly
   validated Machine IR contract (fixed kinds, units,
   limits, safety contracts; unknown input is rejected,
   never guessed). Optional AI planning turns free text
   into that contract — only through the same gate.
2. **Compile** — deterministic codegen emits QNX C build
   files with hashed provenance; identical IR always
   yields byte-identical source.
3. **Run natively** — `qcc` builds six QNX processes that
   run on QNX 8.0 (QEMU x86_64): guard server, periodic
   controller, device endpoint, `/dev/genesis/status`
   resource manager, supervisor, fault-injection client.
4. **Break** — an 8-scenario fault lab on the host and a
   16-check on-target matrix including 9/9 native
   fault-injection checks over real IPC.
5. **Prove** — a hash-linked evidence passport and a
   fail-closed release gate; missing, skipped, crashed or
   tampered evidence yields FAIL. Packs verify offline
   with a stdlib-only `verify.py`.
6. **Explain** — GENESIS Studio (local web UI) with a
   guided tour, a before/after view, an evidence graph, a
   release-decision panel in plain language, light/dark
   themes, keyboard access, and an automated WCAG 2.2
   scan in CI (full screen-reader verification
   outstanding — disclosed, not claimed).

## How we built it

Machine IR → strict validation → deterministic codegen →
`qcc` build with binary digests → staged to the QNX
target over SSH → contract-aware native oracle (expected
ALLOW / DENY / SAFE_STOP derived from the validated IR,
not hard-coded) → transcripts sealed into a 15-link
passport bound to the IR digest and op id → in-op replay
→ release decision. Host suite: 1346 tests collected
(9 Nov 2026 owner run: 1344 passed + 2 honest axe skips,
0 failures; SDK-free CI: 1340 + 6 SDK-gated skips).
Planning unit tests 52/52 in `tests/unit/test_planning.py`
(distinct from the 28/28 published eval dataset);
browser E2E 30 + 2 skips / 32.

## How we use QNX (evidence of QNX use)

The generated controller is QNX-native C: guard and
controller communicate over Neutrino synchronous message
passing (`name_attach`/`name_open`,
`MsgSend`/`MsgReceive`/`MsgReply`), telemetry is served
by a resource manager (`resmgr_attach`, `io_read`) at
`/dev/genesis/status`, control timing uses
`CLOCK_MONOTONIC` with RFC 1982 wrap-safe
sequence/deadline arithmetic, and a custom supervisor
owns bounded respawn and GIVE_UP (QNX HAM is not used —
it is absent from the image). Target: QNX SDP 8.0, `qcc`
12.2.0 (`gcc_ntox86_64`), QEMU x86_64. Key files:
`target/qnx8/include/genesis_ipc.h`,
`target/qnx8/guard/`, `target/qnx8/controller/`,
`target/qnx8/status/`, `target/qnx8/supervisor/`,
`target/qnx8/common/guard_policy.c`. Executed natively
twice on current source (BEFORE/AFTER packs below);
`qnx_verified=True` with replay matches on both.

## Technical proof: one change, verified natively twice

Omega2 flagship (8 Nov 2026, current source):

| | BEFORE | AFTER |
|---|---|---|
| Contract | AMR v1 | AMR v2 (guarded safe-stop) |
| Native matrix | 16/16 PASS, sealed | 16/16 PASS, sealed |
| Pack | `evidence/qnx8-x86_64-omega2-before/` (34 files) | `evidence/qnx8-x86_64-omega2-after/` (36 files) |

Stale control: the v2 contract against the v1-built
binary fails 14/16, exactly on `estop_target` +
`v2_transitions`. Historical limits proof (1.2 → 1.6 m/s
DENY→ALLOW flip, 18/18 bit-for-bit rebuilds) in
`evidence/qnx8-x86_64-w11-*/` (7 Nov 2026).

## AI disclosure (read this before scoring Innovation)

The optional planner is model-proposes,
deterministic-disposes: the model extracts a structured
intent, deterministic code checks units/ranges/ambiguity
first and builds IR from templates, and the same
validation gate applies. The model can never authorize
safety, mark a build verified, or grant release
eligibility (regression-pinned). Default: the offline
deterministic keyword planner.

Measured honesty, newest first (local Ollama CPU,
`qwen2.5:7b-instruct` + `llama3.1:8b-instruct`):

- **v6 blind holdout** (72 cases, separately
  agent-authored, frozen BEFORE the fixes, 8 Nov 2026):
  **46/72 on all three providers** (24/24 valid, 22/48
  reject, 26 unsafe accepts, 0 false rejects;
  fail sets byte-identical). The model was consulted
  ZERO times — the deterministic layer short-circuited
  every case. v6 does not prove model safety; it
  measures the deterministic layer against novel
  paraphrases, multilingual removal, evasion tricks,
  and injections.
- Post-v6 hardening fixed the v6 failure *classes*
  with fresh phrasings (never v6 strings); v4/v5
  offline regression now 36/36 + 36/36 — but those
  sets are development-touched, so this measures
  regression, NOT generalization. A fresh v7 set is
  required for the next honest claim.
- v5 (36 cases): 24/36 per provider with 12
  accepted-should-refuse — the 12 classes that drove
  the deterministic fixes. v4: 32/32/31 per provider.
  Earlier 98-case holdout: 87/98 (Qwen), 81/98
  (Llama), then 98/98 + 30/30 post-fix on touched
  sets (not generalization proof).

Raw logs: `evals/results/2026-11-08-omega3-v6/`,
`evals/results/2026-11-08-omega3-v4v5-postfix/`,
`evals/results/2026-11-08-omega2-v5/`, full analysis
`docs/audits/OMEGA3_AI_EVALUATION.md`.

## Potential impact (no theatre)

GENESIS RT is a change-verification and evidence layer
for QNX teams: it complements Momentics and established
suites (Parasoft, LDRA, VectorCAST), never replaces
them. Demonstrable today: reproducible native evidence,
stale-binary rejection, offline third-party
verification, and a deterministic 8-vs-30-command /
5-of-5-vs-3-of-5 fault benchmark (`bench/productivity/`).
**No pilots, no customer measurements, no user time
savings exist** — the paired pilot kit (full 6-task +
quick 3-task tiers, consent + anonymization enforced)
is ready in `docs/business/pilot-study.md` and
`bench/productivity/`, with zero invitations sent.
`HUMAN USER BENEFIT NOT YET MEASURED` governs.

## Try it (judge path, ~5 minutes, no SDK)

```sh
git clone https://github.com/toskaman/genesis-rt.git
cd genesis-rt
pip install -e ".[dev]"
python evidence/qnx8-x86_64-omega2-before/verify.py \
  evidence/qnx8-x86_64-omega2-before
python evidence/qnx8-x86_64-omega2-after/verify.py \
  evidence/qnx8-x86_64-omega2-after
PYTHONPATH=host python scripts/run_verified_demo.py
PYTHONPATH=host python -m genesis_rt.cli serve
# Studio at http://127.0.0.1:8077/
python -m pytest tests/ -q
# 1346 collected; SDK-free CI: 1340 + 6 honest skips
```

With an SDK: `python scripts/qnx_env_check.py`, then
`docs/quickstart-qnx8-qemu.md` (Windows + Linux).

## Limitations (complete list: `docs/jury/KNOWN_LIMITATIONS.md`)

QEMU only (no real hardware); TCG timing is relative;
simulation-only machines; no safety certification; no
hardware attestation; packs are hash-only (UNSIGNED, no
signer authentication); native CI lane is build-only
(target campaigns run on the author's machine and ship
as packs); AI planner has 26 measured v6 unsafe-accept
classes outstanding (v7 needed); no external user
study; full screen-reader pass outstanding.

## Eligibility statement

Repository created during the submission period:
initial commit `a2bde91` dated 2026-11-04 ("P0: GENESIS
RT alpha"), within the Nov 2 – Dec 15, 2026 window.
Original work, solely owned, Apache-2.0, public, free
of charge and restriction for judging. No QNX SDK
files, images, keys, or credentials in the repo or
artifacts (CI scans enforced). Codelab authored during
the period (originated in the initial commit, maintained
through `33d361c` Omega2, all host steps re-executed
8 Nov 2026).

## Bonus strategy (internal note, not pasted)

Enter BOTH bonus boxes (allowed; at most one Bonus
prize can be won — official cap is one Overall + one
Bonus + Community Choice, max $13,500):

1. **Best Use of QNX-specific Technologies (lead):**
   deepest verified evidence — synchronous IPC,
   resource manager, supervision + fault containment,
   contract-aware native oracle, 16/16 matrices,
   bit-reproducible `qcc` builds. Hardest to replicate.
2. **Best Codelab/Tutorial (strong second):** complete
   QNX 8.0 tutorial (`README` + `ADVANCED-QNX` +
   `EXTERNAL-BUILD`), authored in-period, re-executed
   on Windows + Linux with an anti-rot test harness.

## Community Choice (internal note, not pasted)

Organic only during Jan 15–29, 2027 voting:
publish the repo + codelab + technical write-ups in
relevant QNX/embedded communities where the owner
already participates; never buy, automate, or
incentivize votes; never use multiple accounts.
No outreach sent to date.

## Rules compliance checklist (verified 8 Nov 2026)

- Public repo + Apache-2.0 detected: YES.
- One category (Developer Tooling & Host Tools): YES.
- Installable + runs as depicted: YES (judge path
  above; SDK path documented).
- QNX 8.0 evidence + identified files: YES.
- Video <3:00, public YouTube, device footage:
  PENDING OWNER (storyboard ready).
- English materials: YES.
- Free availability through judging (Jan 29, 2027):
  YES.
- Original work, no IP violation, OSS-compliant: YES.
- Deadline Dec 15, 2026 2:00 PM EST: ON TRACK.
