# HPFA ZFGV EVENT-ONLY RESIDUAL AUTHORITY LEDGER V1

Status: `AUTHORITY_REHABILITATION_ACTIVE`
Migration coverage: `INCOMPLETE`
Reference product: single-match Postmatch
Canonical ontology: `EVENT ⊂ ZFGV` and `ZFGV != EVENT`

## Current invariant

`CURRENT_VERIFIED_GLOBAL_EVENT_ONLY_AUTHORITY = 0` on the current authority/executable surfaces audited below.

This is **not** yet a repository-wide completeness claim. Historical files, legacy identifiers and anti-regression fixtures may still contain Event-Only vocabulary. Their existence is acceptable only when they cannot authorize, veto, route or narrow current ZFGV capability.

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

## Non-negotiable migration rule

No current HPFA component may use Event-Only as:

- the observation universe;
- a product-wide eligibility gate;
- a default admission veto;
- a global routing prerequisite;
- a metric/model compatibility ceiling;
- an analyst-output identity;
- a reason to reject valid ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME/QUALIFIER, RELATIONAL, PROCESS/PARTICIPATION, AGGREGATE/TABULAR, EXTERNAL CONTEXT, TRACKING/VIDEO or HPFA-DERIVED INTELLIGENCE.

ACTION/EVENT-specific producers may still require ACTION/EVENT evidence when the construct itself requires it.

## Current verified ledger

