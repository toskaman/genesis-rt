# Omega4 baseline (9 Nov 2026)

Branch: `titan-omega4` from `main` @ `f93399a` (PR #12
merged, main CI run `42528912050` success). Working tree
clean at branch creation. No `titan-omega4` existed
before. No open PRs/issues rechecked at creation time
(OMEGA3 final state).

## Starting measurements (OMEGA3, committed)

- Owner full suite: 1329 passed + 2 skipped / 1331, EXIT=0.
- Consistency 37/37, planning 52/52, E2E 30+2/32.
- Packs BEFORE/AFTER VERIFY OK, 16/16, qnx_verified=True.
- Scorecard 30.5/40 (9.5/8/5/8); independent 9/7/5/7.
- v6 blind: 46/72 x3 identical, 26 unsafe, 0 false
  rejects, 0 model consults (inferred from latency +
  short-circuit; counter now exists, unmeasured).

## §3.1 freeze record (implementation side)

- Code base: `f93399a` (+ §2 doc/test commits on
  `titan-omega4`, which do not touch the planner).
- `host/genesis_rt/planning.py` sha256[:16]:
  `9a14d1191f30d3a1` (at `f93399a`; re-recorded after
  the §3.2 disclosure fix, before v7 authoring).
- `host/genesis_rt/planner.py` sha256[:16]:
  `99f1514396797f11` (same note).
- Frozen datasets byte-identical (pin test green 9 Nov):
  - v4 `3f515015eace34443496b19ac8f016fc17ebbc7eafd8fba384e849ff01018824`
  - v5 `5b94e18e812cd497b851a5eaba81bc622b445e0a2d10c39224a35e09ae`
  - v6 `e5fbcd4985a6cc90d2959319c71aeda5aa06b2ef3b0079a5a193bb6965469fde`
  - eval `9f5623f4a8fc339457ccd52780c44c2bf5a6663eec022aa44f1bbce0557335a7`
- Models present (local Ollama, no downloads planned):
  `llama3.1:8b-instruct-q4_K_M`, `qwen2.5:7b-instruct`.
- Project Python: 3.14.4, `cryptography` **43.0.3** in
  the ACTIVE interpreter, which is GLOBAL
  (prefix == base_prefix) → per §6 the upgrade is an
  OWNER command, not performed here. Declared floor
  `cryptography>=49` stands; CI installs fresh.

## §3.2 pre-finding (drives adjudication order)

OMEGA3 called bare-kind defaults "output-disclosed".
Code inspection (9 Nov 2026) shows NO disclosure marker:
`planner.py:221` (`period_ms = 10`) and `:233`
(`max_linear = 1.2`) bake defaults into the emitted IR
(`:292-302`) with no provenance field, and the shipped
rejection text (`:266`) invites omission-for-default.
Adjudication cannot honestly pick "A, disclosed" without
first implementing disclosure. Therefore: the
`defaults_applied` disclosure fix lands BEFORE the v7
authoring freeze (recorded above), with red-then-green
tests; the versioned contract then freezes for v7.

## §2 drift confirmed (9 Nov 2026)

- `docs/CLAIMS.md:79-88`: AI section foregrounds v4/v5,
  "12 v5 unsafe-accept classes OPEN" — stale post-v6.
- `README.md:26-36`: "What's proven" foregrounds W11
  (limit flip + three packs); Omega2 current-source pair
  absent from the flagship slot.
- Directive §2.3 paths `docs/START_HERE.md`,
  `docs/REPRODUCE.md`, `docs/COMPLIANCE.md` do not exist;
  actual paths are `docs/jury/*` (corrected in review).
- `docs/audits/OMEGA3_AI_EVALUATION.md` §5 carries the
  P0c snapshot (1320+2/1322) — needs a snapshot-scope
  note so it is not read as the final tree.

## Order of execution (this branch)

1. §2 doc/test fixes + sync + commit.
2. §3.2 disclosure fix + contract doc + commit; record
   final planner hashes (freeze).
3. Spawn separate v7 eval agent (contract + threat model
   only; no parser access); P1 work in parallel.
4. v7 freeze commit → measure once × 3 → report.
5. P1 completion → rules recheck → independent attack →
   scorecard → PR → CI → merge.
