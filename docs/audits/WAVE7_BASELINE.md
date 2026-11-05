# Wave 7 Baseline Audit

Date: 2026-11-05
HEAD: `e4775871e83b593f0e41dc52021afca770351756` (e477587 "Wave 5: target cleanup + fresh 16/16 matrix, perf, MEASURED passport, anchored replay (run-449210581ea2)")
Scope: repo at `genesis-rt/`; read-only audit except this file.
Prior results consumed: 1, 7, 6, 3, 2, 4, 5, 8, 9 (handoff files read to completion).

## 1. Repo state

- HEAD SHA: `e4775871e83b593f0e41dc52021afca770351756`
- Uncommitted changes: none (`git status --short` empty).
- Branches: local `main` checked out (`* main`); remotes `origin/HEAD->origin/main`, `origin/main`, `origin/muse/provenance-v2-buildset`, `origin/muse/provenance-v2-rebased`.
- Open PRs: 1 open — #3 "Wave 6 A1/A2/A4: CLI v1/v2 consistency and doc drift", branch `muse/wave6-cli-docs`, OPEN 2026-11-05T02:49:04Z.
- Open issues: none.
- Latest CI (host-ci, all completed/success):
  - 41957640034 pull_request `muse/wave6-cli-docs` 19s 2026-11-05T02:49:07Z
  - 41957636189 push `muse/wave6-cli-docs` 19s 2026-11-05T02:49:05Z
  - 41952599203 push `main` 24s 2026-11-05T02:03:07Z
  - 41949868767 push `main` 31s 2026-11-05T01:38:23Z
  - 41949799256 push `main` 34s 2026-11-05T01:37:47Z

Source: prior result 1.

## 2. Environment

| Component | Value | Evidence |
|---|---|---|
| Python | 3.14.4 | prior result 7 |
| pytest | 7.4.0 | prior result 7 |
| pytest config | `pyproject.toml [tool.pytest.ini_options] addopts="-q"`; prescribed CLI `-q` => effective `-qq` (no summary line) | prior result 7 |
| QNX SDK | present; `qnx_host=E:/qnx800/host/win64/x86_64`, `qnx_target=E:/qnx800/target/qnx` | prior result 4 |
| qcc | `E:/qnx800/host/win64/x86_64/usr/bin/qcc.EXE`, 12.2.0 `gcc_ntox86_64` default + `gcc_ntoaarch64le`/cxx/gpp variants; bare `qcc -V` lists targets on stderr with nonzero exit (expected, handled by probe) | prior result 4 |
| QNX env | `Test-Path E:\qnx800`=True; `QNX_HOST`/`QNX_TARGET` set; `Get-Command qcc` resolves to SDK path | prior result 4 |
| QEMU | present; `E:\VMs\qemu\qemu-system-x86_64.exe`, `QEMU emulator version 11.1.0 (v11.1.0-12130-ge470268ff4)`; process `qemu-system-x86_64` PID 26936 running since 05/11/2026 00:40:33 | prior result 4 |
| probe logic | `genesis-rt/host/genesis_rt/build_adapter.py probe()` inspected; no SSH attempted | prior result 4 |
| SSH reachability | NOT verified here (parent verifies separately) | prior result 4 unresolved |

## 3. Test baseline

- Prescribed run `python -m pytest tests/ -q -p no:warnings` in `genesis-rt/`: exit 0, 52.53s, output UTF-16 decoded (`$env:TEMP\pytest_full.txt`, 1298 bytes), 8 progress lines, marker regex `^[.sFxE]+` total 527: passes (dots) 527, skips 0, fails 0, errors 0.
- Cross-check `pytest tests/ -o addopts='' -q -p no:warnings`: exit 0, 52.32s, summary `527 passed in 51.51s`.
- Missing summary in prescribed run is expected (double `-q`); single-file probe `test_belt_sim.py` shows no summary under double `-q` but `6 passed` with `-o addopts='' -q`.
- No tests modified.
- Source: prior result 7.

Claim status: **527/527 PASS** (host suite, green).

## 4. Feature traceability matrix

Columns: feature | source | test | target execution | raw evidence | UI | docs | claim status.

