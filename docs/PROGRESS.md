# Progress log

## 2026-11-05 -- Wave 10 Sprint A: baseline, boot fix, F4, recovery fix

- Baseline 851/851 green, 0 skips (`docs/audits/WAVE10_BASELINE.md`).
- Boot hardening: `build_qemu_argv` pins `format=vmdk|qcow2|raw`
  (a torn .vmdk descriptor probed as raw → guest lost its disk,
  campaign failed at wait_ssh; descriptor repaired, backup kept).
- F4: Judge Mode + synchronized A/B twin replay documented as
  implemented (verified in `ui/studio.html`); 2 anti-rot tests.
- Recovery ownership: crash recovery reaps only dead/absent owners
  (+24h pid-reuse backstop); `test_serve_bind` no longer touches
  the real store. Trigger: it reaped a live campaign op mid-verify.
- Suite 851/851 green, 0 skips (CI on push; SDK-less 846 + 5).

## 2026-11-05 -- Wave 9 §17: competitive landscape & buyer dossier

- `docs/business/COMPETITIVE_LANDSCAPE.md`: source-backed vendor
  notes (QNX Tool Suite, Simulink/ECoder, SCADE/TargetLink,
  Parasoft/LDRA/VectorCAST/Coco, Jama/Codebeamer/Polarion/DOORS,
  RapiTime), 10-dimension assessment matrix, 3 buyer personas,
  adoption/integration/pricing hypotheses (all labeled),
  pilot-partner criteria (no invented names), 5 PMF risks with
  kill criteria. Consistent with COMMERCIAL_VISION §4
  (complementary framing, no unmeasured superiority).
- Falsifiable claims spot-checked (simulation_only gate,
  Apache-2.0/no-CLA, suite counts); docs guard 6/6.

## 2026-11-05 -- Wave 9 §20: advanced QNX codelab + anti-rot harness

- `docs/codelab/ADVANCED-QNX.md`: 6 labs (guard microscope incl.
  wrap-boundary vectors, deterministic codegen + provenance,
  passport anatomy, replay + tamper, native qcc build, on-target
  IPC/supervision/telemetry/latency). Every host/SDK command
  executed here; every target command executed live on QNX 8.0.0
  QEMU (real transcripts: 9/9 faultinject, BEFORE/AFTER status,
  200-sample bench, RESPAWN×4, GIVE_UP, SIGKILL containment
  GBEFORE=GAFTER, distinct PIDs in RECEIVE).
- Harness `tests/integration/test_codelab_advanced.py` (3/3):
  runs all `sh-harness` blocks in order (self-asserting),
  SDK-gates Lab 5, pins lab/block coverage. Fixed along the
  way: Store-stub `python` under QNX sh, backslash env paths
  in python one-liners, set-e vs intentional-failure line.
- Suite 851/851 green, 0 skips (CI on push; SDK-less 846 + 5).

## 2026-11-05 -- Wave 9 §25: red-team round 1 (replay swap fixed)

- Attack A1 (evidence swap at replay) SUCCEEDED pre-fix: `_step_replay`
  never bound the file to the op, so a valid foreign passport with
  a matching verdict replayed as ours. Fixed: replay requires
  `run_id == op_id` and `ir_sha256 == sealed sha`. Failing-first
  tests kept (`test_replay_rejects_foreign_op_passport`,
  `test_replay_rejects_ir_mismatch`); real SDK seal→replay path
  still green.
- Report `docs/audits/RED_TEAM_ROUND1.md`: all 19 §25 items mapped
  (18 HOLD with pinning tests, 1 FIXED), 2 accepted residuals
  (point-in-time evidence, unsealed server-side op records).
- Suite 838/838 green, 0 skips (CI on push).

## 2026-11-05 -- Wave 9 Phase 2: Judge Mode + Decision link + bench repro

- Judge Mode (@f1954a5): guided 7-stage tab (A machine → G value),
  every action drives the real product (tab navigation or live
  POST /jobs fault/verify runs); backend-offline shows the
  archived sample labeled ARCHIVED. Node harness 4/4.
- Proof-to-Decision link (@323f544): stage G renders the live
  release banner (TARGETED/PENDING vs eligible) from the judge
  job passport; UI 47/47.
- Benchmark re-run: totals reproduce exactly (8 vs 30+10 cmds,
  5/5 vs 2/5 faults, repro True); committed REPORT.json refreshed;
  pilot kit `docs/business/pilot-study.md` (protocol + templates,
  no invented participants).
