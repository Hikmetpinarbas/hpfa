# HPFA OPERATOR HANDOFF — CURRENT

Updated: 2026-09-15 TRT
Record role: CURRENT_OPERATOR_HANDOFF
Product repo: `Hikmetpinarbas/hpfa`
Runtime authority: `runtime/active_single_match/current`

## 0. NEW OPERATOR — READ THIS FIRST

This file exists so a new operator can continue HPFA without asking the user to reconstruct prior work.

Mandatory startup sequence:
1. Read `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`.
2. Read this file completely.
3. Re-fetch GitHub current main and current development frontier before any write.
4. Verify `runtime/active_single_match/current` before any ACTIVE_MATCH claim.
5. Historical runtime evidence never transfers automatically to a new head or a new match.
6. Do not ask the user to repeat project history already recorded here unless a material ambiguity remains after verification.

## 1. IMMUTABLE OPERATING RULES

- `hpfa` is the only executable product repo.
- HP-Motor / HP-Engine / HP-PROJELERI are donors only: `ADAPT_NOT_COPY`.
- Google Drive / Dropbox / PDFs / archives / academic sources are SUPPORT/HISTORICAL and never override ACTIVE_MATCH.
- Runtime truth exists only at `runtime/active_single_match/current`.
- `EVENT ⊂ ZFGV`; event is one observation family, not the whole observation universe.
- CSV/XML/XLSX visible rows are not canonical events.
- `canonical_event_count=UNKNOWN`.
- `true_action_count=UNKNOWN`.
- `production_release=false`.
- PASS != RELEASE; CI SUCCESS != ACTIVE_MATCH evidence; MERGED != PRODUCTION_RELEASE.
- Same-content reflections must not be double-counted.
- Product code must remain match-agnostic and preserve `test_no_sample_match_identity_leak`.
- No merge/release/production decision without explicit user approval.
- Existing producers/contracts/tests must be rehabilitated before any parallel engine is opened.

## 2. CANONICAL OBSERVATION MODEL

HPFA operates on Zenginleştirilmiş Futbol Gözlem Verisi (ZFGV).

Observation families:
- ACTION/EVENT
- ENTITY/ACTOR
- TEMPORAL
- SPATIAL
- OUTCOME/QUALIFIER
- RELATIONAL
- PROCESS/PARTICIPATION
- AGGREGATE/TABULAR
- EXTERNAL CONTEXT
- TRACKING/VIDEO only when admitted
- HPFA-DERIVED INTELLIGENCE

Construct admission is capability-specific.

Required model:
`CONSTRUCT → REQUIRED OBSERVATION CAPABILITIES → ADMITTED CAPABILITIES → OPTIONAL CAPABILITIES → FORBIDDEN WITHOUT → CLAIM CEILING → ADMISSION DECISION`

Missing required capability: FAIL_CLOSED / DOWNGRADE.
Missing optional capability: DEGRADED.
Legacy `event_only_compatible` metadata may survive for compatibility/regression lineage, but it must not be product admission authority.

Preserve truth locks:
- ROW != EVENT TRUTH
- EVENT != WHOLE OBSERVATION UNIVERSE
- PROVIDER LABEL != PHYSICAL/TACTICAL TRUTH
- AGGREGATE != ACTION IDENTITY
- MULTIFORMAT != INDEPENDENT EVIDENCE
- SAME TIMESTAMP != TOTAL ORDER
- COORDINATE != TRACKING
- PROCESS LABEL != COACH INTENTION
- RECURRENCE != CAUSALITY
- MODEL OUTPUT != FACT
- LLM TEXT != EVIDENCE
- ABSENCE != COUNTEREVIDENCE

## 3. CURRENT DEVELOPMENT FRONTIER

Repository: `Hikmetpinarbas/hpfa`
Current development PR: `#359 — ZFGV: Action Grammar synced to current frontier`
Current development head after this governance supersession: `9e03334544a4136f8f8c93e1db3fe0ad63e70a9e`.
Last exact physical ACTIVE_MATCH acceptance head: `b0dc4dc97f1c03ab766b61826e5ec92279807ae4`.
State: OPEN / DRAFT / UNMERGED / NOT_PRODUCTION.

