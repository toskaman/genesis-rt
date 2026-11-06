# Wave 12 media validation report — voiced final demo

Date: 2026-11-06. Deterministic pipeline, all numbers measured.

## Final MP4 (submission video)

- File: `docs/demo/genesis-rt-demo-w12.mp4` (6,772,015 B)
- Duration: **154.664063 s (2:34.7)** — under the 3-minute cap
- Video: H.264 1920x1080 30 fps, stream-copied from the Wave 11
  silent edit (`-c:v copy`); duration unchanged to the packet
  (154.664062 s before and after)
- Audio: AAC 48 kHz stereo 128 kb/s, faststart enabled
- Peak −5.9 dBFS, mean −25.0 dB, flat-factor 0 (no clipping)
- No `-shortest`: audio track built to exactly the video length
  (154.664 s), mux additionally guarded with `-t 154.664`

Reproducible assembly (from repo root):

```sh
python docs/demo/voiceover_w12.py --voice-dir <piper-voices> \
  --video docs/demo/genesis-rt-demo-w11.mp4 \
  --script docs/demo/voiceover-w12.txt \
  --out /tmp/voiceover-w12.wav --report docs/demo/VOICEOVER_W12.json
ffmpeg -y -i docs/demo/genesis-rt-demo-w11.mp4 -i /tmp/voiceover-w12.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy \
  -af "volume=0.7079457848,aresample=48000,aformat=channel_layouts=stereo" \
  -c:a aac -b:a 128k -ar 48000 -ac 2 -t 154.664 \
  -movflags +faststart docs/demo/genesis-rt-demo-w12.mp4
python docs/demo/retime_srt_w12.py
```

## Voiceover

- Engine: Piper TTS 1.8.0 (GPL-3.0 tool; used locally only, not
  redistributed — no GPL material enters this repository)
- Voice: `en_US-lessac-medium`, 22050 Hz mono, dataset "lessac"
  (Blizzard-derived). The model metadata carries no license field;
  demo/hackathon use is low-risk, but the owner should confirm the
  voice terms before any monetized publication
- Script: `docs/demo/voiceover-w12.txt` (editable source, 220 words,
  10 blocks); render report `docs/demo/VOICEOVER_W12.json`;
  lossless source `docs/demo/voiceover-w12.flac`
- Pace: 143 words/min of speech; zero slot overruns, zero bleed

Pronunciation (verified via `piper --debug` phoneme dump):

| Written (subs) | Spoken (voice) | Phonemes |
|---|---|---|
| QNX | QNX | cue-en-ex |
| QEMU | Q-Emu | kyoo-ee-myoo (plain QEMU reads "keh-moo") |
| GENESIS RT | GENESIS RT | genesis ar tee |
| 1.2 / 1.5 / 1.6 | numeric | one point two/five/six |

Silence map (all intended — inter-segment pauses, 4.26 s title
head, 10.3 s end-card hold; every block ends cleanly inside its
visual segment; no clipped sentences).

## Subtitles

- `docs/demo/subtitles-w12.srt`: 21 cues, monotonic, in-bounds,
  max 2 lines; timings derived from measured block spans
  (word-fraction with pause weights — see `retime_srt_w12.py`)
- One verbatim fix vs w11: cue 2 restores the 4 spoken words
  ("This is Genesis RT:") the w11 captions dropped; QEMU spelling
  kept for readers

## §4B footage audit verdict — PASS, zero drift

Proof cards (s8a/s8b/s8c) diffed programmatically against fresh
verifier runs: **0 drift lines** (BEFORE rc=0, AFTER rc=0, tamper
rc=2). Spot checks against the public packs:

| Claim on screen | Evidence |
|---|---|
| 16/16 BEFORE + AFTER | verifier `observed:` lines, both packs |
| IR 1.2 → 1.6 | `linear_limit_mps` in both target records |
| 1.5 DENY → ALLOW | `target-limits_differ.log` AMR probes |
| Independent replay | `verify.py` stdout cards, verbatim |
| Tamper rc=2 | reproduced 2026-11-06 (1-byte flip) |
| Stale build refused, no passport | op-ad562b34f8de: 1.6 IR + 1.2-built guard, no passport file |
| QNX 8 under QEMU | platform `qnx8_x86_64_qemu`, uname QNX 8.0.0 |
| Host fault job "targeted" | narration + SHOT_EVIDENCE run-ce237c9af65d |

Notes: the AFTER `v2_transitions` transcript also shows a
`1.500 DENY` row — that probe targets the pinned secondary
`genesis_guard_v2` (fixed IR `5639d986…`, identical bytes in both
campaigns, `host/genesis_rt/buildset.py`), whose fixed oracle
expects DENY; the campaign-guard flip is the `limits_differ` row.
The s5/s7c scenes rest on git-ignored local captures, reproducible
via `docs/demo/capture_w11.py` with the seeded jobs.

## Residual (owner actions)

- The voice was verified by phonemes, levels and timing — not by
  ear in this session. Listen once before publishing.
- Confirm the Lessac voice terms if the video is ever monetized.
- Publication itself (YouTube + Devpost URL) needs the owner's
  connected account — see `PUBLICATION_HANDOFF_W12.md`.