| Feature | Source | Test | Target execution | Raw evidence | UI | Docs | Claim status |
|---|---|---|---|---|---|---|---|
| IR v1 validate | `host/genesis_rt/cli.py:15-27` via `ir.load_ir_file`; `ir.py:72-91,118-120` (JSON/YAML, schema_version==1) | host suite 527/527 (no per-feature split inspected) | n/a (host) | prior 6 | n/a | `TECHNICAL_EVIDENCE.md:6` cites `schemas/machine-ir-v1.schema.json`; `README.md:29` diagram `[Machine IR v1]` | SUPPORTED (v1 path) |
| IR v2 validate/generate | `cli.py:15-27,48-64` peek dispatch to `ir_v2.load_ir_v2_file` (JSON-only, `ir_v2.py:538-547`, schema_version==2); `_peek_schema_version cli.py:41-45` (.yaml forces v1) | `test_ir_v2.py` amr/conveyor fixtures only, no cell/presence test | n/a (host) | prior 6, 9 | n/a | `JUDGE_SCORECARD.md:9` "IR v2 E2E"; `TECHNICAL_EVIDENCE.md:27` codegen_v2 + guard v2 tail, 9/9 on v2 binary | SUPPORTED for non-cell; CELL/PRESENCE GAP (see §5.1) |
| IR v2 cell/presence_bool | `ir_v2.py:26-31` imports v1 kinds+types (incl. industrial_cell, presence_bool); `SENSOR_UNITS ir_v2.py:53-59` lacks presence_bool; `ir_v2.py:230-233,569,582` index => raw KeyError; `REQUIRED_TOP 88-102` no cell; migrate drops cell block silently | no v2 cell example; only `cell-ir.json` v1 | n/a | prior 9 | n/a | `machine-ir-v2.schema.json:17,56` narrows to 3 kinds/5 types but header says Python validator normative; `PROGRESS.md:493-494` claims v2 superset (out of docs scope) | GAP: raw KeyError unintended; must be IRValidationError or supported (prior 9 note) |
| CLI simulate | `cli.py:82-90` v1-only `load_ir_file` + hardcoded `run_scenario(ir,'nominal_navigation')`; parser `cli.py:168-169` IR arg only, no scenario flag | host suite (no CLI-scenario mapping inspected) | n/a | prior 6 | n/a | Run-tab static CLI text (studio.html) | GAP: v1-only, single scenario, v2 => IRValidationError exit 2 (`cli.py:189-195`) |
| CLI faults | `cli.py:93-103` v1-only + `faultlab.run_all(ir)` over `verification.scenarios` | host suite | n/a | prior 6 | n/a | `README.md:70` "8-scenario fault campaign" | GAP: v1-only; count mismatch 8 (docs) vs 14 code (10+4 cell) |
| Faultlab scenarios/oracles | `faultlab.py:60-77` SCENARIO_WINDOWS 14 (10 base+4 cell); `639-654` _ORACLES same 14; `run_all 657-659` runs listed only; `DEFAULT_SEEDS 1000+i` (:32) | host suite | n/a | prior 5, 6 | Lab tab renders scenarios from passport (local) | `README.md:70` 8-scenario; `TECHNICAL:17-23` matrix/interlock/device steps | SUPPORTED (14); DOC COUNT MISMATCH unresolved |
| Kind×scenario gating | `faultlab.py:84-109`: unknown=>ValueError; belt_jam non-conveyor=>crash; cell mismatch=>crash; cell->CellSim, conveyor->BeltSim, else DiffDriveSim | host suite | n/a | prior 6 | n/a | — | SUPPORTED (explicit crash dicts, plus load-time reject `ir.py:192-193`, `ir_v2.py:504-505`) |
| robotic_arm_virtual physics | `faultlab.py:106-109` else-branch => DiffDriveSim corridor, silent, no warning | no intent test inspected | n/a | prior 6 | n/a | — | UNKNOWN INTENT (verbatim unresolved) |
| Conveyor generic-nav cohabitation | allowed on BeltSim 1D, aided by `simulator.py:184-191` final_x/collision aliases | host suite | n/a | prior 6 | n/a | — | SUPPORTED (allowed) |
| Orchestrator pipeline | `orchestrator.py:95-99 run_pipeline(ir_path,artifacts_dir,run_id,scenarios,target_record,perf_record)`; `:118-130` v1/v2 dispatch; `:165-167` verification calls same `faultlab.run_all(ir)` even for v2 | host suite | n/a | prior 5, 6 | n/a | `architecture.md:38-39` validate→codegen→build→verify→evidence→gate (version-silent) | SUPPORTED with V2-VERIFICATION CONTRADICTION (CLI rejects v2, orchestrator runs it) |
| Fail-closed pipeline | `:102-109` invalid/colliding run_id => PipelineError; `:131-137` IR error writes failure.json + re-raise; `:144-172` codegen/verify exceptions => failure, never pass | host suite | n/a | prior 5 | n/a | — | SUPPORTED |
| Evidence chain/passport | `evidence.py:65-71` hash=sha256(canonical(body)+prev_hash), timestamps excluded (`:5-7`); `:85-106` build_passport ir/codegen/qnx_build/qnx_target/qnx_perf; `:107-114` pipeline_error + scenario bodies; `:136-157` verify_chain | host suite | n/a | prior 5 | Passport tab `verifyChainText` (genesis_verify.js:238-283); invalid chain empties Lab/Twin | — | SUPPORTED |
| Gate tiers/verdict | `gate.py:54-105` NONE<HOST_TESTED<QNX_COMPILED<QNX_EXECUTED<QNX_BEHAVIOR_VERIFIED<QNX_PERFORMANCE_MEASURED; `:83-100` target/perf binding gates; `:108-150` FAIL rules; `:156-178` qnx_verified/release_eligible + omitted-declared | host suite | n/a | prior 5 | n/a | `README.md:11` qnx_verified:true; scorecard:9 MEASURED replay | SUPPORTED (logic inspected; no live passport inspected) |
| Target/perf binding | `provenance.py:3-20` UNTRUSTED until bound; `:208-254` target binding (version/matrix/window/identity/digests/binaries/attribution/transcripts); `:257-305` perf binding (window/identity/raw_samples/recomputed dist/build-set equality); `:38-55` EXPECTED 16-step matrix; `:57` TARGET_PLATFORM qnx8_x86_64_qemu | host suite | 16-step matrix claimed | prior 5 | n/a | `TECHNICAL:17` 16-step SSH matrix; `TECHNICAL:21` sched p50 -45%/p99 -65% informational | SUPPORTED (validation logic); LIVE BINDING UNGROUNDED here |
| Build-set replay | `buildset.py:30-33` replay via `scripts/replay.py --build-set --source-passport`; `:72-79` build_id; `:97-99` entry verifies chain; `:147-221` check_build_set (attribution/cksum+size/REQUIRED_SECONDARIES/no reused primary) | host suite | claimed replay run-449210581ea2 | prior 5 | n/a | scorecard:9 "QNX_PERFORMANCE_MEASURED replay + tamper control" | PARTIAL: replay.py body not inspected (verbatim unresolved) |
| Planner (offline) | `planning.py:56-65` PROVIDERS={offline:BaselineProvider} → planner.propose; doc `:11-16` deterministic keyword, no network/paid API; `:68-105` refuse-unsafe + plan_machine validation | host suite | n/a | prior 5 | n/a | scorecard:12 "28-case planning eval 28/28 behind strict gate" | SUPPORTED as keyword-only; EVAL HARNESS + 28/28 LINKAGE not inspected; planner.propose internals not inspected (verbatim unresolved) |
| Adversarial suite | not in inspected code set | not inspected | n/a | — | n/a | scorecard:12 "18-test adversarial suite"; `TECHNICAL:28` red-green 2/6 FAIL | UNGROUNDED here |
| On-target matrix 16/16 | binding expects 16 steps (`provenance.py:38-55`) | n/a (target) | claimed 16/16 PASS, qcc 0 warnings, crash containment x3, sched 4x200, CELL_POLICY 12/12, faultinject 9/9, v2 9/9 | prior 5 docs refs | n/a | `README.md:11,87`, scorecard:9 verified col, `TECHNICAL:17-23,26-27` | CLAIMED; LIVE SSH/passport/transcript NOT inspected in this baseline |
| Crash containment | `faultlab.py:197-210,323-342` crash=>crash never pass; pass iff all oracles pass | host suite | claimed 3 steps freeze ≤3, NONGUARD=0 | prior 5 + `TECHNICAL:18-20` | n/a | `TECHNICAL:18-20`; scorecard:9 crash x3 | SUPPORTED (host logic); TARGET RUN ungrounded here |
| Supervisor respawn/giveup | — (target-side; not in inspected host set) | — | claimed matrix steps | — | n/a | `limitations-and-safety.md:18-19`; `TECHNICAL:26` RESPAWN×3+GIVE_UP | UNGROUNDED here (docs only) |
| Studio API | `api.py:89-91` GET /health; `:93-94` POST /runs; `:169-170` DELETE cancel→202; `:178-179` GET run; `:195-196` GET list; `:209-210` GET export; `:226-227` POST /compare; `:55,143` global _lock sync blocking; `:58-68,157-166,184/201/215/233` SQLite WAL `runs.db` history, no job queue | host suite | n/a | prior 2 | none live (zero fetch/XHR/WS refs in ui/) | — | SUPPORTED as sync+SQLite; GAPS: no async queue, cancel-while-blocked uninterleaved, no target_record/perf_record in RunRequest so MEASURED via API unevidenced |
| Studio UI | `studio.html` 7 tabs intent/source/twin/lab/passport/diff/run (`:37-45`; header `:3` says six-tab, stale); all tabs FileReader+local recompute/verify/render, Run tab static `<pre>` only | n/a (static) | n/a | prior 2 | 7 tabs, all static-local | — | SUPPORTED as static viewer; NO Studio→API wiring |

