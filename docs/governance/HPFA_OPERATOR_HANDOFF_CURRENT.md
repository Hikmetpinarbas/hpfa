# HPFA OPERATOR HANDOFF — CURRENT

Updated: 2026-09-15 TRT
Record role: CURRENT_OPERATOR_HANDOFF
Product repo: `Hikmetpinarbas/hpfa`
Runtime authority: `runtime/active_single_match/current`

## 0. NEW OPERATOR — READ THIS FIRST

Mandatory startup sequence:
1. Read `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md`.
2. Read this file completely.
3. Re-fetch GitHub current main and current development frontier before every write.
4. Verify `runtime/active_single_match/current` before any ACTIVE_MATCH claim.
5. Historical runtime evidence never transfers automatically to a new head or match.
6. Do not ask the user to reconstruct recorded project history.

## 1. IMMUTABLE OPERATING RULES

- `hpfa` is the only executable product repo.
- HP-Motor / HP-Engine / HP-PROJELERI are donors only: `ADAPT_NOT_COPY`.
- Google Drive / Dropbox / PDFs / archives / academic sources are SUPPORT/HISTORICAL and never override ACTIVE_MATCH.
- `EVENT ⊂ ZFGV`; event is one observation family, not the observation universe.
- CSV/XML/XLSX visible rows are not canonical events.
- `canonical_event_count=UNKNOWN`.
- `true_action_count=UNKNOWN`.
- `production_release=false`.
- PASS != RELEASE; CI SUCCESS != ACTIVE_MATCH evidence; MERGED != PRODUCTION_RELEASE.
- Same-content reflections must not be double-counted.
- Product code must remain match-agnostic.
- No merge/release/production decision without explicit exact-head user approval.
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

Construct admission is capability-specific:

`CONSTRUCT → REQUIRED OBSERVATION CAPABILITIES → ADMITTED CAPABILITIES → OPTIONAL CAPABILITIES → FORBIDDEN WITHOUT → CLAIM CEILING → ADMISSION DECISION`

Missing required capability: FAIL_CLOSED / DOWNGRADE.
Missing optional capability: DEGRADED.
Legacy binary compatibility metadata may remain only for compatibility/regression lineage; it must never be product admission authority.

Truth locks:
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
Current development head: `FRESH_VERIFY_REQUIRED`.
Last exact physical ACTIVE_MATCH acceptance head: `b0dc4dc97f1c03ab766b61826e5ec92279807ae4`.
State: OPEN / DRAFT / UNMERGED / NOT_PRODUCTION unless freshly verified otherwise.

Do not store a live PR head SHA as static authority in this handoff. Re-fetch before every write/current-state claim.

## 4. FULL SYSTEM MATCH DIAGNOSTIC — CLOSED WIP

Closure classification:
`REVIEW_REQUIRED / FUNCTIONALLY_COMPLETE`

Physical ACTIVE_MATCH evidence on `b0dc4dc97f1c03ab766b61826e5ec92279807ae4`:
- canonical full-spine rc=0
- diagnostic rc=0
- hard blocks=0
- intelligence chains=1961
- completed=1961
- failed=0
- machine/report accounting: 1961=1961 / PASS
- variant challenge current-run ledger: PASS
- variant challenge artifact/runtime binding: 467=467
- Safe Finding current canonical run: NOT_BOUND_CURRENT_RUN
- claim decisions: NOT_EVALUATED=100; DOWNGRADE=0; EMIT=0; ABSTAIN=0
- `NOT_EVALUATED != DOWNGRADE`
- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

Safe meaning: remaining REVIEW_REQUIRED states are product/evidence limitations, not diagnostic-accounting failure.

## 5. CURRENT-PRODUCT EVENT-ONLY CLOSURE — VERIFIED, BUT NOT REPOSITORY COMPLETENESS

Closure record:
`docs/governance/HPFA_ZFGV_EVENT_ONLY_CURRENT_PRODUCT_CLOSURE_V1.md`