- Docs guard caught stale counts (CI red on 3 pushes): fixed to
  836/836 with-SDK and 832 + 4 honest SDK-less skips (measured:
  CI ubuntu bfa549e 822+4 at 826 + 10 SDK-independent new tests).
- Suite 836/836 green, 0 skips (CI on push).

## 2026-11-05 -- Wave 8 §8 remainder + §17 retention + judge docs

- DNS-rebinding audit closed (`docs/local-security-model.md`): 5
  layers verified (loopback bind, no CORS, Origin guard, JSON-only
  writes, 31-route GET inventory), each pinned
  (`test_rebinding_posture.py` 4/4 + `test_serve_bind.py` 1/1);
  Host validation assessed unnecessary, documented why.
- Retention (`docs/retention-and-cleanup.md`): measured growth
  (~332 KiB/full op, ~167 KiB/run, 1.3 MiB runs.db), caps table,
  worker cleanup verified (tmp unlink, QEMU wait-reap, SSE
  terminal-close), manual purge SQL validated on a DB copy.
  No auto-delete of user evidence, by policy.
- Judge docs de-staled (Finding E): KNOWN_LIMITATIONS (Studio Live
  + Target tab), devpost/REPRODUCE/START_HERE/SCORECARD/COMMERCIAL/
  planning-eval counts → 831/831 verified, demo-video-plan goes
  Studio-first (full Task 14 assets pending).
- Suite 831/831 green, 0 skips (CI on push).

## 2026-11-05 -- Wave 8 Task 3b + Task 4: sealed passports + formal campaign

- Runner SEAL/REPLAY real (@4dcbe3f): seal mirrors run_pipeline
  (host sims + build_passport + gate; gate FAIL fails the op),
  replay recomputes chain + gate from the sealed file; artifacts
  persisted in the op record. 27/27 target tests, 821 suite green.
- Runner hardening (@c3c6e4b): hermetic staging (leftovers dropped
  before put), extra_src param, IR normalize-once at validate
  (posted order vs validated order digest differently — the gate
  caught it), build_set passed to perf. 826/826 green.
- Formal campaign op-dc74546f8fa2 (Task 4 record:
  docs/audits/TASK4_FORMAL_CAMPAIGN.md): 13/13 COMPLETED, fresh
  qcc 12.2.0 build, hermetic staging of 9 binaries (6 primary +
  3 attributed secondaries), 16/16 matrix PASS on QNX 8.0.0 TCG,
  1000-sample perf bound, verdict PASS, replay PASS,
  level QNX_PERFORMANCE_MEASURED, release_eligible True,
  tamper control refused. Honest gap: no explicit 2^32
  wrap-boundary vector on target (host-tested); matrix v2 recommended.

## 2026-11-05 -- Wave 8 Phase A: API/Target Runner + fresh native proof

- §6 Origin guard now covers PUT/PATCH (was POST/DELETE only; PUT
  /projects/{pid} proven writable cross-origin before the fix); negative
  tests; docs/local-security-model.md.
- §7 bounded job admission: MAX_LIVE_JOBS=50, JobOverloaded→429 +
  Retry-After, no orphan tmp on refusal; burst/stress tests.
- §5 Studio Target Runner: TargetRunner (9-state machine, file store,
  single campaign lock shared with the qnx_target.py CLI, cancel,
  honest BLOCKED, bounded QEMU cleanup, stdout capture on failure),
  5 Origin-guarded endpoints, Studio Target tab + node harness.
- Fresh native proof op-a507c7ecb9cf (this box, TCG): 11/11 steps,
  qcc 12.2.0 build, 16/16 target matrix PASS on QNX 8.0.0 x86_64,
  0 orphans; artifacts under artifacts/runs/target-ops/ (git-ignored).
  WHPX still broken on host (needs reboot); TCG+cpu max boots.
- Crash fix (audit): os.kill() on self kills sandboxed trees; liveness
  now observed via tasklist//proc (no signaling where unneeded).

## 2026-11-05 -- Wave 7 M1+M2+M3§8 : Studio Live + Evidence Graph

- M1 reliability (§5+§7 @bdeac07/119d442): version-aware CLI, docs pins
  with consistency guard, async jobs + SSE + Origin guard; 576 green.
