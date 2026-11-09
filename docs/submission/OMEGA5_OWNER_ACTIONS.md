# OMEGA5 owner actions (human-only, NOT done by automation)

Date: 9 Nov 2026. Branch `titan-omega5` (from `main` @ `eacab88`).
Supersedes `OMEGA4_OWNER_ACTIONS.md` as the checklist; that file stays
as history. Nothing below is authorized for agents.

## 0. Rules recheck (9 Nov 2026)

Official announcements (live rules page bot-guards automated fetch;
verify by hand before submitting): deadline **15 Dec 2026** (assume
14:00 EST / 20:00 Paris unless the page says otherwise); winners Feb
2027; criteria technological implementation / design / potential
impact / quality of idea; category `Developer Tooling & Host Tools`;
bonuses incl. Codelab/Tutorial + QNX-specific Technologies; only ONE
bonus winnable per project. Keep the repo public through judging.

## 1. Final video (DEFERRED_BY_OWNER, blocks submission)

Hard requirements: < 3 min, actual current product, real QNX/QEMU
evidence, public YouTube URL in the Devpost video field.

Capture checklist (prepare only — no agent records anything):

1. Studio start page → flagship Omega2 BEFORE/AFTER pair (both
   packs, `VERIFY OK`, 16/16 matrix, qnx_verified=True).
2. BEFORE→AFTER behavior change (v1→v2 guarded transitions) +
   the stale-binary rejection (state it is operator-recorded).
3. Machine Designer: valid contract → generated QNX C → build
   provenance (qcc 12.2.0, 0 warnings).
4. Target Runner states (READY/RUNNING/QNX_VERIFIED) OR the
   archived-evidence replay when the target is down — label
   honestly which one the viewer sees.
5. Passport explorer: hash chain + offline replay + release verdict.
6. Planner safety demo (optional, 15 s): an unsafe request refused
   with its explanation; a valid request accepted.
7. Closing card: Apache-2.0, repo URL, QEMU-only + no-certification
   + no-human-data limitations (one line each).

Storyboard timing: 0:00-0:20 problem+promise; 0:20-1:10 native
proof; 1:10-2:00 change-verification story; 2:00-2:40 evidence +
safety; 2:40-2:55 limitations + repo; ≤ 2:55 total. Do NOT reuse
the W12 cut as final. Until done: `SUBMISSION_PENDING_FINAL_VIDEO`.

## 2. Devpost submission (after the video exists)

- Canonical text: `docs/submission/DEVPOST_FINAL_DRAFT.md`.
- Codelab URL + video URL in their Devpost fields.
- Submit BEFORE the deadline; keep repo + evidence available.

## 3. Human pilot (quick paired tier)

- Status: `HUMAN USER BENEFIT NOT YET MEASURED`. Zero participants,
  zero invitations, zero records. Protocol/timer/analyzer validated
  on fixtures only (`docs/business/pilot-study.md`).
- Your lane: recruit TWO independent teams; 3 quick tasks (generate,
  campaign, evidence) × both lanes; consent + anonymization per the
  checklist; verify timer output before aggregation. Earns at most
  `QUICK_PAIRED_PILOT` — never a generalization claim.
- Agents send nothing and fabricate nothing.

## 4. QNX target password rotation (security)

- Image still boots with its DEFAULT password. Procedure:
  `docs/security/QNX_PASSWORD_ROTATION.md`. Export per session
  only (`$env:GENESIS_TARGET_PASSWORD`), never in repo files.
  No agent will read, request, or store the new password.

## 5. `cryptography` floor (global interpreter — owner command only)

- This box: 43.0.3 (10 known vulns). Lock + CI: 50.0.2.
- Run yourself: `py -m pip install -U "cryptography==50.0.2"`,
  then confirm `50.0.2`. No agent touches the global interpreter.

## 6. Release / tag

- Forbidden until video uploaded AND Devpost submitted. Then tag
  from green `main`. No agent creates releases or tags.

## 7. Explicitly NOT required

- No native CI runner (BUILD-ONLY by design; untrusted-PR +
  licensed-SDK exfiltration risk). No fresh QEMU campaign needed
  in OMEGA5 unless `target/` changes (packs re-verified VERIFY OK
  16/16 on the OMEGA5 branch). No paid APIs or new models.