Current audited invariant:
`CURRENT_VERIFIED_GLOBAL_EVENT_ONLY_AUTHORITY = 0`

This means the audited current product/reference path no longer uses Event-Only as observation universe, product-wide eligibility gate, default admission veto, global routing prerequisite, metric/model ceiling or analyst-output identity.

It does **not** mean repository-wide migration completeness has been proved.

Therefore both statements are simultaneously valid:
- `COMPLETE_CURRENT_PRODUCT_SCOPE`
- `MIGRATION_COVERAGE=INCOMPLETE`

The migration may be called complete only after semantic residual authority and reverse-capability coverage are closed across current and future-current surfaces.

## 6. CONFIRMED REHABILITATION

- Current product/governance identity is ZFGV.
- Metric registry uses `observation_model=ZFGV_V1`.
- Observation and metric admission are construct/capability-specific.
- L0 AGGREGATE constructs do not require fake event-family prerequisites.
- L8 TRACKING/VIDEO constructs do not require fake event-family prerequisites.
- Genuine L1 ACTION constructs still fail closed when their required ACTION/EVENT semantics are missing.
- Provider legacy Event-Only metadata cannot veto ZFGV.
- Evidence Lens Matrix can be construct-specific rather than action-centric.
- XLSX aggregate evidence can travel without becoming action identity or an independent vote.
- Metric Fusion, Reasoning Grammar and progression planning are ZFGV-scoped.
- The legacy `eventonly_metric_allowlist_v1.json` is retained as compatibility lineage only; it has zero product-wide admission/veto authority.
- Capability Closure Guard prevents positive global Event-Only doctrine from returning.

## 7. LEGITIMATE ACTION/EVENT SUBPATHS — PRESERVE

Do not destroy legitimate event-specific capability while auditing global ontology.

Verified examples:
- `tools/hpfa_data_quality_gate_v1.py` feeds the ACTION/EVENT-shaped phase/sequence path. Its event_id/event_type/team/period requirements are scoped to that event/action consumer and are currently classified `LEGITIMATE_EVENT_TERM`, not global ZFGV authority.
- Primary Event Surface Gate reviews event-derived candidates only; it is not the product-wide surface selector.
- Event identity, occurrence, temporal relation, consequence and action-sequence producers may require event-shaped evidence when the construct itself requires it.

The rule is not “event terms = 0”. The rule is “no hidden universal ACTION/EVENT prerequisite for ZFGV”.

## 8. CURRENT WIP — ZFGV MIGRATION COMPLETENESS AUDIT — SEMANTIC RESIDUAL AUTHORITY CLOSURE

Priority: HIGH architectural product debt.
WIP=1.

Objective:
Prove that no current or future-current generic producer, consumer, router, schema, prompt, plan or runtime pack silently treats ACTION/EVENT-shaped input as a universal prerequisite for the whole ZFGV observation universe.

This is a semantic authority audit, not a string-cleanup exercise.

Until the stop condition is met:
`MIGRATION_COVERAGE=INCOMPLETE`.

### Required audit axes

1. **Non-literal semantic global-event assumptions**
   Search beyond `event-only` / `event_only`: generic event_id/event_type requirements, event-table prerequisites, construct eligibility tied to event-family presence, event-shaped routing defaults, non-event families forced into event schema, tracking absence interpreted as event-only, or L2-L8 capability suppressed by an event flag.

2. **Reverse capability consumer trace**
   Trace current consumers for:
   - ENTITY/ACTOR
   - TEMPORAL
   - SPATIAL
   - RELATIONAL
   - PROCESS/PARTICIPATION
   - AGGREGATE/TABULAR
   - EXTERNAL CONTEXT
   - TRACKING/VIDEO
   - HPFA-DERIVED INTELLIGENCE

   For each family ask: which current gate/producer/contract/policy can prevent admitted evidence from moving further through the spine, and is that prevention construct-required or a hidden global event assumption?

