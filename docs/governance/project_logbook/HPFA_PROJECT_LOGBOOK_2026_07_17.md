# HPFA PROJECT LOGBOOK — 2026-07-17

Record type: PROJECT_STATE_SNAPSHOT
Main SHA: `0605abadcc6455b4852905a5aa2a52d51380e6f3`
Runtime authority: `runtime/active_single_match/current`
Canonical event count: `UNKNOWN`
Production release: `false`

## Main state
Current main ends at Triplex Source Alignment Adapter Lite V1.
Recent merged infrastructure includes:
- `core_pipeline_orchestrator_lite_v1`
- `triplex_source_alignment_adapter_lite_v1`

Both remain subject to module-specific runtime evidence. Main membership alone does not establish ACTIVE_MATCH proof or production release.

## PR #164 — Multiformat File Inventory Lite V1
Base: `main`
Head: `327b3c2317cdfda5c052a9163325fb04eb2fbb16`
State: open, draft, mergeable, not merged.

Recorded current-head evidence:
- focused tests: `22 passed`
- status: `PASS`
- supported visible files: `18`
- unique content fingerprints: `10`
- exact duplicate reflection groups: `8`
- duplicate conflicts: `0`
- reference/governance-only unsupported files: `6`
- unresolved unsupported files: `0`
- hard blocks: `0`
- outputs written: `true`

Release label:
`ACTIVE_MATCH_EVIDENCE_PASS / FILE_DISCOVERY_NODE_COMPLETE / NOT_PRODUCTION / NOT_MERGED`

Analyst-safe reading:
The runtime package exposes multiple visible file surfaces and duplicate reflections. This is discovery evidence only.

## PR #166 — CSV Surface Reader Lite V1
Base: `multiformat-file-inventory-lite-v1`
Head: `b0bef9b5d835b306369c3c36eeb9261be4ff0002`
State: open, draft, mergeable, not merged.

Previous-head runtime inventory:
- CSV surfaces: `3`
- Goalkeepers.csv: `193 surface rows`
- Players.csv: `3463 surface rows`
- Teams.csv: `4069 surface rows`

Recorded defect:
The team surface had no separate team column. Provider team tokens were embedded in `code` before an exact `" - " + action` suffix. The previous rule produced a source-role schema false positive.

Recorded correction:
- embedded extraction limited to `TEAM_SURFACE_CANDIDATE`
- exact suffix match required
- player and goalkeeper code prefixes excluded from team binding
- provider identifiers retained as candidates
- validated team identity remains false
- unresolved surfaces keep `team_field_unusable`

Current-head engineering record:
- compile: PASS
- shell syntax: PASS
- focused tests: `26 passed`
- GitHub Actions: success

Current gate:
`CURRENT_HEAD_CI_SUCCESS / SOURCE_ROLE_TEAM_BINDING_CORRECTED / ACTIVE_MATCH_REVALIDATION_REQUIRED / NOT_PRODUCTION / NOT_MERGED`

## CI incident record
Two earlier CSV-reader workflow failures were classified as historical false negatives caused by brittle exact-string grep checks. Compile, focused tests and shell syntax were already passing. The workflow now validates Python constants and contract JSON semantically.

Recorded status vocabulary:
`HISTORICAL_FAILED_SUPERSEDED`

## Older event-admission stack
- PR #155: lossless Canonical Event Lite intake; draft; not merged.
- PR #157: Event Instance Admission Guard; fail-closed/spec correction; not merged.
- PR #158: Evidence Atom Contract; recorded ACTIVE_MATCH evidence; not merged.
- PR #159: Match-Local Identity Decoder; CI success; updated-head ACTIVE_MATCH pending; not merged.
- PR #161: composite event diagnostic stack; 49 commits; multiple product nodes; split required.

Recorded dependency order:
Evidence Atom Contract → Match-Local Identity → Semantic Classifier → Cross-Role Reflection → Aggregate Reconciliation → Residual Diagnostic → Pipeline Manifest/Provenance.

## Governance update
The 2026-06-22 short directive is superseded by the 2026-07-17 short-current record.
Two separate governance records now exist:
1. short current directive;
2. dated project logbook.

## Current product order
1. inventory
2. CSV reader
3. XLSX reader
4. XML reader
5. provider alias and field semantics
6. cross-format reconciliation
7. aggregate definition alignment
8. row nuclei and G01–G18 rollup
9. evidence atoms and identity
10. semantic roles, action bundles and cross-role relations
11. context, sequence, phase, metric and visual evidence
12. claim-safe analyst output

## Claim and release boundary
No open PR listed here is a production release.
No numeric canonical event count is admitted.
No validated global identity, complete sequence truth, tactical truth, dominance truth, pitch-control truth, off-ball truth or coach-intention truth is recorded.

Current project status:
`PRODUCT_ENGINEERING_ACTIVE / INGEST_MODERNISATION_IN_PROGRESS / CURRENT_HEAD_RUNTIME_GAPS_EXPLICIT / canonical_event_count=UNKNOWN / production_release=false`
