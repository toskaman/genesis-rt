# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Causal hypotheses: deterministic ranking + elimination (no LLM).

The table below is the bounded hypothesis space for this cycle: every
entry names its mechanism, its discriminating faultlab scenario (when
one exists), its native matrix check (when natively supported), and
the falsifier experiment that would refute it. Ranking is pure
signal matching over the incident text with a deterministic
table-order tiebreak. There are no probability percentages: rank and
matched signals are the reported confidence.

Elimination verdicts come from experiment outcomes, never from model
confidence. A faultlab "pass" means the mechanism responded as
designed (verified against the oracle bodies, e.g. _o_cell_estop:
deny+latch+no-motion); it SUPPORTS the hypothesis only when the
incident carries the mechanism's signature markers. A "fail" means
the safety response itself is broken: with matching markers the
testbed contradicts the field observation (INCONCLUSIVE,
investigate), without them the hypothesis is REFUTED. An
un-runnable experiment is NOT_TESTABLE, a missing one INCONCLUSIVE.
"""

from __future__ import annotations

from typing import Any

#: Bounded hypothesis space. ``scenarios`` maps a machine-kind group
#: to a faultlab scenario id; ``native_check`` names an
#: EXPECTED_TARGET_CHECKS matrix step or None when the mechanism has
#: no native injector (stale-sensor/jam are PARTIAL: host oracles
#: exist, native probes do not).
HYPOTHESES: tuple[dict[str, Any], ...] = (
    {
        "id": "H-estop",
        "cause": "emergency-stop interlock propagation",
        "mechanism": "ESTOP input latched by the guard; motion "
                     "denied until operator reset",
        "scenarios": {"cell": "cell_estop_during_transfer",
                      "base": "estop_pressed"},
        "native_check": "estop_target",
        "falsifier": "run the estop scenario: a PASS (no halt) "
                     "refutes propagation",
        "signals": ("estop", "emergency stop", "halt", "interlock",
                    "state=3", "last_reason"),
    },
    {
        "id": "H-crash",
        "cause": "controller/device/guard process crash",
        "mechanism": "supervised process dies; supervisor respawns "
                     "or gives up per policy",
        "scenarios": {"base": "planner_process_crash"},
        "native_check": "controller_crash",
        "falsifier": "run the crash scenario: clean completion "
                     "without respawn refutes a crash",
        "signals": ("crash", "respawn", "died", "segfault",
                    "core dump", "give_up", "restart"),
    },
    {
        "id": "H-stalebin",
        "cause": "staged binary older than the machine contract",
        "mechanism": "on-target binaries do not match the staged "
                     "manifest for the current IR",
        "scenarios": {},
        "native_check": "v2_transitions",
        "falsifier": "staged-vs-manifest check: a match refutes "
                     "staleness",
        "signals": ("stale binary", "outdated", "mismatch",
                    "rebuilt", "not deployed", "old binary"),
    },
    {
        "id": "H-seq",
        "cause": "IPC sequence failure (replay/overdue/drop)",
        "mechanism": "guard rejects replayed or overdue sequence "
                     "numbers; drops break the chain",
        "scenarios": {"base": "dropped_message"},
        "native_check": "faultinject",
        "falsifier": "run the drop scenario: intact delivery "
                     "refutes a sequence break",
        "signals": ("seq", "sequence", "replay", "overdue",
                    "duplicate", "dropped", "gap"),
    },
    {
        "id": "H-jam",
        "cause": "conveyor belt jam",
        "mechanism": "belt mechanics freeze while jammed; transfer "
                     "never completes",
        "scenarios": {"conveyor": "belt_jam",
                      "cell": "cell_transfer_jam",
                      "base": "belt_jam"},
        "native_check": None,
        "falsifier": "run the jam scenario: a completed transfer "
                     "refutes a jam",
        "signals": ("jam", "stuck", "blocked belt", "no transfer"),
    },
    {
        "id": "H-stale-sensor",
        "cause": "stale sensor presence observation",
        "mechanism": "presence reading older than the freshness "
                     "limit gates the transfer",
        "scenarios": {"cell": "cell_stale_presence",
                      "base": "stale_proximity_150ms"},
        "native_check": None,
        "falsifier": "run the stale scenario: fresh readings "
                     "refute staleness",
        "signals": ("stale sensor", "presence", "sensor_age",
                    "150ms", "freshness", "old reading"),
    },
)

_BY_ID = {h["id"]: h for h in HYPOTHESES}

_KIND_GROUPS = {"industrial_cell": "cell", "conveyor": "conveyor"}


def get_hypothesis(hyp_id: str) -> dict[str, Any] | None:
    """Return the table entry, or None for an unknown id."""
    return _BY_ID.get(hyp_id)


def scenario_for(hyp_id: str, machine_kind: str) -> str | None:
    """Resolve the discriminating faultlab scenario (None: no scenario)."""
    hyp = _BY_ID.get(hyp_id)
    if hyp is None:
        return None
    group = _KIND_GROUPS.get(machine_kind, "base")
    scenarios = hyp["scenarios"]
    if group in scenarios:
        return scenarios[group]
    if group == "cell":
        # Cell machines run cell scenarios only: a missing cell entry
        # means the host cannot test this mechanism (no silent base
        # fallback that would crash on kind mismatch).
        return None
    return scenarios.get("base")


def _incident_text(incident: dict[str, Any]) -> str:
    parts = [str(incident.get("title", ""))]
    observed = incident.get("observed", [])
    if isinstance(observed, list):
        for item in observed:
            if isinstance(item, dict):
                parts.append(str(item.get("detail", "")))
    return "\n".join(parts).lower()


def rank_hypotheses(incident: dict[str, Any]) -> list[dict[str, Any]]:
    """Rank every hypothesis by matched signals (table-order tiebreak)."""
    text = _incident_text(incident)
    scored = []
    for index, hyp in enumerate(HYPOTHESES):
        matched = sorted(s for s in hyp["signals"] if s in text)
        scored.append((len(matched), -index, hyp, matched))
    # Higher count first, table order on ties.
    scored.sort(key=lambda t: (-t[0], -t[1]))
    ranked = []
    for rank, (count, _neg, hyp, matched) in enumerate(scored, start=1):
        ranked.append({"id": hyp["id"], "cause": hyp["cause"],
                       "mechanism": hyp["mechanism"],
                       "native_check": hyp["native_check"],
                       "falsifier": hyp["falsifier"],
                       "matched_signals": matched,
                       "signal_hits": count, "rank": rank})
    return ranked


def verdict_for(hyp_id: str,
                outcome: dict[str, Any] | None,
                incident: dict[str, Any] | None = None) -> str:
    """Map an experiment outcome to an elimination verdict.

    ``pass`` means the mechanism responded as designed: it SUPPORTS
    the hypothesis only when the incident carries the mechanism's
    signature markers, else INCONCLUSIVE. ``fail`` means the safety
    response itself is broken: with matching markers the testbed
    contradicts the field observation (INCONCLUSIVE), without them
    the hypothesis is REFUTED. Without incident text no signature
    comparison is possible, so pass/fail both fail closed to
    INCONCLUSIVE.
    """
    hyp = _BY_ID.get(hyp_id)
    if hyp is None:
        return "INCONCLUSIVE"
    status = outcome.get("status") if isinstance(outcome, dict) else None
    if status == "unsupported":
        return "NOT_TESTABLE"
    if status not in ("pass", "fail"):
        return "INCONCLUSIVE"
    if incident is None:
        return "INCONCLUSIVE"
    text = _incident_text(incident)
    matched = any(s in text for s in hyp["signals"])
    if status == "pass":
        return "SUPPORTED" if matched else "INCONCLUSIVE"
    return "INCONCLUSIVE" if matched else "REFUTED"
