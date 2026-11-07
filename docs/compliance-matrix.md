# Compliance matrix (QNX Global Hackathon rules)

Source rules: https://qnx.devpost.com/rules (checked 5 Nov 2026: deadline Dec 15 2026 2pm EST, judging Jan 15–29 2027, video <3 min public YouTube, repo created Nov 4 inside the entry window).

| Rule | How we comply | Evidence |
|---|---|---|
| Public repo with detectable open-source license | Apache-2.0 `LICENSE`, detected by GitHub (About section) | repo root |
| Full source + assets + reproducible instructions | this repo; README quickstart; jury docs | `README.md`, `docs/jury/` |
| QNX 8.0 target + toolchain stated | `qnx8_x86_64_qemu`, SDP 8.0 `qcc -Vgcc_ntox86_64` | IR, `docs/quickstart-qnx8-qemu.md` |
| Genuine QNX evidence | native IPC C code, resource manager, build/run logs path | `target/qnx8/`, passports |
| Demo video < 3 min, public YouTube | final voiced MP4 ready: `docs/demo/genesis-rt-demo-w12.mp4` (154.664 s, AAC, verbatim `subtitles-w12.srt`, validation report); **DEFERRED BY USER** (7 Nov 2026): final video production deferred; the w12 MP4 is a historical cut, not declared final; YouTube publication pending; full submission blocked on this item | `docs/demo/MEDIA_VALIDATION_W12.md`, `docs/demo/PUBLICATION_HANDOFF_W12.md` |
| English | all submission materials in English | this repo |
| One entry category | Developer Tooling & Host Tools | Devpost form |
| Created/updated during entry period | repo created 4 Nov 2026, history public | git log |
| Available without restriction through judging (29 Jan 2027) | public repo, no hardware beyond QEMU | GitHub |
| Original work, entrant-owned | authored for this entry; no copied code | `docs/jury/COMPLIANCE.md` |
| No financial/preferential sponsor support | none sought or accepted; no commercial QNX license | `docs/jury/COMPLIANCE.md` |
| No sponsor/Admin IP misuse | no QNX binaries/headers redistributed | `.gitignore`, CI |
| Bonus: Best Use of QNX-specific Technologies | native message passing, resource manager, priorities/timers, supervisor | `target/qnx8/` |

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
