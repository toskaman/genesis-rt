# Progress log

## 2026-11-04 (later) — vérifié sur vrai QNX 8.0 (QEMU)

- QSTI 0.5.0 booté sous QEMU 11.1 (WHPX, `-cpu host`, boot disque ;
  `-kernel` direct et CPU émulé stallent le loader — documenté).
- SSH cible OK (`qnxuser`, `QNX qnxqemu 8.0.0 x86_64`) ; 6 binaires natifs
  transférés et exécutés. Matrice on-target 5/5 : faultinject 6/6 via IPC
  natif, resmgr lu via `/dev/genesis/status` (root), 60/60 ALLOW à 100 ms,
  superviseur stable (4 processus), device résident.
- Bugs trouvés PAR la cible et corrigés : `io_read` resmgr (offset/EOF,
  OCB opaque), device qui exitait, attente SSH/exec sans timeout.
- `qnx_verified: True` de bout en bout : `qnx_target.py verify` →
  `demo --target-record` → gate PASS, replay valide.
- G2/G3/G4/G10 désormais OUI (cible). Reste : vidéo (fin projet), Devpost.

## 2026-11-04 (later) — SDP 8.0 installé, build natif vert

- Licence Education activée via QSC CLI; SDP 8.0.0 installé en
  `E:\qnx800` (baseline épinglée, métadonnées miroirées).
- Corrigés par le vrai `qcc` : include `common/` manquant dans le
  makefile généré (+test de régression), `-lm` requis à l'édition de
  liens, `dispatch_block` QNX8 (contexte alloc), `stdlib.h` manquant.
- 5 binaires natifs `elf64-x86-64`, zéro warning. Détection SDK auto
  sans variables d'env (candidats standards + env enfant).
- Suite complète verte, 0 skip (le test QNX build tourne vraiment).
- Paquet `com.qnx.qnx800.quickstart.qemu` 0.5.0 installé ; extraction
  QSTI en cours, boot + runs on-target ensuite.

## 2026-11-04 (later) — QEMU ready, SDK wall mapped

- QEMU 11.1.0 verified at `E:\VMs\qemu\`; env probe + `GENESIS_QEMU`
  override added (`probe_qemu`, tested).
- Official QNX path grounded in docs: myQNX account → licence
  accept/deploy → QSC → SDP 8.0 + `com.qnx.qnx800.quickstart.qemu` →
  `unpack_qemu_image.sh` → boot. QSC/SDP downloads are login-walled:
  no legitimate unattended install exists; user click-path documented.
- Added `scripts/qnx_target.py` (`probe-image`, `boot`) using the official
  QSTI launch template (ifs.bin kernel, serial console, virtio-net),
  host-adapted (KVM/WHPX/TCG); transcripts + markers, never assumed pass.
- Next: user runs §1 of `docs/quickstart-qnx8-qemu.md`, then one command
  boots QEMU and the on-target genesis runs begin.

## 2026-11-04 (later) — audit + hygiene

- Swept tracked files: no secrets, no SDK/proprietary material, no run
  outputs committed (only the labelled host-simulated sample passport).
- Added `.gitattributes` (LF normalization) to end CRLF churn.
- Video production explicitly deferred by entrant to end of project; the
  HyperFrames scaffold + genuine capture transcripts are shelved at
  `../genesis-rt-video/` (outside the submission repo), narration scripts
  kept with them. G11 stays PENDING until then.
- Fresh-clone install re-verified green (suite + demo PASS).

## 2026-11-04 — P0: repo + host pipeline + QNX sources (this session)

- Implemented: Machine IR v1 (schema + strict validator), deterministic
  codegen + templates, guard policy in C and Python with conformance
  harness, 5 QNX-native processes, simulator, 8-scenario fault lab with
  oracles, hash-linked evidence passport, fail-closed gate, orchestrator,
  CLI, optional FastAPI API, static dashboard, examples (AMR + conveyor).
- Tested: full pytest suite green (unit/property/integration/faults/
  acceptance; QNX test honestly skips without SDK), C/Python conformance
  vectors identical, break-then-fix gate cycle proven.
- Blocked (external): QNX SDP 8.0 install (interactive license acceptance by
  the entrant) → on-target build/run evidence; demo video recording.
- Next: SDK setup per `docs/quickstart-qnx8-qemu.md`, capture real `qcc`
  build + QEMU run transcripts, attach target evidence to a passport,
  record the <3:00 video from genuine runs, draft Devpost text.

## Acceptance-gate status

- G0 license/redistribution clean: YES (Apache-2.0, no SDK material in repo)
- G1 deterministic codegen: YES (tested)
- G2 QNX native build/run evidenced: PENDING (SDK setup)
- G3 guard rejects on real target: PENDING (SDK setup; host-proven)
- G4 QNX-specific sources visible/tested: PARTIAL (sources + host conformance)
- G5 no-test⇒no-pass: YES (tested)
- G6 seeded reproducible faults: YES (tested)
- G7 clock boundaries separated: YES (methodology + code)
- G8 simulation-only outputs: YES (enforced by IR + validator)
- G9 hardening basics: PARTIAL (timeouts, argv lists, fuzz-ish property tests)
- G10 clean-install repro: PENDING (needs independent reviewer + SDK)
- G11 real demo video <3:00: PENDING
- G12 README pitch/arch/commands/limitations/FAQ: YES
