# Winners Delta — NEW sourced entries outside prior Meta/Anthropic/OpenAI coverage

Strategy research only (READ-ONLY on genesis-rt; this file is the deliverable).
Compiled 2026-11-09. Prior cycle covered Meta/Cerebral Valley + Anthropic/OpenAI ecosystems in
`hackathon-knowledge/HISTORICAL_WINNER_DATABASE.md` and `HACKATHON_WINNER_INTELLIGENCE.md`
(both read first; nothing below repeats them).

## Label legend

- **Confirmed** — stated in an opened official page (organizer, university, agency) or the winning
  team's own linked artifact. Source link attached.
- **Observed** — visible in an opened secondary recap, corroborated by 2+ independent roundups
  where noted. Weaker than Confirmed; exact team claims not independently verified.
- **Reasoned-hypothesis** — inference from the evidence; never presented as fact.
- **Unknown** — explicitly missing (demo contents, rubric text, per-team scores).
- No metrics, scores, judge feedback, or testimonials are invented. Every number below is quoted
  from a cited opened body.

## Coverage tally

- **18 new entries (D1–D18)** across **9 competitions**, **10 domains**, all within the last
  24 months (Mar 2025–Dec 2025 announcements; events Oct 2024–Oct 2025).
- Competitions: Google Cloud ADK Hackathon (Devpost) · NASA Space Apps 2025 · ETHGlobal Cannes
  2025 · ETHGlobal NYC 2025 · Embodied AI Hackathon (Circuit Launch) · H2AI Georgetown 2025 ·
  Sahlgrenska Global Health Hackathon 2025 · DARPA AI Cyber Challenge (DEF CON 33) · Colorado
  Sustainability Challenge 2025.
- Domains: dev tools · AI agents · scientific infra · space/regulatory · climate (x4) · fintech
  (x4) · security/privacy (x4) · health (x4) · gaming/AR · robotics.

---

## D1. SalesShortcut — Grand Prize, Agent Development Kit Hackathon with Google Cloud (Devpost)