- M2 Studio Live (@900f229 backend + @037923f frontend): server-side
  projects w/ history/diff/export, JSON designer + v2 state graph,
  SSE pipeline with run/cancel/history, byte-exact raw passports;
  9 tabs browser-verified 12/12; 619 green, CI green.
- M3 §8 Evidence Graph: `evidence_graph.py` folds a hash-verified
  passport (+ optional v2 IR requirements) into typed nodes/edges
  (req→IR→file→binary→process→scenario→oracle→trace→verdict);
  tamper→InvalidPassport/409, caps→GraphTooLarge/400; `graph` CLI;
  `POST /graphs` + `/graphs/compare` accept dict or raw text
  (browsers must send raw text: JS `1.0`→`1` breaks the chain —
  found live, regression-tested); Studio Evidence tab (10th):
  run/file/Passport sources, IR picker, scenario/status/search
  filters, node detail w/ edges + generated-file viewer, revision
  compare; browser-verified 15/15 incl. 0.9-limit diff.
- M3 §11 Requirements-to-Release: `impact.py` (change-impact over
  two validated revisions: precise requirement→scenario mapping,
  conservative global set for limits/control/machine/contracts,
  fail-closed unclassified moves, generated files reported-only);
  targeted retest can never imply release eligibility;
  `POST /impact`, `/impact/release`, `GET /projects/{pid}/impact`,
  `impact` CLI; Studio project Impact + retest runner + targeted/full
  banners + Evidence release-check section; browser 14/14 incl.
  stale/current digests.
- IR numeric canonicalization (found live via the release check):
  validators store float-semantic fields as float and collapse
  integral floats to int, so a JS `1.0`→`1` round-trip cannot move
  `ir_sha256`; genuinely fractional values never truncated;
  example digests pinned unchanged (history-lock tests).
- M3 §9 Counterexample Explorer: `explorer.py` (seeded bounded
  search over a scripted driver reusing guard_policy+simulator:
  6 invariants, 4 strategies — boundary/pairs/windows/mutate —,
  greedy shrink, deterministic replay on same/fixed IR);
  `explorer_conformance.py` replays the script against the C
  `guard_vector` harness; tiers kept separate
  (host-discovered / c-conformance-reproduced / c-divergent /
  native). `explore` + `replay` CLI, `POST /explore` +
  `POST /explore/replay`, Studio Lab explorer section with
  fix-replay; browser 11/11 incl. host-discovered finding.
- M3 §10 Twin 2.0: `twin.py` folds any scenario trace into a
  replay track (frames + timeline markers under stepwise-hold:
  last recorded tick shown, gaps flagged never bridged);
  chain-verified passports only, run source labeled honestly
  (host-only / qnx-bound, ticks stay host-sim). `twin` CLI,
  `POST /twin/frames`, Studio Twin tab rebuilt: cell schematic
  (AMR/belt/station/presence/interlock/phase/leg), scrub + speed
  + event nav + markers + scenario select + A/B sync compare,
  marker→trace/guard/checks sync, one-click Evidence Graph jump;
  single interval, canvas+textContent paints, loop stops on
  pause/tab-switch. JS/Python fold parity node-tested; browser
  30/30 incl. screenshots.
- M4 §12 Productivity Benchmark: `bench_productivity.py` runs
  six engineering tasks through the real CLI vs checked-in
  synthetic reference workflows (`scripts/bench_ref/`, labeled):
  8 genesis cmds vs 30 ref cmds + 10 counted manual steps,
  faults 5/5 vs 2/5, genesis lane reproducible; `bench` CLI,
  `bench/productivity/METHODOLOGY.md` + recorded `REPORT.json`,
  commercial vision updated with measured numbers only.
- M4 §16 time wrap fixed: deadline comparison was a plain
  `now > deadline` (fail-open overdue + false overdue across the
  uint32 wrap); now RFC 1982 serial arithmetic in Python + C,
  ABI unchanged, 5 new conformance vectors, wrap/recovery/version
  unit tests green.
- M4 §15 robustness: `_done` track cap (200, oldest-terminal evict, DB fallback), `job=` structured logs; 6 lifecycle tests.
- Suite 758/758 with SDK (SDK-free 755 + 3 honest QNX-build skips);
  jury pins + architecture updated; consistency guard green.

## 2026-11-05 -- P1 Wave 5 : jury delivery (termine)

