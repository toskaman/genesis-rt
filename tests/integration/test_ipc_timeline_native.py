# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §12: the committed native trace parses cleanly.

Guards the evidence/ipc-timeline sample (real QNX 8.0 monotonic
stamps, captured 2026-11-06): 5 complete trips, no parse/order
errors, sane spans, SAMPLE deltas matching parser round trips.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from genesis_rt import ipc_timeline as tl

EVIDENCE = (Path(__file__).resolve().parent.parent.parent / "evidence" /
            "ipc-timeline")


def _sample() -> str:
    return (EVIDENCE / "bench-stdout.log").read_text(encoding="utf-8")


def test_native_sample_parses_with_no_errors():
    parsed = tl.parse_trace(_sample())
    assert parsed["errors"] == []
    assert sorted(parsed["trips"]) == [1, 2, 3, 4, 5]


def test_native_sample_trips_complete_and_allow():
    parsed = tl.parse_trace(_sample())
    for seq, trip in parsed["trips"].items():
        assert trip["send"] is not None, seq
        assert trip["recv"] is not None, seq
        assert trip["reply"] is not None, seq
        assert trip["done"] is not None, seq
        assert trip["send"] <= trip["recv"] <= trip["reply"] \
            <= trip["done"], seq
        assert trip["decision"] == "ALLOW", seq


def test_native_sample_spans_positive_and_sane():
    parsed = tl.parse_trace(_sample())
    for seq, trip in parsed["trips"].items():
        guard_us = (trip["reply"] - trip["recv"]) / 1000.0
        round_us = (trip["done"] - trip["send"]) / 1000.0
        assert 0 < guard_us < round_us, seq
        assert round_us < 60_000_000, seq  # under a minute, sanity only


def test_native_sample_matches_bench_deltas():
    """Independent check: bench SAMPLE deltas equal DONE-SEND."""
    text = _sample()
    samples = [float(v) for v in re.findall(r"^SAMPLE ([\d.]+)",
                                             text, re.M)]
    parsed = tl.parse_trace(text)
    assert len(samples) == 5
    for seq, sample in zip(sorted(parsed["trips"]), samples):
        trip = parsed["trips"][seq]
        computed = (trip["done"] - trip["send"]) / 1000.0
        assert abs(computed - sample) < 0.001, seq


def test_native_sample_matches_committed_timeline():
    committed = json.loads(
        (EVIDENCE / "timeline.json").read_text(encoding="utf-8"))
    assert committed == tl.to_json(tl.parse_trace(_sample()))
    ascii_art = (EVIDENCE / "timeline.txt").read_text(encoding="utf-8")
    assert ascii_art == tl.render_ascii(tl.parse_trace(_sample()))


def test_native_sample_meta_binds_binaries():
    meta = json.loads(
        (EVIDENCE / "run-meta.json").read_text(encoding="utf-8"))
    assert set(meta["binaries"]) == {"genesis_guard",
                                     "genesis_faultinject"}
    for digest in meta["binaries"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert meta["trips"] == 5 and meta["errors"] == []
