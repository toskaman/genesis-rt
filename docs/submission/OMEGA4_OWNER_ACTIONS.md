# OMEGA4 owner actions (human-only, NOT done by automation)

Date: 9 Nov 2026. Branch `titan-omega4` (commit `144c693` at writing).
Nothing below is authorized for agents: do each item yourself, in order.

## 1. Final video (DEFERRED_BY_OWNER, blocks submission)

- Record < 3 min, real product on its real platform (Studio +
  QNX evidence), upload PUBLIC to YouTube.
- Storyboard/shot list: see prior waves' video-production notes
  (repo-external). Do NOT present the W12 cut as final.
- Until done: `SUBMISSION_STATUS = PENDING_FINAL_VIDEO`.

## 2. Devpost submission (after the video exists)

- Canonical text: `docs/submission/DEVPOST_FINAL_DRAFT.md` (v8-synced).
- Category: `Developer Tooling & Host Tools`.
- Bonus fields (if the rules permit two selections): QNX-specific
  Technologies (primary) + Codelab/Tutorial (second). Only ONE bonus
  can be won — never imply both.
- Codelab URL goes in the correct Devpost field; video URL likewise.
- Submit BEFORE 15 Dec 2026 14:00 EST / 20:00 Paris. Keep the repo
  public and available through judging (29 Jan 2027).

## 3. Human pilot (quick tier; nothing sent or faked)

- Status: `HUMAN USER BENEFIT NOT YET MEASURED`. Zero participants,
  zero invitations sent, zero records in `bench/`.
- Protocol + timer + analyzer validated on fixtures only:
  `docs/business/pilot-study.md`, `bench/productivity/`.
- To run: follow the pilot-study consent + anonymization checklist,
  recruit TWO independent teams for the 3 quick tasks (generate,
  campaign, evidence) in both lanes. That earns
  `QUICK_PAIRED_PILOT` — never `INDEPENDENT_PILOT_COMPLETE`
  (needs all six tasks) and never a generalization claim.
- Invitation draft: inside `pilot-study.md`. Send it yourself;
  no agent may contact anyone.

## 4. QNX target password rotation (security)

- The QNX image still boots with its DEFAULT password. Rotate it:
  procedure in `docs/security/QNX_PASSWORD_ROTATION.md`.
- Export per session only: `$env:GENESIS_TARGET_PASSWORD = '...'`
  (PowerShell) — never commit it, never put it in repo files.
- No agent will ever read, request, or store the new password.

## 5. `cryptography>=49` floor (global interpreter — owner command only)

- Measured 9 Nov 2026: `cryptography 43.0.3` in the GLOBAL
  interpreter (`C:\Users\TheBox\AppData\Local\Python\pythoncore-3.14-64\`).
  No project venv exists, so agents must NOT upgrade it.
- Run yourself (сlose other Python work first):
  `py -m pip install -U "cryptography>=49"`, then
  `py -c "import cryptography; print(cryptography.__version__)"`
  and confirm `>= 49`.
- Residual until done: the declared floor is aspirational in
  this environment; hash-only pack verification does not depend
  on it (packs are UNSIGNED by design, see §7).

## 6. Release / tag (deferred while video + submission pending)

- Do NOT create a release or tag until the video is uploaded
  AND Devpost is submitted. Then tag from green `main`.

## 7. Explicitly NOT required (do not do)

- No native CI runner exists (`.github/workflows/qnx.yml` is
  BUILD-ONLY by design). Do not register one casually: licensed
  SDK + untrusted PR code = exfiltration risk. Owner-machine
  campaigns + hash-only packs are the current provenance story.
- No target C changes in OMEGA4: no fresh QEMU campaign needed
  (Omega2 packs re-verified VERIFY OK 16/16 on 9 Nov 2026).
- No paid APIs, no new model downloads needed (local Ollama
  `qwen2.5:7b-instruct` + `llama3.1:8b-instruct-q4_K_M` used).
