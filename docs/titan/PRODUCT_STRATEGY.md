# GENESIS RT — Product strategy: exactly three choices (Wave 12 §14)

Status: decision record, 2026-11-06. Selects ONE primary
direction. Supporting capabilities from the other two may be
retained, but there will be no three disconnected products.

## 1. Candidates

- **A. ProofOS Continuous Verification.** Deep CI integration,
  verification plans, evidence-based release decisions, QNX
  target verification in the review flow. (Wave 12 §§6–11.)
- **B. Fault Intelligence Platform.** Advanced counterexample
  discovery, fault shrinking, root-cause analysis, regression
  automation on top of the existing explorer.
- **C. Industrial Twin Studio.** Multiple virtual machines with
  native QNX coordination and synchronized evidence
  visualization.

## 2. Scoring

Weights: Grand Prize alignment 35%, eligible bonus value 30%,
demonstration impact 20%, commercial potential 15%. Scores are
0–10 judgments with reasons; only ONE bonus prize per project
is allowed (rules), so bonus value scores the single best
bonus each direction can credibly chase.

| Criterion (weight) | A. ProofOS | B. Fault Intel | C. Twin Studio |
|---|---|---|---|
| Grand Prize alignment (35%) | 9 — spans all four criteria: native tech, review UX, pilot-ready impact, deterministic innovation | 7 — strong tech/innovation, weaker design/impact without a review story | 6 — strong design/demo, thinner tech depth per machine |
| Eligible bonus value (30%) | 9 — Best Use of QNX-specific Technologies (native CI loop, IPC timeline, runner); codelab stays eligible as the single bonus pick | 6 — QNX bonus plausible but fault-shrinking is host-heavy; weaker QNX-specificity | 5 — visual breadth dilutes the QNX-specific story |
| Demonstration impact (20%) | 9 — change → plan → native proof → review brief in one flow; the 15-second WOW is a real verdict | 7 — shrinking demos well but needs setup narration | 8 — multi-machine visuals impress fast, explain slow |
| Commercial potential (15%) | 9 — CI-integrated verification is the budgeted pain (see venture thesis §2.A); pilot kit already targets it | 6 — valuable but narrower buyer (verification specialists) | 5 — twin breadth without depth risks "demo, not tool" |
| **Weighted total** | **9.00** | **6.55** | **5.85** |

Totals: A = .35*9+.30*9+.20*9+.15*9 = 9.00;
B = .35*7+.30*6+.20*7+.15*6 = 6.55;
C = .35*6+.30*5+.20*8+.15*5 = 5.85.

## 3. Assumptions

1. Judges reward a complete verifiable loop over feature count
   (consistent with Waves 9–11 feedback themes).
2. The QNX-specific bonus is the highest-expected-value single
   bonus (native depth is demonstrated; tutorial bonus stays
   eligible via the two codelabs but is picked only if the
   QNX-bonus case weakens).
3. Commercial buyers pay for review/CI workflow integration,
   not for visualizations (per buyer personas; unmeasured —
   pilot survey Q7 will test it).
4. Team capacity is one flagship direction; breadth would
   degrade the flagship release (Wave 12 §17 deferral rule).

## 4. Sensitivity

- If commercial weight doubled (15→30, renormalized), A still
  wins (A 9.00 vs B 6.44 vs C 5.63) — A's lead is broad-based.
- If demonstration impact dominated (50%), C rises to second
  (C 7.05) but A still leads (8.55): A's demo is both fast
  and substantive.
- B wins only if Grand Prize alignment is ignored entirely
  AND fault-depth is weighted above all else — an implausible
  judging model. C wins under no plausible weighting.
- The decision flips only if assumption 2 fails (QNX-bonus
  case collapses) — monitored via the QNX technical moat doc
  and native re-verification in T+28-34.

## 5. Decision

**Primary direction: A. ProofOS Continuous Verification.**

Retained from B: counterexample explorer, bounded oracles, and
regression persistence stay as the diagnosis layer inside the
ProofOS flow (already integrated; no new platform).
Retained from C: the single-machine Digital Twin stays as the
trace-diagnosis view; multi-machine coordination is NOT built.
Deferred, not started: second industrial scenario (§17) —
revisit only after pilots validate assumption 3.

## 6. What this means for the rest of Wave 12

T+28-34 and T+34-36 spend goes to: native re-verification of
the ProofOS-touched paths, review-flow E2E, the 30-question
gauntlet, and release packaging — not to B/C breadth. Any new
feature proposal must name which ProofOS review step it
improves or be deferred.
