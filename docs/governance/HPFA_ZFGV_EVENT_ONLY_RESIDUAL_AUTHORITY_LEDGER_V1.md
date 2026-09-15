# HPFA ZFGV EVENT-ONLY RESIDUAL AUTHORITY LEDGER V1

Status: `DISCOVERY_IN_PROGRESS`
Migration coverage: `INCOMPLETE`
Reference product: single-match Postmatch
Canonical ontology: `EVENT ⊂ ZFGV` and `ZFGV != EVENT`

This ledger is an authority/consumer audit, not a string-cleanup list.

The earlier 50-file inventory is a discovered minimum set only. It is not completeness proof, migration scope or Definition of Done.

## Classification vocabulary

- `GLOBAL_ERROR`
- `EXECUTABLE_LEGACY_GATE`
- `ACTIVE_GOVERNANCE_STALE`
- `LEGACY_IDENTIFIER`
- `LEGITIMATE_EVENT_TERM`
- `PRESERVE_AS_GUARD`
- `HISTORICAL`
- `NEGATIVE_REGRESSION`
- `REVIEW_REQUIRED`

## Authority vocabulary

- `CURRENT_PRODUCT_AUTHORITY`
- `CURRENT_EXECUTABLE`
- `CURRENT_CONSUMED_SUPPORT`
- `LEGACY_COMPATIBILITY`
- `HISTORICAL_ONLY`
- `UNBOUND`
- `UNKNOWN`

## Audit rules

1. Literal `event-only`, `event_only` or `eventonly` is not sufficient evidence of a product defect.
2. Absence of those strings is not sufficient evidence that Event-Only authority is gone.
3. A current executable file is not automatically current reference-runtime authority.
4. A current file may be `CURRENT_EXECUTABLE` while its current full-spine consumer binding remains `UNBOUND` or `UNKNOWN`.
5. Event-specific identity, occurrence, temporal, consequence and ACTION/EVENT constructs are legitimate.
6. Global observation-universe, eligibility or downstream-routing vetoes based on event-shaped input are migration targets.
7. `event_only_compatible` may survive as compatibility/regression metadata but must not be product admission authority.
8. Tracking/video claim ceilings are preserved.

## Current verified ledger