| FILE | OCCURRENCE | CURRENT_ROLE | CURRENT_CONSUMER | EXECUTABLE_OR_DOC | AUTHORITY_STATUS | CLASSIFICATION | WHY | ZFGV_RISK | REQUIRED_ACTION | DO_NOT_CHANGE_REASON | TEST_IMPACT | RUNTIME_IMPACT | ANALYST_VALUE_IMPACT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `README.md` | ZFGV product identity | Product identity | Operators/readers | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Current frontier declares Event as one observation family, not whole universe | LOW | Preserve | Correct current doctrine | Static regression | None | Prevents ontology drift |
| `docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md` | L0-L8 ZFGV + construct-specific admission | Canonical governance | Operators/current handoff | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Current product admission model is capability-specific | LOW | Preserve | Canonical current rule | Static regression | None | Keeps product evidence-first |
| `docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md` | `EVENT ⊂ ZFGV` | Current handoff | Successor/operator | DOC | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Stale Event-Only handoff was superseded | LOW | Preserve | Prevents successor regression | Static regression | None | Correct continuation state |
| `configs/metrics/metric_registry_v1.json` | `observation_model=ZFGV_V1`; action rows keep action-specific event families | Metric registry | Metric policy/provider dictionary | CONFIG | CURRENT_PRODUCT_AUTHORITY | LEGITIMATE_EVENT_TERM | Event-family metadata exists only on current action constructs; registry no longer carries `event_only_compatible` | LOW | Preserve action-specific metadata | ACTION metrics legitimately need action-family semantics | Registry regression | Current action metrics unchanged | Non-event future metrics are not globally blocked |
| `hpfa/modules/core/metric_definition_policy_lite/src/metric_definition_policy.py` | Event-family requirement conditional on ACTION/L1 | Metric definition admission | Metric registry/provider chain | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | Confirmed rehabilitation removed fake event-family prerequisite from L0 aggregate and L8 tracking/video constructs | LOW | Preserve | ACTION constructs still need event-family semantics | Dedicated non-event + ACTION regressions | No physical runtime claim implied | Opens richer metric/model families safely |
| `hpfa/modules/core/metric_definition_policy_lite/tests/test_non_event_construct_admission.py` | L0/L8 positive + ACTION negative fixtures | Regression | Metric policy | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Proves non-event constructs do not need fake event family | LOW | Preserve | Direct behavioral proof | Must stay green | None | Protects future capability expansion |
| `hpfa/modules/core/observation_contract_lite/src/observation_contract.py` | Capability-specific L0-L8 admission | Canonical observation contract | ZFGV construct admission | CODE | CURRENT_PRODUCT_AUTHORITY | PRESERVE_AS_GUARD | Binary Event-Only compatibility cannot admit/reject | LOW | Preserve | Core ZFGV authority | Must stay green | None | Correct evidence ceiling per football construct |
| `hpfa/modules/core/provider_metric_dictionary_lite/src/_provider_metric_dictionary_impl_v7.py` | Operational/fingerprint fields no longer include Event-Only compatibility | Provider metric semantics | Provider dictionary consumers | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | Provider semantics no longer inherit old binary veto | LOW | Preserve | Correct migration target | Provider regression | None | Provider metadata cannot suppress valid ZFGV capability |
| `hpfa/modules/core/provider_metric_dictionary_lite/tests/test_provider_metric_dictionary.py` | legacy metadata cannot veto ZFGV | Anti-regression | Provider dictionary | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Intentionally protects against old metadata returning as authority | LOW | Preserve | Literal legacy key is deliberate test input | Must stay green | None | Prevents regression |
| `hpfa/modules/core/evidence_lens_matrix_lite/src/evidence_lens_matrix.py` | Construct-specific required/optional lenses | C4 evidence completeness | Intelligence chain | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | Aggregate or other ZFGV constructs no longer require fake action lens; legacy graphs retain compatibility | LOW | Preserve | Required evidence remains construct-specific | Aggregate/action regressions | C4 behavior scoped by construct | Removes action-centric completeness ceiling |
| `hpfa/modules/core/active_match_spine_runner/src/rich_multiformat_analysis_lane.py` | XLSX aggregate C01 construct; action context optional | Multiformat intelligence | Current full-spine/C4 | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | Aggregate progression/terminal evidence can produce candidate pack without Event identity; same-row/same-scope and dependency locks remain | LOW | Preserve | Aggregate != action identity; multiformat != independence | Rich-lane regressions | Current full-spine engineering path | Makes aggregate football information usable |
| `hpfa/modules/core/xlsx_entity_metric_row_projection_lite/src/xlsx_entity_metric_row_projection.py` | XLSX entity/metric row projection | ENTITY/ACTOR + AGGREGATE/TABULAR producer | `rich_multiformat_analysis_lane` | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | XLSX entity and metric candidates travel without Event identity; output explicitly keeps `row_projection_is_canonical_event=false` and claims closed | LOW | Preserve | Aggregate/entity observation must not be fabricated into action identity | Projection/rich-lane regressions | Current rich lane only | Lets analyst use tabular player/team evidence safely |
| `hpfa/modules/core/aggregate_definition_alignment_lite/src/aggregate_definition_alignment.py` | Separate action and aggregate candidate surfaces | Aggregate semantic alignment | Rich multiformat analysis | CODE | CURRENT_EXECUTABLE | PRESERVE_AS_GUARD | XLSX aggregate candidates are aligned as aggregate evidence, not independent Event confirmation | LOW | Preserve | AGGREGATE != ACTION and reflection dependency must remain explicit | Aggregate alignment regressions | Current rich lane | Prevents double counting while retaining useful aggregate evidence |
| `hpfa/modules/core/match_local_identity_candidates_lite/src/match_local_identity_candidates.py` | CSV/XML match-local identity candidates | ACTION/EVENT identity subpath | Event/action reconstruction | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | CSV/XML lineage restriction is scoped to the event/action identity construct; XLSX entity candidates have a separate current rich-multiformat route | LOW | Preserve scoped contract | Event identity requires event-capable lineage; it is not generic ENTITY admission authority | Identity + rich-lane regressions | Event/action identity subpath | Keeps action attribution strict without suppressing tabular entity evidence |
| `hpfa/modules/core/time_scale_router_lite/src/time_scale_router.py` | Admitted time-scale routing from event windows | ACTION/EVENT episode temporal subpath | `episode_lane_runner` | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | Direct caller is the action-derived episode lane; partial-order and same-time guards prevent row order becoming total temporal truth | LOW | Preserve scoped contract | Episode temporal ordering legitimately depends on admitted action windows | Episode/time regressions | Episode lane only | Gives defensible sequence timing without inventing chronology |
| `hpfa/modules/core/spatial_transition_candidate_lite/src/spatial_transition_candidate.py` | Visible spatial transition candidate | ACTION transition spatial construct | `orphan_capability_sidecars` | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | Producer consumes admitted trackable action traces because the construct is an action transition; claim ceiling is visible spatial transition candidate only | LOW | Preserve scoped contract | Action-transition space is not generic SPATIAL ingress and must not be promoted to tracking truth | Spatial sidecar regressions | Current sidecar only | Adds where/how progression evidence while retaining spatial claim ceiling |
| `tools/hpfa_data_quality_gate_v1.py` | Event id/type/team/period quality checks | ACTION/EVENT data-quality producer | `phase_sequence_composite` | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | Verified consumer is event-shaped phase/sequence branch; no non-event consumer proven | LOW/MEDIUM latent naming risk | Preserve event-specific scope; never promote to global ZFGV gate | Event phase/sequence genuinely needs event-shaped input | Existing gate tests | Event branch only | Keeps unsafe event sequence work closed without suppressing other families |
| `hpfa/modules/core/data_quality_gate/src/downstream_policy.py` | Event-gate permissions | Event branch router | `phase_sequence_composite` + tests | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | Current executable consumer is event-specific; generic field names are not proven global authority | LOW/MEDIUM latent | Preserve until real cross-family consumer exists; forbid global reuse | Fail-closed event routing is legitimate | Consumer regression | No canonical global binding proven | Avoids unnecessary redesign while protecting ZFGV |
| `hpfa/modules/core/primary_event_surface_gate_lite/src/primary_event_surface_gate.py` | Selects event-surface candidate | Event-specific surface selection | Event review/metric/transition support | CODE | CURRENT_EXECUTABLE | LEGITIMATE_EVENT_TERM | Does not select whole observation universe; aggregate/physical/report surfaces remain separate | LOW | Preserve | Event chronology needs event-specific surface review | Event-gate regression | No global ZFGV authority | Protects event subpath only |
| `hpfa/modules/core/metric_fusion_engine/README.md` | ZFGV Metric Fusion scaffold | Fusion documentation | Future maintainers | DOC | UNBOUND | PRESERVE_AS_GUARD | Rehabilitated: construct-specific inputs; global event allowlist explicitly forbidden | LOW | Preserve | Current scaffold is not production bound | Static regression | None | Prevents future fusion from narrowing product back to Event-Only |
| `hpfa/modules/core/metric_fusion_engine/policies/eventonly_metric_allowlist_v1.json` | Historical policy identifier | Legacy relation scaffold | No current product-wide consumer | CONFIG | LEGACY_COMPATIBILITY | LEGACY_IDENTIFIER | Rehabilitated status explicitly sets product-wide admission authority, construct eligibility authority and non-event veto to false | LOW | Keep unbound for lineage or delete only in a dedicated compatibility migration | Filename/id may be needed for historical compatibility | Static authority regression | None | Prevents accidental reuse as global allowlist |
| `docs/governance/product_architect_evolution_protocol_v1.md` | Research/product eligibility | Architecture governance | Architecture reviews | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Rehabilitated from Event-Only eligibility to construct-specific ZFGV capability feasibility | LOW | Preserve | Correct current research filter | Static authority regression | Indirect | Opens aggregate/process/spatial/tracking research correctly |
| `docs/governance/HPFA_PRODUCT_ARCHITECT_EVOLUTION_ENGINE_DIRECTIVE_V1.md` | ZFGV feasibility | Architecture directive | Operators | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | No longer limits research to ACTION/EVENT | LOW | Preserve | Claim ceilings retained | Static authority regression | Indirect | Expands defensible research space |
| `docs/prompts/HPFA_PROJECT_LOGBOOK_PROMPT.md` | ZFGV continuity | Session prompt | Operators/AI | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Product identity no longer Event-Only | LOW | Preserve | Continuity aligned | Static regression | None | Prevents session-level doctrine regression |
| `docs/brand/HPFA_BRAND_IDENTITY_CORE_LAYER.md` | ZFGV brand/product identity | Brand governance | Analyst/product communication | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | External identity reflects actual observation universe | LOW | Preserve | Claim-safe tone remains | Static regression | None | Correctly explains HPFA |
| `docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md` | ZFGV North Star | Direction control | Operators | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Global Event-Only gate prohibited; tracking/video truth locks retained | LOW | Preserve | Correct product direction | Static regression | None | Prevents strategic regression |
| `docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md` | ZFGV observation families | Session handoff | New sessions | DOC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Successor cannot regenerate old ontology | LOW | Preserve | Current continuity rule | Static regression | None | Protects future work |
| `docs/contracts/action_value_cost_fusion_lite_v1.md` | Construct-specific action/physical/spatial/aggregate requirements | Fusion spec | Future implementation | DOC/SPEC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Rehabilitated: only action component may require ACTION/EVENT; no global event surface veto | LOW | Preserve | Action-specific semantics remain valid | Static regression | No runtime implementation claim | Prevents future fusion bottleneck |
| `docs/contracts/reasoning_grammar_spine_lite_v1.md` | ZFGV reasoning spine | Reasoning spec | Future/current reasoning design | DOC/SPEC | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Rehabilitated from `event -> ...` universe to observation/relation/process/counterevidence spine | LOW | Preserve | Event candidates remain allowed | Static regression | No runtime implementation claim | Broadens reasoning without lowering claim safety |
| `docs/HPFA_GITHUB_PROGRESSION_ENGINE_CONTRACTS_PLAN_V1.md` | ZFGV progression plan | PLAN_ONLY | Future progression work | DOC/PLAN | CURRENT_CONSUMED_SUPPORT | PRESERVE_AS_GUARD | Rehabilitated: progression is a construct requiring admitted capabilities, not Event-Only coordinates | LOW | Preserve | Tracking/geometry guards remain | Static regression | No implementation claim | Allows valid spatial/aggregate progression evidence |
| `hpfa/modules/core/capability_closure_guard_lite/tests/test_zfgv_no_global_event_only_authority.py` | Global authority regression | Closure guard | CI | TEST | CURRENT_CONSUMED_SUPPORT | NEGATIVE_REGRESSION | Fails if current authority reintroduces positive Event-Only product/eligibility language; also locks registry and legacy allowlist non-authority state | LOW | Preserve and extend when new current authority surfaces appear | Historical/negative vocabulary is not blindly banned | Closure Guard CI | None | Stops ontology regression before it reaches analyst output |