## 5. Gaps

### 5.1 CLI gaps

1. `simulate` and `faults` are v1-only (`cli.py:82-103` call `ir.load_ir_file` only). v2 docs fail with `IRValidationError` (exit 2 per `cli.py:189-195`). `validate`/`generate` dispatch v1/v2 correctly (`cli.py:15-27,48-64`).
2. `simulate` hardcodes `nominal_navigation` with no scenario flag (`cli.py:168-169` parser takes only `ir`). No CLI path for single crash-containment or fault-injection runs claimed in docs.
3. `_peek_schema_version` (`cli.py:41-45`): `.yaml/.yml` forces v1 (v2 JSON-only); JSON with missing `schema_version` => `None` => unsupported `IRValidationError`. Legacy-JSON / YAML-v2 intent unevidenced.
4. v2 cell/presence_bool crash: `SENSOR_UNITS` lacks `presence_bool`, but membership passes via v1 import, so `ir_v2.py:230-233,569,582` raise raw `KeyError` instead of `IRValidationError`; migrate drops v1 `cell` block silently (`ir_v2.py:621-661`). Prior 9 resolves the crash as definitively unintended; remaining choice is support-vs-clean-reject.
5. `robotic_arm_virtual` silently runs the `DiffDriveSim` corridor (`faultlab.py:106-109`) with no warning — intent unknown (verbatim unresolved).
6. Orchestrator/API vs CLI contradiction: `orchestrator.py:118-130,165-167` dispatches v1/v2 then calls the same `faultlab.run_all(ir)` for v2, while CLI `simulate`/`faults` cannot load v2. No evidence `faultlab` supports the v2 IR shape.
7. API tier reach: `RunRequest` (`example|ir|scenarios|run_id`) shows no `target_record`/`perf_record`, but `run_pipeline` tiers above `QNX_EXECUTED`/`BEHAVIOR_VERIFIED` require them — no evidence the API can produce a `MEASURED` passport.
8. Cancel-while-blocked: `POST /runs` holds the global `_lock` synchronously (`api.py:55,143`) with no queue, yet `DELETE` cancel + `GET` 202 active-poll exist — no evidence cancel can interleave a blocked run.

