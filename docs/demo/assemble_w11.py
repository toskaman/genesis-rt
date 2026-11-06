# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 demo assembly: deterministic final MP4 from captured scenes.

Inputs: docs/demo/footage-w11/s*.webm (capture_w11.py) + terminal
proof cards rendered here from VERBATIM command outputs (long lines
wrapped for legibility; bytes unchanged -- see SHOT_EVIDENCE.md).

Usage (from repo root):
  python docs/demo/assemble_w11.py --footage docs/demo/footage-w11 \
      --out docs/demo/genesis-rt-demo-w11.mp4

Output: H.264 + yuv420p (YouTube-compatible), silent (voice is an
owner handoff; docs/demo/subtitles-w11.srt carries the narration).
Prints the segment timeline for subtitle authoring.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

FONT_MONO = "'C\\:/Windows/Fonts/consola.ttf'"
FONT_SANS = "'C\\:/Windows/Fonts/arial.ttf'"
BG = "0x0b0e14"

CARD_BEFORE = """$ python evidence/qnx8-x86_64-w11-before/verify.py evidence/qnx8-x86_64-w11-before
pack: qnx8-x86_64-w11-before  op: op-d08d3d3ea346  commit: a465e7f
files: 34/34 digests OK
passport chain: 15 links via repo genesis_rt.evidence.verify_chain
binding: passport.run_id == op-d08d3d3ea346 OK
binding: IR digest 356dc135f27f4586... OK
anchor: passport sha256 2cf6bd6e6e3997cd... OK
observed: op=COMPLETED gate=PASS matrix=16/16 samples=1000
  qnx_verified=True
VERIFY OK: integrity + bindings hold; compare observed claims
  with EXPECTED_RESULTS.md"""

CARD_AFTER = """$ python evidence/qnx8-x86_64-w11-after/verify.py evidence/qnx8-x86_64-w11-after
pack: qnx8-x86_64-w11-after  op: op-67a4595a858f  commit: a465e7f
files: 34/34 digests OK
passport chain: 15 links via repo genesis_rt.evidence.verify_chain
binding: passport.run_id == op-67a4595a858f OK
binding: IR digest fb2dbb3de8a19546... OK
anchor: passport sha256 3c6401934e9efb72... OK
observed: op=COMPLETED gate=PASS matrix=16/16 samples=1000
  qnx_verified=True
VERIFY OK: integrity + bindings hold; compare observed claims
  with EXPECTED_RESULTS.md"""

CARD_TAMPER = """$ cp -r evidence/qnx8-x86_64-w11-before /tmp/tamperdemo/pack
# 1 byte flipped in transcripts/target-faultinject.log (python)
$ python /tmp/tamperdemo/pack/verify.py /tmp/tamperdemo/pack
pack: qnx8-x86_64-w11-before  op: op-d08d3d3ea346  commit: a465e7f
files: 33/34 digests OK
passport chain: 15 links via stdlib mirror
  (repo import unavailable: No module named 'genesis_rt')
binding: passport.run_id == op-d08d3d3ea346 OK
binding: IR digest 356dc135f27f4586... OK
anchor: passport sha256 2cf6bd6e6e3997cd... OK
observed: op=COMPLETED gate=PASS matrix=16/16 samples=1000
  qnx_verified=True
FAIL:
  - digest mismatch: transcripts/target-faultinject.log"""

TITLE = "GENESIS RT\\: The Physical World Compiler for QNX"
SUBTITLE = "Specify \u2192  Compile \u2192  Run \u2192  Break \u2192  Prove"
END_1 = "Evidence your whole team can inspect."
END_2 = "github.com/toskaman/genesis-rt"


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"{cmd}\n{r.stderr[-2000:]}"
    return r.stdout


def duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration", "-of", "default=noprint_wrappers=1",
               str(path)])
    return float(out.strip().split("=")[-1])


def render_card(out: Path, text: str, header: str, seconds: float) -> None:
    txt = out.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"color=c={BG}:s=1920x1080:d={seconds}:r=30",
         "-vf",
         f"drawtext=fontfile={FONT_MONO}:textfile='{txt.as_posix()}'"
         ":fontcolor=#d6deeb:fontsize=26:x=120:y=200,"
         f"drawtext=fontfile={FONT_SANS}:text='{header}'"
         ":fontcolor=#7ee787:fontsize=40:x=120:y=110",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])


def render_title(out: Path, line1: str, line2: str, seconds: float) -> None:
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"color=c={BG}:s=1920x1080:d={seconds}:r=30",
         "-vf",
         f"drawtext=fontfile={FONT_SANS}:text='{line1}'"
         ":fontcolor=#ffffff:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-60,"
         f"drawtext=fontfile={FONT_SANS}:text='{line2}'"
         ":fontcolor=#8b949e:fontsize=44:x=(w-text_w)/2:y=(h-text_h)/2+60",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--footage", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    foot = Path(args.footage)
    out = Path(args.out)

    render_title(foot / "t_title.mp4", TITLE, SUBTITLE, 4.0)
    render_title(foot / "t_end.mp4", END_1, END_2, 5.0)
    render_card(foot / "s8a.mp4", CARD_BEFORE,
                "INDEPENDENT REPLAY \u2014 BEFORE PACK", 7.0)
    render_card(foot / "s8b.mp4", CARD_AFTER,
                "INDEPENDENT REPLAY \u2014 AFTER PACK", 7.0)
    render_card(foot / "s8c.mp4", CARD_TAMPER,
                "TAMPER CONTROL \u2014 1 BYTE FLIPPED", 8.0)

    order = ["t_title.mp4", "s1.webm", "s2.webm", "s3.webm", "s4.webm",
             "s5.webm", "s6.webm", "s7.webm", "s7c.webm", "s8a.mp4",
             "s8b.mp4", "s8c.mp4", "s9.webm", "t_end.mp4"]
    print("segment timeline:", flush=True)
    total = 0.0
    normed: list[Path] = []
    for name in order:
        seg = foot / name
        assert seg.is_file(), name
        dur = duration(seg)
        print(f"  {total:6.1f}s +{dur:5.1f}s  {name}", flush=True)
        total += dur
        uni = foot / f"n_{Path(name).stem}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(seg),
             "-vf", "scale=1920:1080,fps=30,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-an", str(uni)])
        normed.append(uni)
    print(f"total: {total:.1f}s", flush=True)
    assert total < 180, "over the 3-minute cap"
    lst = foot / "concat.txt"
    with lst.open("w", encoding="utf-8") as fh:
        for uni in normed:
            fh.write(f"file '{uni.resolve().as_posix()}'\n")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(out)])
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
