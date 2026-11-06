# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §12: IPC timeline parser unit tests (synthetic traces)."""
from __future__ import annotations

from genesis_rt import ipc_timeline as tl

FULL = """\
guard: attached as 'genesis_guard' chid=3
TRACE SEND seq=1 t=1000000000
TRACE RECV seq=1 t=1000005000
TRACE REPLY seq=1 t=1000009000 decision=ALLOW
TRACE DONE seq=1 t=1000012000
SAMPLE 12.000
TRACE SEND seq=2 t=1000020000
TRACE RECV seq=2 t=1000024000
TRACE REPLY seq=2 t=1000027000 decision=DENY
TRACE DONE seq=2 t=1000030000
PERF_DONE n=2
"""


def test_parse_full_trace_joins_by_seq():
    parsed = tl.parse_trace(FULL)
    assert parsed["errors"] == []
    assert sorted(parsed["trips"]) == [1, 2]
    one = parsed["trips"][1]
    assert one == {"send": 1000000000, "recv": 1000005000,
                   "reply": 1000009000, "done": 1000012000,
                   "decision": "ALLOW"}
    assert parsed["trips"][2]["decision"] == "DENY"


def test_parse_ignores_non_trace_chatter():
    parsed = tl.parse_trace(FULL)
    assert parsed["lines"] == 11  # every non-blank line counted
    assert parsed["errors"] == []  # SAMPLE/PERF/guard lines skipped


def test_parse_missing_events_stay_unknown():
    parsed = tl.parse_trace("TRACE SEND seq=7 t=5000\n"
                            "TRACE DONE seq=7 t=9000\n")
    trip = parsed["trips"][7]
    assert trip["recv"] is None and trip["reply"] is None
    assert trip["decision"] is None
    assert parsed["errors"] == []


def test_parse_malformed_lines_are_errors_not_crashes():
    parsed = tl.parse_trace("TRACE SEND seq=1 t=100\n"
                            "TRACE SEND seq=x t=100\n"
                            "TRACE FROB seq=1 t=200\n"
                            "TRACE RECV seq=1 t=-5\n")
    assert len(parsed["errors"]) == 3
    assert parsed["trips"][1]["send"] == 100


def test_parse_duplicate_seq_is_an_error():
    parsed = tl.parse_trace("TRACE SEND seq=1 t=100\n"
                            "TRACE SEND seq=1 t=200\n")
    assert parsed["trips"][1]["send"] == 100  # first wins
    assert any("duplicate SEND" in e for e in parsed["errors"])


def test_parse_clock_regression_is_an_error():
    parsed = tl.parse_trace("TRACE SEND seq=1 t=9000\n"
                            "TRACE DONE seq=1 t=1000\n")
    assert any("precedes" in e for e in parsed["errors"])


def test_to_json_stringifies_seq_keys():
    out = tl.to_json(tl.parse_trace(FULL))
    assert out["trips"]["1"]["decision"] == "ALLOW"
    assert out["lines"] == 11


def test_render_ascii_waterfall():
    text = tl.render_ascii(tl.parse_trace(FULL))
    assert "QNX IPC timeline" in text
    assert "ALLOW" in text and "DENY" in text
    # guard span of trip 1: (1000009000-1000005000)/1000 = 4.000 us
    assert "4.000" in text
    # round trip of trip 1: 12.000 us, matching the SAMPLE line
    assert "12.000" in text


def test_render_ascii_marks_unknown():
    text = tl.render_ascii(tl.parse_trace("TRACE SEND seq=7 t=5000\n"
                                          "TRACE DONE seq=7 t=9000\n"))
    assert "?" in text
    assert "4.000" in text  # round trip still computable


def test_render_ascii_empty_and_no_send():
    assert "no traced trips" in tl.render_ascii(tl.parse_trace(""))
    assert "no SEND events" in tl.render_ascii(
        tl.parse_trace("TRACE RECV seq=1 t=5\n"))
