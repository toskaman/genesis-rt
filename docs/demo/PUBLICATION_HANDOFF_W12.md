# Publication handoff — Wave 12 demo video

> ON HOLD — WITHDRAWN 2026-11-12: the cut was removed for an owner remake.
> Checklist below resumes when the new cut lands; do not follow it as-is.

Status 2026-11-06: video, captions and thumbnail are ready.
**Upload + Devpost link need the owner's connected account.**
Do not claim publication until a real public URL exists.

## YouTube title (82 chars)

GENESIS RT: the physical world compiler for QNX — native verification demo

## YouTube description

Embedded software must behave correctly even when real systems fail.
GENESIS RT is a proof-driven engineering workspace for QNX-native
machine software: describe a machine, generate the QNX controller,
run it on a QNX 8 target, inject faults, and produce independently
verifiable evidence.

In 2:35: a live machine contract, generated QNX code, a 16/16 native
target campaign, fault injection, the evidence graph, a verified
before/after contract change (1.2 → 1.6 m/s, DENY → ALLOW at the
1.5 probe), a refused stale build, independent replay of both
evidence passports, and a 1-byte tamper rejection.

All footage is real software; proof cards are verbatim terminal
output. QNX 8.0 under QEMU (qcc 12.2.0, x86_64).

Links:
- Source: https://github.com/toskaman/genesis-rt
- Evidence packs: evidence/qnx8-x86_64-w11-before and -after
  (verify with `python verify.py`, no SDK needed)
- Codelab: <paste final codelab URL before publishing>

Chapters:
00:00 Title — the problem
00:04 The machine in Studio
00:15 The machine contract
00:29 Generated QNX controller
00:44 Native target run, 16/16 PASS
01:00 Fault injection, targeted verdict
01:12 Evidence graph diagnosis
01:30 Before/after: one limit changed, both verified
01:50 Stale build refused — fail closed
01:57 Independent replay, both passports
02:11 Tamper control: 1 byte flipped, pack rejected
02:19 The value — evidence your team can inspect

## Thumbnail

`docs/demo/thumbnail-w12.png` (1920x1080 frame from the
before/after scene at 96 s).

## Captions

Upload `docs/demo/subtitles-w12.srt` as English captions (21 cues,
verbatim, timed to the voice track).

## Devpost video-link field

PENDING — paste the public YouTube URL into `docs/devpost-draft.md`
(video URL field) once published.

## Submission checklist

- [ ] Listen to the voiceover once (phoneme/level-verified, not
      ear-checked in-session)
- [ ] Upload MP4 to YouTube (unlisted first), attach captions +
      thumbnail, set chapters from the description above
- [ ] Switch to public, copy the URL
- [ ] Paste URL into `docs/devpost-draft.md` and Devpost form
- [ ] Confirm total runtime < 3:00 on YouTube (source: 2:34.7)
- [ ] Confirm the codelab URL in the description is final