Important: this document itself may move the branch head when updated. Therefore the live PR head must still be freshly verified before every subsequent write/current-state claim; the physical acceptance head remains the last runtime-evidenced code head until a later physical run proves otherwise.

## 4. FULL SYSTEM MATCH DIAGNOSTIC — CLOSED WIP

Closure classification:
`REVIEW_REQUIRED / FUNCTIONALLY_COMPLETE`

Exact-head physical ACTIVE_MATCH evidence on `b0dc4dc97f1c03ab766b61826e5ec92279807ae4`:
- canonical full-spine return code: 0
- diagnostic return code: 0
- full-spine status: REVIEW_REQUIRED
- diagnostic status: REVIEW_REQUIRED
- hard blocks: 0
- intelligence chains: 1961
- completed intelligence chains: 1961
- failed intelligence chains: 0
- machine vs human intelligence chain accounting: 1961 = 1961 / PASS
- variant feature challenge current-invocation accounting: PASS
- variant challenge artifact rows: 467
- variant challenge runtime binding rows: 467
- challenge artifact declared current invocation: true
- Safe Finding artifact current invocation: false
- Safe Finding runtime state: NOT_BOUND_CURRENT_RUN
- claim contract current invocation: true
- claim safe-finding consumed: false
- claim decisions: NOT_EVALUATED=100; DOWNGRADE=0; EMIT=0; ABSTAIN=0
- `NOT_EVALUATED != DOWNGRADE` preserved
- canonical_event_count=UNKNOWN
- true_action_count=UNKNOWN
- production_release=false

Exact-head engineering evidence on the same physical-acceptance head:
- full-repo fail-local audit: PASS
- product compile: PASS
- isolated test files: 228
- isolated tests: 1687
- isolated failures: 0
- isolated errors: 0
- monolithic product-core run remains REVIEW_REQUIRED due confirmed full-suite state/import contamination and is not the product gate.

Safe meaning:
The diagnostic now correctly separates artifact existence from current-run execution and does not promote a non-executed Safe Finding layer into a DOWNGRADE result. Remaining REVIEW_REQUIRED states are product/evidence limitations, not diagnostic-accounting failure.

## 5. CURRENT WIP — ZFGV EVENT-ONLY RESIDUAL AUTHORITY & SEMANTIC CEILING AUDIT + REHABILITATION

Priority: HIGH / architectural product debt.
WIP=1. Do not open a second implementation stream.

This is NOT a string-cleanup task.

Primary objective:
Remove every current product authority or executable behavior where Event-Only acts as a global observation-universe ceiling, admission veto, eligibility default, routing assumption or analyst-output identity, while preserving legitimate ACTION/EVENT producers, event-specific contracts, claim-safety guards, historical lineage and negative regression tests.

Completion requires BOTH:
A) lexical migration audit
B) behavioral/semantic migration audit

The earlier 50-file inventory is a DISCOVERED MINIMUM SET only.
It is not migration scope, completeness proof or Definition of Done.

Required classification vocabulary:
- GLOBAL_ERROR
- EXECUTABLE_LEGACY_GATE
- ACTIVE_GOVERNANCE_STALE
- LEGACY_IDENTIFIER
- LEGITIMATE_EVENT_TERM
- PRESERVE_AS_GUARD
- HISTORICAL
- NEGATIVE_REGRESSION
- REVIEW_REQUIRED

Required authority vocabulary:
- CURRENT_PRODUCT_AUTHORITY
- CURRENT_EXECUTABLE
- CURRENT_CONSUMED_SUPPORT
- LEGACY_COMPATIBILITY
- HISTORICAL_ONLY
- UNBOUND
- UNKNOWN

## 6. FRESH VERIFIED FIRST FINDINGS FOR CURRENT WIP

### P0 — executable legacy gate confirmed
`tools/hpfa_data_quality_gate_v1.py`

Current exact frontier still describes itself as validation for `event-only ACTIVE_MATCH surfaces` and applies a global schema requiring event-shaped groups including event id/type, team identity and period before downstream analysis is allowed.

This is a real executable Event-Only ceiling candidate because valid ZFGV observation families such as ENTITY/ACTOR, RELATIONAL, PROCESS/PARTICIPATION or AGGREGATE/TABULAR may not legitimately carry universal event identity fields.