- Clone frais GitHub : `run_verified_demo.py` PASS + suite 525/525
  (@a642cd0) ; le glob `replay.py artifacts/runs/*/passport.json` du
  parcours juge ne passait pas sous PowerShell -> `replay.py` etend
  les globs lui-meme (1 match ok, 0/ambigu -> exit 2) + 2 tests.
- Docs jury : 518/487 -> chiffres mesures (527 passe avec SDK,
  524 + 3 skips honnetes sans SDK via simu probe), Devpost rafraichi
  (cellule, v2, sched, eval 28, codelab URL bonus).
- Docs jury : 9/9 (walkthrough, why-qnx, why-genesis, scorecard ajoutes).
- Re-preuve sans SSH : replay ancre v2 run-079ce9374c58 -> 16/16
  transcripts + 2/2 build-set + PASS exit 0 ; tamper controle ->
  MODIFIED exit 1. Demo C re-verifiee live (FAIL->PASS, 3 fixed).
- SSH cible retabli (image-default via GENESIS_TARGET_PASSWORD ;
  candidats fournis refuses) -> cleanup /tmp/genesis (rm *.log,
  9 binaires conserves, 0 process), 3 producteurs frais re-executes
  (cell run-19742302c723, conv run-5fc173416e61, v2 run-1918800f0ca5).
- Cycle frais post-cleanup PASS : matrice 16/16 (qnx-final5),
  perf 1000/1000 p50 253.8 (stable vs 254.7 Run 3), passeport
  MEASURED run-449210581ea2, replay ancre 16/16 + 2/2 build-set +
  gate PASS (ancre bfce46ac...9a34ff7), tamper -> MODIFIED refuse.
  Wave 5 termine ; video <3:00 + Devpost a l'utilisateur.

## 2026-11-05 -- P2 Wave 4C : dossier commercial

- `docs/business/COMMERCIAL_VISION.md` : utilisateur cible, 8 cas
  d'usage, paysage (positionnement par categorie, sans superiorite
  non mesuree), 5 hypotheses a valider, obstacles honnetes, 4 options
  de modele (open core recommande), licences (QNX Everywhere !=
  usage commercial), roadmap, pitch 60 s.

## 2026-11-05 -- P1 Wave 4B : AI eval 28 cas

- Dataset `evals/planning_eval.json` 15 -> 28 cas (toutes classes
  §11 : valides, ambigus, dangereux, unites, injection, hors-domaine ;
  transitions impossibles + refs manquantes en stub-provider).
- 2 vrais bugs trouves par TDD : requetes ambigues (1er kind gagne
  en silence) et unites fausses ("5 km/h" -> defaut 1.2 silencieux)
  -> rejets guides + 7 tests. CLI `plan` route via `plan_machine`.
- `docs/planning-eval.md` : criteres, resultats 28/28, 3 regressions,
  limites. Suite 525/525.

## 2026-11-05 -- P2 Wave 4A : codelab reecrit et reverifie live

- Toutes les commandes reexecutees (hote + cible /tmp/genesis) :
  trouves 2 inexactitudes (binaires 7->9 selon build, step 5
  superviseur vs chaine manuelle STALE_SEQ) -> corrigees.
- Nouveau codelab : variantes Windows+Linux, sorties attendues reelles,
  schema archi, troubleshooting (9 entrees), cleanup, limites, URL
  Devpost finale.

## 2026-11-05 -- P1 Wave 3C : scheduling sched + perf refresh

- `qnx_target.py sched` : 4 configs (baseline 10r/10r, fifo_guard,
  fifo_both, rr_both) via `on -p`, policy guard verifiee par
  pidin (setup assert, zero seuil timing). 10 tests.
- Campagne cellule n=200/config PASS : baseline p50 509.2 p99
  1787.0 (1 stall 60.9 ms), fifo_both p50 311.4 p99 618.5,
  rr_both p50 269.3 p99 573.5. Lecture : sender side domine
  sous TCG ; contraste scheduling uniquement, pas de gate tier.
- Perf-baseline : colonne Run 3 (cellule v2 n=1000 : p50 254.7,
  p95 399.9, p99 493.7) + section scheduling. Latence IPC
  declaree machine-independante par construction (1 code path),
  donc campagne par cible, pas par machine.
- Suite hote 518/518.
  Chiffres canoniques : 518 tests, matrice 16/16, 9 stages.

## 2026-11-05 -- P1 Wave 3B : containment controller/device + fix pidin

