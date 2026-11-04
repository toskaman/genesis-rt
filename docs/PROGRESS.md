# Progress log

## 2026-11-04 — P0: repo + host pipeline + QNX sources (this session)

- Implemented: Machine IR v1 (schema + strict validator), deterministic
  codegen + templates, guard policy in C and Python with conformance
  harness, 5 QNX-native processes, simulator, 8-scenario fault lab with
  oracles, hash-linked evidence passport, fail-closed gate, orchestrator,
  CLI, optional FastAPI API, static dashboard, examples (AMR + conveyor).
- Tested: full pytest suite green (unit/property/integration/faults/
  acceptance; QNX test honestly skips without SDK), C/Python conformance
  vectors identical, break-then-fix gate cycle proven.
- Blocked (external): QNX SDP 8.0 install (interactive license acceptance by
  the entrant) → on-target build/run evidence; demo video recording.
- Next: SDK setup per `docs/quickstart-qnx8-qemu.md`, capture real `qcc`
  build + QEMU run transcripts, attach target evidence to a passport,
  record the <3:00 video from genuine runs, draft Devpost text.

## Acceptance-gate status

- G0 license/redistribution clean: YES (Apache-2.0, no SDK material in repo)
- G1 deterministic codegen: YES (tested)
- G2 QNX native build/run evidenced: PENDING (SDK setup)
- G3 guard rejects on real target: PENDING (SDK setup; host-proven)
- G4 QNX-specific sources visible/tested: PARTIAL (sources + host conformance)
- G5 no-test⇒no-pass: YES (tested)
- G6 seeded reproducible faults: YES (tested)
- G7 clock boundaries separated: YES (methodology + code)
- G8 simulation-only outputs: YES (enforced by IR + validator)
- G9 hardening basics: PARTIAL (timeouts, argv lists, fuzz-ish property tests)
- G10 clean-install repro: PENDING (needs independent reviewer + SDK)
- G11 real demo video <3:00: PENDING
- G12 README pitch/arch/commands/limitations/FAQ: YES
