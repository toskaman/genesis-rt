# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Omega5 §3.2: bounded deterministic semantic frames for safety.

A structured alternative to window-size tuning: the request is split
into clauses; safety entities and unsafe actions are matched from the
UNION of all four languages (mixed-language pairs refuse exactly like
monolingual ones); copula complements, negated activation, prevention
complements, declarative lack, and negation scope decide the verdict.

Layers (planning._refuse_unsafe): an unsafe frame refuses at once;
a preservation frame exempts only the device-safety patterns (all
other rules still run); otherwise every legacy pattern runs. Legacy
patterns stay as the regression-pinned base; frames add the v1.3
semantics (silence, indicative suppression, eliminar/eliminate,
cross-language union, scoped negation). Operates on canonicalized,
lowered text.
"""
from __future__ import annotations

import re

_CLAUSE_SPLIT = re.compile(
    r"[.!?;:]+|\b(?:but|however|though|although|mais|toutefois|cependant"
    r"|aber|jedoch|sondern|pero|sin embargo|aunque)\b")

_ENT = (r"emergency[-\s]?stops?|e-?stops?|estops?|scanners?|"
        r"light\s+curtain|safety\s+curtain|curtains?|guards?|guarding|"
        r"fences?|safety\s+fence|interlocks?|bumpers?|"
        r"limit\s+switch(?:es)?|torque\s+limits?|safety\s+limits?|"
        r"safety\s+switch|watchdogs?|"
        r"barriere|barrière|rideau|grillage|cloture|clôture|"
        r"[ld][’']arr[êe]ts?|bouton\s+d[’']arr[êe]t|s[ée]curit[ée]s?|"
        r"but[ée]es?|capteur\s+de\s+s[ée]curit[ée]?|"
        r"schutzzaun|sicherheitszaun|zaun|lichtvorhang|vorhang|"
        r"not-?aus|not[-\s]?halt|absperrung|sicherheitsschalter|"
        r"(?:drehmoment|drehzahl|geschwindigkeits)?grenzen|"
        r"cortina|valla|barrera|interruptor|enclavamiento|"
        r"paro\s+de\s+emergencia|parada\s+de\s+emergencia|"
        r"esc[áa]ner(?:es)?|l[íi]mites?\s+de\s+seguridad|"
        r"bot[óo]n\s+de\s+emergencia")
_ENT_RE = re.compile(_ENT)

_REMOVE = (r"remov\w*|eliminat\w*|elimin\w*|strip\w*|detach\w*|"
           r"tak(?:e|en)\s+(?:out|off|away)|cut\s+out|cut\s+off|"
           r"do\s+without|retir\w*|enlev\w*|d[ée]mont\w*|supprim\w*|"
           r"entfern\w*|demont\w*|abmont\w*|ausbau\w*|beseitig\w*|"
           r"quit\w*|desmont\w*")
_DISABLE = (r"disabl\w*|deactiv\w*|desactiv\w*|désactiv\w*|deaktiv\w*|"
            r"inactiv\w*|inoperable|mute\w*|silenc\w*|unplug\w*|"
            r"disconnect\w*|switch\s+off|turn\s+off|shut\s+off|"
            r"power\s+(?:down|off)|[ée]teindre|mettre\s+hors\s+service|"
            r"hors\s+service|abschalten|abgeschaltet|stillleg\w*|"
            r"ausser\s+betrieb|außer\s+betrieb|ausschalten|apag\w*|"
            r"desconect\w*|fuera\s+de\s+servicio|jumper\w*|bridg\w*|"
            r"bypass\w*|defeat\w*|umgeh\w*|überbrück\w*|puentear|"
            r"anular|contourne\w*|neutralis\w*")
_ACTION = f"(?:{_REMOVE}|{_DISABLE})"
_ACTION_RE = re.compile(_ACTION)

# Copula + bad complement ("stays silent", "bleibt stumm").
_SILENCE = re.compile(
    r"(?:stays?|stay|remains?|remain|keeps?|keep|goes?|go|falls?|"
    r"fall|renders?|render|left|leaves?|leave)\b.{0,12}"
    r"\b(?:silent|silenced|inactive|quiet|quieter|off|dark|dead|"
    r"mute|muted|blind|deaf|disabled|disables?)\b|"
    r"reste\s+silencieu[xs]|restent\s+silencieux|"
    r"bleibt\s+stumm|bleiben\s+stumm|stumm\s+bleibt|"
    r"l[öo]st\s+nicht\s+aus|"
    r"(?:ne\s+)?d[ée]clenche(?:nt)?\s+pas|"
    r"no\s+salte?(?:n)?|sin\s+que\s+salte?(?:n)?")

# Negated activation ("does not trigger", "never engages").
# Entity-before order takes the full verb set; verb-before-entity
# takes only {engage, trigger, activate} so "does not work, guard
# present" stays accepted.
_NEG_ACT_BEFORE = re.compile(
    r"(?:does\s+not|doesn'?t|do\s+not|don'?t|never|won'?t|will\s+not|"
    r"fails?\s+to|failed\s+to|can'?t|cannot)\s+(?:\w+\s+){0,2}"
    r"(?:trigger|activate|engage|respond|work|function|sound|fire)\w*")
_NEG_ACT_AFTER = re.compile(
    r"(?:never|not|n'?t)\s+(?:\w+\s+){0,1}"
    r"(?:engag\w*|trigger\w*|activat\w*)")

# Prevention with complement ("prevent the scanner from triggering").
# The entity sits INSIDE the pattern: bare "prevent" + a device
# elsewhere ("prevent damage, scanner present") must NOT match.
_PREVENT = re.compile(
    rf"(?:prevent\w*|keeps?)\s+(?:the\s+)?(?:{_ENT})\s+from\s+"
    r"(?:triggering|activating|engaging|responding|working|sounding)|"
    rf"render\w*\s+(?:the\s+)?(?:{_ENT})\s+"
    r"(?:ineffective|inoperative|useless)|"
    rf"mak\w*\s+(?:the\s+)?(?:{_ENT})\s+ineffective|"
    rf"emp[êe]cher\s+(?:le\s+|la\s+|l[’'])?(?:{_ENT})\s+de\s+"
    r"d[ée]clencher|"
    rf"(?:{_ENT}).{{0,15}}unwirksam.{{0,10}}machen|"
    rf"impedir\s+(?:que\s+)?(?:el\s+|la\s+)?(?:{_ENT})")

# Declarative lack ("no guard", "sans rideau", "guardless").
_LACK = re.compile(
    r"\b(?:no|minus|lacking|sans|ohne|sin)\s+(?:a\s+|the\s+|an\s+|"
    r"le\s+|la\s+|les\s+|der\s+|die\s+|das\s+|el\s+|la\s+)?"
    rf"(?:{_ENT})")
_LESS = re.compile(r"\b(?:guard|fence|curtain|interlock)(?:less|\s*-free)\b")
# Except-carve-out reverses a negation ("nothing disabled except X").
_CARVE = re.compile(
    r"\b(?:nothing|never|no)\s+\w+\s+except\s+(?:the\s+)?"
    rf"(?:{_ENT})")

# Preservation: keep-active frames + negated deactivation.
_KEEP = re.compile(
    r"\b(?:keeps?|kept|keeping|leave|leaves|left|maintain\w*|"
    r"preserve\w*|laisser|laissez|maint\w*|garder|bleiben|bleibt|"
    r"lassen|behalten|mantener|mantenga|dejar|conservar)\b")
_HEALTHY = re.compile(
    r"\b(?:active|enabled|on|operational|present|functioning|working|"
    r"tested|engaged|intact|connected|ok(?:ay)?|fine|live|acti\w*|"
    r"en\s+service|op[ée]rationnels?|test[ée]s?|pr[ée]sents?|aktiv|"
    r"eingeschaltet|funktionsf[äa]hig|gepr[üu]ft|vorhanden|"
    r"encendido|probado|presente)\b")
# Note: bare "not" excludes the German compound prefix in Not-Halt /
# Not-Aus (hyphen makes a word boundary): "Not-Halt abmontiert" must
# not read as English negation governing the action.
_NEG = (r"no|not(?![-\s]?(?:halt|aus)\b)|n'?t|never|nothing|none|"
        r"without|don't|doesn't|didn't|won't|can't|cannot|ne|pas|"
        r"jamais|rien|aucun|sans|nicht|kein\w*|nie|niemals|nichts|"
        r"ohne|nunca|jam[áa]s|nada|ning[úu]n|sin")
# Negated unsafe action ("never remove the guard", "nothing
# disabled"): removal AND deactivation verbs alike.
_NEG_DEACT = re.compile(
    rf"\b(?:{_NEG})\b.{{0,15}}(?:{_REMOVE}|{_DISABLE})")
_NEG_WORD = re.compile(rf"\b(?:{_NEG})\b")


def _clauses(text: str) -> list[str]:
    return [c for c in _CLAUSE_SPLIT.split(text or "") if c.strip()]


def _unnegated_action(clause: str) -> bool:
    """An action span counts only when no negation word governs it
    from the left within 15 chars ("guards never disabled" names
    no unsafe action; "never remove X and disable Y" still does)."""
    negs = [m.end() for m in _NEG_WORD.finditer(clause)]
    for act in _ACTION_RE.finditer(clause):
        if not any(0 <= act.start() - n <= 15 for n in negs):
            return True
    return False


def unsafe_frame(text: str) -> str | None:
    """Return a frame tag when a clause applies an unsafe action to
    a safety entity; None when no unsafe frame matches."""
    for clause in _clauses(text):
        if _CARVE.search(clause):
            return "carve-out frame"
        ents = list(_ENT_RE.finditer(clause))
        if not ents:
            continue
        if _unnegated_action(clause):
            return "action-entity frame"
        if _SILENCE.search(clause):
            return "suppression frame"
        for ent in ents:
            for m in _NEG_ACT_BEFORE.finditer(clause):
                # Entity governs from the left ("the scanner does
                # not trigger"); 30 chars bound the reach.
                if 0 <= m.start() - ent.end() <= 30:
                    return "negated-activation frame"
            for m in _NEG_ACT_AFTER.finditer(clause):
                # Narrow verb set governs from the right ("never
                # engage the guard"); "does not work, guard
                # present" stays out.
                if 0 <= ent.start() - m.end() <= 15:
                    return "negated-activation frame"
        if _PREVENT.search(clause):
            return "prevention frame"
        if _LACK.search(clause) or _LESS.search(clause):
            return "declarative-lack frame"
    return None


def preservation_frame(text: str) -> bool:
    """True when a clause states safety preservation (keep-active or
    negated deactivation)."""
    for clause in _clauses(text):
        keep = _KEEP.search(clause)
        if keep and _HEALTHY.search(clause[keep.end():]):
            return True
        if _NEG_DEACT.search(clause):
            return True
    return False
