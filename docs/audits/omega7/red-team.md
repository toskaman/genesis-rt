# GENESIS RT (titan/omega7-v10-stale-arm) — OMEGA7 Red-Team Audit

> **LANDING NOTE (10 Nov 2026, landing reviewer — not the auditor):**
> the original report below is TRUNCATED mid-sentence at "1525/61 pins/r"
> (criterion 1 of §4; §§4-rest/5/6/7 were never written — the cited
> falsification/evidence sections exist only as references). Landing
> independently reproduced the two cited probes: M4 (`55640be` message
> digests match no computable form — CONFIRMED, dated note in
> `docs/audits/OMEGA7_AI_EVALUATION.md`) and Q1/B4 (`physics_note`
> dropped by `build_passport` — CONFIRMED and FIXED: propagation +
> regression test in this branch). Hostile total 27.5/40 per the
> agent's structured result (per-criterion split beyond Tech 8.5 not
> preserved in-file). Original follows verbatim.

Branch read via private scratch worktree at detached `7cb64d7` (== `origin/titan/omega7-v10-stale-arm` tip; shared checkout untouched, worktree removed after). Prior packets 1–4 (arm brief, v10 author, fixer, stale agent) read first via the handoff index; every claim below was re-grounded independently — implementer evidence treated as discovery pointers only.

Claim labels: **VERIFIED FACT** (inspected source / executed command), **OBSERVATION** (inference from inspected evidence), **ASSUMPTION** (unverified). Confidence high/med/low. All `genesis-rt/` paths are at `7cb64d7` unless a commit is named. Frozen evals v4–v9 were never opened for content; v10 dataset/results JSON was read and executed **only** to verify reported numbers (counts, IDs, error strings — never case phrasings, never to tune).

## 1. Perspective A — Product / impact judge ("who is this for, and does it matter?")

**A1. Zero humans, unchanged — the Impact cell is still hollow.**
No pilot, invitation, buyer conversation, cold reader, or screen-reader session was added; `HUMAN USER BENEFIT NOT YET MEASURED` still governs and the video is still `DEFERRED BY OWNER` (VERIFIED FACT, high: `genesis-rt/docs/jury/JUDGE_SCORECARD.md:1-60`). A product judge files this under "impressive prototype, no evidence of use" exactly as in OMEGA6. OBSERVATION (high): OMEGA7 spent its runway on measurement integrity, which earns trust but zero Impact points.

**A2. Unsafe accepts 5 → 15 is the new debate exhibit.**
The audited unsafe count tripled in absolute terms and the rate rose 4.5% → 11.0% (5/112 → 15/136), all 15 reproduced by this auditor on all three providers with identical IDs (VERIFIED FACT, high: `v10-240..245,265,271,273,277,289,290,294,296,297`; raw `evals/results/2026-11-10-omega7-v10/*.json`). The "harder targeted set" defense is process, not results: a hostile judge scores the number, and 9 of the 15 sit in known-dispute classes (6 unit-omission + 1 JSON-speed omission + 2 documented unicode residuals) that still accept unsafe input today (VERIFIED FACT, high: `genesis-rt/docs/audits/OMEGA7_AI_EVALUATION.md:126-170`).

**A3. STALE is still prose — the strongest claim still has the weakest artifact.**
No sealed stale-control transcript exists on disk (only BEFORE/AFTER + historical packs in `evidence/`), CLAIMS.md still says "prose-grade, no sealed transcript ships in the packs; sealing it is future work", and backlog B-13 is still open (VERIFIED FACT, high: `genesis-rt/docs/CLAIMS.md:50-54`, `genesis-rt/docs/audits/titanv3/backlog.md:165-180`). 35 green tests prove the sealing *path* on synthetic data only. OBSERVATION (high): a product judge cannot distinguish "built, awaiting a 15-minute owner run" from "not done".

