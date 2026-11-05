# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 7 M3 (§10): Digital Twin 2.0 replay-track model.

Folds one scenario trace (full or slim head/tail) into a normalized
replay track: frames + timeline markers under an explicit stepwise
interpolation policy. The browser mirrors this contract in
``twinFold`` (``ui/studio.html``); node tests cross-check both folds
on real fault-lab traces.

Honesty rules:
- Frames only restate recorded ticks. Between two recorded ticks the
  twin holds the earlier frame (``stepwise-hold``); it never invents
  intermediate motion, and truncated gaps are flagged, not bridged.
- The track carries the *run* source. Scenario ticks are host
  simulation unless the producing run genuinely recorded target
  ticks; a QNX-bound passport still replays host ticks, labelled
  as such (see :func:`describe_source`).
"""
from __future__ import annotations

from typing import Any

TRACK_VERSION = 1
INTERP_POLICY = "stepwise-hold"
INTERP_LABEL = ("stepwise hold: each frame shows the last recorded tick; "
                "nothing is interpolated and gaps are never bridged")

SOURCE_HOST_SIM = "host-sim"
SOURCE_QNX_TARGET = "qnx-target"
KNOWN_SOURCES = (SOURCE_HOST_SIM, SOURCE_QNX_TARGET)

MAX_FRAMES = 20000
MAX_INPUT_EVENTS = 100000

KINDS = ("diff", "belt", "cell")


class TwinInputError(ValueError):
    """Malformed trace, scenario or passport for the twin."""


class TwinTooLarge(ValueError):
    """Input exceeds the twin's hard replay budget."""


class TwinChainError(ValueError):
    """Passport hash chain does not verify: no replay on it."""


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def detect_kind(ticks: list[dict[str, Any]]) -> str:
    """Detect the track kind from tick fields (cell > belt > diff)."""
    for tick in ticks:
        if not isinstance(tick, dict):
            continue
        if "cell_phase" in tick:
            return "cell"
    for tick in ticks:
        if isinstance(tick, dict) and "position" in tick:
            return "belt"
    return "diff"


def _split_trace(trace: Any) -> tuple[list[Any], list[Any], bool, Any, Any]:
    """Return (head, tail, truncated, event_count, digest) for a trace."""
    if isinstance(trace, list):
        return trace, [], False, len(trace), None
    if not isinstance(trace, dict):
        raise TwinInputError("trace must be a list or a slim-trace object")
    if isinstance(trace.get("events"), list):
        events = trace["events"]
        return events, [], False, len(events), trace.get("digest")
    if "events_head" not in trace and "events_tail" not in trace:
        raise TwinInputError("trace object carries no events")
    head = trace.get("events_head", [])
    tail = trace.get("events_tail", [])
    if not isinstance(head, list) or not isinstance(tail, list):
        raise TwinInputError("slim trace needs events_head/events_tail lists")
    return (head, tail, bool(trace.get("truncated", True)),
            trace.get("event_count"), trace.get("digest"))


def _motion_of(kind: str, tick: dict[str, Any]) -> dict[str, Any]:
    if kind == "cell":
        motion: dict[str, Any] = {
            "cell_phase": tick.get("cell_phase"),
            "presence": tick.get("presence"),
            "presence_fresh": tick.get("presence_fresh"),
            "transfers": tick.get("transfers"),
            "transfer_ticks": tick.get("transfer_ticks"),
            "inhibited": tick.get("inhibited"),
            "amr_x": tick.get("amr_x"),
            "belt_pos": tick.get("belt_pos"),
            "belt_jammed": tick.get("belt_jammed"),
        }
    elif kind == "belt":
        motion = {"position": tick.get("position"),
                  "speed": tick.get("speed"),
                  "jammed": tick.get("jammed")}
    else:
        motion = {"x": tick.get("x"), "y": tick.get("y"),
                  "theta": tick.get("theta")}
    return motion


def _marker(frames: list[dict[str, Any]], idx: int, label: str,
            severity: str) -> dict[str, Any]:
    return {"i": idx, "t_ms": frames[idx]["t_ms"], "label": label,
            "severity": severity}