| FILE | OCCURRENCE | CURRENT_ROLE | CURRENT_CONSUMER | EXECUTABLE_OR_DOC | AUTHORITY_STATUS | CLASSIFICATION | WHY | ZFGV_RISK | REQUIRED_ACTION | DO_NOT_CHANGE_REASON | TEST_IMPACT | RUNTIME_IMPACT | ANALYST_VALUE_IMPACT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `README.md` | `event-only` explicitly declared legacy/source-class only | Product identity | New operators / repository readers | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Current frontier already states ZFGV is product model and Event-Only is not global ceiling | LOW | Preserve; use as migration reference | Already correct current doctrine | Regression only | None | Prevents ontology drift |
| `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md` | `event-only` explicitly denied as product-wide ceiling | Canonical short governance | Current handoff / operators | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Defines L0-L8 observation model and construct-specific admission | LOW | Preserve | It is the current governance reference | Governance regression | None | Protects claim-safe ZFGV expansion |
| `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md` | Current handoff says `EVENT ⊂ ZFGV` | Successor/operator authority | New operators | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | 2026-09-15 supersession removed stale Event-Only-era current state | LOW | Preserve and fresh-verify live head externally | Historical state was superseded, not rewritten | Governance regression | None | Prevents successor regression |
| `tools/hpfa_data_quality_gate_v1.py` | Purpose remains event-shaped; `DEFAULT_REQUIRED_ANY` includes event id/type, team, period; report exposes phase/sequence and metric permission | Event-surface data-quality producer | Event gate report consumer / downstream policy when explicitly used | CODE | CURRENT_EXECUTABLE | EXECUTABLE_LEGACY_GATE | The producer is valid for ACTION/EVENT surfaces, but its permission vocabulary is broader than an event-only branch if consumed generically | MEDIUM latent | Continue reverse-consumer trace before code change; preserve event validation; scope any future binding by observation family/capability | Event-specific validation is legitimate | Add family-scope regression only if a real non-event consumer binding is proved | Exact current canonical full-spine direct binding not found | Protects event-surface quality without silently suppressing other ZFGV families |
| `hpfa/modules/core/data_quality_gate/src/downstream_policy.py` | Gate status controls `phase_sequence_allowed` and `metric_layer_allowed` for callers | Permission router for the data-quality gate | Explicit callers of Data Quality Gate policy | CODE | CURRENT_EXECUTABLE | EXECUTABLE_LEGACY_GATE | Generic layer names can become a global veto if a future/current caller applies this event gate outside the ACTION/EVENT branch | MEDIUM latent | Reverse-consumer trace; do not redesign until a real cross-family consumer is proved; if bound, scope permissions to the admitted observation branch | Fail-closed propagation is legitimate | Consumer-specific routing regression if bound | Current reference full-spine direct consumer not found | Prevents unrelated missing event fields from silencing valid non-event constructs |
| `hpfa/modules/core/data_quality_gate/src/gate_report_reader.py` | Requires `next_action` fields `phase_sequence_allowed`, `metric_layer_allowed`, `claim_layer_allowed` | Report reader/transport | `downstream_policy.py` | CODE | CURRENT_EXECUTABLE | REVIEW_REQUIRED | Reader transports the legacy permission contract but does not itself create Event-Only semantics | LOW/MEDIUM | Adapt only if a proved consumer requires contract migration | It is transport/validation, not root cause | Contract compatibility tests | Depends on any later gate migration | Keeps downstream permission auditable |
| `hpfa/modules/core/data_quality_gate/contracts/data_quality_gate_output_contract_v1.json` and root mirror | Layer-permission object | Data-quality output contract | Gate report reader / policy | CONTRACT | CURRENT_CONSUMED_SUPPORT | REVIEW_REQUIRED | Contract remains broad in naming, but current governance scopes this gate to ACTION/EVENT consumer branches | LOW/MEDIUM | Keep compatible until reverse-consumer trace proves a cross-family conflict | Do not break event-specific consumer compatibility speculatively | Schema/contract tests | No current canonical direct binding proved | Explicit future capability scope can improve explainability if needed |
| `docs/hpfa_postmatch_analysis_stage_map_v1.tsv` | ZFGV observation-family admission precedes conditional ACTION/EVENT data-quality gate | Product stage map | Governance/planning | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current map explicitly makes event quality a conditional event branch and construct admission capability-specific | LOW | Preserve; regression-check against future global gate drift | Current mapping is the intended ZFGV architecture | Governance regression | No direct runtime truth | Keeps non-event observation families available without weakening event checks |
| `docs/hpfa_postmatch_analysis_dependency_graph_v1.tsv` | Event gate edges are `conditional_event_branch`; construct path runs through observation capability admission | Dependency governance | Planning / downstream design | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current graph stops only the ACTION/EVENT consumer branch when the event gate fails and keeps construct-specific ZFGV paths separate | LOW | Preserve; use as target model for any executable gate migration | Fail-closed dependency semantics remain intact | Governance/graph checks | No direct runtime truth | Makes admission reason visible per football construct |
| `configs/metrics/metric_registry_v1.json` | `required_event_families` remains for current action-based metrics; ZFGV fields are authoritative | Metric registry | Metric definition policy | CONFIG | CURRENT_PRODUCT_AUTHORITY | LEGITIMATE_EVENT_TERM | Current seed metrics are action/event constructs and declare ZFGV layers/capabilities | LOW for current rows | Preserve current rows; do not treat `required_event_families` as universal future construct requirement | Event-family metadata is legitimate for action metrics | Existing registry regressions | Current action metrics unchanged | Preserves action metric semantics |
| `hpfa/modules/core/metric_definition_policy_lite/src/metric_definition_policy.py` | `required_event_families` removed from global required-field set and checked only for `L1_ACTION_OBSERVATION` / `ACTION` constructs | Metric definition admission | Metric registry / provider dictionary chain | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | Confirmed rehabilitation: legitimate L0 aggregate and L8 tracking/video constructs no longer invent fake event-family prerequisites; ACTION/EVENT constructs still fail closed without event-family metadata | LOW | Preserve conditional requirement and its regression tests | Event-family validation remains necessary for ACTION/EVENT constructs | Metric Definition Policy CI must remain green | No new physical claim implied | Opens non-event constructs while preserving exact action semantics |
| `hpfa/modules/core/metric_definition_policy_lite/tests/test_non_event_construct_admission.py` | Explicit L0 aggregate, L8 tracking/video and ACTION negative fixtures | ZFGV falsification/regression | Metric definition policy | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Directly proves non-event constructs can omit event-family metadata while ACTION constructs cannot | LOW | Preserve | This is the behavioral proof of the rehabilitation | Must remain green | None by itself | Protects future ZFGV metric/model expansion |
| `hpfa/modules/core/metric_definition_policy_lite/tests/test_enriched_observation_contract.py` | Enriched observation regression on existing metric fixtures | ZFGV regression tests | Metric definition policy | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Still valuable, but no longer carries the burden of proving non-event admission because dedicated falsification tests now exist | LOW | Preserve alongside dedicated non-event tests | Existing coverage remains useful | Extend only when new capability classes require it | None by itself | Protects enriched observation semantics |
| `hpfa/modules/core/observation_contract_lite/src/observation_contract.py` | Explicit L0-L8 and capability-specific contract; deprecated event-only shadow cannot admit/reject | Canonical observation contract | Metric definition policy / ZFGV adapters | CODE | CURRENT_PRODUCT_AUTHORITY | NEGATIVE_REGRESSION | Correct target model; `event_only_is_product_ceiling=False` | LOW | Preserve; use as migration target | Core migration authority | Strong regression protection | None | Enables richer defensible observation without overclaim |
| `hpfa/modules/core/observation_contract_lite/test_zfgv_event_only_ceiling_removed.py` | Tracking construct carries `event_only_compatible=False` and must PASS ZFGV contract | Anti-regression | Observation contract | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Prevents reintroduction of binary Event-Only veto | LOW | Preserve | Literal Event-Only reference is intentional | Must remain green | None | Protects future tracking/video-capable constructs |
| `hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary.py` | `test_legacy_event_only_metadata_cannot_veto_zfgv` | Anti-regression | Provider dictionary | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Explicitly proves legacy metadata cannot create Event-Only fail-close | LOW | Preserve | Deleting it weakens migration safety | Must remain green | None | Prevents provider metadata suppressing ZFGV constructs |
| `hpfa/modules/core/metric_fusion_engine/policies/eventonly_metric_allowlist_v1.json` | Legacy policy id and allowlist | Scaffold policy | No current product-wide consumer proved in current reference spine | CONFIG | UNBOUND | LEGACY_IDENTIFIER | File says `candidate_not_production_bound`; current source inspection did not prove global admission authority | MEDIUM future risk | Reverse-consumer trace; do not rename/delete until consumer role is known | Historical/scaffold lineage may be useful | Consumer-specific tests if bound | None proven | Avoids future accidental global allowlist authority |
| `hpfa/modules/core/metric_fusion_engine/README.md` | Title=`Event-Only Metric Fusion Engine V1` | Scaffold documentation | Metric fusion maintainers | DOC | UNBOUND | LEGACY_IDENTIFIER | Module status is scaffold/not production bound; source code inspected is relation-specific, not global observation admission | LOW/MEDIUM | Reclassify terminology after consumer audit; no behavior change based on title alone | Preserve scaffold lineage until migration is explicit | Documentation only | None proven | Reduces future design drift once classified |
| `hpfa/modules/core/primary_event_surface_gate_lite/src/primary_event_surface_gate.py` | Selects candidate only when event type + coordinates exist; excludes XLSX aggregate | Event-specific surface selection | Historical/legacy contracts; exact current full-spine direct consumer not found | CODE | CURRENT_EXECUTABLE | REVIEW_REQUIRED | Could be legitimate ACTION/EVENT subpath, but must not become universal surface selector for all ZFGV families | MEDIUM | Reverse-consumer trace. If unbound, keep legacy/event-specific. If bound globally, scope to ACTION/EVENT observation family | Event-specific duplicate/primary-surface review remains legitimate | Existing event gate tests must remain | No direct current full-spine binding proved | Protects event chronology without suppressing aggregate/process/entity surfaces |
| `docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md` | Product identity now uses ZFGV; global Event-Only veto explicitly prohibited | Session continuity prompt | Operators/AI logbook generation | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current prompt records observation families/capabilities and preserves claim guards without Event-Only product identity | LOW | Preserve | Session continuity is now aligned with current ontology | Prompt/governance regression | No direct match runtime | Prevents future operators from reintroducing Event-Only doctrine |
| `docs/brand/HPFA_BRAND_IDENTITY_CORE_LAYER.md` | Brand identity now states `EVENT ⊂ ZFGV`, evidence-first and claim-safe observation model | Brand/product language | Analyst-facing communication | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current external/product identity matches the ZFGV evidence spine | LOW | Preserve | Brand tone and epistemic guards remain valid | Documentation review | No runtime | User-facing product language matches actual architecture |
| `docs/governance/HPFA_PRODUCT_ARCHITECT_EVOLUTION_ENGINE_DIRECTIVE_V1.md` | Product feasibility now uses construct-specific admitted ZFGV capabilities and retains tracking/video truth guards | Active architecture directive | New operators / architecture decisions | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current directive no longer restricts ideas to ACTION/EVENT; it explicitly evaluates multiple observation families | LOW | Preserve and regression-check future edits | Research feasibility and claim-safety checks are legitimate | Governance regression | Indirect architecture impact only | Opens correct research space without lowering evidence ceiling |
| `docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md` | Product objective now starts from admitted football observation surfaces; global Event-Only gate prohibited; tracking/video guard preserved | Direction-control prompt | Operators | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current North Star separates observation-universe scope from claim ceiling | LOW | Preserve | Forbidden physical/tactical claims remain evidence-gated | Prompt regression | No direct runtime | Prevents direction drift while keeping safe claim ceiling |
| `docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md` | Continuity prompt now declares full ZFGV observation families and forbids product-wide Event-Only ontology | Session continuity prompt | New sessions/operators | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Current handoff prevents successor sessions from regenerating the retired global doctrine | LOW | Preserve and fresh-verify head at session start | Continuity/authority discipline remains valid | Prompt regression | No direct runtime | Prevents successor regression |
| `docs/governance/product_architect_evolution_protocol_v1.md` | `long-lived event-only product`, `best event-only platform`, `event-only eligibility gate`, only event-data ideas eligible | Architecture protocol | No current consumer reference found in first pass | DOC | UNBOUND | REVIEW_REQUIRED | Content is globally stale if reactivated, but current consumer not proved | MEDIUM future risk | Mark superseded or migrate after authority/consumer review | Preserve historical decision lineage if no longer active | Documentation only | None proven | Prevents dormant policy becoming future ceiling |