**A4. Arm verdicts now fail closed — the one product-visible trust gain.**
An end-to-end arm campaign now earns FAIL with an explicit `quarantined physics` reason instead of a green PASS on car physics, verified live in this session; native verdicts are unaffected (VERIFIED FACT, high: probe at §6/Q1; `genesis-rt/host/genesis_rt/gate.py:159-184`). The jury copy now discloses the finding it previously omitted entirely (VERIFIED FACT, high: `2b60f02`, `genesis-rt/docs/jury/KNOWN_LIMITATIONS.md`). OBSERVATION (med): this is the only OMEGA7 change a stranger can *see* without reading an audit.

**A5. Bare tier-2 nouns now work on real models (6/6) — a small real UX fix.**
`valid-tier2` went 0/6 offline to 6/6 on both models with exactly-once consults and documented defaults (VERIFIED FACT, high: raw results summaries; rule-23 tests `genesis-rt/tests/unit/test_llm_provider.py`). OBSERVATION (low): genuine, but it serves the demo script more than any user.

**A6. No filing progress — award probability is still administratively zero.**
No video, no filed entry, no rules re-check observable from this branch (VERIFIED FACT, high: scorecard "submission pending the video", `genesis-rt/docs/jury/JUDGE_SCORECARD.md:50-60`). Everything below scores a hypothetical filed entry, not an entry.

## 2. Perspective B — Technical expert ("is it real engineering, and is it sound?")

**B1. The v10 measurement reproduced bit-identically on all three providers — the strongest verification this session.**
Independent re-runs at tip (offline exit 0; qwen/llama exit 1 by design) reproduced every committed row: pass/fail, error text, consult counts, wrong-kind flags — 0 diffs over 184×3 rows; same 15 unsafe IDs, same 3 unexpected-consult IDs, same veto totals (VERIFIED FACT, high: §6/M1–M3; `genesis-rt/scripts/eval_planner.py:140-200`). OBSERVATION (high): fabrication is falsified, not merely doubted. Temperature 0 is pinned in code (`genesis-rt/host/genesis_rt/planning.py:545`).

**B2. Frozen-before-fix was honored, with one broken link.**
Commit order is `45a95f0` v10 freeze → `b8178f1` v1.4 contract → rules 19–23 → `5eace86` pin → arm → `55640be` measurement; the dataset file was touched by exactly one commit ever, and file sha256 == `.SHA256` == freeze message `d550b802…` (VERIFIED FACT, high: `git log --oneline --reverse 45a95f0..7cb64d7`, `git log --all -- evals/planning_holdout_v10.json`). Author blindness rests on the PROVENANCE statement (contract-only inputs, sources enumerated) — process evidence, not repo-verifiable (OBSERVATION, high: trustable only if delegation is trusted, U4).

**B3. The measurement commit's digest strings are unverifiable (WOUNDED).**
`55640be`'s message lists three full sha256 digests that match **no** computable form of the committed files (raw, newline-stripped, LF-normalized, canonical-JSON all tested — NONE, VERIFIED FACT, high: §6/M4). Integrity still holds three other ways (single-commit files never modified, tip re-runs bit-identical, fixer-reported short digests `b795e82f/31f68c44/ebf3fe2e` verified correct), but the belt-and-suspenders record in the message is broken. OBSERVATION (med): likely digests of pre-commit bytes; provenance unknown (U6).

**B4. The arm quarantine is half a gate in the real pipeline (WOUNDED).**
Live probe: faultlab stamps `physics_note` on arm results, but `build_passport` drops it, so the `physics_note` OR-branch fires only on hand-built passports; the kind branch carries the quarantine end to end (VERIFIED FACT, high: §6/Q1). The limitation is disclosed honestly in docs and prior results — the wound is in the code, not the candor. Sealed-body propagation is the follow-up.

**B5. The veto metric conflates two phenomena; the published split is reproducible but unpinned.**
`veto_refusals` counts any error containing veto vocabulary (VERIFIED FACT, high: `genesis-rt/scripts/eval_planner.py:155-159`). The audit's "qwen 31 = 17 det + 14 echo; llama 34 = 27 + 7 (+1 guard echo)" split reproduces exactly via message-text classes (`llm refused: …` shorts vs deterministic longs; v10-139's `llm refused: remove the guard` sits outside the metric) (VERIFIED FACT, high: §6/M5). OBSERVATION (med): the split method lives in prose, not in the harness — a re-analyst must rediscover it.

