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

## Current verified ledger — first authority pass

| FILE | OCCURRENCE | CURRENT_ROLE | CURRENT_CONSUMER | EXECUTABLE_OR_DOC | AUTHORITY_STATUS | CLASSIFICATION | WHY | ZFGV_RISK | REQUIRED_ACTION | DO_NOT_CHANGE_REASON | TEST_IMPACT | RUNTIME_IMPACT | ANALYST_VALUE_IMPACT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `README.md` | `event-only` explicitly declared legacy/source-class only | Product identity | New operators / repository readers | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Current frontier already states ZFGV is product model and Event-Only is not global ceiling | LOW | Preserve; use as migration reference | Already correct current doctrine | Regression only | None | Prevents ontology drift |
| `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md` | `event-only` explicitly denied as product-wide ceiling | Canonical short governance | Current handoff / operators | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Defines L0-L8 observation model and construct-specific admission | LOW | Preserve | It is the current governance reference | Governance regression | None | Protects claim-safe ZFGV expansion |
| `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md` | Current handoff now says `EVENT ⊂ ZFGV` | Successor/operator authority | New operators | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | 2026-09-15 supersession removed stale Event-Only-era current state | LOW | Preserve and fresh-verify live head externally | Historical state was superseded, not rewritten | Governance regression | None | Prevents successor regression |
| `tools/hpfa_data_quality_gate_v1.py` | Purpose=`event-only ACTIVE_MATCH surfaces`; global `DEFAULT_REQUIRED_ANY` includes event id/type, team, period; PASS/DEGRADED/FAIL_CLOSED controls downstream permission | Data-quality producer | Gate report consumer + downstream policy; stage/dependency governance | CODE | CURRENT_EXECUTABLE | EXECUTABLE_LEGACY_GATE | Valid ZFGV surfaces may not have universal event identity/type fields | HIGH | Rehabilitate existing producer into observation-family / declared-capability quality admission; keep ACTION/EVENT validation scoped to ACTION/EVENT | Event-specific validation remains useful | New positive/negative family-specific gate tests | Current canonical full-spine binding not found in exact runner; runtime binding must be proved before ACTIVE_MATCH claim | Opens non-event observation families without weakening claim gates |
| `hpfa/modules/core/data_quality_gate/src/downstream_policy.py` | Global gate status controls `phase_sequence_allowed` and `metric_layer_allowed` | Permission router | Any caller of Data Quality Gate policy | CODE | CURRENT_EXECUTABLE | EXECUTABLE_LEGACY_GATE | One event-shaped gate can globally stop phase/sequence or metric branches | HIGH | Replace global event-surface permission semantics with observation/capability-scoped downstream permissions, preserving fail-closed behavior | Fail-closed propagation is legitimate and must remain | Contract + routing regression | Current reference full-spine direct consumer not found; binding status still to be proved | Prevents valid ZFGV capabilities being silenced by unrelated missing event fields |
| `hpfa/modules/core/data_quality_gate/src/gate_report_reader.py` | Requires global `next_action` fields `phase_sequence_allowed`, `metric_layer_allowed`, `claim_layer_allowed` | Report reader/transport | `downstream_policy.py` | CODE | CURRENT_EXECUTABLE | REVIEW_REQUIRED | Reader itself does not create Event-Only semantics, but its contract transports the global permission model | MEDIUM | Adapt only if output contract changes; do not rewrite independently | It is a transport/validation layer, not root cause | Contract compatibility tests | Depends on gate redesign | Keeps downstream permission auditable |
| `hpfa/modules/core/data_quality_gate/contracts/data_quality_gate_output_contract_v1.json` and root mirror | Global layer permission object | Data-quality output contract | Gate report reader / policy | CONTRACT | CURRENT_CONSUMED_SUPPORT | REVIEW_REQUIRED | Contract may encode global rather than construct/capability-specific routing | MEDIUM | Migrate contract with producer/reader together if consumer trace confirms | Do not break compatibility before migration path exists | Schema/contract tests | Conditional | Explicit capability-scoped routing improves explainability |
| `docs/hpfa_postmatch_analysis_stage_map_v1.tsv` | `selected_event_surface`, `raw event surface`, `canonical_events.jsonl`; Data Quality Gate marked execution-proven and mandatory path | Product stage map | Governance/planning | DOC | CURRENT_CONSUMED_SUPPORT | ACTIVE_GOVERNANCE_STALE | Stage map defines OBSERVATION as event-shaped pipeline despite current ZFGV reference product | HIGH | Rehabilitate to SURFACE→OBSERVATION family admission; keep ACTION/EVENT subpath as one branch | Historical event stages may remain as lineage annotations | Governance consistency tests if any | No direct runtime truth | Prevents architecture planning from reintroducing Event-Only |
| `docs/hpfa_postmatch_analysis_dependency_graph_v1.tsv` | Data Quality Gate→consumer→phase/sequence/metric edges marked mandatory | Dependency governance | Planning / downstream design | DOC | CURRENT_CONSUMED_SUPPORT | ACTIVE_GOVERNANCE_STALE | Makes one global gate authoritative for multiple capability branches | HIGH | Replace with capability-specific dependency edges and explicit event-only subpath where legitimate | Preserve fail-closed dependency semantics | Governance/graph checks | No direct runtime truth until executable consumer binding exists | Makes admission reason visible per football construct |
| `configs/metrics/metric_registry_v1.json` | `required_event_families` remains for current action-based metrics; ZFGV fields are authoritative | Metric registry | Metric definition policy | CONFIG | CURRENT_PRODUCT_AUTHORITY | LEGITIMATE_EVENT_TERM | Current seed metrics are action/event constructs and declare ZFGV layers/capabilities | LOW for current rows | Preserve current rows; do not treat `required_event_families` as universal future construct requirement | Event-family metadata is legitimate for action metrics | Add non-event construct regression separately | Current action metrics unchanged | Preserves action metric semantics |
| `hpfa/modules/core/metric_definition_policy_lite/src/metric_definition_policy.py` | `REQUIRED_METRIC_FIELDS` still globally includes non-empty `required_event_families` | Metric definition admission | Metric registry / provider dictionary chain | CODE | CURRENT_EXECUTABLE | REVIEW_REQUIRED | Hidden semantic residue candidate: a pure L0 aggregate or L8 tracking/video construct may fail before observation-contract admission if it has no event family | HIGH if confirmed | First add a regression with a legitimate non-event construct and no fake event family; then make event-family requirement construct-specific if test proves failure | Do not remove event-family validation from ACTION/EVENT constructs | HIGH: new L0/L8/non-event tests + existing action regressions | Metric/model admission behavior may change; ACTIVE_MATCH only if current runtime-bound construct path changes | Removes fake event prerequisites while keeping exact claim ceiling |
| `hpfa/modules/core/metric_definition_policy_lite/tests/test_enriched_observation_contract.py` | L8 test mutates an existing action metric row, so legacy `required_event_families` remains populated | ZFGV regression tests | Metric definition policy | TEST | CURRENT_CONSUMED_SUPPORT | REVIEW_REQUIRED | Current tests prove `event_only_compatible` cannot veto rich constructs but do not prove a non-event construct can omit event-family metadata | MEDIUM | Add explicit aggregate-only and tracking/video-only construct fixtures with no event-family requirement | Existing tests are valuable and must remain | Extend, do not delete | None by itself | Proves actual ZFGV capability admission rather than field survival |
| `hpfa/modules/core/observation_contract_lite/src/observation_contract.py` | Explicit L0-L8 and capability-specific contract; deprecated event-only shadow cannot admit/reject | Canonical observation contract | Metric definition policy / ZFGV adapters | CODE | CURRENT_PRODUCT_AUTHORITY | NEGATIVE_REGRESSION | Correct target model; `event_only_is_product_ceiling=False` | LOW | Preserve; use as migration target | Core migration authority | Strong regression protection | None | Enables richer defensible observation without overclaim |
| `hpfa/modules/core/observation_contract_lite/test_zfgv_event_only_ceiling_removed.py` | Tracking construct carries `event_only_compatible=False` and must PASS ZFGV contract | Anti-regression | Observation contract | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Prevents reintroduction of binary Event-Only veto | LOW | Preserve | Literal Event-Only reference is intentional | Must remain green | None | Protects future tracking/video-capable constructs |
| `hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary.py` | `test_legacy_event_only_metadata_cannot_veto_zfgv` | Anti-regression | Provider dictionary | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Explicitly proves legacy metadata cannot create Event-Only fail-close | LOW | Preserve | Deleting it weakens migration safety | Must remain green | None | Prevents provider metadata suppressing ZFGV constructs |
| `hpfa/modules/core/metric_fusion_engine/policies/eventonly_metric_allowlist_v1.json` | Legacy policy id and allowlist | Scaffold policy | No current product-wide consumer proved in current reference spine | CONFIG | UNBOUND | LEGACY_IDENTIFIER | File says `candidate_not_production_bound`; current source inspection did not prove global admission authority | MEDIUM future risk | Reverse-consumer trace; do not rename/delete until consumer role is known | Historical/scaffold lineage may be useful | Consumer-specific tests if bound | None proven | Avoids future accidental global allowlist authority |
| `hpfa/modules/core/metric_fusion_engine/README.md` | Title=`Event-Only Metric Fusion Engine V1` | Scaffold documentation | Metric fusion maintainers | DOC | UNBOUND | LEGACY_IDENTIFIER | Module status is scaffold/not production bound; source code inspected is relation-specific, not global observation admission | LOW/MEDIUM | Reclassify terminology after consumer audit; no behavior change based on title alone | Preserve scaffold lineage until migration is explicit | Documentation only | None proven | Reduces future design drift once classified |
| `hpfa/modules/core/primary_event_surface_gate_lite/src/primary_event_surface_gate.py` | Selects candidate only when event type + coordinates exist; excludes XLSX aggregate | Event-specific surface selection | Historical/legacy contracts; exact current full-spine direct consumer not found | CODE | CURRENT_EXECUTABLE | REVIEW_REQUIRED | Could be legitimate ACTION/EVENT subpath, but must not become universal surface selector for all ZFGV families | MEDIUM | Reverse-consumer trace. If unbound, keep legacy/event-specific. If bound globally, scope to ACTION/EVENT observation family | Event-specific duplicate/primary-surface review remains legitimate | Existing event gate tests must remain | No direct current full-spine binding proved | Protects event chronology without suppressing aggregate/process/entity surfaces |
| `docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md` | `HPFA is an event-only... Football Intelligence Platform` | Session continuity prompt | Operators/AI logbook generation | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | GLOBAL_ERROR | Recreates obsolete product identity every session | HIGH governance | Replace product identity with ZFGV; preserve claim guards and historical example names as lineage where needed | Do not erase historical filenames/examples blindly | Prompt/governance regression | No direct match runtime | Prevents future operators from reintroducing Event-Only doctrine |
| `docs/brand/HPFA_BRAND_IDENTITY_CORE_LAYER.md` | Multiple global brand statements: event-only discipline, event data→tactical intelligence, event-only evidence→... | Brand/product language | Analyst-facing communication | DOC | CURRENT_CONSUMED_SUPPORT | GLOBAL_ERROR | Current brand identity contradicts current product ontology | MEDIUM/HIGH | Rehabilitate brand language to observation/evidence spine while preserving epistemic guards | Brand tone/claim safety remains valid | Documentation review | No runtime | External/user-facing product identity matches actual architecture |
| `docs/governance/HPFA_PRODUCT_ARCHITECT_EVOLUTION_ENGINE_DIRECTIVE_V1.md` | `Yalnızca event data ile uygulanabilecek fikirler`; Football Scientist=`event-only geçerlilik`; tracking-dependent truth framed as event-only eligibility | Active architecture directive referenced by New-Page prompt | New operators / architecture decisions | DOC | CURRENT_CONSUMED_SUPPORT | ACTIVE_GOVERNANCE_STALE | Can reject valid L0/L2-L7/L8 constructs before capability-specific admission | HIGH | Replace global event eligibility with construct-specific observation capability feasibility; preserve tracking/video truth guards | Research feasibility and claim-safety checks are legitimate | Governance regression | Indirect future architecture impact | Opens correct research space without lowering evidence ceiling |
| `docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md` | Product objective=`ham event yüzeylerinden...`; separate `Event-only veriden tracking truth` guard | Direction-control prompt | Operators | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | REVIEW_REQUIRED | Product-universe wording is stale, but tracking overclaim guard is epistemically valid | MEDIUM | Split classification by occurrence: migrate product identity, preserve/generalize guard to non-tracking admitted observation | Do not weaken forbidden physical/tactical claims | Prompt regression | No direct runtime | Prevents direction drift while keeping safe claim ceiling |
| `docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md` | Product objective=`ham event yüzeylerinden...`; event-only guard; references stale Product Architect directive | Session continuity prompt | New sessions/operators | DOC/PROMPT | CURRENT_CONSUMED_SUPPORT | ACTIVE_GOVERNANCE_STALE | Can regenerate obsolete doctrine and stale architecture reading order | HIGH | Rehabilitate product objective and referenced governance set; preserve non-tracking claim guards | Continuity/authority discipline remains valid | Prompt regression | No direct runtime | Prevents successor regression |
| `docs/governance/product_architect_evolution_protocol_v1.md` | `long-lived event-only product`, `best event-only platform`, `event-only eligibility gate`, only event-data ideas eligible | Architecture protocol | No current consumer reference found in first pass | DOC | UNBOUND | REVIEW_REQUIRED | Content is globally stale if reactivated, but current consumer not proved | MEDIUM future risk | Mark superseded or migrate after authority/consumer review | Preserve historical decision lineage if no longer active | Documentation only | None proven | Prevents dormant policy becoming future ceiling |

