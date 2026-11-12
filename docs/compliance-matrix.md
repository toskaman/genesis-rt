# Compliance matrix (QNX Global Hackathon rules)

Source rules: https://qnx.devpost.com/rules (re-fetched 7 Nov 2026; first checked 5 Nov 2026: deadline Dec 15 2026 2pm EST, judging Jan 15–29 2027, video <3 min public YouTube, repo created Nov 4 inside the entry window).

| Rule | How we comply | Evidence | Status (7 Nov 2026) |
|---|---|---|---|
| Public repo with detectable open-source license | Apache-2.0 `LICENSE`, detected by GitHub (About section) | repo root | PASS (GitHub API: apache-2.0, PUBLIC) |
| Full source + assets + reproducible instructions | this repo; README quickstart; jury docs | `README.md`, `docs/jury/` | PASS (fresh-clone replay 7 Nov) |
| QNX 8.0 target + toolchain stated | `qnx8_x86_64_qemu`, SDP 8.0 `qcc -Vgcc_ntox86_64` | IR, `docs/quickstart-qnx8-qemu.md` | PASS (QEMU x86_64, qcc 12.2.0) |
| Genuine QNX evidence | native IPC C code, resource manager, build/run logs path | `target/qnx8/`, passports | PASS (3 packs VERIFY OK; rerun op-24fecbf11df8) |
| Demo video < 3 min, public YouTube | **WITHDRAWN 2026-11-10**: all cuts removed for an owner remake, no video file shipped; **DEFERRED BY USER**: final video production deferred; YouTube publication pending; full submission blocked on this item. Rule detail: the video must show the project running on the intended device (QEMU target) | `docs/demo/MEDIA_VALIDATION_W12.md`, `docs/demo/MEDIA_VALIDATION_CAUSAL.md`, `docs/demo/PUBLICATION_HANDOFF_W12.md` (all ON HOLD / historical) | DEFERRED BY USER |
| English | all submission materials in English | this repo | PASS |
| One entry category | Developer Tooling & Host Tools | Devpost form | PASS (at submission) |
| Created/updated during entry period | repo created 4 Nov 2026, history public | git log | PASS |
| Available without restriction through judging (29 Jan 2027) | public repo, no hardware beyond QEMU | GitHub | PASS (keep repo public until 29 Jan 2027) |
| Original work, entrant-owned | authored for this entry; no copied code | `docs/jury/COMPLIANCE.md` | PASS |
| No financial/preferential sponsor support | none sought or accepted; no commercial QNX license | `docs/jury/COMPLIANCE.md` | PASS |
| No sponsor/Admin IP misuse | no QNX binaries/headers redistributed | `.gitignore`, CI | PASS |
| Bonus: Best Use of QNX-specific Technologies | native message passing, resource manager, priorities/timers, supervisor | `target/qnx8/` | PASS (candidate) |
| Bonus: Best Codelab/Tutorial | beginner codelab + advanced QNX codelab; SDK-free blocks replayed on a fresh clone 7 Nov 2026; host blocks CI-enforced | `docs/codelab/`, `tests/integration/test_codelab_advanced.py` | PASS (candidate; only one bonus prize can be won) |

Software readiness: `SOFTWARE_READY_WITH_LIMITATIONS`. Submission readiness: `SUBMISSION_PENDING_DEFERRED_VIDEO`.

## License decision (OpenBridge request)

The brief asked to reuse the OpenBridge license if possible. Findings:

1. The referenced project (`toskaman/openbridge`) uses **PolyForm Strict
   1.0.0**, which forbids distribution and modification — it is **not** an
   open-source license (GitHub reports `spdx: NOASSERTION`) and would violate
   the Devpost "public and open source" requirement. Reuse is not possible.
2. The OpenBridge design-system project uses a delayed AGPL-3.0 → Apache-2.0
   model that GitHub cannot auto-detect during the judging window — risky
   against the "detectable license" rule.

Decision: pure **Apache-2.0** — OSI-approved, GitHub-detectable, matching both
the master-plan recommendation and the license OpenBridge converges to.
