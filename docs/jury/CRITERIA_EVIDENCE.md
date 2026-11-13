# The four judging criteria: where to look

One section per official criterion. Every line points at a file or a
command you can run; nothing here is a score. Canonical numbers live
in [`docs/CLAIMS.md`](../CLAIMS.md); what is *not* claimed is in
[`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).

## 1. Technological Implementation

- **Runs natively on QNX 8.0.** Seven C processes built with `qcc`
  (0 warnings): guard server, periodic controller, device endpoint,
  status resource manager, supervisor, fault injector, cell checker
  (`target/qnx8/`). They talk over native message passing
  (`name_attach` / `MsgSend` / `MsgReceive` / `MsgReply`, protocol in
  `target/qnx8/include/genesis_ipc.h`).
- **Checked on the target.** A 16-step on-target matrix passes 16/16
  on QNX 8.0 (QEMU x86_64), including crash containment for the
  guard, the controller and the device.
- **Re-checkable without an SDK.** Sealed evidence packs under
  `evidence/` each ship a stdlib-only `verify.py`
  (`python evidence/qnx8-x86_64-omega2-after/verify.py evidence/qnx8-x86_64-omega2-after`
  prints `VERIFY OK`). The packs are hash-only and unsigned: they
  prove integrity and binding, not who produced them.
- **Tested.** 1629 host tests (SDK-free: 1623 + 6 honest skips, each
  naming its reason), including a 24-test adversarial suite that
  tampers with passports, and a C-versus-Python conformance test of
  the guard policy (`tests/integration/test_c_conformance.py`).
- Full claim-to-file map: [`TECHNICAL_EVIDENCE.md`](TECHNICAL_EVIDENCE.md).

## 2. Design

- **One command per job.** `genesis-rt demo`, `verify-change`,
  `causal-repro`, `demo-break` each end in a one-line verdict and a
  file a reviewer can open.
- **GENESIS Studio** (`genesis-rt serve`, local web UI): a guided
  tour, a before/after view of a requirement change, an evidence
  graph and a release decision written in plain language, with light
  and dark themes and keyboard access.
- **Accessibility.** An automated WCAG 2.2 scan runs in CI. A manual
  pass with a screen reader has not been done.
- Walkthrough with exact outputs: [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md).

## 3. Potential Impact

- **Who it is for.** The embedded engineer who changes one
  requirement on a QNX controller and must show a reviewer that the
  binary on the target is the one that satisfies it.
- **What changes for them.** The answer becomes a sealed file anyone
  can re-check offline, and a binary that was not rebuilt is refused
  (`genesis-rt demo-break`).
- **What is not shown.** HUMAN USER BENEFIT NOT YET MEASURED: no
  pilot session with a real engineer has been run. The pilot kit is
  ready (`docs/business/pilot-study.md`). Everything ran on QEMU;
  no physical board has been used.
- Why a real-time OS is the right foundation: [`WHY_QNX.md`](WHY_QNX.md).

## 4. Innovation & AI Creativity

- **Evidence as the product.** A hash-linked passport plus a
  fail-closed gate: missing, skipped, crashed or tampered evidence
  always yields FAIL (`tests/unit/test_evidence_gate.py`).
- **Incident to cause, on the target.** `genesis-rt causal-repro
  --target live` turns an incident report into ranked hypotheses and
  grounds the winner in a native QNX run
  (`evidence/t10-causal-live-dossier/verify_causal.py`).
- **AI that is measured, and never trusted.** The model only
  proposes; a deterministic validator decides. On the development
  set: 28-case planning eval at 28/28. On the latest blind holdout
  (184 cases): 165/184 for each local model, 15 unsafe accepts of 136
  reject cases (the same 15 on every provider), 0 wrong-kind accepts.
  Report: `docs/audits/OMEGA7_AI_EVALUATION.md`.

---

## Bonus prizes

- **Best use of QNX-specific Technologies:** native message passing,
  a resource manager (`/dev/genesis/status`), process supervision
  with bounded respawn, crash containment — see
  [`WHY_QNX.md`](WHY_QNX.md) and
  [`TECHNICAL_EVIDENCE.md`](TECHNICAL_EVIDENCE.md).
- **Best Codelab / Tutorial:** [`docs/codelab/README.md`](../codelab/README.md)
  (a native IPC controller in 45 minutes), with two companions:
  `ADVANCED-QNX.md` and `EXTERNAL-BUILD.md`.

## Status

Final video: DEFERRED BY OWNER until the final cut is published.
