# 10 hardest questions, answered live vs the product (OMEGA6 F3)

Date: 9 Nov 2026, branch `titan/omega6-product-proof`. Each lens
from `v4-output/report-H-jury.md` §"10 lenses" is answered
against the running product, not the docs. Gaps stay open
until they are measured, not when they are written about.

1. Product/impact — "Who has used this for real work?"
   Live: nobody — `HUMAN USER BENEFIT NOT YET MEASURED`
   still governs; the pilot kit exists (`docs/business/pilot-study.md`)
   with zero invitations sent. E3 added persona/buyer prose,
   which is positioning, not evidence.
   GAP: owner-run quick-tier pilot (unchanged, binding).

2. Technical — "Prove it ran on QNX, not just your laptop."
   Live: `python evidence/qnx8-x86_64-omega2-after/verify.py …`
   → VERIFY OK, 16/16, `qnx_verified=True` (re-ran this
   branch, both packs). New: `WHY_QNX.md` footprint table
   (measured `size` output), SSE page bound, dossier
   traversal fix — all tested. Single-host provenance stands.
   GAP: second-host record unfilled (owner).

3. Innovation — "What is non-obvious, and what did you do
   about the 5 unsafe accepts?" Live: stale refusal +
   contract-knob verdict + offline passports, all runnable
   above; unsafe accepts still 5/112 on frozen v9 (no
   planner touch this branch — forbidden). New: the v10
   trigger rule is pinned in `KNOWN_LIMITATIONS.md`.
   GAP: v10 fix-then-measure cycle (HIGH-RISK, post-filing).

4. UX — "Prove a cold judge can use this." Live: CLOSED
   substantially — the Prove button is now really clicked
   in Chromium (`test_prove_browser.py`, 9 tests: card,
   empty/loading/error states, 320/390/1366, keyboard-only
   path, zoom 200/400, ran-where labels), K1 hero on the
   landing page, hero line + 30 s card on all front doors.
   GAP: no screen-reader session (protocol ready, human
   pending), no cold-read proof (owner recruits).

5. Reliability/security — "Is it flaky? Is it patched?"
   Live: the race-distribution flake is fixed (A1, 20× loop
   green); traversal/ZIP-slip hardened (A3, was genuinely
   exploitable via `../`); Studio XSS audited + hostile-name
   card test; `pip-audit` runs in CI (non-blocking) with a
   dated triage note. GAP: global-interpreter crypto 43.0.3
   (owner-only upgrade).

6. Sponsor — "Why is this a QNX entry, not a Python demo?"
   Live: 6 binaries built with `qcc -Vgcc_ntox86_64`
   (0 warnings) 9 Nov 2026 + measured footprint; IPC/resmgr/
   supervisor/faultinject matrix 16/16 in committed packs;
   B2-first surfacing pinned. QEMU-only, labeled.
   GAP: no real-hardware timing (structural, disclosed).

7. Demo — "Show me in 60 seconds." Live: CLOSED for the
   product half — hook + WOW + browser proof run in under
   10 s of product time (`DEMO_BEATS_TIMED.md`), fallback
   ladder rehearsed incl. backend-dead (`DEMO_FALLBACK_LADDER.md`).
   GAP: final video (owner-deferred, binding blocker).

8. Commercial — "Who pays, and why do you win?" Live:
   persona (controls/verification lead) + buyer hypothesis
   (open-core, UNVALIDATED) + win/loss table + 18/18
   bit-rebuild receipt are now in the Final Draft — all
   labeled prose. GAP: zero buyer conversations, zero
   pilots (owner).

9. Compliance — "Is it filed and eligible?" Live: filing-day
   checklist dry-run recorded (G3), freeze note thru Jan 29
   (G4), old-draft banner points at the canonical draft.
   GAP: video + Devpost filing + eligibility self-confirms
   (all owner-only, deadline 15 Dec 2026 14:00 ET).

10. Skeptical generalist — "Why should I remember this?"
    Live: "The wrong binary cannot pass" — now demonstrated
    live in 0.0 s by `scripts/demo_stale_refusal.py` (host
    digest refusal) with the archived 14/16 behavioral
    refusal one replay away; hero line front-doored
    everywhere. GAP: cold-read proof that the line lands
    (owner recruits one non-author human).