### 5.2 Docs gaps

1. STALE: `docs/limitations-and-safety.md:9` says "11-step matrix" while `README.md:11,87`, `JUDGE_SCORECARD.md:9`, `TECHNICAL_EVIDENCE.md:17` say 16/16 (16-step).
2. V1-ONLY vs v2 claims: `README.md:29` diagram pins `[Machine IR v1]` and `TECHNICAL_EVIDENCE.md:6` cites only `machine-ir-v1.schema.json`, while `JUDGE_SCORECARD.md:9` claims "IR v2 E2E" and `TECHNICAL_EVIDENCE.md:27` documents `codegen_v2` + `v2_transitions` step. `architecture.md:38-39` is version-silent (lists only `codegen.py`, no v2).
3. Count inventory (in-scope, current): tests 527/527, matrix 16/16, planning eval 28/28, adversarial 18-test, faults 8-scenario, sched 4x200 / 4 configs, cell 12/12, faultinject 9/9, v2 9/9, red-green 2/6 FAIL. Scenario mismatch: docs 8-scenario campaign vs code 14 (10 base + 4 cell); no 8-vs-10-vs-14 mapping inspected.
4. Studio header drift: `ui/studio.html:3` says "six-tab" but markup has seven tabs (run added).
5. Out-of-scope deferrals (verbatim unresolved): binaries built/staged count, benchmarks beyond sched contrast, stale tokens 11/11, 310, 6/6, 7/7 (see §7).
6. Branch-coverage caveat (prior 8): open PR #3 title ("Wave 6 A1/A2/A4: CLI v1/v2 consistency and doc drift") exactly matches these CLI/doc findings, but no PR-diff evidence was inspected; unknown whether gaps are already fixed on `muse/wave6-cli-docs`.