def fold_trace(trace: Any, *, source: str = SOURCE_HOST_SIM) -> dict[str, Any]:
    """Fold a scenario trace into a replay track.

    ``trace`` is either a raw event list or a slim passport trace
    (``events`` or ``events_head``/``events_tail`` + ``truncated``).
    Raises :class:`TwinInputError` / :class:`TwinTooLarge`.
    """
    if source not in KNOWN_SOURCES:
        raise TwinInputError(f"unknown track source: {source!r}")
    head, tail, truncated, event_count, digest = _split_trace(trace)
    events = head + tail
    if len(events) > MAX_INPUT_EVENTS:
        raise TwinTooLarge(
            f"trace holds {len(events)} events (budget {MAX_INPUT_EVENTS})")
    ticks = [e for e in head if isinstance(e, dict) and e.get("kind") == "tick"]
    head_ticks = len(ticks)
    ticks += [e for e in tail if isinstance(e, dict) and e.get("kind") == "tick"]
    if len(ticks) > MAX_FRAMES:
        raise TwinTooLarge(
            f"trace holds {len(ticks)} ticks (budget {MAX_FRAMES})")
    for tick in ticks:
        if not _is_num(tick.get("t")):
            raise TwinInputError("tick without numeric t_ms")
    kind = detect_kind(ticks)
    side: dict[int, list[str]] = {}
    for event in events:
        if (isinstance(event, dict) and event.get("kind") != "tick"
                and _is_num(event.get("t"))):
            side.setdefault(int(event["t"]), []).append(
                str(event.get("kind")))
    frames: list[dict[str, Any]] = []
    for idx, tick in enumerate(ticks):
        frame: dict[str, Any] = {
            "i": idx,
            "t_ms": tick["t"],
            "fault": tick.get("fault", "none"),
            "decision": tick.get("decision"),
            "reason": tick.get("reason"),
            "guard_state": tick.get("guard_state", tick.get("state")),
            "gap_after": bool(truncated and idx + 1 == head_ticks
                              and idx + 1 < len(ticks)),
            "motion": _motion_of(kind, tick),
            "events": sorted(set(side.get(int(tick["t"]), []))),
        }
        if kind == "cell":
            frame["leg"] = tick.get("leg")
        frames.append(frame)
    track = {
        "version": TRACK_VERSION,
        "kind": kind,
        "source": source,
        "interp": INTERP_POLICY,
        "interp_label": INTERP_LABEL,
        "truncated": truncated,
        "gap_at": head_ticks if truncated else None,
        "event_count": event_count,
        "digest": digest,
        "frames": frames,
        "markers": _markers(kind, frames, truncated, head_ticks),
    }
    return track


def _markers(kind: str, frames: list[dict[str, Any]],
             truncated: bool, head_ticks: int) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    if truncated and 0 < head_ticks < len(frames):
        markers.append({"i": head_ticks, "t_ms": frames[head_ticks]["t_ms"],
                        "label": "trace gap: head+tail only, never bridged",
                        "severity": "warn"})
    prev = "{init}"
    for idx, frame in enumerate(frames):
        fault = frame.get("fault", "none")
        if fault != prev:
            if fault not in (None, "none"):
                markers.append(_marker(
                    frames, idx, f"fault {fault} started", "warn"))
            elif prev not in ("{init}", None, "none"):
                markers.append(_marker(frames, idx, "fault cleared", "info"))
            prev = fault
        if idx == 0:
            continue
        before = frames[idx - 1]
        if (frame.get("decision") not in (None, "ALLOW")
                and before.get("decision") in (None, "ALLOW")):
            markers.append(_marker(
                frames, idx,
                f"guard {frame['decision']}: {frame.get('reason')}", "fail"))
        if frame.get("guard_state") != before.get("guard_state"):
            markers.append(_marker(
                frames, idx,
                f"guard state -> {frame.get('guard_state')}", "warn"))
        if (kind == "cell" and frame["motion"].get("cell_phase")
                != before["motion"].get("cell_phase")):
            markers.append(_marker(
                frames, idx,
                f"phase -> {frame['motion'].get('cell_phase')}", "info"))
    for idx, frame in enumerate(frames):
        for name in frame["events"]:
            if name == "supervisor_reset_armed":
                markers.append(_marker(frames, idx, "supervisor re-arm",
                                       "info"))
            elif name == "planner_gap":
                markers.append(_marker(frames, idx, "planner gap (no "
                                       "controller command)", "warn"))
    markers.sort(key=lambda m: (m["i"], m["label"]))
    return markers


