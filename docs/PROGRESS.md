# Progress log

## 2026-11-04 (later) -- Polish final + audit P5 (video/Devpost au user)

- Docs : README (Studio), jury 11/11 + 310 tests, limitations
  (HAM absent QSTI, UI statique), baseline perf cible, codelab
  etape 5 (sudo + cleanup + note STALE_SEQ). Secrets : mot de
  passe cible uniquement via env, aucun secret en historique.
- P5 : clone frais `C:\tmp` -> 310/310 vert + `validate`/`generate`
  /`demo` PASS/`replay` valid (meme machine ; relecteur independant
  hors de portee). Temporaires sous `artifacts/` : gitignore ;
  `replay` demande un chemin explicite sous PowerShell (pas de glob).
- Acceptation finale : P0-P3 + codelab + perf + Studio livres et
  prouves (CI verte). Restent : video demo <3:00 (user, plan dans
  `docs/demo-video-plan.md`) + soumission Devpost (brouillon dans
  `docs/devpost-draft.md`, chiffres 11/11 + 310 a jour).

## 2026-11-04 (later) -- P2 #19b bench perf cible (tier max)

- `faultinject bench N` : N round trips MsgSend nominaux, horloge
  monotone cible, `SAMPLE` brutes + `PERF_DONE` (stats cote hote) ;
  `qnx_target.py perf` : SSH, distribution nearest-rank, record
  `qnx-perf-record.json` (mesures + 1000 echantillons bruts).
- Pipeline : `build_passport(..., qnx_perf=...)`,
  `run_pipeline(..., perf_record=...)`, `demo --perf-record` ;
  matrice 10 -> 11 (`target_perf`, bench 200, forme seule).