- **Competition/date:** Agent Development Kit Hackathon with Google Cloud, spring 2025; built in
  16 days (repo opened Jun 6, 2025). **Confirmed** —
  [Devpost blog](https://info.devpost.com/blog/hackathon-winning-project-salesshortcut).
- **Award:** Grand Prize of 477 submissions: $15,000 cash + Google Cloud credits. **Confirmed** —
  same source (citing cloud.google.com results page).
- **Problem:** Local businesses without websites are invisible; sales prospecting (find leads,
  research, write offers, call, follow up, book meetings) is manual. **Confirmed** — same source.
- **User:** Web designers/agencies hunting clients (hackathon version); later pivoted to the
  businesses themselves. **Confirmed** — same source.
- **Old vs new workflow:** Old: human finds businesses on Maps, researches each, writes offers,
  cold-calls, follows up by email, books meetings. New: type in a city → 34 agents find
  website-less businesses, research, write custom offers, fact-check, AI-voice-call + email
  follow-up, read replies, book calendar meetings — with a human-approval gate before anything
  goes out. **Confirmed** — same source.
- **Innovation:** One-job-agent teams (sequential + parallel + loop agents) coordinated over A2A;
  human-in-the-loop "stop sign" mid-pipeline; fixed invisible-handoff debugging by testing every
  agent against identical sample data instead of live APIs. **Confirmed** — same source.
- **Demo:** AI calls + dashboard were a big part of the hackathon demo (later cut post-win when
  real customers didn't need them). **Confirmed** — same source.
- **Tech:** 5 Cloud Run services over A2A; 21 LLM agents on Gemini via Vertex AI; Maps API,
  BigQuery; Python; 2 issues + 1 accepted docs PR sent back to ADK. **Confirmed** — same source.
- **Evidence:** [Devpost project](https://devpost.com/software/salesshortcut), 58 repo forks;
  post-win field test in Logan UT: 190 website-less businesses, 45 calls, 25 conversations,
  3 meetings, 1 customer; now SalesShortcut Inc., 7 subscriptions, $1,600 MRR. **Confirmed** —
  same source.
- **Presentation:** Multi-agent team exactly matching the challenge ("design teams of AI agents
  that work together"). **Reasoned-hypothesis** — fit is visible; no judge quotes recovered.
- **Rubric:** Unknown — official rubric text not recovered.
- **Lessons:** (1) Match the challenge shape exactly (agent *teams*, not one agent).
  (2) Human-approval gate = trust beat on a system that contacts real people.
  (3) Deterministic sample-data testing unblocked 34-agent debugging. (4) Afterlife: show it to
  one real person with the problem — "If they lean in, you do not have a weekend project."

## D2. SpaceGenes+ — Best Use of Science, NASA Space Apps Challenge 2025

- **Competition/date:** NASA International Space Apps Challenge, Oct 4–5, 2025 (hybrid, 551 local
  events, 167 countries/territories, 114,000+ participants, 11,500+ submissions); winners
  announced Dec 2025. **Confirmed** —
  [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- **Award:** Best Use of Science (1 of 10 global awards), judged by NASA + partner subject-matter
  experts. Solo team member (Saloni T., Germany). Challenge: "Build a Space Biology Knowledge
  Engine". **Confirmed** — same source.
- **Problem/user:** Researchers and mission planners need to see how radiation + microgravity
  jointly affect astronaut health at the molecular level. **Confirmed** — same source.
- **Old vs new workflow:** Old: manually cross-referencing space-biology datasets/papers.
  New: interactive dashboard surfacing key molecular changes + protection strategies for
  long-duration flight. Old half is **Reasoned-hypothesis**; new half **Confirmed** — same source.
- **Innovation/demo/tech/evidence:** Interactive molecular-effects dashboard; project page linked
  from NASA announcement (spaceappschallenge.org project tab). Implementation details (data
  sources, stack) **Unknown** — project page body not opened (cert failure on fetch).
- **Presentation:** Solo builder winning a science-validity award = depth over team size.
  **Reasoned-hypothesis**.
- **Rubric:** Best Use of Science = "best and most valid use of science / scientific method"
  (category semantics **Observed** via third-party recon, not NASA verbatim).
- **Lessons:** A single researcher with one dataset + one legible dashboard can beat large teams
  on a validity-scored award.

## D3. Resonant Exoplanets — Best Use of Data, NASA Space Apps Challenge 2025

- **Competition/date/award:** Same event as D2. Best Use of Data. Team of 4 (USA). Challenge:
  "A World Away: Hunting for Exoplanets with AI". **Confirmed** — [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- **Problem/user:** Manual exoplanet + biosignature identification doesn't scale to modern
  telescope/satellite data volumes; users are astronomers/planetary scientists. **Confirmed**
  (problem) — same source; user **Reasoned-hypothesis**.
- **Old vs new workflow:** Manual spectral inspection → AI system ingesting large telescope +
  satellite datasets incl. JWST spectra, auto-analyzing for exoplanets + possible biosignatures.
  **Confirmed** — same source.
- **Innovation/demo/tech/evidence:** AI pipeline over mission spectra; project page linked from
  NASA announcement. Model architecture, demo form **Unknown** (page body not opened).
- **Rubric/lessons:** Data award rewards making space data accessible/leveraged uniquely
  (**Observed**, third-party paraphrase). Lesson: riding a flagship data source (JWST) + full
  automation story fits "Best Use of Data" cleanly (**Reasoned-hypothesis**).

## D4. Astro Sweepers — Galactic Impact, NASA Space Apps Challenge 2025

- **Competition/date/award:** Same event as D2. Galactic Impact award. Team of 6 (Universal
  Event). Challenge: "Commercializing Low Earth Orbit (LEO)". **Confirmed** — [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- **Problem/user:** Commercial LEO growth creates debris/compliance risk; users are operators,
  regulators, insurers. Problem framing **Confirmed** ("operational, regulatory, environmental
  challenges"); users **Reasoned-hypothesis** — same source.
- **Old vs new workflow:** Manual Debris Assessment Software runs + bespoke disposal reports →
  end-to-end platform auto-ingesting public orbital data, generating DAS reports + an "Astro
  Sweepers Risk Index" per resident space object. **Confirmed** — same source.
- **Innovation:** A per-object risk index ("credit score for satellites" per
  spaceappschallenge.org winners page, **Observed** — snippet only, page body not opened).
- **Demo/tech/evidence:** Platform; implementation **Unknown** (project page body not opened).
- **Lessons:** Regulatory/compliance framing + a single memorable metric (risk index) is the
  one-sentence identity judges repeat (**Reasoned-hypothesis**).

## D5. QUENARIS — Local Impact, NASA Space Apps Challenge 2025

- **Competition/date/award:** Same event as D2. Local Impact award. Team of 6 (Peru). Challenge:
  "BloomWatch". **Confirmed** — [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- **Problem/user:** Water scarcity in Arequipa (Peru's 2nd-largest city) from quenua-forest
  degradation (forests retain water); users are reforestation planners/local authorities.
  **Confirmed** (problem) — same source; users **Reasoned-hypothesis**.
- **Old vs new workflow:** Manual reforestation siting/monitoring → platform combining native
  microorganisms + NASA satellite data + drones + AI to accelerate tree growth, pick
  reforestation sites, monitor ecosystem health. **Confirmed** — same source.
- **Innovation/demo/tech/evidence:** Multi-modal stack (bio + satellite + drone + AI) aimed at
  one named city. Implementation **Unknown** (page body not opened).
- **Lessons:** Local Impact rewards a concrete place + named beneficiaries over generic climate
  tooling (**Reasoned-hypothesis**, consistent with award semantics).

## D6. Gaia+LEO — Global Connection, NASA Space Apps Challenge 2025

- **Competition/date/award:** Same event as D2. Global Connection award. Team of 4 (USA).
  Challenge: "Commercializing LEO". **Confirmed** — [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- **Problem/user:** Earth data centers' power/water demands for AI training + climate modeling.
  **Confirmed** — same source.
- **Old vs new workflow:** Earth-only data-center networks → mixed-integer optimization framework
  co-designing orbital + terrestrial data-center networks for space-based green computing.
  **Confirmed** — same source.
- **Innovation:** Optimization (not LLM) core — operations research as the differentiator.
  **Confirmed** (method named) — same source.
- **Demo/tech/evidence:** Framework; solver/code **Unknown** (page body not opened).
- **Lessons:** A non-AI technical core can win at an AI-flavored hackathon when the method fits
  the problem exactly (**Reasoned-hypothesis**).

## D7. BeamPay — Finalist (top 10 of 334), ETHGlobal Cannes 2025

- **Competition/date:** ETHGlobal Cannes, Jul 2025 (36h, 334 projects). Top-10 finalist.
  **Observed** — [TechFlow/PANews roundup](https://www.techflowpost.com/en-US/article/26828)
  (translated from ETHGlobal announcement), corroborated by Binance Square / MEXC roundups.
- **Award:** Finalist; built by MemExpo and Dmitry. **Observed** — same sources.
- **Problem/user:** ERC-20 payments with metadata need multiple transactions; users are wallet
  developers / payers. **Reasoned-hypothesis** from description.
- **Old vs new workflow:** Multi-tx token payment → single-transaction ERC-20 payment with
  metadata via EIP-7702 wallets, multi-chain deployable. **Observed** — same sources.
- **Innovation:** Uses newest protocol capability (EIP-7702) visibly — the sponsor-stack-native
  pattern. **Observed** (tech) + **Reasoned-hypothesis** (pattern claim).
- **Demo/tech/evidence:** Wallet-level integration; code/demo **Unknown** (roundups carry
  one-paragraph summaries only; no repo opened).
- **Rubric/lessons:** ETHGlobal finalists skew to newest-capability-visible infra.
  **Reasoned-hypothesis**. Lesson: ship on the freshest primitive the ecosystem just released.

## D8. OnlyDanks — Finalist (top 10 of 334), ETHGlobal Cannes 2025

- **Competition/date/award:** Same event as D7. Finalist; built by Paul, Patrick, Fabbaist.
  **Observed** — same roundup sources.
- **Problem/user:** Private messaging depends on apps/servers/intermediaries. **Observed** —
  same sources.
- **Old vs new workflow:** Server-mediated chat → fully Ethereum-based end-to-end encrypted
  communication using block data; no apps, no servers, no intermediaries. **Observed**.
- **Innovation:** "No apps, no servers, no intermediaries" as the one-sentence identity.
  **Observed** (description) + **Reasoned-hypothesis** (identity claim).
- **Demo/tech/evidence:** Implementation **Unknown** (summary only).
- **Lessons:** A legible subtraction ("no X, no Y, no Z") is a memorable judge hook
  (**Reasoned-hypothesis**).

## D9. PrivyCycle — Finalist (top 10 of 334), ETHGlobal Cannes 2025

- **Competition/date/award:** Same event as D7. Finalist; built by Danisharora, Migle, Threshold
  Network. **Observed** — same roundup sources.
- **Problem/user:** Menstrual-cycle tracking data is sensitive and routinely exposed; users are
  people who menstruate. **Observed** — same sources.
- **Old vs new workflow:** Centralized femtech apps holding plaintext health data → AI-powered
  tracker with encrypted records + private sharing, user-controlled. **Observed**.
- **Innovation:** Privacy-preserving health AI (encryption + threshold crypto) on a stigmatized
  dataset. **Observed** (description) + **Reasoned-hypothesis** (framing).
- **Demo/tech/evidence:** Implementation **Unknown** (summary only).
- **Lessons:** Privacy + health intersection won finalist slots at a chain event, not just health
  events — domain-crossing stands out (**Reasoned-hypothesis**).

## D10. Pumpkin Spice Latte — Top 10, ETHGlobal New York 2025

- **Competition/date:** ETHGlobal New York 2025 (weekend hackathon; gaming/payments/DeFi/dev-tools
  tracks). Top-10 winner. **Observed** — [PANews/Odaily roundup](https://panews.io/articles/cf526d7b-083f-409c-b89b-fe61da702db9)
  (reporter attended on site), corroborated by MEXC/Followin roundups.
- **Problem/user:** Saving is boring; users want yield + excitement without risking principal.
  **Observed** — same source.
- **Old vs new workflow:** Plain savings / risky speculation → deposit stablecoins into a shared
  pool (principal safe), pooled earnings fund regular prize draws; winners get excess returns,
  losers keep principal. **Observed** — same source.
- **Innovation:** No-loss lottery (DeFi yields + lottery mechanism); ERC-4626 yield sources
  (Morpho, Kinetic); Flare/Flow VRF randomness for fairness. **Observed** — same source.
- **Demo/tech/evidence:** Smart-contract pool; code/demo **Unknown** (roundup only).
- **Lessons:** A playful name + one-line mechanism ("winners get yield, losers keep principal")
  is peak one-sentence identity (**Reasoned-hypothesis**).

## D11. Hardhat 3-Ledger — Top 10, ETHGlobal New York 2025

- **Competition/date/award:** Same event as D10. Top-10 winner. **Observed** — same roundup.
- **Problem/user:** Devs expose private keys when deploying contracts; users are smart-contract
  developers. **Observed** — same source.
- **Old vs new workflow:** Plaintext keys in dev env → Ledger hardware-wallet signing inside
  Hardhat 3 (TypeScript, Ledger device-management toolkit, tested on Ledger Flex).
  **Observed** — same source.
- **Innovation:** Boring-but-critical dev-tooling + upstream contribution (doc/code-example
  improvement suggestions to Ledger). **Observed** — same source.
- **Demo/tech/evidence:** Integration + docs suggestions; repo **Unknown**.
- **Lessons:** Dev-tools win by removing a real footgun + giving back upstream — "criterion zero"
  for the builder-judge persona (**Reasoned-hypothesis**).

## D12. Noah — Top 10, ETHGlobal New York 2025

- **Competition/date/award:** Same event as D10. Top-10 winner. **Observed** — same roundup.
- **Problem/user:** Crypto holders die; heirs lose assets. Users: holders + non-crypto-native
  beneficiaries. **Observed** — same source.
- **Old vs new workflow:** Manual key handover / lost funds → smart-contract "dead man's switch":
  inactivity triggers auto-transfer to beneficiaries; Dutch-auction/Uniswap liquidation; convert
  to USDC/PYUSD/fiat via Fern so heirs need no crypto knowledge; ENS inheritance; deployed on
  Flow, Chiliz, Katana. **Observed** — same source.
- **Innovation:** Fiat off-ramp for heirs (inherit without understanding crypto) — designing for
  the non-user. **Observed** (feature) + **Reasoned-hypothesis** (design reading).
- **Demo/tech/evidence:** Multi-chain deployment; code **Unknown**.
- **Lessons:** "Works for people who never touch the tech" is a strong impact story
  (**Reasoned-hypothesis**).

## D13. Rivals — Top 10, ETHGlobal New York 2025

- **Competition/date/award:** Same event as D10. Top-10 winner. **Observed** — same roundup.
- **Problem/user:** AR games lack real stakes/economy; users are mobile gamers. **Observed** —
  same source.
- **Old vs new workflow:** High-score AR play → multiplayer phone AR shooter vs AI zombies in
  physical space (Unity AR Foundation); kills earn RIVAL tokens, death deducts balance.
  **Observed** — same source.
- **Innovation:** Token economy as the score system; physical-space gameplay. **Observed**.
- **Demo/tech/evidence:** Unity AR Foundation + chain economy; build **Unknown**.
- **Lessons:** Live-playable beats describable — a game judges can play on a phone is its own
  rehearsal-proof demo (**Reasoned-hypothesis**).

## D14. Firebreathing Rubber Duckies — Winner, Embodied AI Hackathon (Circuit Launch)

- **Competition/date:** Embodied AI Hackathon, Circuit Launch, Mountain View CA, Mar 22–23, 2025
  (2 days). Winner. **Confirmed** —
  [Hackster](https://www.hackster.io/news/embodied-ai-hackathon-winners-announced-2dc69c76942e.amp).
- **Award:** Hackathon winner; prizes incl. SO-ARM100 arms + NVIDIA hardware. **Confirmed** —
  same source.
- **Problem/user:** Collaborative bimanual manipulation is hard to program; users are robotics
  researchers/engineers/enthusiasts. Problem **Reasoned-hypothesis**; user quote **Confirmed**
  ("inspire researchers, engineers, and enthusiasts") — same source.
- **Old vs new workflow:** Hand-coded multi-arm coordination → teleoperate two LeRobot SO-ARM100
  arms through collaborative pick-and-place demos (bowl-to-bowl), train vision-language-action
  models (NVIDIA Groot N1, ACT, Pi0) to reproduce it; Arducams per arm + Logitech overview cam.
  **Confirmed** — same source.
- **Innovation:** Two low-cost arms "playing nicely together" via VLA models trained in a weekend.
  **Confirmed** (setup) — same source.
- **Demo:** Live pick-and-place; experimentation video embedded in recap. **Confirmed** (video
  existence; contents not transcribed) — same source.
- **Tech:** SO-ARM100 kits + LeRobot + Jetson/Isaac Lab; dataset uploaded to Hugging Face; code
  on [GitHub](https://github.com/JChunX/apple_pie/tree/seeed_hacks) (link **Confirmed**, body not
  opened). Same source.
- **Evidence:** Public dataset + code; "what a dedicated team can do in two days" per recap.
  **Confirmed** — same source.
- **Presentation/rubric:** Rubric Unknown. Physical-robot live demo = OpenGlass-pattern hardware
  legibility (**Reasoned-hypothesis**).
- **Lessons:** Cheap open hardware (SO-100 class) + open datasets + VLA models = weekend-viable
  robotics wins; publishing data+code extends afterlife.

## D15. Team Rabbit — Grand Prize ($5,000), H2AI Healthcare Hackathon with AI (Georgetown)

- **Competition/date:** H2AI, Georgetown University, Mar 14–16, 2025 (36h, 160+ participants,
  2nd edition, student-organized). **Confirmed** —
  [Georgetown](https://meded.georgetown.edu/news-stories/medical-students-host-healthcare-hackathon-with-ai/).
- **Award:** Grand Prize $5,000 of $15,000 pool ("most innovative, impactful and well-executed");
  also won the $1,000 Patient Safety Technology Challenge prize. Team: students from MIT,
  UPenn, George Mason. **Confirmed** — Georgetown source + event report (H2AI framework paper
  notes the double win).
- **Problem/user:** Fall risk in Parkinson's patients; users are clinicians/patients (case study
  co-designed with a donor living with Parkinson's). **Confirmed** — Georgetown source.
- **Old vs new workflow:** Clinical gait exams in sterile settings → immersive VR simulations of
  real-world scenarios (crowded spaces, complex turns) + AI-driven neuromuscular/gait analytics.
  **Confirmed** — same source.
- **Innovation:** Real-world-scenario VR assessment + dual prize (grand + safety) via
  safety-conscious design. **Confirmed** (what) — same source.
- **Demo/tech/evidence:** Winning-team photo + $5k check published; VR/AI stack details
  **Unknown** (no repo recovered).
- **Rubric:** "Most innovative, impactful and well-executed" stated as the grand-prize standard.
  **Confirmed** — same source.
- **Lessons:** (1) Designing with a named patient population + safety prize in the same event =
  double surface area. (2) Real-world-scenario fidelity (crowds, turns) over lab metrics.

## D16. eNose Diagnostic — 1st Place (€10,000), Sahlgrenska Global Health Hackathon

- **Competition/date:** Sahlgrenska Global Health Hackathon (hybrid: 8 local hackathons, 6
  countries, ~1,000 participants, 118 teams); Grand Finale Gothenburg, Oct 13, 2025.
  **Confirmed** —
  [Eventornado use case](https://eventornado.com/blog/hackathon-use-case-sahlgrenska-global-health-hackathon).
- **Award:** 1st Place, €10,000 giant check; jury-selected "for its groundbreaking approach to
  early, non-invasive disease detection". **Confirmed** — same source.
- **Problem/user:** Late-invasive disease screening; users are patients/clinicians/public-health
  programs. **Confirmed** (problem) — same source.
- **Old vs new workflow:** Invasive/biopsy-or-lab screening → gas-sensing + AI detection of
  volatile organic compounds from human samples; first target colorectal cancer; also flags
  antimicrobial-resistant bacteria. **Confirmed** — same source.
- **Innovation/demo/tech/evidence:** Gas-sensor hardware + AI; beat 7 named finalists (incl.
  SensEye smartphone eye screening, Bioshield Pro, MediFlow, PediAItrics, DIA-AID, Yukis,
  LuckieTech). Hardware/demo details **Unknown** (pitch format; no repo recovered).
- **Presentation:** Finalists pitched live; jury Q&A added decisive points. **Confirmed** — same
  source. Live Q&A handling therefore part of the win (**Reasoned-hypothesis**).
- **Lessons:** Non-invasive + early + dual-use (cancer + AMR) = stacked impact claims; in
  pitch-decided finales, Q&A is scored work, not ceremony.

## D17. Team Atlanta — 1st ($4M), DARPA AI Cyber Challenge (AIxCC), DEF CON 33

- **Competition/date:** AI Cyber Challenge final, DEF CON 33, Aug 8–9, 2025 (2-year competition;
  7 finalists, each awarded $2M at DEF CON 32 semifinal). **Confirmed** —
  [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/defcon-ai-cyber-challenge-winners/).
- **Award:** 1st, $4M (2nd Trail of Bits $3M; 3rd Theori $1.5M). Team: Georgia Tech + Samsung
  Research + KAIST + POSTECH, led by Prof. Taesoo Kim. **Confirmed** — same source.
- **Problem/user:** Finding/fixing vulnerabilities in critical + health infra too slowly (health
  sector averages 491 days to patch vs 60–90 elsewhere). Users: OSS maintainers, infra
  operators. **Confirmed** — same source.
- **Old vs new workflow:** Manual vuln-hunting (months) → cyber-reasoning systems: traditional
  methods (dynamic/static analysis, fuzzing) + LLMs (o4-mini, GPT-4o, o3); 45-min average patch
  time; finalists found 54/70 planted vulns (77%, up from 37%), patched 43, plus 18 real
  zero-days found / 11 patched; Team Atlanta topped all-but-one category + most real-world vulns.
  **Confirmed** — same source.
- **Innovation:** Traditional-methods-first + LLM augmentation beat LLM-mostly (Theori 3rd despite
  "thrifty" cost-efficiency); top-3 systems open-sourced. **Confirmed** — same source.
- **Demo/tech/evidence:** Live scored competition on planted + real vulns; disclosure to
  maintainers underway. **Confirmed** — same source.
- **Rubric:** Objective scoring: detection rate, patches, real-world vulns, cost-efficiency,
  CWE breadth per-team (Trail of Bits: most CWE categories; Theori: cheapest per-patch + most
  Java real-world vulns). **Confirmed** — same source.
- **Lessons:** (1) Objective, scored, adversarial evaluation is the strongest possible "demo".
  (2) Deterministic-core + LLM-edges (P4) wins even at $4M scale. (3) Open-sourcing the system
  converts a win into infrastructure. Note: 2-year format, not a weekend — transfer tactics,
  not timelines (**Reasoned-hypothesis**).

## D18. BioOX — 1st Place ($5,000), Colorado Sustainability Challenge 2025

- **Competition/date:** Colorado Sustainability Challenge Finals, Oct 12, 2025 (2-week
  hackathon-style; Front Range colleges; $21,000 pool). **Confirmed** —
  [CU Boulder](https://www.colorado.edu/innovate/congratulations-2025-colorado-sustainability-challenge-winners).
- **Award:** First Place $5,000. Team: 5 (engineering + business mix). **Confirmed** — same source.
- **Problem/user:** Raw biochar is bulky/low-value; farmers need dense, usable soil amendment;
  biochar = carbon sequestration. Users: farmers. **Confirmed** (solution) — same source; carbon
  framing **Reasoned-hypothesis**.
- **Old vs new workflow:** Raw biochar handling → proprietary processing into dense pelletized
  form for farm use. **Confirmed** — same source.
- **Innovation/demo/tech/evidence:** Process/hardware innovation over software; beat runners-up
  Amply (home power storage + AI workloads), MyPack, Owen Parker, Uplink Energy. Process details
  **Unknown** (one-line solution only).
- **Lessons:** Hardware/process climate solutions can take 1st over app-format entries; mixed
  eng+business team composition matches investor-legible judging (**Reasoned-hypothesis**).

---

## Cross-delta patterns (new vs prior cycle)

- **DP1. Newest-primitive wins (ETHGlobal-heavy).** BeamPay (EIP-7702), Hardhat 3-Ledger (Hardhat
  3 + Ledger Flex), Pumpkin (ERC-4626 + VRF) all ship visibly on the freshest stack layer —
  same P3 sponsor-stack-native pattern, new ecosystem. **Observed.**
- **DP2. Objective scoring >> pitch polish.** AIxCC (detection/patch counts), H2AI (dual safety
  prize), Sahlgrenska (jury Q&A points) all added scored work beyond the pitch.
  **Confirmed** (each mechanism) + **Reasoned-hypothesis** (generalization).
- **DP3. One-metric identities travel.** Risk index (D4), no-loss rule (D10), dead-man's switch
  (D12), 45-minute patch (D17). **Observed.**
- **DP4. Non-AI cores still win.** Mixed-integer optimization (D6), fuzzing+static analysis (D17),
  biochar process (D18), gas sensors (D16) — method-fit over fashion. **Confirmed** (methods named).
- **DP5. Designing for the non-user.** Noah's fiat heirs, PrivyCycle's exposed patients, Rabbit's
  Parkinson's cohort. **Reasoned-hypothesis.**

## Honest coverage + unresolved

- **Strong (opened bodies):** D1, D2–D6 (NASA official), D14, D15, D16, D17, D18. **Medium
  (secondary roundups, 2+ corroboration):** D7–D13 (ETHGlobal; no ETHGlobal official/showcase
  pages or repos opened — thin per-project depth).
- **Thin spots:** Dedicated fintech-hackathon and Devpost-direct project pages were thin this
  pass (Devpost 403s also blocked the prior cycle); fintech is covered via ETHGlobal entries.
  Robotics beyond D14 (e.g. LeRobot Worldwide Hackathon LeChef 1st, robo.innovate GROWBOT) and
  NASA 2024 winners (SkyShield, Asteroid Destroyer) were located but not deep-dived — expansion
  material, not cited facts.
- **Unknown across delta:** Per-team scores/judge feedback (all); official rubric texts except
  H2AI's one-line standard and AIxCC's scored categories; demo video contents (existence only);
  implementation stacks for D2–D13 (summaries only); repos for D7–D13, D15, D16.
- **Failed fetches:** spaceappschallenge.org project pages (TLS cert), NUS HealthHack winners
  page (empty/JS), patientsafetytech H2AI page (404), one Sahlgrenska URL (redirect — followed
  successfully).