def frame_at(track: dict[str, Any], t_ms: float) -> int:
    """Stepwise lookup: index of the last frame at or before ``t_ms``.

    Clamped to the track ends (before the first tick the twin shows
    frame 0 with its recorded values; it never extrapolates back).
    """
    frames = track.get("frames", [])
    if not frames:
        raise TwinInputError("track holds no frames")
    if t_ms < frames[0]["t_ms"]:
        return 0
    lo = 0
    for idx, frame in enumerate(frames):
        if frame["t_ms"] <= t_ms:
            lo = idx
        else:
            break
    return lo


def check_fidelity(track: dict[str, Any], trace: Any) -> list[str]:
    """Compare a folded track against its source trace.

    Returns a list of defect strings (empty = faithful). The passport
    hash chain — not this check — guards integrity; this guards the
    fold itself (order, count, gap position, marker range).
    """
    errors: list[str] = []
    try:
        head, tail, truncated, _count, _digest = _split_trace(trace)
    except TwinInputError as exc:
        return [f"unreadable trace: {exc}"]
    ticks = [e for e in head + tail
             if isinstance(e, dict) and e.get("kind") == "tick"]
    frames = track.get("frames", [])
    if len(frames) != len(ticks):
        errors.append(f"frame count {len(frames)} != tick count {len(ticks)}")
    for idx, (frame, tick) in enumerate(zip(frames, ticks)):
        if frame.get("t_ms") != tick.get("t"):
            errors.append(f"frame {idx} t_ms {frame.get('t_ms')} != "
                          f"tick t {tick.get('t')}")
            break
        if frame.get("decision") != tick.get("decision"):
            errors.append(f"frame {idx} decision restates tick wrongly")
            break
    times = [f.get("t_ms") for f in frames]
    if any(not _is_num(t) for t in times):
        errors.append("non-numeric frame time")
    elif any(b < a for a, b in zip(times, times[1:])):
        errors.append("frame times not monotonic")
    if bool(track.get("truncated")) != bool(truncated):
        errors.append("truncated flag disagrees with trace")
    head_ticks = len([e for e in head
                      if isinstance(e, dict) and e.get("kind") == "tick"])
    if truncated and track.get("gap_at") != head_ticks:
        errors.append(f"gap_at {track.get('gap_at')} != head ticks "
                      f"{head_ticks}")
    for marker in track.get("markers", []):
        i = marker.get("i")
        if not isinstance(i, int) or not 0 <= i < len(frames):
            errors.append(f"marker {marker.get('label')!r} out of range")
        elif marker.get("t_ms") != frames[i].get("t_ms"):
            errors.append(f"marker {marker.get('label')!r} time mismatch")
    if track.get("interp") != INTERP_POLICY:
        errors.append("track interpolation policy is not stepwise-hold")
    return errors


def verify_track(track: Any) -> list[str]:
    """Validate a serialized track's shape (API round-trip guard)."""
    if not isinstance(track, dict):
        return ["track must be an object"]
    errors: list[str] = []
    if track.get("version") != TRACK_VERSION:
        errors.append(f"unsupported track version {track.get('version')!r}")
    if track.get("kind") not in KINDS:
        errors.append(f"unknown kind {track.get('kind')!r}")
    if track.get("source") not in KNOWN_SOURCES:
        errors.append(f"unknown source {track.get('source')!r}")
    if track.get("interp") != INTERP_POLICY:
        errors.append("track interpolation policy is not stepwise-hold")
    frames = track.get("frames")
    if not isinstance(frames, list) or len(frames) > MAX_FRAMES:
        errors.append("frames must be a bounded list")
        return errors
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            errors.append(f"frame {idx} is not an object")
            break
        if frame.get("i") != idx or not _is_num(frame.get("t_ms")):
            errors.append(f"frame {idx} index/time broken")
            break
        if not isinstance(frame.get("motion"), dict):
            errors.append(f"frame {idx} motion missing")
            break
    markers = track.get("markers", [])
    if not isinstance(markers, list):
        errors.append("markers must be a list")
    else:
        for marker in markers:
            if not isinstance(marker, dict):
                errors.append("marker is not an object")
                break
            i = marker.get("i")
            if not isinstance(i, int) or not 0 <= i < len(frames):
                errors.append("marker index out of range")
                break
    return errors


