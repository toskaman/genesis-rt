# QNX Global Hackathon — Forensics Refresh (9 Nov 2026)

> Baseline: `hackathon-knowledge/COMPETITION_COMPLIANCE_MATRIX.md` (verified 9 Nov 2026).
> This refresh re-fetched both official bodies the same day and re-checked GENESIS RT evidence paths (read-only).
> **Result: NO CHANGES vs baseline. All competition facts re-confirmed.**
> Hard rules honored: no contact, no submissions, no media production, no releases/tags, no secrets,
> no history rewrites; `genesis-rt/` touched read-only; this file is the only write, under `v3-research/`.

## 0. Provenance

| Source | Method | Result |
|---|---|---|
| [Official Rules](https://qnx.devpost.com/rules) (S1) | Direct fetch, 200 OK, ~660 lines read in full (§§1–15) | VERIFIED FACT (high) |
| [Homepage](https://qnx.devpost.com/) (S2) | Direct fetch HTTP 403 (bot protection); re-read in full via text-reader proxy of identical URL | VERIFIED FACT (high) |
| GENESIS RT local evidence | Read-only listing + LICENSE head read 9 Nov 2026 | VERIFIED FACT (high) |

Rules-reminder carried forward: Rules amendable at any time, effective on posting (§11.5); Rules prevail over homepage/form on conflict (§11.4). Owner must re-open S1+S2 in a browser ~1 week before 15 Dec 2026.

## 1. Change log vs baseline — NONE

Every item below was compared line-by-line against the baseline matrix. No date, weight, prize, category, field, or rule-text change was found.

## 2. Re-verified competition facts (all VERIFIED FACT, high, unless labeled)

### Timeline (S1 §1) — Eastern Time

- Registration + Submission: 2 Nov 2026 11:00 am ET → **15 Dec 2026 2:00 pm ET** (hard stop; no edits after, §5).
- Judging: 15 Jan 2027 10:00 am ET → 29 Jan 2027 5:00 pm ET. Project must stay free/unrestricted through end (§4 Testing).
- Community Voting: 15–29 Jan 2027 (same window); verified votes, not publicly displayed (§6).
- Winners announced: on or around 4 Feb 2027 2:00 pm ET, after verification + affidavit (§8).

### Judging (S1 §6, S2 criteria section)

- **Stage One (gate):** pass/fail — Project reasonably fits the theme + reasonably applies the required APIs/SDKs.
- **Stage Two:** four **equally weighted** criteria (exact weights: 25% each implied by "equally weighted"; no numeric split published):
  1. Technological Implementation — real engineering effort; genuinely builds for or runs on QNX.
  2. Design — complete, coherent product experience, not just a technical proof of concept.
  3. Potential Impact — credible, specific case for a real problem in a QNX market; why real-time QNX is the right choice.
  4. Innovation & AI Creativity — creative, non-obvious use of QNX; genuine understanding of the problem space.
- **Tie-breaks:** highest score on criterion 1, then 2, 3, 4 in order; residual ties → Judges vote. Community-Choice vote ties → Sponsor/Administrator sole discretion.
- **Method:** expert panels / peer review / automated AI-driven analysis, or any mix; judges may change, may not all be listed. No AI-use disclosure rule found in §§1–15 (OBSERVATION, high — keeping a prepared disclosure is prudent but not rule-mandated).

### Categories (S1 §4, S2) — select exactly one

1. Robotics & Medical; 2. Automotive & Mobility; 3. Low-level Software (DDK drivers/BSP);
4. Developer Tooling & Host Tools; 5. Open-Source Contribution & Ports (new in-period repo, patches/porting layer + QNX build files + instructions + docs; reference upstream by URL; do NOT submit a fork).

### Sponsor / tech requirements (S1 §4, S2)

- Working project running on or targeting **QNX 8.0 (QNX Everywhere)**: (a) app/driver/library/component on QNX 8.0 on any supported target incl. QEMU; or (b) host tool (Windows/macOS/Linux) that builds/tests/analyzes/supports QNX 8.0 software.
- Free QNX SDP 8.0 via QNX Everywhere (non-commercial). QEMU explicitly allowed; no target hardware required.
- Evidence-of-QNX-use: submission must explain the QNX connection and identify relevant files/functions/output/demo in the description; POSIX-compatible code, interpreted languages, ports, and host tools remain eligible with a clear meaningful QNX connection.

### Bonus prizes + eligibility (S1 §6, §8)

- **B1 Best Codelab/Tutorial ($3,500, 1 winner):** eligible Submission + codelab URL authored during the Submission Period teaching a QNX 8.0 task. Need NOT relate to the Project. Judged on the 4 criteria. URL in designated form field.
- **B2 Best Use of QNX-Specific Technologies ($3,500, 1 winner):** eligible Submission; judges pick most creative/impactful/sophisticated use of unique QNX capabilities (native message passing, resource managers, microkernel architecture, boot/startup customization, real-time services, security policies — non-exhaustive). No extra field; judged from the Submission (OBSERVATION, high).
- Unawarded if no eligible submissions for that bonus (§8).

### Prize stacking (S1 §8)

- One (1) Overall + one (1) Bonus + one (1) Community Choice per project. Only ONE Bonus winnable — polish effort should favor the stronger candidacy (OBSERVATION, high).
- Cash total $50,000: Grand $10k (+podcast + CEO chat); 5×$4k category Best (+exec chat); 5×$2k Runner-Up; 3×$1k Honorable Mentions (Overall); 2×$3.5k Bonus. Community Choice non-cash (blog/social + swag).

### Video rules (S1 §4, S2)

- "Should be" <3 min BUT judges not required to watch beyond 3 min → treat **<180 s as mandatory** (OBSERVATION, high).
- Should show the Project functioning on the device built for (for GENESIS RT: QEMU target).
- MUST be public on **YouTube** (no Vimeo option documented — OBSERVATION, high, use YouTube only); link on form.
- No third-party trademarks / copyrighted music or material without permission.

### Repo / license rules (S1 §4, S2)

- Public repo on GitHub/GitLab/Bitbucket with ALL source + assets + instructions; must show genuine QNX 8.0 build/run, not README-name-dropping.
- Must be public AND open source with license file detectable + visible in About section.

### Creation-period rules (S1 §4)

- Created 2 Nov–15 Dec 2026, OR pre-existing + significantly updated after 2 Nov 2026 with explanation ("significantly updated" threshold undefined — OBSERVATION, high; N/A to GENESIS RT, created in-window).

### Submission fields (S1 §4, S2)

Repo URL; one category; build/run instructions (QNX version + target + toolchain); text description; video URL; OSS-category extras (upstream URL, PR URL); B1 codelab URL in designated field. Multiple submissions allowed if unique and substantially different.

### Team rules (S1 §§3–4)

- Open to 18+ individuals, Teams of eligible individuals, Organizations. One individual may join multiple Teams/Orgs and also enter solo. Team/Org must appoint one authorized Representative (who must meet eligibility).
- Excluded: residents/domiciled in US-sanctioned/prohibited territories (incl. Brazil, Russia, Crimea, Cuba, Iran, North Korea + OFAC-sanctioned); Promotion Entities + employees/agents/families/households; Judges + employers; affiliates; conflicts of interest (Sponsor/Administrator discretion).
- Winner forms due 10 business days; prizes delivered within 60 days; winners bear taxes/fees; W-9/W-8BEN may apply (§8).
- Community Choice: one vote per person per Submission; no circumvention/multiple emails/compensating voters — violations disqualify votes and may disqualify the Maker (§6 + Devpost ToS).

### Other binding rules (S1)

- IP: submissions remain entrant's; Sponsor gets non-exclusive license for judging; Sponsor/Devpost may promote Submission + use contributors' name/likeness/voice/image during Hackathon + 3 years (§§4,7,10).
- Contracted help allowed only if result is solely entrant's work product from entrant's ideas; OSS inclusion allowed if license-compliant AND enhanced (§4).
- Drafts pre-deadline OK; no changes after period end (portfolio updates allowed); post-period edits only with permission for infringing/PII/inappropriate material, substantively same (§5).
- Sponsor BlackBerry Ltd; Administrator Devpost, Inc. (§2). Disputes → binding AAA arbitration, New York law (§§13–14).

### New data points this refresh (OBSERVATION, med–high)

- Homepage names 9 judges (QNX staff): Sheridan Ethier (VP Engineering Middleware), Patrick Murtha (Sr Director Product Mgmt), Cris Sinnott (Sr Director Eng Open Source), Andy Gryc (Director Developer Ecosystem), Dongkai Guo (Director SW Dev), John Dallas (Principal Academic Partnerships Mgr), Morgan McKeen (Developer Engagement Marketing Mgr), Mike Shane (Sr Systems SW Dev), John Hanam (Mgr Developer Relations). Judges may change per §6 — do not hard-code.
- Rules-page nav showed "Participants (968)" at fetch time (OBSERVATION, med — live count, will move; no action).
- Rules page links a "Français" details page — bilingual presentation exists (OBSERVATION, med; English materials rule §4 unchanged).

## 3. GENESIS RT compliance checklist (status re-verified 9 Nov 2026)

Status key: PASS (evidenced now) / READY (prepared, filed at submission) / BLOCKED (missing) / WATCH (ongoing). Evidence paths relative to `genesis-rt/` unless stated.

| # | Requirement | Source | Status | Evidence path |
|---|---|---|---|---|
| M1 | Working project on/targeting QNX 8.0 (QEMU allowed) | S1 §4, S2 | PASS | `target/qnx8/` (exists); `docs/quickstart-qnx8-qemu.md` (exists) |
| M2 | Exactly one category: Developer Tooling & Host Tools | S1 §4, S2 | READY (form at filing) | `docs/devpost-draft.md`, `docs/submission/DEVPOST_FINAL_DRAFT.md` (exist) |
| M3 | Public repo with all source + assets + instructions | S1 §4, S2 | PASS (per baseline S4: public, pushed 9 Nov) | https://github.com/toskaman/genesis-rt (re-check public at filing) |
| M4 | OSS license file, detectable + visible in About | S1 §4, S2 | PASS — Apache-2.0 | `LICENSE` head re-read (Apache 2.0); baseline S4 `license.key: apache-2.0` |
| M5 | Genuine QNX 8.0 build/run evidence, not README-only | S1 §4, S2 | PASS | `target/qnx8/`; `evidence/qnx8-x86_64-omega2-before` + `-after` (exist) |
| M6 | Build/run instructions: QNX version + target + toolchain | S1 §4, S2 | PASS | `docs/quickstart-qnx8-qemu.md`, `README.md` (exist) |
| M7 | Text description of features/functionality | S1 §4, S2 | READY (drafts prepared) | `docs/devpost-draft.md`, `docs/submission/DEVPOST_FINAL_DRAFT.md` |
| M8 | Demo video <180 s, QEMU footage, public YouTube, clean rights | S1 §4, S2 | BLOCKED — final video DEFERRED BY OWNER (7 Nov); `docs/demo/genesis-rt-demo-w12.mp4` exists but predates Studio, NOT the submission video | `docs/demo/PUBLICATION_HANDOFF_W12.md`, `docs/demo/MEDIA_VALIDATION_W12.md`, `docs/submission/VIDEO_STORYBOARD_DEFERRED.md`; YT upload pending |
| M9 | Created 2 Nov–15 Dec 2026 | S1 §4 | PASS (created 4 Nov 2026, per baseline S4 + git log) | Re-verify `git log` at filing (read-only `git log --oneline \| tail`) |
| M10 | Free + unrestricted through 29 Jan 2027; judges need not test | S1 §4 | WATCH — currently PASS | Keep repo public to 29 Jan 2027; QEMU-only, no rare hardware |
| M11 | All materials in English (or translate) | S1 §4 | PASS | Repo contents English |
| M12 | Original, solely-owned; OSS only if compliant AND enhanced | S1 §§4,7 | PASS per project record | `docs/jury/COMPLIANCE.md` (exists) |
| M13 | No sponsor financial/preferential support, ever before period end | S1 §4 | PASS (QNX Everywhere non-commercial only) | `docs/jury/COMPLIANCE.md` (exists) |
| M14 | Entrant eligible: 18+, not excluded/sanctioned, no conflicts | S1 §3 | OWNER-CHECK — not research-verifiable | Owner self-confirms (age, residence, employer conflicts) |
| B1 | Codelab authored in-period teaching QNX 8.0 task; URL in bonus field | S1 §§4,6 | PASS artifacts / READY filing | `docs/codelab/README.md`, `docs/codelab/ADVANCED-QNX.md` (exist) |
| B2 | Creative/impactful/sophisticated QNX-specific tech use, surfaced in text + video | S1 §6 | PASS code / READY surfacing | `target/qnx8/` (IPC, `/dev/genesis/status` resmgr); name files/functions in Devpost text; show on screen in video |

## 4. Pre-filing checklist (day of filing)

- [ ] M8: final video <180 s, QEMU footage on screen, English, no third-party marks/music, public YouTube; URL also committed in README + release asset same-day (never portal-only).
- [ ] M2/M5/M6: category selected; Devpost text names exact QNX files/functions/output/demo.
- [ ] B1: codelab URL pasted in designated bonus field.
- [ ] M3/M10: repo public (stays public through 29 Jan 2027).
- [ ] M14: owner eligibility self-confirmed.
- [ ] S1+S2 re-opened in browser for last-minute amendments (§11.5).
- [ ] Draft saved early; final submit well before 15 Dec 2026 2:00 pm ET.

## 5. Unresolved / carried forward

- U1: exact Devpost form field labels/validation (form requires login; field list verified from Rules + homepage).
- U2: "significantly updated" threshold undefined (N/A to GENESIS RT).
- U3: judges may never run the project — submission must stand alone on text + video.
- U4: owner §3 eligibility self-confirmation (age, residence, conflicts).
- U5 (new): judge roster and participant count are live values — re-check near filing; no action now.