## Confirmed non-current-binding distinction

The exact current `active_match_spine_runner` and exact-head wrapper inspected in this pass did not contain direct `data_quality_gate` or `primary_event_surface` bindings. Therefore:

- `tools/hpfa_data_quality_gate_v1.py` is a current executable artifact with an architectural ceiling risk;
- its own `downstream_policy.py` makes the ceiling behavior real when that gate is consumed;
- but this audit does **not** yet claim that the current single-match reference full-spine is presently blocked by that gate.

Until reverse-consumer trace proves otherwise, current reference-run binding remains `UNBOUND / UNKNOWN`, not assumed.

## Newly discovered semantic residue — no Event-Only literal required

`metric_definition_policy_lite` currently includes `required_event_families` in the globally required metric field set. The policy validates required fields before/alongside the ZFGV observation contract. Existing enriched-observation tests mutate seed action metrics, so they retain a populated event-family field even when testing L8 tracking/video semantics.

Required next falsification test:

1. construct with `L0_AGGREGATE_SURFACE` + `AGGREGATE` capability and no ACTION/EVENT requirement;
2. construct with `L8_TRACKING_VIDEO_PHYSICAL_OFF_BALL_STATE` + tracking/video capability and no ACTION/EVENT requirement;
3. neither construct may be forced to invent `required_event_families` merely to satisfy a global field contract;
4. ACTION/EVENT constructs must continue to validate their event-family requirements.

