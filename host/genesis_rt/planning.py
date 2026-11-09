# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-independent planning interface with validated output.

AI (or any provider) may *propose* machine specifications, but every
proposal travels the same strict validation gate as offline input:
provider output is untrusted until ``validate_ir`` accepts it. Providers
can never override safety policy, bypass the gate, or mark tests passed
-- they only produce candidate IR.

The deterministic offline provider is the default; no paid API and no
network are required. An opt-in OpenAI-compatible ``llm`` provider exists
(env-configured, stdlib HTTP, 64 KiB cap) and is held to the same gate. Third parties add a provider by implementing one
method (``propose_raw``) and registering it in ``PROVIDERS``; see
``docs/planning-eval.md``. Requests that demand unsafe, out-of-scope,
or prompt-injecting behavior are refused with a precise explanation.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol

from .ir import IRValidationError, validate_ir
from .planner import PlannerRejection
from .planner import _KIND_HINTS
from .planner import propose as offline_propose

# Unsafe / out-of-scope request patterns (matched on the lowered text).
# Each maps to a precise refusal explanation shown to the requester.
# This is a courtesy pre-filter for clear explanations, NOT the safety
# boundary: a rephrased request can slip past a regex. The boundary is
# validate_ir (simulation_only, bounded limits, guards) plus the
# deterministic compiler and the fail-closed evidence gate.
#
# Omega3 §5.3: the device/action classes below generalize the Titan
# verb lists (strip/mute/deactivate/detach/unplug/defeat,
# sans/ohne/sin, unnecessary-class) after the v5 0/6 unsafe score.
# Safe presence ("guard verified present", "curtain tested") contains
# no removal verb and still accepts.
_REMOVAL_VERBS = (r"strip(?:ped|ping)?|mute[sd]?|deactiv\w*|detach\w*"
                  r"|disconnect\w*|unplug\w*|defeat\w*|do\s+without"
                  r"|tak(?:e|en)\s+(?:out|off|away)|cut\s+out"
                  # Hardening-2: wide-window-safe additions only
                  # (silenced curtains, jumpered loop classes).
                  r"|silenc\w*|jumper\w*"
                  # Omega4 fix-1: plain "remove" was missing here, so
                  # "remove the <device>" only fired for the small
                  # inline device set (v7-r01 class). The device on
                  # the other side keeps the window safe.
                  r"|remov\w*")
# Hardening-2: verbs that must directly govern the device
# ("drop the guard", "lift the rear guard") — too risky in a
# wide window ("drop off totes, guard present" is benign).
_GOVERN_VERBS = (r"lift\w*|rais\w*|hoist\w*|open|drop|quiet\w*"
                 r"|bridg\w*|disabl\w*|bypass\w*")
# Hardening-2: disabled-state participles after the device
# ("guard lifted", "fence disabled", "relay bridged").
_DISABLED_STATES = (r"lifted|raised|hoisted|opened|dropped|jumpered"
                    r"|bridged|silenced|quieted|shorted|disabl\w*"
                    r"|remov\w*|bypassed")
# Hardening-2: removal nominalizations ("removal of the e-stop",
# "curtain bypass").
_REMOVAL_NOUNS = r"removal|disabling|deactivation|bypass|absence"
# Hardening-2: lack/minus govern the device directly
# ("lacking any interlock", "minus its bumper").
_LACK_VERBS = r"lack\w*|missing"
# Hardening-2: German/Spanish/French device + removal tables
# (blind-v6 multilingual classes).
_DE_DEVICES = (r"schutzzaun|zaun|lichtvorhang|vorhang|not-?aus"
               r"|absperrung|sicherheitsschalter|scanner"
               # Omega4 fix-1: "Not-Halt" and torque-limit compounds
               # (v7-r06/r08 classes).
               r"|not[-\s]?halt|(?:drehmoment|drehzahl"
               r"|geschwindigkeits)?grenzen")
_DE_REMOVAL = (r"demont\w*|abmont\w*|ausgebaut|entfern\w*|deaktiv\w*"
               r"|stillleg\w*|ausser\s+betrieb|außer\s+betrieb"
               # Omega4 fix-1: "abgeschaltet" (switched off).
               r"|abgeschaltet|abschalten")
_ES_DEVICES = (r"cortina|valla|barrera|interruptor|enclavamiento"
               # Omega4 fix-1: emergency-stop nouns + safety scanner.
               r"|paro\s+de\s+emergencia|parada\s+de\s+emergencia"
               r"|esc[áa]ner(?:es)?")
_ES_REMOVAL = (r"desmont\w*|desactiv\w*|sin\s+activ\w*"
               r"|fuera\s+de\s+servicio|quit\w*")