## Confirmed non-current-binding distinction

The exact current `active_match_spine_runner` / `full_spine_runner` inspection in this pass did not contain a direct `data_quality_gate` binding. Repository search found the policy helper itself and its tests, but did not prove a current canonical reference-spine consumer. Therefore:

- `tools/hpfa_data_quality_gate_v1.py` remains an event-shaped current executable;
- its `downstream_policy.py` can enforce broad phase/sequence/metric permissions when explicitly consumed;
- current stage/dependency governance now scopes that behavior to a conditional ACTION/EVENT branch;
- this audit does **not** claim that the current single-match reference full-spine is presently blocked by that gate.

Until reverse-consumer trace proves a broader binding, current reference-run binding remains `UNBOUND / UNKNOWN`, not assumed.

## Confirmed semantic rehabilitation — no Event-Only literal required

A hidden semantic residue was proven and rehabilitated in `metric_definition_policy_lite`:

1. historical policy treated `required_event_families` as globally required;
2. legitimate L0 aggregate and L8 tracking/video construct fixtures falsified that design;
3. current policy requires event-family metadata only when the construct requires `L1_ACTION_OBSERVATION` or `ACTION`;
4. L0 aggregate and L8 tracking/video constructs can omit event-family metadata;
5. ACTION/EVENT constructs still fail closed when event-family metadata is absent;
6. dedicated regression lives in `test_non_event_construct_admission.py`;
7. exact-head Metric Definition Policy workflow is green.

