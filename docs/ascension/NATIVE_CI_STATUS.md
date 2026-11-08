# Native QNX CI status (7 Nov 2026)

**Native CI is build-only. No target campaign runs in CI.**

| Lane | Where | What it proves | Executed? |
|---|---|---|---|
| `host-ci.yml` | GitHub-hosted Ubuntu | host suite, C policy, browser E2E, axe scan, IR check, host passport replay | yes, every push/PR |
| `qnx.yml` stages 1–4 | self-hosted runner labelled `qnx` | qcc build of generated sources + SHA256SUMS | **no runner registered** — never executed |
| `qnx.yml` stage 5 (new) | same | every published pack binary rebuilds bit-for-bit | **not executed in CI**; same script verified 18/18 on the owner's machine |
| Native target campaign | owner's machine (Studio / `TargetRunner`) | 16/16 matrix on QEMU, sealed passport | yes, manually (3 canonical packs + 1 legacy pack, all 16/16) |

Why no full native lane: it needs the QNX SDP + QSTI image on a machine
the project controls, a myQNX licence that cannot be shared with public
runners, and isolation from untrusted PRs (workflow is
`workflow_dispatch` only). Recovery path: register a self-hosted runner
on a machine with the SDK, label it `qnx`, dispatch the workflow; extend
it with the existing `TargetRunner` full workflow once a runner exists.
Until then no CI badge implies a QNX run.