If current policy rejects the legitimate non-event constructs solely because `required_event_families` is empty/missing, reclassify from `REVIEW_REQUIRED` to `EXECUTABLE_LEGACY_GATE` and rehabilitate the field requirement conditionally.

## Search still required before completeness claim

- repository-wide semantic equivalents beyond current seed searches;
- code branches of form `if not event... reject` and universal `event_id/event_type` assumptions;
- reverse capability tracing for ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME, RELATIONAL, PROCESS, AGGREGATE, EXTERNAL CONTEXT, TRACKING/VIDEO, HPFA-DERIVED INTELLIGENCE;
- runtime-pack and generated-policy consumers;
- analyst/user output identity language;
- historical/current/legacy separation for remaining literal occurrences;
- tests that encode `non-event observation → reject` without using Event-Only vocabulary.

Until these are closed:

`MIGRATION_COVERAGE=INCOMPLETE`

## Next safe action

1. Add falsification tests for non-event metric constructs at the existing metric-definition policy boundary.
2. Continue reverse-consumer trace for the Data Quality Gate and Primary Event Surface Gate.
3. Rehabilitate active governance prompts that are already proven current-consumed stale.
4. Do not change `hpfa_data_quality_gate_v1.py` behavior until its current consumer/runtime binding is fully mapped.

Release locks remain:

`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