This closes the confirmed metric-definition global Event-Only ceiling while preserving action semantics.

## Governance rehabilitation confirmed in current head

The following previously stale current-consumed governance surfaces are now aligned with ZFGV and must no longer be listed as unresolved Event-Only product identity:

- `docs/hpfa_postmatch_analysis_stage_map_v1.tsv`
- `docs/hpfa_postmatch_analysis_dependency_graph_v1.tsv`
- `docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md`
- `docs/brand/HPFA_BRAND_IDENTITY_CORE_LAYER.md`
- `docs/governance/HPFA_PRODUCT_ARCHITECT_EVOLUTION_ENGINE_DIRECTIVE_V1.md`
- `docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md`
- `docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md`

These are governance/product-language closures, not physical ACTIVE_MATCH evidence.

## Search still required before completeness claim

- repository-wide semantic equivalents beyond current seed searches;
- code branches of form `if not event... reject` and universal `event_id/event_type` assumptions;
- reverse capability tracing for ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME, RELATIONAL, PROCESS, AGGREGATE, EXTERNAL CONTEXT, TRACKING/VIDEO, HPFA-DERIVED INTELLIGENCE;
- reverse-consumer trace for Data Quality Gate, Primary Event Surface Gate and legacy metric-fusion allowlist;
- runtime-pack and generated-policy consumers;
- analyst/user output identity language;
- historical/current/legacy separation for remaining literal occurrences;
- tests that encode `non-event observation → reject` without using Event-Only vocabulary.

Until these are closed:

`MIGRATION_COVERAGE=INCOMPLETE`

## Next safe action

1. Continue reverse-consumer trace for the Data Quality Gate and Primary Event Surface Gate before altering either executable producer.
2. Search semantic equivalents that reject non-event observation without using Event-Only vocabulary.
3. Audit remaining unbound/historical governance such as `product_architect_evolution_protocol_v1.md` before migration or supersession.
4. Do not request ACTIVE_MATCH merely for governance/ledger synchronization; physical evidence is required only if executable current-run behavior changes materially.

Release locks remain:

`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
