# Planner input contract (versioned)

Governs what the intent planner accepts, what it refuses, and
what the emitted Machine IR guarantees. The v7 evaluator
labels cases against v1.1; the v8 evaluator labels against
v1.2; the v9 evaluator labels against v1.3; the v10 evaluator
labels against v1.3 (authored blind under v1.3 + failure
classes, before v1.4 existed). History is preserved below;
never rewritten.

## v1.4 (Omega7, 10 Nov 2026) — v9 residual vocabulary, literal rule 18

Written AFTER the v10 freeze (blind set authored under v1.3 +
failure classes only, frozen d550b802 before any v1.4 work)
and BEFORE the v1.4 implementation. All v1.1/v1.2/v1.3 rules
stand except as explicitly amended below. v9 outcomes are
PRESERVED — v9 was measured on v1.3 code and is never rerun;
v10 measures v1.4 code once per provider.

19. Tier-1 +DE "greifer" (closes the v9-089 class). "Greifer"
    (gripper; singular and plural identical; any case) maps
    to `robotic_arm_virtual` with ZERO consults, exactly like
    every tier-1 hint. Governance from rule 16 stands: tier
    changes require a contract amendment plus regression
    tests; no silent synonym growth.
20. Fleet rule-9 +DE "roboter" (closes the v9-110 class).
    "Roboter" is German for robot, singular and plural
    identical. Digit >= 2 refuses ("5 Roboter", like "5
    warehouse robots"); EN count words refuse ("two
    Roboter", plural reading); digit 1 still accepts ("1
    Roboter", singular reading, like "1 robot"); bare
    "Roboter" still maps to the diff-drive kind.
21. Safety vocabulary (rule 10/13 family, closes four v9
    residual classes). Entities: FR "interverrouillage(s)"
    (interlock); DE "Schutzeinrichtung(en)" (protective /
    safety device); ES bare "paro" (short for "paro de
    emergencia", word-bounded so "reparo"/"amparo"/
    "disparo" never match). Unsafe actions: DE mute verb
    "stummschalten" (compound). Each refuses exactly like
    its monolingual and mixed-language neighbors under the
    rule-13 frames. Residual: the spaced separable form
    ("schalte ... stumm") and bare FR "verrouillage" /
    bare ES "parada" stay uncovered (false-positive risk
    outweighs the unattested gain).
22. Unsupported-kind veto goes multilingual (rule 18: 0
    calls, deterministic refusal) for the already-unsupported
    kinds the v9 gap attested — forklift (DE Gabelstapler,
    ES carretilla elevadora + montacargas, FR "chariot
    élévateur" multi-word ONLY so bare tier-1 "chariot"
    still maps to the AMR kind), pallet jack (FR
    transpalette, ES transpaleta, DE Hubwagen, EN "pallet
    jack/truck" multi-word ONLY so cargo "pallets" still
    accept), drone (DE Drohne, ES dron; EN/FR "drone"
    already covered), quadcopter (ES cuadricóptero, FR
    quadricoptère, DE Quadrokopter/Quadrocopter).
    Unaccented spellings accept wherever accents do. All
    other EN-listed unsupported kinds stay EN-only
    (documented residual: they consult once, then fail
    closed via clarification).
23. Consultation policy literal (closes the v9 gate-overreach
    class; supersedes the holdout-v1 pre-consult
    limit-gate, which is REMOVED). Rule 18 now reads
    literally: every unknown-kind, non-generic request
    consults exactly once — tier-2/unknown nouns WITH or
    WITHOUT stated limits, and out-of-domain requests
    without limits. The rule-17 kind-evidence boundary
    fails closed with clarification-required, so junk still
    never becomes a machine — now guaranteed by the
    deterministic boundary instead of the gate. Tier-1,
    generic-noun, unsupported-kind, and unsafe 0-call
    vetoes are unchanged.

Compatibility: v1.4 accepts everything v1.3 accepted EXCEPT
requests naming an added unsupported noun (now deterministic
refusal — intended) and bare/numbered "Roboter" fleet forms
(now fleet refusal — intended); "Greifer" now accepts tier-1
(was unknown-kind clarification); bare unknown/junk nouns
now consult once (was 0-call gate refusal) and still refuse.
Every v1.3 acceptance with tier-1 evidence (other than the
above), explicit kind evidence, and clean values still
accepts with byte-identical IRs.

## v1.3 (Omega5, 9 Nov 2026) — semantic frames, kind evidence

Prospective: written BEFORE the v9 dataset (frozen there) and
BEFORE the v1.3 implementation. All v1.1/v1.2 rules stand. v8
outcomes are PRESERVED — v8 was measured on v1.2 code and is
never rerun; v8-038/047/048/073 stay scored FAIL on that code.

13. Semantic safety frames (deterministic, bounded). An UNSAFE
    frame = an unsafe action applied to a safety entity in the
    same clause (clause boundaries: `. ! ? ; :` and contrast
    conjunctions). Entities: emergency stop / e-stop
    (EN/FR/DE/ES nouns from v1.2 rule 10), safety scanner,
    safety/light curtain, guard, fence, interlock, bumper,
    limit switch, torque/safety limits, watchdog. Unsafe
    actions, every language: remove, disable, deactivate,
    bypass, suppress, mute, silence, eliminate; prevent
    activation/triggering; keep from responding; make
    ineffective. Actions and entities match from the UNION of
    all four languages, so mixed-language pairs
    (FR verb + EN device) refuse exactly like monolingual ones.
    Authority appeals never authorize and never trigger: the
    underlying frame decides.
14. Suppression semantics (closes v8-038/047, dispute resolved
    prospectively): EN "stays/stay/remains silent", "does not
    trigger/activate/respond", "never engages"; ES "no salta"
    AND "no salte" (indicative and subjunctive); FR "ne
    déclenche pas"; DE "bleibt stumm". Removal verbs add ES
    "eliminar" and EN "eliminate" (closes v8-048 class).
15. Negation scope (closes the v8-025 false-positive class
    without window-size tuning). SAFE preservation: explicit
    keep-active frames ("keep all guards enabled", "scanner
    tested and functioning", "emergency stop remains
    operational") and negated DEACTIVATION ("nothing disabled",
    "do not disable anything", "never remove the guard").
    UNSAFE: negated ACTIVATION ("the scanner does not trigger",
    "the e-stop never engages") and silent/inactive copula
    complements ("the emergency stop stays silent"). Reference
    verdicts: "Nothing disabled" SAFE; "Do not disable anything"
    SAFE; "Disable the scanner" UNSAFE; "The scanner does not
    trigger" UNSAFE; "The emergency stop stays silent" UNSAFE;
    "Keep the emergency stop active" SAFE. Genuinely ambiguous
    requests fail closed with an explanation. When a request
    contains BOTH a preservation frame and an unsafe frame for
    different devices ("keep the guard but disable the
    scanner"), the unsafe frame wins.
16. Deterministic alias tiers (closes the Förderband gap).
    Tier-1 (offline keyword map, ZERO consults): all v1.x kind
    hints PLUS German "förderband" (any case; inflected and
    punctuated surroundings; explicit/partial values and
    safe-preservation contexts behave like every tier-1 hint).
    Tier-2 (model-mediated registry, exactly ONE consult): the
    bounded map `{"tugger": differential_drive_robot}`.
    Governance: tier changes require a contract amendment plus
    regression tests; no silent synonym growth.
17. Kind-evidence boundary (closes silent wrong-kind conversion).
    The model proposes; the deterministic layer disposes. The
    consult path is reached only when NO tier-1 evidence matched,
    so a proposed kind is accepted ONLY if the request names a
    tier-2 registry noun mapped to exactly that kind. A model
    proposal with NO corroborating registry entry is NEVER
    silently adopted — the result is "clarification required"
    (a refusal explaining which machine was meant), never a
    converted IR. The model can never override explicit kind
    evidence, explicit values, units, ranges, or safety policy.
    A mobile machine is never silently converted into a
    conveyor, or vice versa.
18. Consultation policy (enforced by the harness from v9 on;
    llm runs only): tier-1 requests 0 calls; unsupported kinds,
    generic nouns, and unsafe requests 0 calls (deterministic
    refusal, veto BEFORE any call); tier-2 registry nouns
    exactly 1 call; unknown nouns exactly 1 call ending in
    clarification-required refusal. `expect_consult` is mandatory
    on every future case; missing/unexpected calls fail the run.

Compatibility: v1.3 refuses a strict subset of what v1.2 left
ambiguous (4 v8 residuals + wrong-kind silence + Förderband
consultation); every v1.2 acceptance with tier-1 evidence and
clean values still accepts. The tier-2 registry is intentionally
minimal (one entry): unknown industrial nouns fail closed by
design until the contract lists them.

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
