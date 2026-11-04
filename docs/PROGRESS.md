# Progress log

## 2026-11-04 (later) -- P1 IR v2 : schema strict + migration v1 deterministe

- Nouveau module `host/genesis_rt/ir_v2.py` : 13 sections requises, monde
  ferme (unites par type d'actionneur/capteur, evenements, fautes, arch
  x86_64 unique), cles inconnues rejetees, references croisees resolues
  (transitions/commandes/telemetrie/fault_responses), etats d'entree sur
  faute obligatoirement safe, exactement 1 etat initial. Les enums v2
  sont des sur-ensembles stricts de v1 (kinds, if/then, scenarios).
- `migrate_v1_to_v2` : pur, deterministe, tagge chaque entree derivee
  `"origin": "migrated-v1"` ; vocabulaire contrat v1 copie verbatim,
  faute derivee via table totale `V1_IF_FAULT_MAP` ; bornes migrees
  symetriques (fidele au `abs()` de `guard_policy.py`).
- Secondaires : `schemas/machine-ir-v2.schema.json` (draft-07, le Python
  reste normatif), `examples/{amr,conveyor}-demo/machine-ir-v2.json`
  rediges a la main, plan `docs/superpowers/plans/2026-11-04-ir-v2.md`.
- CLI `validate` dispatche v1/v2 sur `schema_version` (YAML -> v1,
  sortie `valid: schema vN ...`, contrat `valid:` preserve).
- 66 tests `tests/unit/test_ir_v2.py` (2 valides, 50 rejets, 7 migration,
  4 CLI + divers) ; preuve rouge : validateur neutre -> 51 FAIL ;
  suite 205/205 verte. Pipeline v1 inchange (v2 non branche a codegen).

## 2026-11-04 (later) — P0 #7 : niveaux de vérification + SSH penalty-box

- `gate.evaluate` assigne désormais le plus haut niveau de preuve MÉRITÉ :
  `NONE < HOST_TESTED < QNX_COMPILED < QNX_EXECUTED <
  QNX_BEHAVIOR_VERIFIED < QNX_PERFORMANCE_MEASURED`, avec
  `release_eligible` vrai uniquement à partir de
  `QNX_BEHAVIOR_VERIFIED`. Un PASS hôte ne peut plus se lire comme une
  autorisation de release ; la preuve cible est liée au build natif
  (build non-ok + cible ok → `HOST_TESTED`, `qnx_verified: False`).
  Sémantiques `verdict`/`reasons` inchangées. `qnx_perf` n'a pas encore
  de producteur (harness P1) : les passeports plafonnent honnêtement à
  `QNX_BEHAVIOR_VERIFIED` avec raison explicite.
- CLI `demo` affiche `level` + `release_eligible` + `level_reasons`.
- 4 tests gate ajoutés (paliers, exécuté-vs-vérifié, liaison au build,
  NONE sur échec) + 1 test mutant always-ALLOW (garde désactivée →
  5 scénarios FAIL → gate FAIL/NONE/non-éligible). Suite 139/139.
- Incident SSH résolu (cause racine) : le sshd invité (OpenSSH 10.3)
  applique `PerSourcePenalties` — nos rafales de reconnexions ont mis la
  source au ban (`Not allowed at this time`). Deuxième effet mesuré 3/3 :
  un succès immédiatement suivi de retries rapides donne 8/8 échecs +
  re-ban (flap transitoire SLIRP/WHPX + pénalité en cascade).
  `_ssh_client` : 4 essais PATIENTS espacés de 45 s + cooldown unique de
  300 s sur signature penalty-box (bannière absente) ; règle
  opérationnelle : une seule commande SSH à la fois, jamais de sonde
  juste avant la vraie commande.
- Incident WHPX (bloquant cible, sans reboot possible) : `HypervisorPresent
  = False` après reboot hôte 20:02, `hypervisorlaunchtype Off` → QEMU
  `No accelerator found`. Remis à `Auto` (effectif au prochain reboot).
  Fallback TCG tenté et abandonné (bloqué au QNX Boot Loader, CPU qemu64
  incompatible). Travail cible suspendu jusqu'au reboot ; suite hôte.

## 2026-11-04 (later) — P0 #3 : limites générées pilotent le runtime, 7/7

- Garde/contrôleur/faultinject incluent `genesis_config_gen.h` : finis les
  `{1.2, 1.0, 100}` et `period 10` codés en dur. Période/cruise dérivés
  (cruise = 40 % de la limite), faultinject 9 checks valides sur toute
  machine (FI_CRUISE/FI_OVER) + mode `probe <linear_mps>`.
