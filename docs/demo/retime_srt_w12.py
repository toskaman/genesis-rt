"""Wave 12: re-time SRT cues to the rendered voiceover blocks.

Method (documented, deterministic): each narration cue maps to one
voice block with measured start/end (VOICEOVER_W12.json). Cue
boundaries are placed by word fraction within the block span, with
pause weights (sentence-final words count 1.6x for the TTS pause).
Cue text is unchanged (QEMU spelling kept for readers).

Usage: python docs/demo/retime_srt_w12.py  (from repo root)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# cue index (1-based in w11 srt) -> voice block index; None = keep as-is.
CUE_BLOCK = {1: None, 2: 0, 3: 0, 4: 1, 5: 1, 6: 2, 7: 2, 8: 3, 9: 3,
             10: 4, 11: 4, 12: 5, 13: 5, 14: 6, 15: 6, 16: 7,
             17: 8, 18: 8, 19: 8, 20: 9, 21: None}

# Verbatim text patches (w11 srt dropped 4 spoken words covered by the
# title card; w12 restores them so captions match the voice track).
TEXT_PATCHES = {
    2: ["Embedded software must behave correctly",
        "even when real systems fail. This is Genesis RT:"],
}


def norm(w: str) -> str:
    w = w.lower().strip(".,:;!?\"'()")
    return {"q-emu": "qemu"}.get(w, w)


def parse_srt(text: str):
    cues = []
    for chunk in text.strip().split("\n\n"):
        lines = chunk.splitlines()
        idx = int(lines[0])
        start, end = lines[1].split(" --> ")
        cues.append((idx, start, end, lines[2:]))
    return cues


def srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    demo = Path("docs/demo")
    script_blocks: list[list[str]] = []
    words: list[str] = []
    for raw in (demo / "voiceover-w12.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            if words:
                script_blocks.append(words)
            words = []
        elif line and not line.startswith("#"):
            words.extend(line.split())
    if words:
        script_blocks.append(words)

    rep = json.loads((demo / "VOICEOVER_W12.json").read_text(encoding="utf-8"))
    cues = parse_srt((demo / "subtitles-w11.srt").read_text(encoding="utf-8"))
    cues = [(idx, s, e, TEXT_PATCHES.get(idx, lines))
            for idx, s, e, lines in cues]

    # Verify cue text matches script words per block (normalised).
    by_block: dict[int, list] = {}
    for cue in cues:
        b = CUE_BLOCK[cue[0]]
        if b is not None:
            by_block.setdefault(b, []).append(cue)
    for b, blist in by_block.items():
        cue_words = [norm(w) for cue in blist for ln in cue[3]
                     for w in ln.replace("--", " ").split()]
        script_words = [norm(w) for w in script_blocks[b]]
        assert cue_words == script_words, f"block {b} text mismatch:\n{cue_words}\n{script_words}"

    out = []
    for idx, start, end, lines in cues:
        b = CUE_BLOCK[idx]
        if b is None:
            out.append((idx, start, end, lines))
            continue
        blist = by_block[b]
        # Weight: 1.0 per word + 0.6 pause after sentence-final words.
        weights: list[float] = []
        for _, _, _, clines in blist:
            ws = [w for ln in clines for w in ln.replace("--", " ").split()]
            for i, w in enumerate(ws):
                last = (i == len(ws) - 1)
                weights.append(1.6 if (last and w[-1] in ".:") else 1.0)
        total = sum(weights)
        # This cue's word span -> time span within the block.
        before = sum(len([w for ln in c[3]
                          for w in ln.replace("--", " ").split()])
                     for c in blist[:blist.index((idx, start, end, lines))])
        n = len([w for ln in lines for w in ln.replace("--", " ").split()])
        w0 = sum(weights[:before])
        w1 = sum(weights[:before + n])
        span = rep["blocks"][b]
        t0 = span["start"] + (span["end"] - span["start"]) * w0 / total
        t1 = span["start"] + (span["end"] - span["start"]) * w1 / total
        # Pad only outward at block edges (never into a neighbour cue).
        pos = blist.index((idx, start, end, lines))
        if pos == 0:
            t0 = max(span["start"], t0 - 0.15)
        if pos == len(blist) - 1:
            t1 = min(span["end"] + 0.4, t1 + 0.15)
        out.append((idx, srt_time(t0), srt_time(t1), lines))

    with (demo / "subtitles-w12.srt").open("w", encoding="utf-8") as fh:
        for idx, start, end, lines in out:
            fh.write(f"{idx}\n{start} --> {end}\n" + "\n".join(lines) + "\n\n")
    print("wrote subtitles-w12.srt, cues:", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