_FR_DEVICES = (r"barriere|barrière|rideau|grillage|cloture|clôture"
               # Omega4 fix-1: e-stop nouns, safeties, limit stops,
               # safety scanner (v7-r03/r04/r05 classes).
               r"|[ld][’']arr[êe]ts?|s[ée]curit[ée]s?|but[ée]es?|scanners?")
_FR_REMOVAL = (r"d[ée]mont\w*|retir\w*|enlev\w*|hors\s+service"
               r"|désactiv\w*|desactiv\w*")
# Omega4 fix-1: suppression phrasings that name no removal verb
# ("does not trigger/trip", "stays silent"); each requires a
# safety device within 30 chars so benign uses stay accepted.
_FR_SUPPRESS = r"(?:ne\s+)?d[ée]clenche(?:nt)?\s+pas"
_DE_SUPPRESS = r"stumm.{0,30}bleib\w*|bleib\w*.{0,30}stumm"
_ES_SUPPRESS = r"no\s+salte(?:n)?"
# Omega4 fix-1: explicit unknown/TBD limit markers. Omission
# (bare kind) takes documented defaults; an explicit unknown
# is not omission and must refuse. Each marker requires a
# value-slot token within 30 chars ("unknown payload" passes).
_UNKNOWN_MARKERS = (r"unknown|tbd|tba|\bn/a\b|tbc|unspecified"
                    r"|inconnu|inconnue|ind[ée]finis?|non\s+d[ée]fini"
                    r"|[àa]\s+d[ée]finir|unbekannt\w*|desconocid[oa]s?"
                    r"|sin\s+definir|por\s+definir")
_VALUE_SLOTS = (r"period|speed|velocity|vitesse|p[ée]riode|periode"
                r"|geschwindigkeit|tempo|velocidad|periodo")
# Omega4 fix-1: bare units are promiscuous ("unknown payload,
# 20 ms" must pass), so they only count adjacent to the marker.
_VALUE_UNITS = r"\bms\b|m/s"
# Hardening-2: explicit counts turn a plural into a fleet
# ("three rovers" refuses; bare "rovers" accepts).
_COUNT_WORDS = (r"two|three|four|five|six|seven|eight|nine|ten"
                r"|eleven|twelve|both|dozen|several|multiple|many")
_PLURAL_KINDS = (r"rovers|robots|amrs|mobiles|conveyors|belts|lines"
                 r"|arms|grippers|manipulators|agvs|cobots")
# Omega4 fix-1: singular kind nouns that only signal a fleet with
# a digit >= 2 ("7 Rover", "2 AMR"); digit 1 keeps accepting.
_SINGULAR_FLEET_KINDS = (r"robot|rover|amr|agv|cobot|mobile|belt"
                         r"|conveyor|arm|gripper|manipulator")
# Omega4 fix-1: generic machine nouns that name no specific kind
# ("set up a machine", "une Maschine"). With no kind hint they
# veto the model consult (ambiguous); invented aliases with no
# generic noun still consult.
_GENERIC_NOUNS = (r"machine|unit|device|apparatus|equipment|system"
                  r"|contraption|gadget|thing"
                  r"|dispositif|appareil|unit[ée]|syst[èe]me|équipement"
                  r"|maschine|gerät|einheit|vorrichtung|anlage"
                  r"|m[áa]quina|unidad|dispositivo|aparato|equipo|sistema")
_SAFETY_DEVICES = (r"guards?|guarding|e-?stops?|estops?|interlocks?"
                   r"|watchdogs?|curtains?|light\s+curtain"
                   r"|safety\s+curtain|bumpers?|safety\s+switch"
                   r"|safety\s+fence|fences?|safety"
                   r"|not-?aus\b|arr[êe]t|enclavamiento|verriegelung"
                   # Omega4 fix-1: the canonical emergency-stop nouns
                   # plus the safety scanner (v7-r01/r02 classes).
                   r"|emergency[-\s]?stops?|scanners?"
                   r"|[ld][’']arr[êe]ts?|paro\s+de\s+emergencia"
                   r"|parada\s+de\s+emergencia|not[-\s]?halt")
_ZERO_WIDTH_RE = re.compile(
    "[\u200b\u200c\u200d\ufeff\u00ad"
    # Omega4 fix-1: word joiner, directional marks, Mongolian
    # vowel separator, isolate controls, line/paragraph
    # separators (v7-r51/r54 classes). Bounded set; the full
    # Cf/Cc/Zl/Zp space is NOT covered.
    "\u2060\u180e\u200e\u200f\u061c\u2061\u2062\u2063\u2064\u2028\u2029]")