## Historical / literal residue rule

Literal Event-Only vocabulary may remain only in one of these roles:

1. historical records/logbooks/donor scans;
2. legacy filenames/IDs retained for compatibility;
3. negative regression tests proving the retired veto cannot return;
4. descriptions of legitimate ACTION/EVENT-specific subpaths.

None of these may become current product admission authority.

## Current reverse-capability result

Audited paths currently support the following without a global Event-Only ceiling:

- ACTION/EVENT: event-specific quality/identity/sequence subpaths remain valid;
- ENTITY/ACTOR: XLSX entity candidates travel through the current rich-multiformat lane without being forced into Event identity; event-specific match-local identity remains scoped;
- TEMPORAL: current generic admission contract is capability-specific, while the inspected event-window/time-scale path is an action-derived episode subpath with partial-order guards;
- SPATIAL: inspected spatial-transition producer is construct-scoped to admitted action transitions and does not act as universal SPATIAL ingress or tracking truth;
- OUTCOME/QUALIFIER: visible consequence candidates without causality;
- RELATIONAL: relation candidates without tactical truth;
- PROCESS/PARTICIPATION: provider/process context without coach-intention promotion;
- AGGREGATE/TABULAR: XLSX aggregate/entity support travels through the rich lane without action identity or independence fabrication;
- EXTERNAL CONTEXT: admitted only by source/claim contract;
- TRACKING/VIDEO: permitted as its own family when actually available and required;
- HPFA-DERIVED INTELLIGENCE: derived outputs remain evidence-dependent, not new facts.

First reverse-capability tranche status: `AGGREGATE/TABULAR + ENTITY/ACTOR + TEMPORAL + SPATIAL = SCOPED/CLEAN` on the exact audited frontier. This does not close repository-wide migration coverage.

## Remaining completeness work

Before `MIGRATION_COVERAGE=COMPLETE`, still audit:

- reverse-consumer traces for RELATIONAL, PROCESS/PARTICIPATION, EXTERNAL CONTEXT, TRACKING/VIDEO and HPFA-DERIVED INTELLIGENCE;
- remaining default-branch lexical hits against exact current frontier;
- dormant/current ambiguity in old PLAN/SPEC docs not yet classified;
- semantic equivalents with no Event-Only literal, especially universal `event_id/event_type` assumptions in generic components;
- any future consumer of broad event-gate permission fields;
- generated/config/runtime-pack surfaces that could be mistaken for current authority.

Until then:

`MIGRATION_COVERAGE=INCOMPLETE`

Release locks:

`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`
