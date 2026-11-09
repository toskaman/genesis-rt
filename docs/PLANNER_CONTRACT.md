# Planner input contract (versioned)

Governs what the intent planner accepts, what it refuses, and
what the emitted Machine IR guarantees. The v7 evaluator
labels cases against v1.1; the v8 evaluator labels against
v1.2. History is preserved below; never rewritten.

## v1.2 (Omega4 fix-1, 9 Nov 2026) — v7 failure classes

Blind v7 (120 cases, frozen d91e3956) exposed refusal gaps
the v1.0/v1.1 text already implied but the code did not
enforce. v1.2 makes them explicit. All v1.1 rules stand;
nothing accepted under v1.1 becomes accepted-under-protest
— the new rules only refuse inputs v1.1 already called
ambiguous, unknown, or unsupported.

7. Generic machine nouns with no specific kind hint
   ("a machine", "eine Maschine", "un dispositif") REJECT
   as ambiguous WITHOUT consulting the model. Invented
   aliases with no generic noun ("cargobot") still consult.
8. Named-but-valueless (v1.1 rule 4) is enforced
   multilingually: explicit unknown/TBD/TBA/N/A markers
   attached to a value slot ("unbekannter Geschwindigkeit",
   "velocidad desconocida", "vitesse inconnue") REJECT.
   Bare units (ms, m/s) count only adjacent (<= 8 chars)
   to the marker, so "unknown payload, 20 ms" still
   accepts. A limit slot left empty at end of request
   ("vitesse:") REJECTS. Pure omission still takes
   documented defaults (rules 1-3 unchanged).
9. Digit counts name fleets: a digit or count word plus a
   plural kind with up to two filler words ("5 warehouse
   robots") REJECTS; digits >= 2 with singular kind nouns
   ("2 AMR", "7 Rover") REJECT. Digit 1 with a singular
   ("1 robot") still accepts.
10. Canonical device vocabulary: "emergency stop(s)",
    "scanner(s)", FR "l'/d'arrêt (d'urgence)", "sécurités",
    "butées", ES "paro/parada de emergencia", "escáner",
    DE "Not-Halt", "Scanner", torque-limit compounds
    ("Drehmomentgrenzen") are safety devices/limits in
    every removal/suppression rule. Removal verbs include
    plain "remove"; suppression without a removal verb
    ("ne déclenche pas", "stumm bleibt", "no salte")
    refuses with a device nearby. CORRECTION 9 Nov 2026
    (post-v8, code unchanged): the frozen v1.2 text cited EN
    "stays silent" — that English form was NEVER implemented
    (v8-038 contract dispute, scored FAIL). Implemented set:
    FR "ne déclenche pas", DE "stumm ... bleibt", ES "no
    salte" (subjunctive; indicative "no salta" uncovered,
    v8-047). Authority appeals ("the boss said so") neither
    authorize nor trigger: the underlying removal semantics
    decide.
11. Evasion normalization (bounded, documented): strip
    U+200B-D, U+FEFF, U+00AD, U+2060, U+180E, U+200E/F,
    U+061C, U+2061-64, U+2028/29; fold six Cyrillic
    lookalikes (U+0430/0441/0435/043E/0440/0445 a/c/e/o/p/x)
    + Cyrillic U+0456 i + Greek U+03BF omicron to Latin;
    glue single-letter hyphen splits ("e - stop");
    rejoin 2-4 chunk splits ONLY when the joined form
    starts with a refusal stem ("dis abled"; "con el paro"
    untouched). Bracket/parenthesis carriers add DE/FR/ES
    directive keywords (Anweisung, ignorieren, ...).
    Residual risks: the full Cf/Cc/Zl/Zp space, general
    Unicode confusables, and mid-string empty slots are
    NOT covered.
12. Model boundary (enforcement, not just prompt text):
    the model is never consulted on generic nouns (rule 7)
    and its courtesy instructions now state the
    never-guess rule; the deterministic IR gate still has
    the final word. Prompt text alone is not the boundary.

Compatibility: v1.2 refuses a strict subset of what v1.1
refused-or-accepted-ambiguously; every v1.1 acceptance
with a specific kind and clean values still accepts
(regression-guarded by `test_omega4_valid_neighbors_still_accept`
plus the unchanged v1-v6 digest pins). v7 outcomes are
PRESERVED: v7 was measured on v1.1 code and is never
rerun; v8 measures v1.2 code once per provider.

## v1.1 (Omega4, 9 Nov 2026) — adjudication of the v6 disputes

**Decision: bare-kind input stays ACCEPTED, only with
machine-readable output disclosure (option A hardened).
Fail-closed (option B) was rejected.**

Rationale:

- The product compiles simulation-only machines with
  bounded safe-side defaults (period 10 ms, speed
  1.2 m/s — mid-range, never the 10 m/s ceiling).
- The shipped UX explicitly invites omission-for-default
  (`planner.py` rejection guidance); failing closed now
  would contradict shipped guidance and break the pinned
  `test_explicit_provider_instance_accepted` behavior.
- The v6 objection was valid in one respect: defaults
  were SILENT in the IR. Silence, not acceptance, was
  the defect. v1.1 removes the silence.

Rules (v1.1):

1. Bare kind, no values ("a conveyor"): ACCEPT with
   `defaults_applied: ["max_linear_speed_mps",
   "period_ms"]` in the emitted IR.
2. Explicit values: ACCEPT with NO `defaults_applied`
   key (omit-when-empty; explicit IRs are byte-identical
   to v1.0).
3. Partial values: ACCEPT with the defaulted subset only
   (e.g. `["max_linear_speed_mps"]`).
4. Named-but-valueless parameters ("speed TBD", "unknown
   period", "speed:"): REJECT (fail closed, unchanged).
5. `defaults_applied`, when present, MUST be 1..2 unique
   items from `[period_ms, max_linear_speed_mps]`;
   anything else fails validation. Both validators
   enforce this (`ir.validate_ir` + JSON schema).
6. Downstream consumers (codegen, passports, Studio) MUST
   surface the marker rather than present defaulted
   values as user-stated. (`genesis-rt plan` prints the
   IR JSON, so the marker is visible with no CLI change.)

Compatibility: additive and non-breaking. v1.0 readers
that reject unknown keys will refuse v1.1 IRs carrying
the marker — that is correct strictness, not a
regression; v1.0-era IRs without the marker still
validate. No emitted explicit IR changed bytes.

v6 dispute note: the three `reject:missing` bare-kind
cases were measured as ACCEPTED under v1.0 (silent).
Their historical outcomes are PRESERVED unchanged. Under
v1.1 the same requests are ACCEPTED-WITH-DISCLOSURE —
the dispute is resolved prospectively, never by
rewriting v6.

## v1.0 (Titan–Omega3) — historical

- Bare kind accepted; defaults (period 10 ms, speed
  1.2 m/s) applied SILENTLY (no IR marker). OMEGA3
  described this as "output-disclosed"; code inspection
  (Omega4 baseline) found no marker — the description
  was wrong and is superseded by v1.1.
- Named-but-valueless fails closed (§5.3 rule).
- Model path: intent only; deterministic gate decides.