_SPACED_LETTERS_RE = re.compile(r"\b([a-z])(?:\s+[a-z]){2,}\b")
# Omega4 fix-1: single-letter hyphen splits ("e - stop").
_SPACED_HYPHEN_RE = re.compile(r"\b([a-z])\s*-\s*([a-z])")
# Omega4 fix-1: bounded Cyrillic/Greek lookalike fold applied to
# the lowered text ("guаrd" -> "guard"). Six Cyrillic letters
# plus i/omicron only; general confusable folding is out of
# scope and documented as a residual risk.
_HOMOGLYPH_FOLD = str.maketrans({
    "а": "a",  # U+0430 CYRILLIC SMALL LETTER A
    "с": "c",  # U+0441 CYRILLIC SMALL LETTER ES
    "е": "e",  # U+0435 CYRILLIC SMALL LETTER IE
    "о": "o",  # U+043E CYRILLIC SMALL LETTER O
    "р": "p",  # U+0440 CYRILLIC SMALL LETTER ER
    "х": "x",  # U+0445 CYRILLIC SMALL LETTER HA
    "і": "i",  # U+0456 CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    "ο": "o",  # U+03BF GREEK SMALL LETTER OMICRON
})
# Omega4 fix-1: split-word evasion ("dis abled", "des acti vado").
# Chunk sequences rejoin ONLY when the joined form starts with a
# refusal stem, so ordinary word pairs ("con el paro") pass
# through untouched.
_REJOIN_CHUNKS_RE = re.compile(
    r"\b([a-zà-ÿ]{1,6}(?:\s+[a-zà-ÿ]{1,6}){1,3})\b")
_REJOIN_STEMS = ("remov", "disabl", "deactiv", "desactiv", "désactiv",
                 "retir", "enlev", "démont", "demont", "desmont",
                 "entfern", "deaktiv", "abmont", "stillleg", "quit",
                 "bypass", "silenc", "inactiv", "sactiva")


def _rejoin_split_words(text: str) -> str:
    """Slide a 2-4 chunk window over each chunk run; rejoin a
    window only when the joined form starts with a refusal stem
    ("guard dis abled for" -> "guard disabled for")."""
    def fix(m: "re.Match[str]") -> str:
        chunks = m.group(1).split(" ")
        # Shortest window first: "dis abled for" must rejoin to
        # "disabled", not to "disabledfor".
        for width in (2, 3, 4):
            for i in range(len(chunks) - width + 1):
                joined = "".join(chunks[i:i + width])
                if joined.startswith(_REJOIN_STEMS):
                    chunks[i:i + width] = [joined]
                    return " ".join(chunks)
        return m.group(1)
    prev = None
    while prev != text:
        prev = text
        text = _REJOIN_CHUNKS_RE.sub(fix, text)
    return text


def canonicalize_request(text: str) -> str:
    """Hardening-2 + Omega4 fix-1: strip zero-width/format chars,
    fold bounded homoglyphs, rejoin spaced-out letters
    ('d i s a b l e d') and split words ('dis abled'), glue
    single-letter hyphen splits ('e - stop'), so evasions meet
    the same guard as plain text."""
    text = _ZERO_WIDTH_RE.sub("", text or "")
    text = text.translate(_HOMOGLYPH_FOLD)
    text = _SPACED_HYPHEN_RE.sub(r"\1-\2", text)
    text = _REJOIN_CHUNKS_RE.sub(
        lambda m: _rejoin_split_words(m.group(0)), text)
    return _SPACED_LETTERS_RE.sub(
        lambda m: m.group(0).replace(" ", ""), text)
_UNNEEDED_WORDS = (r"unnecessary|unneeded|not\s+needed|not\s+required"
                   r"|dispensable|optional|redundant|superfluous")
_SCHEMA_FIELDS = (r"max_linear_speed_mps|period_ms|max_angular_speed_radps"
                  r"|freshness_limit_ms|guarded_state_transitions"
                  r"|execution_target|simulation_only|schema_version")