3. **Dormant surface authority classification**
   Classify old PLAN/SPEC/runtime-pack/prompt/policy surfaces as:
   - CURRENT
   - COMPATIBILITY
   - HISTORICAL
   - UNBOUND
   - UNKNOWN / REVIEW_REQUIRED

4. **Completeness closure**
   Only when all current/future-current generic paths have an authority classification and no hidden universal event prerequisite remains may `MIGRATION_COVERAGE=COMPLETE` be emitted.

## 9. CLASSIFICATION VOCABULARY

Semantic classification:
- GLOBAL_ERROR
- EXECUTABLE_LEGACY_GATE
- ACTIVE_GOVERNANCE_STALE
- LEGACY_IDENTIFIER
- LEGITIMATE_EVENT_TERM
- PRESERVE_AS_GUARD
- HISTORICAL
- NEGATIVE_REGRESSION
- REVIEW_REQUIRED

Authority classification:
- CURRENT_PRODUCT_AUTHORITY
- CURRENT_EXECUTABLE
- CURRENT_CONSUMED_SUPPORT
- LEGACY_COMPATIBILITY
- HISTORICAL_ONLY
- UNBOUND
- UNKNOWN

A literal Event-Only occurrence is not automatically a defect. An Event-Only-free component can still be a defect if it imposes a universal event-shaped prerequisite.

## 10. AUDIT ORDER

DATA QUALITY
→ OBSERVATION CONTRACT
→ METRIC REGISTRY
→ METRIC DEFINITION POLICY
→ PROVIDER METRIC DICTIONARY
→ METRIC/MODEL ADMISSION
→ DOWNSTREAM CONSUMERS
→ TESTS
→ DORMANT PLAN/SPEC/RUNTIME-PACK SURFACES
→ ACTIVE_MATCH NEED
→ ANALYST OUTPUT

For every candidate record:
FILE / OCCURRENCE / CURRENT_ROLE / CURRENT_CONSUMER / EXECUTABLE_OR_DOC / AUTHORITY_STATUS / CLASSIFICATION / WHY / ZFGV_RISK / REQUIRED_ACTION / DO_NOT_CHANGE_REASON / TEST_IMPACT / RUNTIME_IMPACT / ANALYST_VALUE_IMPACT.

## 11. STOP CONDITION

Do not close on lexical absence.

Closure requires all of the following:
- current-product global Event-Only authority remains zero;
- generic executable paths contain no hidden universal ACTION/EVENT prerequisite;
- every ZFGV family has reverse-consumer coverage;
- dormant PLAN/SPEC/runtime-pack surfaces that could become future-current are authority-classified;
- legitimate ACTION/EVENT-specific gates are preserved;
- legacy compatibility and negative regressions remain non-authoritative;
- tracking/video claim ceilings remain intact;
- no unresolved CURRENT / UNKNOWN authority candidate can globally narrow ZFGV.

Only then:
`MIGRATION_COVERAGE=COMPLETE`.

## 12. NEXT SAFE ACTION

Continue exact-frontier semantic sweep without touching spatial progression yet.

Immediate search targets:
- generic `required_event_families` / event-family hard requirements;
- generic `event_id` / `event_type` schema requirements outside ACTION/EVENT-specific consumers;
- router/admission branches that assume an event table exists before non-event capability can travel;
- reverse-consumer traces for AGGREGATE/TABULAR, ENTITY/ACTOR, TEMPORAL and SPATIAL first;
- dormant PLAN/SPEC/runtime packs with possible future-current authority.

CODE LAST.
Rehabilitate only a proven current/future-current authority defect.
Use physical ACTIVE_MATCH only if executable runtime behavior materially changes.

Spatial Progression Capability Recovery is `LATER` until this completeness audit closes.

## 13. RELEASE STATE

PR #359 remains OPEN / DRAFT / UNMERGED.
No merge, auto-merge, release or production binding is authorized without exact-head user approval.

Current locks:
`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
