# Judge scorecard (internal self-assessment)

Internal target only — never a claim about official judging. Scores
are against the four published criteria; every cell links to
verifiable evidence or a named weakness.

| Criterion | Score | Evidence | Weakness | Improvement | Verified result |
|---|---|---|---|---|---|
| A. Technological Implementation | 9/10 | Native guard/controller/device/status/supervisor/faultinject + cellcheck in C; IR v2 E2E (limits + transitions drive target behavior); `qcc` 0 warnings; 16/16 on-target matrix; crash containment ×3; sched campaign 4×200; 550 host tests (SDK-free: 546 + 4 honest skips); C/Python conformance harness | QEMU-only (no real hardware); no HAM (absent from image); uint32 ms clocks wrap | ARM/real-board campaign; HAM integration when image ships it; 64-bit clocks | 16/16 matrix PASS, `QNX_PERFORMANCE_MEASURED` replay + tamper control |
| B. Design | 8/10 | CLI + local API + Studio/Dashboard; coherent run→fault→evidence→compare flow; verified 45-min codelab (Win+Linux); precise errors (exit 2 + reason); judge path is 2 commands | Static UI pages (no live pipeline from browser); full path needs SDK+QEMU | API-driven Studio runs; one-click target stages | Fresh-clone judge path green (demo PASS + suite 550/550) |
| C. Potential Impact | 7/10 | Industrial-cell flagship demo; `docs/business/COMMERCIAL_VISION.md` (users, 8 use cases, landscape, models, roadmap); honest QNX-licensing note; ~45-min onboarding measured | Hypotheses unvalidated (no pilot teams); gains estimated, not measured | 2–3 pilots with before/after numbers | Cell Demo C broken→fixed with causal delta |
| D. Innovation & AI Creativity | 8/10 | Evidence passport + fail-closed gate + counterfactual compare (contract knob → verdict move); 18-test adversarial suite; 28-case planning eval at 28/28 behind the strict gate | Bundled AI is a keyword planner, not an LLM (labeled as such); no real provider adapter | LLM provider adapter measured on the same 28-case set | `compare` output + eval results, both replayable |

## Bonus coverage

- **Best Use of QNX-specific Technologies:** message passing,
  resmgr, RT scheduling experiments, supervision, crash containment —
  see `WHY_QNX.md` + `TECHNICAL_EVIDENCE.md`.
- **Best Codelab/Tutorial:** `docs/codelab/README.md` — every command
  verified live 2026-11-05, Win+Linux, troubleshooting, cleanup,
  limitations, final Devpost URL inside.

(Rules allow one general + one bonus prize per project; both tracks
are prepared without assuming they combine.)