- Bug Wave 3A : pidin `-F %n` affiche `./genesis_guard` + padding,
  donc `grep -c "^genesis_guard$"` ne matchait jamais -> assertion
  ALIVE=0 vacuous. Fix : comptages substring (conv/v2 slain en
  debut de step, pas de collision) + test de regression qui
  interdit les patterns ancres. Valide dans les 2 sens live.
- 2 steps avant guard_crash (cell_policy reste dernier) :
  `controller_crash` (device 81->82, guard 82->82 gele,
  NONGUARD=0, CALIVE=0, GALIVE=1) et `device_crash` (device
  81->82 gele, guard 82->145 decide toujours, DALIVE=0,
  CALIVE=1, GALIVE=1). Parsers : freeze 0..3, NONGUARD=0,
  morts==0, survivants==1, device_crash exige GAFTER-GBEFORE>=20.
- 18 tests (17 containment + 1 pin pidin) ; 33/33 cibles.
- Fusion PR #2 (provenance v2 multi-build, session parallele) :
  rebase + cycle cible frais avec `--build-set` (v1 plafonne a
  QNX_EXECUTED). 3 builds demo (conv run-d6c955a3478d, amr-v2
  run-7700919fdcd1, cellule run-6e946cd6334b), 9 stages frais,
  `verify --ir --build-set` 16/16 PASS, perf 1000/1000
  (p50 254.7 us, p95 399.9, p99 493.7, max 825.1), `demo` ->
  `QNX_PERFORMANCE_MEASURED` (run-079ce9374c58).
- Replay ancre v2 : `chain: valid` + `anchor: match` +
  `transcripts: 16/16 match` + `build-set: 2/2 entries replayed`
  + `gate: PASS` exit 0 ; transcript controller_crash falsifie
  -> `MODIFIED` exit 1. Ancre run-079ce9374c58 :
  `1262137d6537159be410e1ce64c9a347e7f026f20442e8a1681d007488a78623`.
- Suite hote 508/508.
  Chiffres canoniques : 508 tests, matrice 16/16, 9 stages.

## 2026-11-05 -- P0 Wave A : provenance multi-build (v2) + baseline

- Baseline mesure (checkout propre Linux, sans SDK) : 449 passed / 3
  skipped (452), commit 103da7f ; `docs/baseline-2026-11-05.md` (metriques
  distinctes : tests hote, 13 steps, binaires par build, 9 executables
  stages, 3 builds natifs par campagne).
- Trou §5 ferme cote hote : les guards secondaires (`genesis_guard_conv`,
  `genesis_guard_v2`) etaient stages sans origine. `buildset.py` : entree
  par executable derivee du passeport du build producteur (chaine
  verifiee, machine/kind/schema, IR, qcc, build_id, sha256+cksum+taille,
  tete de chaine). Gate : chaque executable stage = exactement un build ;
  refus non-attribue / ambigu / octets differents / mauvaise origine /
  secondaire requis absent / build_id reutilise / perf build set different.
- Producteurs : `scripts/build_set.py create`, `qnx_target.py verify|perf
  --build-set` ; `replay.py --source-passport --require-build-set-replay`
  re-derive chaque entree.
