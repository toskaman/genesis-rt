# Buyer interview guide (GENESIS RT)

Status: template, zero interviews conducted. 30 minutes, one
engineering manager or tech lead per session. Record only with
permission; notes are shared back for correction and anonymized
as team codes before any wider use.

## Opening (2 min)

"We're testing whether evidence-driven verification saves real
engineering time on QNX controller work. There is no pitch at
the end — we want your workflow as it actually runs today."

## Current practice (12 min)

1. Walk me through your last controller change: spec edit to
   "we trust this" — who touched it, what did they run?
2. Where does verification evidence live today (CI logs, docs,
   tickets, heads)? Who re-verifies it, and how long does that
   take?
3. Last escaped defect from a controller change: what slipped
   through, and what check would have caught it?
4. Which step do engineers visibly dread or skip under deadline?

## Reaction to GENESIS RT (12 min)

Demo (5 min max): change a limit in the IR, rebuild, show the
before/after passports + the review brief. Then:

5. Which part of that maps to a chore your team does monthly?
6. What would block adoption in your shop (toolchain, process,
   trust, licensing, target access)?
7. Who else would need to say yes (QA, safety, management)?
8. Budget reality check: whose budget would a verification tool
   come from, and what did you last pay for in that category?

## Close (4 min)

9. If we ran a two-half-day pilot (see `pilot-study.md`), who
   would be the operator and the reviewer on your side?
10. May we follow up in two weeks with the pilot invitation?

## After the call

Fill within 24h: team code, date, role of interviewee, current
toolchain (1 line), top pain (1 line), adoption blockers
(ranked), pilot interest (yes/maybe/no + reason). No names in
the shared notes.