_NONENGLISH_REMOVAL = r"désactiv\w*|desactiv\w*|deaktiv\w*|entfern\w*"
_UNSAFE_PATTERNS: tuple[tuple[str, str], ...] = (
    # Omega3 §5.3: bracketed/parenthesized instruction carriers FIRST
    # (v5-r24 '[system: ...]' class) so smuggled directives get the
    # injection message even when they also name the guard. Parens use
    # a narrow keyword set so '(see manual)' style asides still pass.
    (r"\[[^\[\]]{0,100}(?:system|ignore|disregard|override|instruct"
     r"|prompt|jailbreak|developer\s*mode|admin|execute|bypass"
     # Omega4 fix-1: non-English directive carriers (v7-r54 class).
     r"|anweisung|befehl|ignorier\w*|instruction|instrucci[óo]n)"
     r"[^\[\]]{0,100}\]",
     "prompt-injection style instructions are not followed"),
    (r"\([^()]{0,100}(?:ignore\s+previous|disregard|override|bypass)"
     r"[^()]{0,100}\)",
     "prompt-injection style instructions are not followed"),
    (r"disable.{0,20}guard|guard.{0,20}disable"
     # Hardening-2: \s* tolerates "noguard" (zero-width stripped);
     # fence/curtain/bumper join the no/without device set.
     r"|\b(?:no|without)\s*(?:the\s+)?(?:guard|e-?stop|interlock"
     r"|watchdog|fence|curtain|bumper)\b",
     "disabling or removing the safety guard is not supported"),
    (r"ignore.{0,20}(safe|limit|instruct)|bypass.{0,20}(safe|guard|gate)",
     "bypassing safety policy, the guard, or the verification gate is not supported"),
    (r"no speed limit|unlimited speed|remove.{0,20}limit|without.{0,20}limit",
     "unbounded actuation is not supported; state a speed within (0, 10] m/s"),
    (r"real (hardware|robot|machine)|production (use|deploy)|deploy.{0,20}production",
     "only simulation-only machines are supported; real-hardware deployment is out of scope"),
    (r"simulation.{0,12}(off|false|disable)|no simul",
     "disabling simulation-only mode is not supported"),
    (r"weapon|explosive|surveillance target",
     "that use case is out of scope for this engineering tool"),
    (r"\b(forklifts?|cranes?|hoists?|drones?|quadcopters?|elevators?|"
     r"escalators?|aircraft|airplanes?|helicopters?|submarines?|"
     r"printers?|rockets?|satellites?)\b",
     "that machine is not a supported kind (AMR/conveyor/arm); "
     "describe a supported machine"),
    (r"\b(jokes?|poems?|story|stories|songs?|news|weather|recipes?|"
     r"horoscopes?)\b",
     "that is not a machine specification; describe the machine kind "
     "and its limits"),
    (r"humanoid",
     "that machine is not a supported kind (AMR/conveyor/arm); "
     "describe a supported machine"),
    (r"\b((turn(?:ed|ing)?|switch(?:ed|ing)?|take|took)\s+off\s+"
     # Omega4 fix-1: emergency-stop joins the inline device set.
     r"(the\s+)?(watchdog|e-?stop|safety|guard|interlock|emergency[-\s]?stops?)|"
     r"(watchdog|e-?stop|safety|guard|interlock|emergency[-\s]?stops?)\s+"
     r"(is\s+|was\s+|were\s+|been\s+)?(turn(?:ed|ing)?|switch(?:ed|ing)?)\s+off|"
     r"disabl\w*\s+(the\s+)?(watchdog|e-?stop|safety|guard|interlock|emergency[-\s]?stops?)|"
     r"remov\w*\s+(the\s+)?(watchdog|e-?stop|safety|guard|interlock|emergency[-\s]?stops?)|"
     r"(watchdog|e-?stop|safety|guard|interlock|emergency[-\s]?stops?)\s+"
     r"(is\s+|was\s+|were\s+|been\s+)?remov\w*)",
     "disabling or removing the safety guard is not supported"),
    (r'"kind"\s*:|"max_linear_speed_mps"\s*:|"period_ms"\s*:'
     r'|\bmax_linear_speed_mps\s*[:=]|\bperiod_ms\s*[:=]',
     "prompt-injection style instructions are not followed; describe "
     "the machine in prose"),
    (r"system prompt|jailbreak|ignore previous|do anything now|hidden instructions"
     r"|developer mode|guards? (?:are |is )?(?:optional|off|disabled)",
     "prompt-injection style instructions are not followed"),
    (r"(?:speed |velocity )?limits? (?:removed|off|disabled|lifted)"
     r"|\b(?:no|without) (?:any |speed |velocity )?limits?\b(?! on (?!speed|velocity))",
     "unbounded actuation is not supported; state a speed within (0, 10] m/s"),
    (r"^(?!.*simulat).*(?:production (?:line|floor|use|site)|on site\b|real (?:forklift|motors?|vehicle))",
     "only simulation-only machines are supported; real-world deployment is out of scope"),
    (r"(?<!never )(?<!not )(?<!avoid )(?<!avoids )(?<!without )(?<!no )"
     r"\b(?:push|hit|ram|strike|shove)\w* (?:\w+ )?(?:people|persons?|workers|humans|someone)",
     "behaviour that endangers people is not supported"),
    # Omega3 §5.3: removal verb + safety device in either order
    # (v5-r01/r02/r04/r05/r06 classes: strip/mute/deactivate/
    # detach/unplug/defeat + bumper/curtain/fence/switch).
    (f"(?:{_REMOVAL_VERBS}).{{0,30}}(?:{_SAFETY_DEVICES})"
     f"|(?:{_SAFETY_DEVICES}).{{0,30}}(?:{_REMOVAL_VERBS})",
     "disabling or removing the safety guard is not supported"),
    # Omega3 §5.3: borrowed removal prepositions + non-English
    # removal verbs (v5-r03 'sans interlock' class).
    (f"(?:\\bsans\\b|\\bohne\\b|\\bsin\\b).{{0,15}}(?:{_SAFETY_DEVICES})"
     f"|(?:{_NONENGLISH_REMOVAL}).{{0,30}}(?:{_SAFETY_DEVICES})"
     f"|(?:{_SAFETY_DEVICES}).{{0,30}}(?:{_NONENGLISH_REMOVAL})",
     "disabling or removing the safety guard is not supported"),
    # Omega3 §5.3: device declared unnecessary (v5-r06 class).
    (f"(?:{_UNNEEDED_WORDS})\\b.{{0,30}}(?:{_SAFETY_DEVICES})"
     f"|(?:{_SAFETY_DEVICES}).{{0,30}}(?:{_UNNEEDED_WORDS})\\b",
     "disabling or removing the safety guard is not supported"),
    # Omega3 §5.3: bare schema identifiers (v5-r21 class: no
    # colon/equals needed to count as smuggling).
    (f"\\b(?:{_SCHEMA_FIELDS})\\b\\s*(?:\\d|:|=|\"|true|false|null\\b)"
     f"|\\b\\d+\\s+(?:max_linear_speed_mps|period_ms)\\b"
     f"|\\b(?:set|use|apply)\\b.{{0,12}}"
     f"\\b(?:max_linear_speed_mps|period_ms)\\b"
     # Hardening-2: bare kind= smuggling ("kind=conveyor");
     # kind: fires only with exact schema IDs so questions
     # ("which kind: AMR or belt?") still pass.
     r"|\bkind\s*=\s*[\w\"']"
     r"|\bkind\s*:\s*(?:differential_drive_robot|conveyor"
     r"|robotic_arm_virtual)\b",
     "prompt-injection style instructions are not followed; describe "
     "the machine in prose"),
    # Omega3 §5.3: fleet words and mixed-value correlatives refuse
    # as ambiguous (v5-r23 class) instead of silently defaulting.
    (r"\b(?:fleet|swarms?|convoys?)\b"
     r"|\bsome\b[^.!?;]{0,60}\bsome\b"
     r"|\beach\b.{0,25}\b(?:different|own|separate|individual)\b",
     "ambiguous machine requirement (fleet or mixed values); "
     "name exactly one machine with one set of limits"),
    # Hardening-2: governing verbs ("drop the guard") need the
    # device within two filler words; states ("guard lifted")
    # need the device first or immediately before.
    (f"(?:{_GOVERN_VERBS})\\s+(?:\\w+\\s+){{0,2}}(?:{_SAFETY_DEVICES})"
     f"|(?:{_SAFETY_DEVICES}).{{0,30}}(?:{_DISABLED_STATES})"
     f"|(?:{_DISABLED_STATES}).{{0,12}}(?:{_SAFETY_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: lack/minus govern the device
    # ("lacking any interlock", "minus its bumper").
    (f"(?:{_LACK_VERBS})\\s+(?:any\\s+|the\\s+|its\\s+|an?\\s+)?"
     f"(?:{_SAFETY_DEVICES})"
     r"|\bminus\s+(?:the\s+|its\s+|an?\s+)?" + f"(?:{_SAFETY_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: verb-mediated inactive ("set/switched to
    # inactive") and adjacent inoperable ("inoperable guard").
    (f"(?:{_SAFETY_DEVICES}).{{0,30}}(?:switch\\w*|set|turn\\w*|put)"
     r".{0,15}\binactive\b"
     f"|(?:{_SAFETY_DEVICES})\\s+(?:is\\s+|was\\s+)?"
     r"(?:inoperable|inoperative)\b"
     r"|(?:inoperable|inoperative)\s+(?:the\s+)?" + f"(?:{_SAFETY_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: power loss at the device ("e-stop lost power",
    # "stop was powered down"); bare "line lost power" with the
    # device elsewhere does not match.
    (f"(?:{_SAFETY_DEVICES}).{{0,20}}(?:power\\w*\\s+(?:down|off)"
     r"|los\w*\s+power)"
     r"|(?:power\w*\s+(?:down|off))\s+(?:the\s+)?" + f"(?:{_SAFETY_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: removal nominalizations ("curtain removal",
    # "deactivation of the e-stop").
    (f"(?:{_SAFETY_DEVICES})\\s+(?:{_REMOVAL_NOUNS})\\b"
     f"|(?:{_REMOVAL_NOUNS})\\s+of\\s+(?:the\\s+)?(?:{_SAFETY_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: -free/-less compounds ("interlock-free",
    # "guardless").
    (r"\b\w*(?:guard|fence|curtain|interlock)[- ]free\b"
     r"|\bguardless\b",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: "no <device> needed" ("no fence needed");
    # the comma variant ("no, fence needed!") stays accepted.
    (f"\\bno\\s+(?:a\\s+|the\\s+)?(?:{_SAFETY_DEVICES})\\s+needed\\b",
     "disabling or removing the safety guard is not supported"),
    # Hardening-2: German/Spanish/French removal
    # ("Schutzzaun abmontiert", "valla desmontada",
    # "barriere démontee", "Lichtvorhang ausser Betrieb").
    (f"(?:{_DE_DEVICES}).{{0,30}}(?:{_DE_REMOVAL})"
     f"|(?:{_DE_REMOVAL}).{{0,30}}(?:{_DE_DEVICES})"
     f"|(?:{_ES_DEVICES}).{{0,30}}(?:{_ES_REMOVAL})"
     f"|(?:{_ES_REMOVAL}).{{0,30}}(?:{_ES_DEVICES})"
     f"|(?:{_FR_DEVICES}).{{0,30}}(?:{_FR_REMOVAL})"
     f"|(?:{_FR_REMOVAL}).{{0,30}}(?:{_FR_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Omega4 fix-1: suppression without a removal verb (v7-r04/r07/
    # r10 classes); each arm requires a device within 30 chars.
    (f"(?:{_FR_DEVICES}).{{0,30}}(?:{_FR_SUPPRESS})"
     f"|(?:{_FR_SUPPRESS}).{{0,30}}(?:{_FR_DEVICES})"
     f"|(?:{_DE_DEVICES}).{{0,30}}(?:{_DE_SUPPRESS})"
     f"|(?:{_DE_SUPPRESS}).{{0,30}}(?:{_DE_DEVICES})"
     f"|(?:{_ES_DEVICES}).{{0,30}}(?:{_ES_SUPPRESS})"
     f"|(?:{_ES_SUPPRESS}).{{0,30}}(?:{_ES_DEVICES})",
     "disabling or removing the safety guard is not supported"),
    # Omega4 fix-1: explicit unknown/TBD markers attached to a
    # value slot (v7-r23..r28 classes). Omission-for-default is
    # unaffected: markers without slots ("unknown payload") pass.
    (f"(?:{_UNKNOWN_MARKERS}).{{0,30}}(?:{_VALUE_SLOTS})"
     f"|(?:{_VALUE_SLOTS}).{{0,30}}(?:{_UNKNOWN_MARKERS})"
     f"|(?:{_UNKNOWN_MARKERS}).{{0,8}}(?:{_VALUE_UNITS})"
     f"|(?:{_VALUE_UNITS}).{{0,8}}(?:{_UNKNOWN_MARKERS})",
     "unknown, TBD or empty limit values are not supported; state "
     "an explicit period in ms and speed in m/s"),
    # Omega4 fix-1: a limit slot left empty at the end of the
    # request ("vitesse:"); mid-string empty slots stay uncovered.
    (r"(?:period|speed|velocity|vitesse|p[ée]riode|periode"
     r"|geschwindigkeit|tempo|velocidad|periodo)\s*:\s*$",
     "unknown, TBD or empty limit values are not supported; state "
     "an explicit period in ms and speed in m/s"),
    # Hardening-2: explicit counts make a fleet ("three rovers",
    # "both belts", "2 AMRs"); bare plurals still accept and
    # hyphenated modifiers ("six-axis") never match.
    # Omega4 fix-1: up to two filler words between the count and
    # the kind ("5 warehouse robots"), and digits >= 2 with
    # singular kind nouns ("2 AMR", "7 Rover"). Digit 1 with a
    # singular ("1 robot") still accepts.
    (f"(?:\\b(?:{_COUNT_WORDS})\\b|\\b\\d+\\b)\\s+(?:\\w+\\s+){{0,2}}"
     f"(?:{_PLURAL_KINDS})\\b"
     f"|\\b[2-9]\\d*\\b\\s+(?:\\w+\\s+){{0,2}}"
     f"(?:{_SINGULAR_FLEET_KINDS})\\b",
     "ambiguous machine requirement (fleet or mixed values); "
     "name exactly one machine with one set of limits"),
)


class PlanningProvider(Protocol):
    """One-method adapter: raw proposal for a request (untrusted output)."""

    name: str

    def propose_raw(self, request: str, machine_id: str) -> Any:
        ...


class OfflineProvider:
    """Deterministic bundled provider: keyword planner, no network."""

    name = "offline"

    def propose_raw(self, request: str, machine_id: str) -> Any:
        return offline_propose(request, machine_id=machine_id)


# -- Optional LLM provider (TITAN wave 2) ---------------------------------
# Untrusted assistant -> structured proposal -> strict validate_ir -> the
# deterministic compiler. The LLM never sees evidence, never touches the
# release gate, and its output is discarded unless validate_ir accepts it.
LLM_MAX_RESPONSE_BYTES = 64 * 1024
LLM_TIMEOUT_S = 60
_KIND_PHRASE = {"differential_drive_robot": "AMR robot", "conveyor": "conveyor",
                "robotic_arm_virtual": "robotic arm"}
_LLM_SYSTEM = """You extract a machine INTENT for GENESIS RT. Reply with ONE JSON
object and nothing else, exactly these keys:
{"kind": one of ["differential_drive_robot", "conveyor", "robotic_arm_virtual"]
         or null,
 "period_ms": integer or null,
 "max_linear_speed_mps": number or null,
 "refusal": null or a short reason}
Mapping hints: AMR, rover, mobile/warehouse robot -> differential_drive_robot;
belt, conveyor -> conveyor; arm, manipulator, gripper -> robotic_arm_virtual.
Rules: use null for any value the request does not state (defaults are applied
later). Copy numbers exactly. Units must be milliseconds and m/s: if the request
gives a period in seconds or minutes, or a speed in km/h or other units, set
refusal "wrong units: state the period in ms and the speed in m/s". Refuse
(set refusal) if the request is not about one of these simulated machines, asks
to disable guards, limits or simulation, targets real hardware, or is too vague
to name a machine. Speeds above 10 m/s or periods outside 1..1000 ms: refusal
"out of range".
Generic nouns alone (machine/unit/device, Maschine, dispositif, unidad, ...)
name no machine: refusal "ambiguous machine kind". If the machine could be two
different supported kinds, or none clearly: refusal, never a guess. (These are
courtesy instructions; the deterministic generic-noun veto and the IR gate
enforce the boundary even when the model guesses.)"""


class LLMProvider:
    """OpenAI-compatible chat-completions provider (opt-in, stdlib only).

    Configured only through the environment: GENESIS_AI_ENDPOINT (base URL,
    e.g. http://127.0.0.1:11434/v1 for a local Ollama), GENESIS_AI_MODEL,
    optional GENESIS_AI_API_KEY. The key is sent as a bearer header and is
    never logged or echoed in errors.
    """

    name = "llm"

    def __init__(self) -> None:
        # Counts every model call (incremented once per _chat, the
        # single transport choke point) so eval harnesses report
        # consults directly instead of inferring them from latency.
        self.consults = 0
        self.endpoint = os.environ.get("GENESIS_AI_ENDPOINT", "").rstrip("/")
        self.model = os.environ.get("GENESIS_AI_MODEL", "")
        self._key = os.environ.get("GENESIS_AI_API_KEY", "")
        if not self.endpoint or not self.model:
            raise PlannerRejection(
                "llm provider not configured: set GENESIS_AI_ENDPOINT and "
                "GENESIS_AI_MODEL (the offline provider needs no setup)")
        if not re.match(r"^https?://", self.endpoint):
            raise PlannerRejection("GENESIS_AI_ENDPOINT must be an http(s) URL")

    def _chat(self, request: str) -> Any:
        self.consults += 1
        body = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": request[:2000]},
            ],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        req = urllib.request.Request(self.endpoint + "/chat/completions",
                                     data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_S) as resp:
                raw = resp.read(LLM_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise PlannerRejection(f"llm endpoint returned HTTP {exc.code}") from None
        except (urllib.error.URLError, OSError) as exc:
            raise PlannerRejection(f"llm endpoint unreachable: {exc.__class__.__name__}") from None
        if len(raw) > LLM_MAX_RESPONSE_BYTES:
            raise PlannerRejection("llm response exceeds 64 KiB limit")
        try:
            return json.loads(json.loads(raw)["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise PlannerRejection(f"llm returned malformed output: {exc.__class__.__name__}") from None

    def propose_raw(self, request: str, machine_id: str) -> Any:
        """Model -> structured intent -> deterministic offline template.

        The model never writes IR. Its intent is type-checked here, turned
        into a canonical request for the deterministic planner, and the
        planner's result is checked to carry exactly the intended values.
        """
        # Deterministic-first: units, ranges, ambiguity and length are
        # judged by the offline parser, never by the model (measured on
        # qwen2.5:7b: the model tends to drop "5 km/h" and apply defaults).
        # When the offline parser accepts, its result wins outright — the
        # model is not consulted (measured 8 Nov 2026: model overrides of
        # offline accepts caused false refuses on both models). Only
        # "unknown machine kind" -- i.e. phrasing the keyword parser
        # cannot map -- is handed to the model.
        try:
            return offline_propose(request, machine_id=machine_id)
        except PlannerRejection as exc:
            if not str(exc).startswith("unknown machine kind"):
                raise
            # Omega4 fix-1: generic machine nouns with no specific
            # kind hint veto the consult (v7-r59..r72 overmap
            # class: the model invented kinds for "a machine" /
            # "eine Maschine"). Invented aliases without a generic
            # noun still consult.
            low = (request or "").lower()
            tokens = set(re.findall(r"[a-zà-ÿ]+", low))
            specific = {h for hints, _ in _KIND_HINTS for h in hints}
            if (re.search(rf"\b(?:{_GENERIC_NOUNS})\b", low)
                    and tokens.isdisjoint(specific)):
                raise PlannerRejection(
                    "ambiguous machine kind: a generic machine noun "
                    "names no supported kind (robot/rover/AMR, "
                    "conveyor/belt, arm/gripper)") from None
            # Holdout v1 (llama3.1:8b) turned "write me a poem about QNX"
            # into a machine. With no recognisable machine word, the model
            # is only consulted when the request states a limit in ms or m/s.
            if not re.search(r"\d+(?:\.\d+)?\s*(?:ms|m/s)\b", low):
                raise PlannerRejection(
                    "no supported machine or limit stated; describe the machine "
                    "and give its period in ms or speed in m/s") from None
        intent = self._chat(request)
        if not isinstance(intent, dict):
            raise PlannerRejection("llm returned a non-object intent")
        if intent.get("refusal"):
            raise PlannerRejection(f"llm refused: {str(intent['refusal'])[:200]}")
        kind = intent.get("kind")
        if kind not in _KIND_PHRASE:
            raise PlannerRejection(f"llm intent has unknown kind {kind!r}")
        period = intent.get("period_ms")
        speed = intent.get("max_linear_speed_mps")
        if period is not None and (type(period) is not int or not 1 <= period <= 1000):
            raise PlannerRejection(f"llm intent period_ms out of range: {period!r}")
        if speed is not None and (isinstance(speed, bool) or not isinstance(speed, (int, float))
                                  or not 0 < speed <= 10):
            raise PlannerRejection(f"llm intent speed out of range: {speed!r}")
        canon = _KIND_PHRASE[kind]
        if period is not None:
            canon += f" with {period} ms period"
        if speed is not None:
            canon += f" and {float(speed)} m/s max speed"
        ir = offline_propose(canon, machine_id=machine_id)
        got = ir["machine"]["kind"], ir["control"]["period_ms"], ir["control"]["max_linear_speed_mps"]
        if got[0] != kind or (period is not None and got[1] != period) or \
                (speed is not None and abs(got[2] - float(speed)) > 1e-9):
            raise PlannerRejection(f"deterministic template disagrees with llm intent: {got}")
        return ir


PROVIDERS: dict[str, type[Any]] = {"offline": OfflineProvider, "llm": LLMProvider}


def _refuse_unsafe(request: str) -> None:
    text = canonicalize_request((request or "").lower())
    for pattern, explanation in _UNSAFE_PATTERNS:
        if re.search(pattern, text):
            raise PlannerRejection(f"unsafe or unsupported requirement: {explanation}")


def plan_machine(request: str, machine_id: str = "machine-01",
                 provider: str | PlanningProvider = "offline") -> dict[str, Any]:
    """Plan a machine through a provider; output strictly validated.

    Raises PlannerRejection for unsafe requests, unknown providers,
    provider failures, and proposals that fail IR validation.
    """
    if isinstance(provider, str):
        if provider not in PROVIDERS:
            raise PlannerRejection(
                f"unknown provider {provider!r}; available: {sorted(PROVIDERS)}")
        _refuse_unsafe(request)
        impl: PlanningProvider = PROVIDERS[provider]()
    else:
        impl = provider
    _refuse_unsafe(request)
    try:
        raw = impl.propose_raw(request, machine_id)
    except PlannerRejection:
        raise
    except Exception as exc:  # noqa: BLE001 - provider bugs must not escape raw
        raise PlannerRejection(f"provider {impl.name!r} failed: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlannerRejection(
            f"provider {impl.name!r} returned a non-object proposal: "
            f"{type(raw).__name__}")
    try:
        return validate_ir(raw)
    except IRValidationError as exc:
        raise PlannerRejection(
            f"provider {impl.name!r} proposal rejected by IR validation: {exc}"
        ) from exc