### 5.3 Codelab re-check note

- Docs claim a "verified 45-min codelab (Win+Linux)", "judge path is 2 commands", "suite 527/527" (`JUDGE_SCORECARD.md:10`), plus "8 use cases", "~45-min onboarding measured", "2-3 pilots" (`:11`).
- This baseline did NOT re-run the codelab. What is verified here is consistent with the judge path's suite leg (527/527 host pass, §3; QNX SDK + QEMU present, §2) but does not verify the 45-minute timing, the 2-command judge path end-to-end, Windows+Linux coverage, or the 8 use cases / pilots.
- Re-check needed in Wave 7: run the documented judge path verbatim (both commands), time onboarding, and confirm codelab steps against this HEAD (`e477587`) on the target matrix path, with SSH reachability verified by the parent.

## 6. Milestone readiness notes

- Host baseline is GREEN: 527/527, clean tree, 5/5 host-ci success, QNX SDK 12.2.0 + QEMU 11.1.0 present with a running QEMU process.
- Evidence pipeline logic (chain, passport, gate tiers, target/perf binding, build-set checks, fail-closed paths, offline planner) is inspected and coherent; 16-step `EXPECTED_TARGET_CHECKS` matches the 16/16 doc claims at the logic level.
- Blockers / must-fix before milestone sign-off:
  1. v2 `presence_bool`/cell raw `KeyError` → close as support or clean `IRValidationError` (§5.1.4).
  2. CLI v1-only `simulate`/`faults` + hardcoded scenario (§5.1.1–5.1.2) and the orchestrator-vs-CLI v2 contradiction (§5.1.6).
  3. Stale 11-step line + V1-only diagram/schema refs (§5.2.1–5.2.2).
  4. Live on-target grounding: 16/16 PASS, MEASURED replay, qcc 0 warnings, staged binaries, transcript digests — none inspected live here (SSH by parent; passport/transcript/replay artifacts still to anchor in Wave 7).
  5. Studio↔API disconnect + API MEASURED reachability + cancel-while-blocked (§5.1.7–5.1.8, §4 Studio rows).
  6. Count grounding: 8 vs 14 scenarios; 28/28 planning eval harness; 18-test adversarial suite; sched/cell/faultinject/v2/red-green target numbers (§5.2.3, §4).
- PR #3 (`muse/wave6-cli-docs`) may already address A1/A2/A4 CLI/docs items — diff must be inspected before duplicating fixes.

## 7. Unresolved (verbatim carry)

- Intended physics for robotic_arm_virtual: code silently uses DiffDriveSim corridor; no comment/example/test inspected states whether this aliasing is intentional or a placeholder.
- Binaries built/staged count: NO claim found in the 5 scoped files (only 'binaries hashed' in TECHNICAL_EVIDENCE.md:29, no number). Counts like '7 binaires'/'6 binaires' live in docs/PROGRESS.md:326,370,564 — out of scope.
- Benchmarks beyond sched contrast: no separate benchmark-suite count in scoped files; only p50/p99 deltas (:21) and 4x200 campaign (scorecard:9).
- Stale tokens 11/11, 310, 6/6, 7/7: ABSENT from all 5 scoped files (verified by search); they survive only in docs/PROGRESS.md and docs/superpowers/plans (out of scope). Closest stale residue inside scope is '11-step matrix' (limitations-and-safety.md:9).
- live SSH reachability (parent verifies separately)
- Replay CLI completeness: buildset.py:30-33 cites scripts/replay.py --build-set --source-passport but script body outside assigned 7-file set, not inspected
- SCENARIO_IDS/CELL_SCENARIO_IDS canonical list and guard_limits in ir.py not in assigned set; 14-count inferred from faultlab SCENARIO_WINDOWS/_ORACLES maps
- Offline keyword planner internals in planner.py (propose) not in assigned set; confirmed only as keyword/no-network via planning.py docstring + delegation
- critic: missing complete evidence result

Note: the handoff's prior result 8 (critic) WAS readable in this run and is incorporated above (§5–§6 caveats); the last bullet is carried verbatim per instruction regardless.

## 8. Sources

- Prior result 1 (repo state), 7 (test baseline), 6 (CLI gaps), 3 (docs gaps), 2 (studio/API), 4 (QNX env), 5 (evidence core), 8 (critic cross-check), 9 (v2 cell/presence).
- Handoff files read via `muse.read_file` to completion (no "(more lines below)" remaining on either file).
- No repo edits except this file; no SSH attempts; no tests modified.