- Preuve on-target (matrice 7/7 PASS, `qcc` 0 warning) : probe 1.5 → DENY
  `SPEED_OVER_LIMIT` sur gardeur AMR (limite 1.2), ALLOW sur gardeur
  conveyor (limite 2.0), + 9/9 faultinject contre le gardeur conveyor.
  `demo --target-record` PASS `qnx_verified: True`, replay valide.
- Incidents : un `supervisor_respawn` 4|0 non reproduit au re-run (sup.log
  désormais capturé dans le transcript) ; flap SSH transitoire (4 échecs
  d'auth puis 6/6 OK, cause environnementale) → retries bornés (3×) +
  auth password déterministe dans `_ssh_client`.
- Suite 129/129. Reste : vidéo (fin projet), Devpost.

## 2026-11-04 (later) — P0 Wave B : cible QNX durcie, 6/6 + red-green (`f00f7c0`)

- Guard : vrai `msglen` émetteur (`MsgReceive`+`_msg_info`, BAD_SIZE réel),
  pulses jamais répondus, endpoint stats (allows/denies/last_reason/
  last_seq/dropped). Status : requête IPC live par lecture (timeout 2 s).
  Superviseur : RESPAWN borné (×3, backoff 1/2/4 s) + GIVE_UP avec halt
  (aucun survivant orphelin). Contrôleur : timeout `TimerTimeout` 2 s,
  `clock_nanosleep` absolu, remplissage `0xFF` fail-closed. Faultinject :
  9 checks (bad_version, nan_linear, short_frame).
- `qcc` : 6 binaires, 0 warning. Matrice on-target 6/6 PASS
  (target_info, faultinject 9/9, status_live compteurs exacts,
  controller_flow, supervisor_respawn, supervisor_giveup) →
  `demo --target-record` verdict PASS `qnx_verified: True`, replay valide.
- Red-green prouvé : anciens guard/status/supervisor vs nouveaux oracles
  → 2/6 (faultinject `short_frame reason=7 want 3`, status_live statique,
  2 étapes superviseur FAIL). Méthode reproductible : restaurer les 3
  fichiers depuis le commit parent, rebuild, `put`, `verify`.
- G2/G3/G4 confirmés OUI (cible). Reste : vidéo (fin projet), Devpost.

## 2026-11-04 (later) — P0 Wave A : crédibilité host (`b6787ac`)

- Guard Python fail-closed (OverflowError, limites malformées, parité C),
  oracles Fault Lab réfutables + tests de sabotage, orchestrateur passeport
  partiel véridique, API (temp IR par requête, 400, 1 worker, fix 422),
  dashboard XSS-échappé + re-vérification chaîne en JS pur, IR anti-bool,
  manifest codegen (digests templates, anti-injection), tests PASS
  démasqués (17 vecteurs conformance NaN/inf, golden non-vacueux).
- Suite 127/127 verte, 0 skip. CI verte.

## 2026-11-04 (later) — vérifié sur vrai QNX 8.0 (QEMU)

- QSTI 0.5.0 booté sous QEMU 11.1 (WHPX, `-cpu host`, boot disque ;
  `-kernel` direct et CPU émulé stallent le loader — documenté).
- SSH cible OK (`qnxuser`, `QNX qnxqemu 8.0.0 x86_64`) ; 6 binaires natifs
  transférés et exécutés. Matrice on-target 6/6 : faultinject 9/9 via IPC
  natif, status live via `/dev/genesis/status` (root), 60+ ALLOW à 100 ms,
  superviseur RESPAWN/GIVE_UP prouvé, device résident.
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
- 6 binaires natifs `elf64-x86-64`, zéro warning. Détection SDK auto
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
  harness, 6 QNX-native processes, simulator, 8-scenario fault lab with
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
- G2 QNX native build/run evidenced: YES (qcc 0 warnings, 6/6 on-target)
- G3 guard rejects on real target: YES (9/9 IPC checks incl. BAD_SIZE/NaN)
- G4 QNX-specific sources visible/tested: YES (msg passing, resmgr, timers, supervision)
- G5 no-test⇒no-pass: YES (tested)
- G6 seeded reproducible faults: YES (tested)
- G7 clock boundaries separated: YES (methodology + code)
- G8 simulation-only outputs: YES (enforced by IR + validator)
- G9 hardening basics: PARTIAL (timeouts, argv lists, fuzz-ish property tests)
- G10 clean-install repro: PARTIAL (fresh-clone host green; independent reviewer + SDK pending)
- G11 real demo video <3:00: PENDING
- G12 README pitch/arch/commands/limitations/FAQ: YES
