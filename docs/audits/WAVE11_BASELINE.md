# Wave 11 baseline (Phase Zero)

Date: 2026-11-05. HEAD: `a465e7f` (matches reference), tree clean,
CI host-ci SUCCESS. Unit suite re-run: 621/621 green. SDK qcc 12.2.0
+ QEMU 11.1.0 present on this box.

| Capability | Impl | Test | Browser | Native | Evidence | Docs | Deficiency |
|---|---|---|---|---|---|---|---|
| Machine IR v1/v2 + codegen | VERIFIED | VERIFIED | n/a | VERIFIED | pack | ok | — |
| 16/16 target matrix (BEFORE) | VERIFIED | VERIFIED | n/a | VERIFIED | pack b22cea1 | ok | AFTER has no passport |
| Contract-aware oracle | MISSING | MISSING | n/a | MISSING | — | — | limits_differ hardcodes DENY@1.5 |
| AFTER campaign (1.6) | PARTIAL | PARTIAL | n/a | PARTIAL | local only | §5 issue | 15/16, no passport |
| Negative safety case | PARTIAL | VERIFIED | n/a | PARTIAL | local | ok | needs clean Campaign C |
| Before/after compare view | VERIFIED | VERIFIED | VERIFIED | PARTIAL | — | ok | AFTER side shows FAILED op |
| Dossier / decision panel | VERIFIED | VERIFIED | VERIFIED | VERIFIED | — | ok | — |
| Judge Mode + E2E | VERIFIED | VERIFIED | VERIFIED | n/a | CI | DRIFT | KNOWN_LIMITATIONS says pending |
| Evidence pack + verifier | VERIFIED | VERIFIED | n/a | VERIFIED | pack | ok | single campaign only |
| Video | PARTIAL | n/a | n/a | n/a | 42 s raw | ok | no final edit/voice/upload |
| Bench v2 / F9 / pilot kit | VERIFIED | VERIFIED | n/a | n/a | REPORT.json | DRIFT | devpost says 890 (is 906) |
| Red-team 1+2 / soak | VERIFIED | VERIFIED | n/a | n/a | audits/ | ok | no 24 h run |
| C conformance (41 vec) | VERIFIED | VERIFIED | n/a | n/a | — | ok | — |
| CI integration (JUnit/SARIF) | MISSING | MISSING | n/a | n/a | — | — | Wave 11 §11 |
| IPC timeline | MISSING | MISSING | n/a | MISSING | — | — | Wave 11 §12, needs logs |
| 2nd scenario / LLM | NOT STARTED | — | n/a | — | — | doc'd | optional, likely deferred |

Competition impact of the oracle gap: the flagship demo (contract
change → behavior change → new proof) currently ends in a FAILED op;
fixing it correctly is the highest-value Wave 11 work. Commercial
impact: CI integration (§11) is the smallest credible adoption
bridge. QEMU + password path available (image-default documented in
quickstart); native campaigns feasible this session.
