# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""QNX IPC execution timeline (Wave 11 §12).

Parses the env-gated native trace (``GENESIS_IPC_TRACE=1``) emitted by
``genesis_guard`` (RECV/REPLY) and ``genesis_faultinject bench``
(SEND/DONE). All four stamps come from the target's CLOCK_MONOTONIC,
so they join by sequence number into one round-trip waterfall per
probe: client request → guard receive → policy decision → reply.

Anything missing or malformed is reported as unknown/an error, never
synthesized. Timestamps from different boots are NOT comparable: feed
the parser a single run (one guard log + one bench invocation).
"""
from __future__ import annotations

import re
from typing import Any

TRACE_RE = re.compile(
    r"^TRACE (SEND|RECV|REPLY|DONE) seq=(\d+) t=(\d+)"
    r"(?: decision=(ALLOW|DENY))?\s*$")

KINDS = ("SEND", "RECV", "REPLY", "DONE")


def parse_trace(text: str) -> dict[str, Any]:
    """Parse combined guard + bench trace output.

    Returns {"trips": {seq: {send, recv, reply, done, decision}},
    "errors": [...], "lines": N}. Stamps are integer nanoseconds or
    None when that event was never recorded. First occurrence wins per
    (seq, kind); later duplicates are errors (seq restarts at 1 on
    each bench invocation, so multi-run logs need splitting first).
    """
    trips: dict[int, dict[str, Any]] = {}
    errors: list[str] = []
    n_lines = 0

    def _trip(seq: int) -> dict[str, Any]:
        return trips.setdefault(
            seq, {"send": None, "recv": None, "reply": None,
                  "done": None, "decision": None})

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        n_lines += 1
        if not line.startswith("TRACE "):
            continue  # bench SAMPLE/PERF_DONE/guard chatter: not trace
        match = TRACE_RE.match(line)
        if match is None:
            errors.append(f"malformed TRACE line: {line[:120]}")
            continue
        kind, seq_s, t_s, decision = match.groups()
        seq, stamp = int(seq_s), int(t_s)
        trip = _trip(seq)
        slot = kind.lower()
        if trip[slot] is not None:
            errors.append(f"duplicate {kind} for seq={seq} "
                          "(multi-run log? split it first)")
            continue
        trip[slot] = stamp
        if kind == "REPLY":
            trip["decision"] = decision or "unknown"
    for seq in sorted(trips):
        trip = trips[seq]
        stamps = [(k, trip[k]) for k in ("send", "recv", "reply", "done")
                  if trip[k] is not None]
        for (k1, t1), (k2, t2) in zip(stamps, stamps[1:]):
            if t2 < t1:
                errors.append(f"seq={seq}: {k2} ({t2}) precedes "
                              f"{k1} ({t1}): clocks not comparable")
    return {"trips": trips, "errors": errors, "lines": n_lines}


def to_json(timeline: dict[str, Any]) -> dict[str, Any]:
    """JSON-serializable form (int seq keys become strings)."""
    return {"trips": {str(seq): trip
                      for seq, trip in sorted(timeline["trips"].items())},
            "errors": list(timeline["errors"]),
            "lines": timeline["lines"]}


def render_ascii(timeline: dict[str, Any]) -> str:
    """Fixed-width waterfall in microseconds from the first SEND.

    Unknown events render as "?"; the guard-decision span
    (RECV→REPLY) and the full round trip (SEND→DONE) are shown per
    probe. Pure function of the parsed timeline.
    """
    trips = timeline["trips"]
    if not trips:
        return "no traced trips (empty log or no GENESIS_IPC_TRACE=1 run)"
    sends = [t["send"] for t in trips.values() if t["send"] is not None]
    if not sends:
        return "no SEND events: client trace missing (unknown clock origin)"
    t0 = min(sends)

    def _us(ns: int | None) -> str:
        return f"{(ns - t0) / 1000.0:9.3f}" if ns is not None else "        ?"

    def _span(a: int | None, b: int | None) -> str:
        return f"{(b - a) / 1000.0:8.3f}" if a is not None and b is not None \
            else "       ?"

    lines = ["QNX IPC timeline (us from first SEND; ? = not recorded)",
             "seq |    SEND |    RECV |   REPLY |    DONE |"
             " guard us | round us | decision",
             "----+--------+---------+---------+--------+"
             "----------+----------+----------"]
    for seq in sorted(trips):
        trip = trips[seq]
        lines.append(
            f"{seq:3d} |{_us(trip['send'])} |{_us(trip['recv'])} |"
            f"{_us(trip['reply'])} |{_us(trip['done'])} |"
            f"{_span(trip['recv'], trip['reply'])} |"
            f"{_span(trip['send'], trip['done'])} | "
            f"{trip['decision'] or '?'}")
    if timeline["errors"]:
        lines.append(f"({len(timeline['errors'])} parse/order errors; "
                     "see JSON)")
    return "\n".join(lines) + "\n"