Classification: `EXECUTABLE_LEGACY_GATE / CURRENT_EXECUTABLE / P0`
Action: rehabilitate existing gate into observation-family / construct-capability-specific data-quality admission. Do not delete event-specific validation; scope it to ACTION/EVENT surfaces or constructs that actually require it.

### P0 — stale current handoff confirmed and superseded by this update
Previous `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md` was dated 2026-08-19, described old PRs/match state as current and used Event-Only-era framing. It conflicted with the active short current directive.

Classification: `ACTIVE_GOVERNANCE_STALE / CURRENT_PRODUCT_AUTHORITY / P0`
Action: supersede, not rewrite history. This file is the replacement current handoff.

### Current metric admission core already migrated — preserve
`configs/metrics/metric_registry_v1.json` uses `observation_model=ZFGV_V1` and construct-specific observation layers/capabilities/forbidden_without/tracking requirements.

`metric_definition_policy_lite` imports and assesses the observation contract; legacy `event_only_compatible` is not fingerprint or required admission authority.

`provider_metric_dictionary_lite` no longer contains the old operational Event-Only blocker.

Regression `test_legacy_event_only_metadata_cannot_veto_zfgv` deliberately injects `event_only_compatible=False` and proves it cannot create `event_only_compatibility_required` fail-closed behavior.

Classification for that test: `NEGATIVE_REGRESSION / PRESERVE`.
Do not delete it as lexical residue.

### Metric fusion allowlist — not current production authority, but review required
`hpfa/modules/core/metric_fusion_engine/policies/eventonly_metric_allowlist_v1.json`
status=`candidate_not_production_bound`.

Current metric fusion source files inspected do not establish this file as product-wide admission authority.
Classification: `LEGACY_IDENTIFIER / UNBOUND_OR_SCAFFOLD / REVIEW_REQUIRED` until reverse-consumer trace completes.
Do not mechanically rename or delete.

### Active governance/prompt stale residues confirmed
The current North Star and New-Page Continuity prompts still describe the main product objective as producing intelligence from `ham event yüzeyleri` and use `Event-only veriden...` wording in claim guards. Some of this is guard language; some is product-universe language and requires classification rather than bulk replacement.

`docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md` explicitly says `HPFA is an event-only... Football Intelligence Platform.` This is a current prompt-level global identity error.
Classification: `GLOBAL_ERROR / CURRENT_CONSUMED_SUPPORT` if the prompt remains active.

## 7. AUDIT ORDER

1. Fresh repository-wide lexical discovery on current frontier.
2. Semantic/behavioral discovery for event-shaped universal prerequisites.
3. Reverse capability trace from each ZFGV observation family.
4. Authority/consumer map per occurrence.
5. P0 executable chain:
   DATA QUALITY → OBSERVATION CONTRACT → METRIC REGISTRY → METRIC DEFINITION POLICY → PROVIDER METRIC DICTIONARY → METRIC/MODEL ADMISSION → DOWNSTREAM CONSUMERS → TESTS → ACTIVE_MATCH → ANALYST OUTPUT.
6. Governance/prompt/handoff successor-regression audit.
7. Historical/legacy/negative-regression separation.
8. Minimal rehabilitation plan.
9. Tests.
10. Exact-head ACTIVE_MATCH only where implementation changes runtime behavior.
11. Red Team.
12. Analyst-value delta.

Until the lexical + behavioral + reverse-capability search stop condition is met:
`MIGRATION_COVERAGE=INCOMPLETE`.

## 8. CURRENT NEXT SAFE ACTION

Build the repository-wide Event-Only Residual Authority Ledger on the fresh current frontier and trace the P0 `hpfa_data_quality_gate_v1.py` consumers before changing its behavior.

Do not implement a new gate.
Do not bulk rename event terms.
Do not touch legitimate event-specific chronology/identity/consequence code solely for terminology.
Do not weaken tracking/video claim ceilings.

Construct-Specific Consequence Horizon remains a valid later WIP candidate, but the confirmed global observation admission ceiling is more upstream and therefore takes priority until this audit establishes otherwise.

## 9. RELEASE STATE

PR #359 remains OPEN / DRAFT / UNMERGED.
No merge, auto-merge, release or production binding is authorized.

Current locks:
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
