"""Wave 12 deterministic voiceover renderer.

Renders the TTS script (docs/demo/voiceover-w12.txt) with Piper
(en_US-lessac-medium) and mixes one voice track aligned to the
154.6 s Wave 11 video timeline.

Deterministic: fixed model, fixed config, fixed start times, pure-Python
mix at the voice sample rate. No randomness, no network.

Usage:
    python docs/demo/voiceover_w12.py --voice-dir C:\\tmp\\piper-voices \\
        --video docs/demo/genesis-rt-demo-w11.mp4 \\
        --script docs/demo/voiceover-w12.txt \\
        --out docs/demo/voiceover-w12.wav --report docs/demo/VOICEOVER_W12.json
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import wave
from pathlib import Path


def parse_script(path: Path) -> list[tuple[float, str]]:
    blocks: list[tuple[float, str]] = []
    start: float | None = None
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            if start is not None:
                blocks.append((start, " ".join(lines)))
            start = float(line[3:].strip())
            lines = []
        elif line.startswith("#"):
            continue
        else:
            lines.append(line)
    if start is not None:
        blocks.append((start, " ".join(lines)))
    return blocks


def video_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--voice-dir", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    from piper import PiperVoice

    voice_dir = Path(args.voice_dir)
    model = next(voice_dir.glob("en_US-lessac-medium.onnx"))
    voice = PiperVoice.load(str(model))

    blocks = parse_script(Path(args.script))
    total_dur = video_duration(Path(args.video))
    sr = voice.config.sample_rate
    n_total = int(total_dur * sr)
    mix = bytearray(n_total * 2)  # 16-bit mono
    report_blocks = []
    prev_end = 0.0
    overruns: list[str] = []

    for i, (start, text) in enumerate(blocks):
        chunks: list[bytes] = []
        for chunk in voice.synthesize(text):
            chunks.append(chunk.audio_int16_bytes)
        pcm = b"".join(chunks)
        dur = len(pcm) / 2 / sr
        end = start + dur
        off = int(start * sr) * 2
        if off + len(pcm) > len(mix):
            overruns.append(f"block{i} exceeds video end")
            pcm = pcm[: len(mix) - off]
        mix[off: off + len(pcm)] = pcm
        gap_prev = start - prev_end
        nxt = blocks[i + 1][0] if i + 1 < len(blocks) else total_dur
        bleed = max(0.0, end - nxt)
        if bleed > 0.01:
            overruns.append(f"block{i} bleeds {bleed:.2f}s into next slot")
        report_blocks.append({
            "index": i, "start": round(start, 2),
            "duration": round(dur, 2), "end": round(end, 2),
            "gap_after_prev": round(gap_prev, 2),
            "bleed_into_next": round(bleed, 2),
            "words": len(text.split()),
        })
        prev_end = end

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(mix))

    # Peak level check (no clipping possible in 16-bit mix, report headroom).
    peak = max(struct.unpack(f"<{n_total}h", bytes(mix)), key=abs)
    report = {
        "video": args.video,
        "video_duration_s": round(total_dur, 3),
        "sample_rate": sr,
        "voice": "en_US-lessac-medium",
        "blocks": report_blocks,
        "total_words": sum(b["words"] for b in report_blocks),
        "peak_abs": peak,
        "overruns": overruns,
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("OVERRUNS:", overruns if overruns else "none", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