- Preuve : perf 2x1000/1000 (p50 ~0.31 ms, p99 ~0.65 ms, TCG),
  `verify` 11/11 PASS, `demo --target-record --perf-record` ->
  `QNX_PERFORMANCE_MEASURED`/PASS/release/qnx_verified. Table cible
  dans `perf-baseline.md` (jamais melangee a l'hote). HAM : absent
  de l'image QSTI (clos, superviseur maison garde). Codelab etape 5
  rejouee (fix sudo + cleanup). Suite 310/310 verte.

## 2026-11-04 (later) -- P2 #21 codelab verifie + fix GENESIS_SRC (host)

- Codelab rejoue commande par commande : etapes 1 (valid + rejet
  exact exit 2), 2 (generate + header + diff byte-identique), 3
  (`faults` 8/8 + vecteur main DENY SPEED_OVER_LIMIT), 4 (`make qnx`
  0 warning + binaires), 6 (`run_verified_demo` PASS). Etape 5
  (cible) a rejouer sur QNX avec la session perf.
- Defaut 25 trouve et corrige : `GENESIS_SRC=../../target/qnx8` en
  dur ne marchait que pour `--out` a 2 niveaux ; le CLI calcule
  desormais le relatif vers le checkout (+ `--genesis-src`), v1
  inchange. Codelab enrichi (vecteur estop, note cc/gcc/clang).
- Preuve : `test_cli_generate_src_points_at_target` (1 et 3
  niveaux), map ligne 25, etape 4 rejouee OK. Suite 307/307.

## 2026-11-04 (later) -- P1 #15 tranche B : Studio Diff (broken vs fixed)

- Onglet Diff : 2 passeports (A/B), chaines re-verifiees, tableau
  delta (FIXED/BROKE/NEW/GONE/same + flips par check), banniere
  INVALID si un cote est faux (jamais de delta partiel).
- Preuve : test node `test_studio_diff_fixed_and_invalid` (echec
  structurel rechained via l'API evidence -> FIXED ; sabotage ->
  INVALID) ; smoke standalone node (harnais DOM/canvas jetable) sur
  les bytes finaux : init + 5 rendus OK. Suite 306/306.

## 2026-11-04 (later) -- P1 #15 tranche A : Studio (workspace 6 onglets)

- `ui/genesis_verify.js` : coeur pur extrait du dashboard (verbatim,
  tests node inchanges) ; `ui/studio.html` : Intent (IR + sha256 live
  avec normalisation validateur), Source (provenance v1/v2 pine vs
  IR, MISMATCH bruyant), Twin (replay canvas corridor/belt, gap
  marque, jamais interpole), Lab (scenarios/seeds/checks -> Twin),
  Passport (chaine re-verifiee, Lab/Twin vides si invalide), Run
  (commandes exactes, zero execution simulee).
- Preuve : 12/12 tests UI node (irsha==Python sur 2 IR, pin
  match/mismatch, Lab/Trace diff+belt, tamper rejete) ; garde
  anti-interpolation non-echappee sur les 3 fichiers. Suite 305/305.

## 2026-11-04 (later) -- P1 #12 tranche C : belt sur QNX, matrice 10/10

- Modele belt C (`device_model`) : position/vitesse, dt arrivee,
  clamp 1 s, watchdog 500 ms, `set_jam` (decay *=0.5, freeze) ;
  `genesis_device belt` (argv, banniere, `belt_pos=` audit,
  devstate x=pos/v=speed) ; `probe estop` faultinject (9 checks
  intouches, ligne PROBE +`estop=`).
- Matrice 8 -> 10 : `conv_chain` (garde conv -> belt, APPLIES=83,
  BELT=83, NONGUARD=0, dev_x=1.92) + `estop_target` (probe DENY
  ESTOP, state=3/last_reason=ESTOP en telemetrie). Parser tests
  synthetiques + 6 vecteurs belt.
- Preuve : stage reconstruit (`qcc` 0 warning), `put` 7/7, `verify`
  10/10 PASS sur QNX 8.0/QEMU (TCG `-cpu max`), `demo
  --target-record` PASS `QNX_BEHAVIOR_VERIFIED`/release/qnx_verified.
  Docs jury/quickstart passees en 10/10. Suite 300/300 verte.

## 2026-11-04 (later) -- P1 #12 tranche B : estop niveau garde (host + C)

- Fil : `reserved[0]` -> `estop_engaged` strict 0/1, trame 36 o
  inchangee (`_Static_assert`) ; `R_ESTOP=12`, deny + latch, ordre
  ... -> sim -> estop -> speed ... dans les deux miroirs.
- Harnais `guard_vector` : 14e champ optionnel (repli 13, >255
  refuse) ; 27 vecteurs conformite C/Python verts (estop, dominance
  vitesse, integrite d'abord, reset bloque si estop).
- Scenario `estop_pressed` (registre=10) : boucle `fault`, oracle
  5 checks (tout DENY ESTOP, latch, zero mouvement, reset unique,
  reprise) ; passe sur les 2 sims (AMR garde ses 8, conveyor -> 5).
- Preuve : suite 290/290, `qcc -Werror` 10 fichiers 0 warning,
  faultinject 9/9 inchange (memset zeroise l'estop).

## 2026-11-04 (later) -- P1 #12 tranche A : conveyor simule (BeltSim + jam)

- `simulator.py` : `BeltSim` (position/vitesse/jammed + aliases
  final_x/final_y) ; `faultlab.py` dispatch par kind, oracle
  `_o_belt_jam` (zero_creep/jam_observed/recovery), `belt_jam`
  refuse bruyamment hors conveyor (crash + seed schema-complet).
- `ir.py` : 9e scenario `belt_jam` ; IR conveyor v1+v2 : 4 scenarios
  (stale_proximity remplace, capteur absent du convoyeur).
  Planner : listes par kind ; `test_all` = IR-declare.
- Preuve non-regression : traces AMR avant/apres byte-identiques
  (271772 octets). Gate : couverture = IR-declare (plus registre).
  Snapshots conv regen (diff = seule ligne ir_sha256).
- Suite 283/283 verte (+6 BeltSim, +4 sabotage/differenciation).

## 2026-11-04 (later) -- P0 #4 : DEBLOQUE sans reboot, matrice 8/8 PASS

- TCG ressuscite methodiquement (QMP) : sous CPU `qemu64` defaut,
  invite QNX fige, RIP gele a 0x14020a4 sur 3 min, 2 coeurs brules
  pour zero progres -> `-cpu max` : log 352 -> 3437 octets en 90 s,
  RIP dans le noyau, sshd up. Fix code dans `build_qemu_argv` :
  `tcg` => cpu `max` par defaut, `host` refuse bruyamment sous tcg.
- Cause racine device_chain : `resmgr_attach(/tmp/genesis-status-node)`
  => EPERM sous qnxuser (resmgr absolu exige root). Fix matrice :
  `sudo -n` au demarrage + nettoyage (precedent status_live) ;
  chaine prouvee : APPLIES=83 issus du pid garde, NONGUARD=0.
- Preuve : stage reconstruit (`qcc` 0 warning, 7 binaires), `put` 7/7,
  `verify` 8/8 PASS sur QNX 8.0/QEMU (TCG), `demo --target-record`
  PASS `QNX_BEHAVIOR_VERIFIED`/`release_eligible`/`qnx_verified`,
  replay recharge valide (chaine + gate). Docs jury passees en 8/8.
- Suite 273/273 verte (test_device_chain 5 inclus ; jamais absents).

## 2026-11-04 (later) -- P2 #19 tranche hote : banc perf + baseline

- `scripts/bench_host.py` : garde (distribution p50/p95/p99/max),
  campagne 8 scenarios, codegen, build `qcc` natif + warnings.
  Mesure reel x2, etiquete hote-only : garde p99 ~4-7 us, campagne
  ~14-19 ms, build ~0.7 s 0 warnings. Doc `docs/perf-baseline.md`
  (methode + table) ; test schema sans seuils flaky. Timings cible
  post-reboot, jamais melanges. Suite 268/268 verte.

## 2026-11-04 (later) -- P2 #18 tranche hote : comparaison de builds

- `host/genesis_rt/compare.py` + CLI `genesis-rt compare A B [--json]` :
  diff de deux dossiers run (machine, scenarios declares, sources
  generees avec unified diff, statuts scenarios, verdict/niveau/
  release). Sert le recit broken-vs-fixed : mutation 1.2 -> 0.5
  visible dans le diff du header genere, AMR vs conveyor montres.
- 5 tests (run identique -> diff vide, 2 machines, mutation limite,
  non-run-dir refuse, CLI texte+json). Suite 265/265 verte.

## 2026-11-04 (later) -- P2 #17 tranche hote : interface planning + eval

- `host/genesis_rt/planning.py` : interface independante du fournisseur
  (`PlanningProvider.propose_raw` + registre `PROVIDERS`, seul
  `offline` fourni, zero reseau/cout). Sortie fournisseur traitee
  comme NON fiable : re-validation `validate_ir` systematique,
  non-objets/crashs enveloppes en `PlannerRejection`. Scan unsafe
  AVANT appel (garde, limites, hardware reel, injection de prompt,
  hors-sujet) avec explication precise ; le fournisseur n'est pas
  appele en cas de refus (teste).
- Eval publiee `evals/planning_eval.json` (15 cas : 8 valides, 7 refus)
  + test portail 100% : `offline` 15/15. L'eval a attrape un vrai bug
  avant release : matching sous-chaine classait "robotic arm" en
  robot differentiiel ("robot" dans "robotic") -> matching par mots
  entiers. Doc `docs/planning-eval.md`. Aucune integration LLM
  revendiquee (seul `offline` enregistre).
- Suite 260/260 verte.

## 2026-11-04 (later) -- P1 #16 : couverture gate + annulation runs (TDD)

- Defaut confirme (trou sect.10) : `gate.evaluate` faisait confiance aux
  `required_scenarios` de l'appelant ; un sous-ensemble + preuves cible
  passantes donnait `release_eligible: True` sur 1/8 scenarios. Fix :
  la gate compare au `scenarios` declares de l'IR dans le passeport,
  enregistre `coverage{declared,required,omitted}` et force
  `release_eligible=False` + raison explicite si omission (verdict et
  niveaux inchanges). Changement de contrat assume : le test paliers
  passe en couverture complete pour garder release True.
- Annulation : `run_id` client optionnel (valide, anti-traversal),
  `DELETE /runs/{id}/cancel` (202/404), checks cooperatifs entre
  etapes pipeline, `CancelledRun` -> 409 + `failure.json` step
  cancelled ; collision run_id existant -> 409 (anti-duplicata, pas
  d'ecrasement de preuve). Cycle TDD rouge-vert (6 tests).
- Audite sans changement : `_lock` FIFO garde (pas de 503 ; le test
  concurrence existant exige 2x200), timeouts subprocess tuent
  l'enfant (`make` orphelin `qcc` quelques secondes, borne, local),
  SQLite WAL + connexions par requete, retention run_dirs volontaire
  (preuve). Suite 252/252 verte.

## 2026-11-04 (later) -- P1 #11 tranche hote : generation C specifique-machine

- `host/genesis_rt/codegen_v2.py` + 2 templates : depuis IR v2, genere
  `genesis_machine_gen.{h,c}` (enums etats/evenements/commandes/fautes/
  actions/actionneurs/capteurs/telemetrie + `switch` generes :
  transitions, bornes champs commandes, reponses fautes, bornes
  actionneurs, fraicheur/portee capteurs, map telemetrie). Collisions
  d'identifiants C -> `ValueError` explicite. Config+makefile via v1
  `generate()` inchange ; lien du module dans la regle genesis_guard
  par post-traitement de la copie makefile du dossier v2 (template
  partage intact, hunk #4 en attente preserve).
- Preuves : snapshots bytes des 2 machines + test differenciation
  structurelle (2 commandes vs 1, bornes +-1.2 vs +-2.0, ESTOP vs
  PROXIMITY) ; harnais `machine_vector.c` compile host `-Wall -Wextra`
  zero warning, vecteurs derives de l'IR (2 machines vertes) ; `qcc`
  natif ok 0 warning sur les 2 dossiers v2 ; build natif v1 intact.
- Deferre honnetement : call-site garde (apres preuve cible #4),
  demo comportement natif (post-reboot). Spec + plan dans
  `docs/superpowers/`. Suite 243/243 verte.

## 2026-11-04 (later) -- P0 #6 : wraparound seq (arithmetique serielle)

- Defaut confirme : `seq <= last_seq` coincait la garde apres
  wraparound uint32 (2^32-1 -> 0 refuse a jamais, latch=False donc pas
  de reset possible -> wedge silencieuse cote disponibilite, fail-closed
  cote surete). Remplace par arithmetique serielle RFC 1982 des deux
  cotes : delta = (seq-last) mod 2^32 accepte ssi 1 <= delta < 2^31.
  Wrap accepte, doublons/replays/sauts >= 2^31 refuses STALE_SEQ.
- Fichiers : `guard_policy.py` + `guard_policy.c` (miroirs), 3 tests
  Python, 4 vecteurs conformance C/Python (wrap, replay, dup, jump).
  Rouge-vert : ancien predicat -> 3 FAIL (wrap, jump, conformance).
- Build natif `qcc` reel : ok, rc 0, 0 warning (`-Wall -Wextra`).
- Reste #6 cote cible (post-reboot) : validation d'horloge monotone
  cote target au lieu des timestamps expediteur seuls ; stats
  jitter/deadline-miss (harness P1 #19). Suite 229/229 verte.

## 2026-11-04 (later) -- P0 #8/#9 : oracles + regressions bouclees

- P0 #8 clos : audit des 8 oracles faultlab (aucun `True` inconditionnel,
  tous bases sur stats/trace observees) + 4 tests sabotage directs
  (over_limit, nominal, delayed, stale). Couverture rouge complete :
  crash, dropped, mutant always-ALLOW, watchdog e2e existaient deja.
- P0 #9 : politique SSH extraite en constantes testables
  (`_SSH_MAX_ATTEMPTS=4`, gap 45 s, cooldown 300 s) + classifieur
  `_ssh_is_penalty_box_signature` ELARGI : l'ancien test ne voyait que
  `banner`, or le ban observe dit `Not allowed at this time` (sans le
  mot banner) -> cooldown rate, ban prolonge. 17 tests
  `test_ssh_policy.py` (paramiko/time simules, zero reseau), rouge-vert
  prouve (classifieur casse -> 8 FAIL, restaure -> 17/17).
- `docs/regression-map.md` : 19 defauts confirmes -> fix -> test
  (dont #19 device_chain OPEN, en attente reboot).
- Suite 226/226 verte.

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
- G2 QNX native build/run evidenced: YES (qcc 0 warnings, 11/11 on-target)
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