**B6. Full-suite green is implementer-reported; this session verified the fast subset + counts.**
`tests/` collects exactly 1525 (103-file sum reconciled after excluding a PowerShell error-line artifact), planning 113, stale 35, docs pins 61/61 green, ruff gate clean (same 0.17.4 + select as CI), both Omega2 packs VERIFY OK 16/16 (34/34, 36/36 files), and a 200-test subset (planning + banner + oracles) + gate/stale/freeze suites all exit 0 (VERIFIED FACT, high: §6/C1–C4). The full 1525 and the SDK-free lane were not executed here (U1, U2).

## 3. Perspective C — Sponsor / competition evaluator ("does this serve QNX and the rules?")

**C1. QNX depth is unchanged and intact: no target changes, packs re-verify.**
`target/` untouched (0 commits since `318d46b` per prior result; both Omega2 verifiers re-ran VERIFY OK on this tree, exit 0) (VERIFIED FACT, high: §6/C4). OBSERVATION (med): OMEGA7 neither advanced nor risked the native story — pure host-side branch.

**C2. B-13 is still the credibility keystone, still unsealed.**
The negative control that most needs a sealed transcript is exactly the one without it; the owner handoff (`omega7-research/stale-blocker.md`) is precise and the code is ready, but readiness is not evidence (VERIFIED FACT, high: B-13 open, no pack on disk). OBSERVATION (high): a sponsor judge skimming for "one hostile skim from fabricated" now lands on the stale control, not the arm verdict — the quarantine moved the weakest link, it did not remove it.

**C3. The honesty architecture keeps arming the deductions — and that is the moat.**
Unsafe-15, the half-gate, the unsealed STALE, the conflated veto metric, the 1434/1428 snapshot leftover (confirmed present exactly as disclosed, `genesis-rt/docs/jury/JUDGE_SCORECARD.md:31`) — every deduction in this report is sourced to the project's own disclosures (VERIFIED FACT, high). OBSERVATION (high): under hostile scoring this floor of trustworthiness is why the entry keeps its points.

**C4. Unsafe-15 optics are bad for a safety-adjacent sponsor story.**
6 of the 15 are genuinely new gap classes (Taktzeit vocab, parens-carrier scope ×2, coordination ×3) disclosed as v11 follow-ups with no v11 branch (VERIFIED FACT, high: `genesis-rt/docs/audits/OMEGA7_AI_EVALUATION.md:126-170`). OBSERVATION (med): "we found 6 new holes and scheduled nothing" reads worse than "5 known holes" to a non-technical evaluator, however honest the methodology.

**C5. Competition hygiene: freeze policy held under pressure.**
No file under `evals/results/` was ever modified (all additions); only `55640be` touched results on this branch; planner/validator/eval-script diff between measurement and tip is empty; the one pinned-test edit is a coherent rule-18-literal move with fail-closed re-pinning (VERIFIED FACT, high: §6/H1–H3). OBSERVATION (high): this is competition-grade process evidence — the v10 rule survived its first real test.

**C6. Methodology is now the entry's most defensible asset.**
Separately-authored blind set, frozen-before-fix ordering, enforced consult expectations (exit 1 fired as designed, 0 missing), triple independent reproduction, published raws (VERIFIED FACT, high: §§6–7). OBSERVATION (med): no inspected rival narrative in prior surveys pairs a blind loop with third-party reproduction; the novelty claim is narrow but real.

## 4. Official QNX criteria — hostile INTERNAL scoring (prefer the competitor)

Weights 25% × 4, vs OMEGA6 hostile 8.0 + 7.0 + 4.5 + 7.5 = **27.0/40**.

### Criterion 1 — Technological Implementation: 8.5 (+0.5)

- *Conceded.* Arm verdicts fail closed live; the v10 blind loop ran end to end with enforced consults and triple reproduction; stale sealing path built + tested (35); 1525/61 pins/r