- Migration : `provenance_version` 2 ; v1 sans extra garde son tier ; v1
  avec executables d'autres builds (toutes les campagnes publiees) plafonne
  a `QNX_EXECUTED`, jamais upgrade -> un cycle cible frais avec
  `--build-set` est necessaire (non fait : pas d'acces SDK/QEMU ici).
- +30 tests (`tests/unit/test_buildset.py`), mutation : 6/6 mutants tues.
  Suite hote 487 passed / 3 skipped (490) apres rebase sur Wave 3A.

## 2026-11-05 -- P1 Wave 3A : fault containment (guard_crash)

- Matrice 14e step `guard_crash` avant `cell_policy` (cell_policy
  reste dernier, invariant tests) ; sonde live : guard tue
  mid-stream, applies gelees (BEFORE=82 AFTER=84), NONGUARD=0,
  ALIVE=0, client `MsgSend failed`.
- Parser `_matrix_check guard_crash` : BEFORE>=20, AFTER-BEFORE
  0..3, NONGUARD=0, ALIVE=0, marqueur MsgSend failed (8 tests) ;
  tests cell_policy portes a 14.
- Preuve cible liee : `verify --ir cell-ir.json` 14/14 PASS,
  perf 1000/1000 (p50 263.7 us, p95 439.2, p99 580.2, max 786.0),
  `demo` -> `QNX_PERFORMANCE_MEASURED` (run-401697e34f10).
- Replay ancre : `chain: valid` + `anchor: match` + `transcripts:
  14/14 match` + `gate: PASS` exit 0 ; transcript guard_crash
  falsifie -> `MODIFIED` exit 1. Ancre run-401697e34f10 :
  `c7f890a6543dd12ebd99cb428ca39d21696af2d69c550b18a142af433fae487c`.
- Suite hote 460/460.
  Chiffres canoniques : 460 tests, matrice 14/14, 9 stages.
  Risque : fenetre AFTER-BEFORE 0..3 calibree sur 2 sondes TCG ;
  a revalider si flake.

## 2026-11-05 -- P1 Wave 2B : counterfactual + API (Demo C, history/export)

- Passeport : record `ir` embarque `limits` (guard_limits, None pour
  non-v1) ; additif, chaines existantes intactes.
- `compare` : diff contrat champ-par-champ, delta mesures qnx_perf
  (p50/p95/p99/max), listes fixed/broken, `release_changed`,
  binaires hashes (plus de dump binaire -> plus de crash console).
- Demo C : `cell-ir-broken.json` (1 ligne : 0.3 m/s) -> FAIL/NONE
  1/4 ; fixed -> PASS ; compare : `0.3 -> 1.2`, 3 fixed, verdict
  True. Walkthrough `examples/cell-demo/README.md`, Studio Diff.
- API : `GET /runs` (historique, limit 1..200), `POST /compare`
  (run_ids, 404/409 honnetes, confinement ARTIFACTS),
  `GET /runs/{id}/export` (download), run actif -> 202 ;
  migration DB `run_dir` additive ; `orchestrator.active_runs()`.
- 11 tests (5 compare, 6 API). Suite hote 452/452.
  Chiffres canoniques : 452 tests, matrice 13/13, 9 stages.

## 2026-11-05 -- P1 Wave 2A : GENESIS CELL (industrial cell end-to-end)

- IR `industrial_cell` + bloc `cell` (stations, transfert, interlock),
  `presence_bool`, 4 scenarios cellule valides (35/35 IR) ; CellSim +
  interlock superviseur (10/10) ; faultlab 4/4 + oracles refutables
  (sabotage prouve le FAIL) ; `examples/cell-demo/cell-ir.json`.
- Codegen : header politique `genesis_cell_policy.h`, injection
  makefile (makefiles non-cellule byte-identiques), determinisme
  (12/12) ; `genesis_cellcheck.c` natif (selftest 9 vecteurs +
  3 checks, host C 3/3).
- Matrice 13e step `cell_policy` (7 tests parser) ; `limits_differ`
  lie au `--ir` (banner slot-1 = machine+limite liees, geometrie
  sonde imposee, legacy AMR si non lie ; 10 tests) au lieu du pin
  AMR en dur qui faisait echouer le cycle cellule.
- Trou §6 bouche : `build_qnx` digere aussi les extras `genesis_*`
  (cellcheck) sinon la gate ne les liait pas (+3 tests).
- Preuve cible liee : qcc 7+6+6 binaires 0 warning, 9 stages frais,
  `verify --ir cell-ir.json` 13/13 PASS, perf 1000/1000 (p50 299 us,
  p99 634 us), `demo` -> `QNX_PERFORMANCE_MEASURED`
  (run-8009ee91097e, qnx_verified, release_eligible, 7 binaires lies).
- Replay ancre : `chain: valid` + `anchor: match` + `transcripts:
  13/13 match` + `gate: PASS` exit 0 ; transcript falsifie ->
  `MODIFIED` exit 1. Ancre run-8009ee91097e :
  `e5f46d7c5de628c8d61cc8009f5f8096fb54c2e0a3e2127047cc5dd113e054ee`.
- Suite hote 441/441. Chiffres canoniques : 441 tests, matrice
  13/13, 9 binaires stages. Reste : video (fin projet, user), Devpost.

## 2026-11-05 -- P0 Wave 1c : Evidence Passport 2.0 (provenance + threat model)

- Provenance de bout en bout : `host/genesis_rt/provenance.py`
  (matrice 12 epinglee, plateforme, cksum POSIX CRC bit-identique au
  `cksum` de reference sur 10 entrees, percentiles nearest-rank sans
  interpolation, rendezvous staged cksum+taille, fenetre de capture,
  refus fail-closed avec level_reasons explicites).
- Gate durci : tout tier au-dessus de `QNX_EXECUTED` exige le binding
  IR/build/cible/fenetre/plateforme ; les records legacy sans
  provenance plafonnent a `QNX_EXECUTED`, jamais FAIL.
- Producteurs : `verify --ir` (uname/staged/transcripts/fenetre/digest
  IR), `perf` (staged/fenetre/distribution liee), `build_qnx`
  (sha256+cksum+taille par binaire, built_utc, `qcc -V`).
- Verificateur independant : `replay.py --anchor` (tete de chaine
  publiee hors-bande) + `--transcripts-dir` (re-digest des
  target-*.log) + rapport provenance (IR/machine, build qcc,
  staged cible, fenetre).
- Threat model : `docs/passport-threat-model.md` (5 niveaux distincts :
  integrity, provenance, trusted local execution, independent replay,
  hardware attestation NON fournie ; attaquants A1-A4, risques
  residuels A3/A4 documentes, pas de theatre d'attestation).
- Bug reel trouve PAR le gate : `verify --ir` digerait le JSON brut
  alors que le pipeline digere l'IR valide/normalise -> premier cycle
  lie echoue ferme `QNX_EXECUTED` "stale evidence" (run-67ad0700a651,
  preuve du fail-closed). Fix : `_ir_binding` utilise `load_ir_file`
  + test de regression `test_ir_binding_matches_pipeline_manifest`.
- Preuve cible liee : boot TCG `-cpu max`, qcc 18 binaires 0 warning,
  `verify --ir` 12/12 PASS, perf 1000/1000 (p50 279 us, p99 545 us),
  `demo --target-record --perf-record` -> `QNX_PERFORMANCE_MEASURED`
  (run-652e31767c28, qnx_verified, release_eligible).
- Replay reel : `chain: valid` + `anchor: match` + `transcripts: 12/12
  match` + `gate: PASS` ; controle negatif `--anchor deadbeef` ->
  MISMATCH exit 1. Ancre publiee run-652e31767c28 :
  `c73e6ec0e3438ae40ada1e907dcf31152743330d3f26018bd201349ae686b6b3`.
- Suite hote 380/380 (18 adversariaux, 7 provenance, 4 replay).
  Chiffres canoniques : 380 tests, matrice 12/12, 8 binaires stages.
  Reste : video (fin projet, user), Devpost.

## 2026-11-05 -- P0 Wave 1b : Machine IR v2 end-to-end + matrice 12/12

- v2 de bout en bout : `codegen_v2` (wire map, machine module,
  `-DGENESIS_MACHINE_V2` sur le guard seul), tail v2 dans
  `guard_policy.c` (transitions generees, latch stale/sim/stop
  pilotes par l'IR), dispatch v2 CLI/pipeline/API/passeport/Studio.
- Preuve cible : `faultinject probe state <n>` + step matrice
  `v2_transitions` (contraste bidirectionnel v1/v2 : state 2 ALLOW/DENY,
  state 3 DENY/ALLOW ; 9/9 sur le binaire v2 ; limite 1.5 DENY ; estop
  DENY). `verify` 12/12 PASS natif (QNX 8.0/QEMU TCG `-cpu max`),
  `qcc` 0 warning (18 binaires), perf 1000/1000 (p50 ~0.27 ms),
  `demo --target-record --perf-record` -> `QNX_PERFORMANCE_MEASURED`.
- Incident reproduit + root-cause : `supervisor_respawn` 4|0 (deja vu
  "non reproduit" le 2026-11-04) : ligne RESPAWN ecrasee mid-line par
  un enfant (4 writers sur sup.log, offsets races ; preuve :
  "supervisor: RESPAguard: ..."). Fix : logs par-enfant
  (`posix_spawn_file_actions`, O_APPEND) + `fflush(stderr)` sur les
  lignes d'audit ; sup.log redevient un audit trail single-writer.
  Re-run matrice : 12/12 PASS.
- Suite hote 351/351. Chiffres canoniques : 351 tests, matrice 12/12,
  8 binaires stages. Reste : video (fin projet, user), Devpost.

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
- G2 QNX native build/run evidenced: YES (qcc 0 warnings, 12/12 on-target)
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
