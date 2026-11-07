# Studio information architecture (7 Nov 2026)

| Group | Page (nav label) | Purpose | Needs backend |
|---|---|---|---|
| Start | Overview | value proposition, archived BEFORE/AFTER/stale-binary proof, workflow, status vocabulary | no |
| Start | Guided demo | 7-stage judge walkthrough driving the real product | live or archived |
| Build | Projects | saved machine contracts | yes |
| Build | Machine designer | edit + validate Machine IR (JSON is the source of truth) | yes |
| Build | Generated C | inspect generated QNX build files | no |
| Verify | Host pipeline | validate → generate → 8-scenario fault campaign (host only) | yes |
| Verify | QNX target runner | native campaign on the QEMU target | yes + SDK + QEMU |
| Verify | Fault lab | scenarios, seeds, oracle checks of a passport | no |
| Evidence | Evidence passport | offline hash-chain re-verification | no |
| Evidence | Before / After | two passports, delta only when both chains valid | no |
| Evidence | Evidence graph | requirement → … → verdict graph | yes |
| Explore | Digital twin | replay a scenario trace | no |
| Explore | CLI commands | copy-paste commands for the same flows | no |

Routing: `studio.html#/<page>`; unknown page → Overview. First visit →
Overview; later visits in the same session → last page.

Element ids and `data-tab` values are unchanged from earlier versions, so
every existing test and backend contract still applies.
