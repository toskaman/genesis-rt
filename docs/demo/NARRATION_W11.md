# Wave 11 final demo: narration + voice handoff

> WITHDRAWN 2026-11-12: the referenced cut was removed for an owner remake.
> Script, subtitles and voice sources below stay as remake inputs.

Final visual edit (withdrawn): `docs/demo/genesis-rt-demo-w11.mp4`
(154.6 s, 1920x1080, H.264/yuv420p, 30 fps, silent).
Timed subtitles: `docs/demo/subtitles-w11.srt` (21 cues).

## Narration script (clean read, ~300 words)

> Embedded software must behave correctly even when real systems
> fail. This is Genesis RT: describe a machine, generate native QNX
> software, and prove it behaves.
>
> Everything starts from a machine contract: sensors, actuators,
> safety limits. The designer validates every field before anything
> is built.
>
> Genesis generates the QNX controller: guard policy and build files.
> Each file carries its source hash, pinned against the contract.
>
> Then it runs for real: compiled with the QNX toolchain, executed on
> QNX 8 under QEMU. Sixteen checks, a thousand performance samples.
> Gate: PASS.
>
> Now break it: a stale-sensor fault is injected live. The guard
> answers; the run records it. A targeted verdict -- honest about what
> was not re-tested.
>
> Diagnose with the evidence graph: every verdict links back to
> scenarios, binaries, requirements. Click any node: the proof behind
> the claim, ready for review.
>
> Change one limit -- 1.2 to 1.6 meters per second -- and verify both
> revisions. Before denies the 1.5 command; after allows it. Same
> rigor, new behavior -- two passports.
>
> A stale build bound to the new contract is refused. No passport.
> Fail closed.
>
> Both passports replay independently -- no servers, no trust-me step.
> Before and after verify clean: thirty-four files, fifteen links
> each. Flip a single byte, and the verifier rejects the pack.
> Evidence you can defend.
>
> Specify. Compile. Run. Break. Prove. Genesis RT for QNX.

## Cue alignment

Cues follow `subtitles-w11.srt`, timed to the segment timeline
printed by `docs/demo/assemble_w11.py`:

| Time | Segment | Content |
|---|---|---|
| 0.0-4.0 | title | GENESIS RT title card |
| 4.0-15.0 | s1 | Judge Mode, stage A (the machine) |
| 15.0-28.7 | s2 | Designer: amr contract + validation OK |
| 28.7-43.5 | s3 | Source: generated files pin MATCH |
| 43.5-60.2 | s4 | Target: op A (BEFORE) 16/16 PASS |
| 60.2-72.0 | s5 | Live fault job (stale proximity) |
| 72.0-89.6 | s6 | Evidence graph of that job |
| 89.6-110.3 | s7 | BEFORE/AFTER compare: both PASS, flip |
| 110.3-117.0 | s7c | Campaign C: stale build FAIL |
| 117.0-124.0 | s8a | Independent replay: BEFORE pack |
| 124.0-131.0 | s8b | Independent replay: AFTER pack |
| 131.0-139.0 | s8c | Tamper control: 1 byte flipped, FAIL |
| 139.0-149.6 | s9 | Judge stage G (the value) |
| 149.6-154.6 | end | End card |

## Voice handoff (owner action) — CLOSED in Wave 12

Wave 11 status was NOT RECORDED (silent MP4 + timed subtitles).
Wave 12 recorded the script with local Piper TTS
(`en_US-lessac-medium`): see `voiceover-w12.txt` (editable script),
`voiceover-w12.flac` (lossless voice source), `VOICEOVER_W12.json`
(render report), `subtitles-w12.srt` (re-timed captions) and the
voiced `genesis-rt-demo-w12.mp4` (154.664 s, AAC). Validation:
`MEDIA_VALIDATION_W12.md`. Remaining owner actions (listen-once,
YouTube upload, Devpost URL): `PUBLICATION_HANDOFF_W12.md`.

Note: the Wave 11 draft mux below used `-shortest`, which risks
truncating the video to a shorter audio track. The Wave 12 pipeline
builds the audio to exactly the video length and muxes without
`-shortest` (guarded with `-t 154.664`) — do not use the old form:

```sh
ffmpeg -i genesis-rt-demo-w11.mp4 -i voiceover.wav \
  -c:v copy -c:a aac -shortest genesis-rt-demo-w11-voiced.mp4
```

## YouTube upload (owner action)

PENDING (external account action). Upload the voiced MP4 (or the
silent edit + `subtitles-w11.srt` sidecar) as public, under 3:00,
and record the URL in `docs/devpost-draft.md`.
