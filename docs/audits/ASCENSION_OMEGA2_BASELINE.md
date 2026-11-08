# ASCENSION Ω² baseline (verified 8 Nov 2026, branch `omega2` @ 97b0103)

Machine-readable core:

```json
{
  "branch": "omega2",
  "base": "titan-ascension@97b0103f715391479ccff7554ed40781d920c8e6",
  "main": "5bb2fc447b77f04eda4e6d2f69dc54d696f5f68e",
  "ahead_of_main": 8, "behind_main": 0,
  "tree": "clean", "stash": "empty", "open_prs": 0,
  "ci_head": {"run": 42442759120, "result": "success", "at": "2026-11-08T03:26:52Z"},
  "qnx_workflow_runs": 0,
  "tests_collected": 1251,
  "with_sdk": {"passed": 1249, "skipped": 2, "note": "axe-core absent; measured 8 Nov"},
  "sdk_free_ci": {"passed": 1245, "skipped": 6, "run": 42441670341},
  "e2e_browser": 31,
  "native": {"matrix": "16/16 PASS 8 Nov", "perf": "1000/1000", "sched": "4x200 PASS",
             "packs_verify": "3/3 OK", "rebuild": "18/18 same-host"},
  "ai": {"v1": "98/98 both models (touched)", "v2": "30/30 (touched)",
         "v4_frozen": "off32/qwen32/llama31 of 36, NOT rerun post-reorder",
         "v5": "missing"},
  "impact": "NO_HUMAN_DATA",
  "video": "DEFERRED_BY_OWNER",
  "media_verdict": "RESTORED_TO_MAIN (unauthorized re-render reverted; blob 108c5c44 retained in history)"
}
```

## Wave-1 audit (8 agents, read-only, 8 Nov 2026)

> Correction 8 Nov 2026 (Omega3 §4.2): this section was headed
> "9 Nov 2026" in error — the file was committed 8 Nov 12:44
> +0100, so no 9 Nov execution record can exist. Date corrected
> to the audit day. Coverage is also downgraded: recon and
> ai-pilot returned partial results and critic/synthesis never
> produced their reports (no workflow record was preserved),
> so several finding series (notably ai-pilot B1–B9) have no
> committed definitions and are unrecoverable. The original
> "Complete:" line is replaced by "Partial:" below; git history
> preserves the original wording.

Partial: recon (partial), native-sec (F1–F8), adversarial
(H1–H9, M1–M11), ux-a11y, ai-pilot (A1–A13, B1–B9 — partial,
definitions uncommitted), commercial (sched/codelab/
competitive/BYOQNX-PASS), critic (G1–G16 challenges, no
report), synthesis (no report).
Session ledger (workflow record not preserved); key entries:

- Counts Corroborated two ways (collect + pins + CI tally).
- CAMPAIGN 16/16 + 9/9 hashes corroborated from artifacts.
- AI tables A1–A13 verified against raw eval JSONs; weakest
  link: post-reorder "unchanged" prose lacks raw per-case files.
- BYOQNX trust boundary PASS (unconditional False + AST test).
- Critic challenges retained: absence-claims need grep proof
  (G5/G6/G9), fix specs need owning tests (G14), media
  authorization gap (G2, resolved below).

## Media decision (§video preservation)

Branch media (mp4 7673669 B / 159.664 s, srt 99 cues, png
203210 B) was an unrecorded re-render in b9a1284 that
falsified 10+ `154.664` doc references. No authorization
record exists, and standing rules forbid video work.
RESTORED to main's documented cut (mp4 6772015 B /
154.664063 s, verified by ffprobe just now); all doc
references true again with zero doc edits. The re-render
blob (`108c5c44`) stays in git history; the owner may
re-adopt it at PR review. It will be enumerated in the PR,
never silently included.

## Prioritized remediation (file ownership in parens)

P0:
1. Sched contradiction — 3 current-facing speedup claims
   vs 8-Nov non-replication (`WHY_QNX.md`,
   `TECHNICAL_EVIDENCE.md`, `perf-baseline.md` + PROGRESS note).
2. Campaign concurrency §3.1 — global target lock, stale
   recovery, non-destructive probe, atomic staging
   (`scripts/qnx_target.py`, `host/.../target.py` + tests).
3. H9/H8/M6 trust — verify rc on prov errors, dossier
   redaction scope, release_eligible default
   (`qnx_target.py`, `dossier.py` + tests).
4. Native C — reset_armed resolution §3.3, faultinject
   TimerTimeout rc (F5), 2^31−1 vector (F8)
   (`target/qnx8/**` + conformance tests).
5. Device handshake §3.2 — supervisor-passed pid,
   set-restart, native proof (`genesis_device.c`,
   `genesis_supervisor.c` + matrix).
6. Current-source pack §5 — op flow on live VM
   (needs QEMU campaign).

P1: Studio scoped fixes (`ui/studio.html` + E2E); AI v4
rerun + agent-authored v5 (`evals/**`); pilot B6/B7/B8 +
owner run (`bench/productivity/**`); codelab PS/PYTHONPATH
(`docs/codelab/**`); competitive tags; count sync; PR→merge.

## Known residuals (carried, not new)

No independent pilots; no hardware; qnx.yml 0 runs (no
self-hosted runner); no screen-reader pass; v5 absent;
cross-host reproducibility unproven (same-host only).