def describe_source(passport: dict[str, Any]) -> dict[str, Any]:
    """Label a passport's run source for the twin banner.

    Scenario ticks are host simulation. A passport whose gate verdict
    carries ``qnx_verified: true`` additionally binds native target
    evidence — but the replayed ticks stay host ticks, and the label
    says so. Never claims target ticks without target tick records.
    """
    verdict_body: dict[str, Any] = {}
    for record in passport.get("chain", []):
        if isinstance(record, dict) and record.get("kind") == "gate_verdict":
            body = record.get("body")
            if isinstance(body, dict):
                verdict_body = body
    qnx_verified = verdict_body.get("qnx_verified") is True
    if qnx_verified:
        note = ("QNX-bound run: native target checks passed, but the "
                "replayed ticks are host-simulation records")
        run_source = "qnx-bound"
    else:
        note = "host-only run: replay shows host-simulation ticks"
        run_source = "host-only"
    return {"run_source": run_source, "qnx_verified": qnx_verified,
            "track_source": SOURCE_HOST_SIM, "note": note}


def track_from_passport(passport: dict[str, Any],
                        scenario: str) -> dict[str, Any]:
    """Fold one passport scenario into a replay track.

    The passport hash chain must verify first (Studio and the CLI
    refuse unverified replay). Raises :class:`TwinChainError` /
    :class:`TwinInputError` / :class:`TwinTooLarge`.
    """
    from .evidence import verify_chain

    if not isinstance(passport, dict) or not isinstance(scenario, str):
        raise TwinInputError("passport must be an object and scenario a name")
    errors = verify_chain(passport)
    if errors:
        raise TwinChainError(errors[0])
    want = f"scenario:{scenario}"
    for record in passport.get("chain", []):
        if isinstance(record, dict) and record.get("kind") == want:
            body = record.get("body")
            if not isinstance(body, dict) or "trace" not in body:
                raise TwinInputError(
                    f"scenario record {scenario!r} carries no trace")
            track = fold_trace(body["trace"])
            track["scenario"] = scenario
            track["seed"] = body.get("seed")
            track["status"] = body.get("status")
            track["checks"] = body.get("checks", [])
            track["stats"] = body.get("stats", {})
            track["run"] = describe_source(passport)
            track["run_id"] = passport.get("run_id")
            return track
    names = sorted(str(r.get("kind", ""))[len("scenario:"):]
                   for r in passport.get("chain", [])
                   if isinstance(r, dict)
                   and str(r.get("kind", "")).startswith("scenario:"))
    raise TwinInputError(f"unknown scenario {scenario!r} "
                         f"(passport holds: {', '.join(names) or 'none'})")


def render_track_text(track: dict[str, Any]) -> str:
    """One-screen text summary of a replay track."""
    lines = [f"scenario: {track.get('scenario', '?')} "
             f"kind={track.get('kind')} source={track.get('source')} "
             f"frames={len(track.get('frames', []))} "
             f"markers={len(track.get('markers', []))}",
             f"interp: {track.get('interp_label', INTERP_LABEL)}"]
    run = track.get("run") or {}
    if run:
        lines.append(f"run: {track.get('run_id')} "
                     f"({run.get('run_source')}, "
                     f"qnx_verified={run.get('qnx_verified')})")
    if track.get("truncated"):
        lines.append(f"truncated: gap at frame {track.get('gap_at')} "
                     "(head+tail only)")
    for marker in track.get("markers", [])[:20]:
        lines.append(f"  @{marker['t_ms']}ms [{marker['severity']}] "
                     f"{marker['label']}")
    if len(track.get("markers", [])) > 20:
        lines.append(f"  ... +{len(track['markers']) - 20} more")
    return "\n".join(lines) + "\n"
