# P02 Progression Pool Adapter Boundary V1

Status: contract-only. No runtime implementation in this file.

## Purpose

Define the smallest legal adapter that projects current HPFA outputs into P02 Progression Pool Items without creating a parallel engine, new occurrence truth, new sequence truth, or new reasoning authority.

The adapter is a projection layer only.

## Required upstream artifacts

Primary:
- episode_feature_vector_lite_v1
- analyst_episode_locator_lite_v1
- context_action_semantics_rebind_lite_v1

Conditional:
- temporal_episode_signature_lite_v1
- trackable_action_trace_candidates_lite_v1
- trackable_action_consequence_candidates_lite_v1
- rich_multiformat_analysis_lattice_v1

Aggregate-only context:
- admitted XLSX aggregate projections

## Prohibited upstream promotion

The adapter must not:
- convert aggregate metrics into occurrence identity;
- force same-timestamp rows into total order;
- infer possession truth from row continuity;
- infer physical trajectory from coordinates;
- infer tactical intent, dominance, control, pressure geometry or causality;
- treat missing visible follow-up as failure;
- create independent support votes when the same dependency root appears across multiple projections.

## Minimum adapter stages

1. LOAD_DECLARED_UPSTREAM
2. VALIDATE_REQUIRED_IDENTITIES
3. NORMALIZE_TO_FINDING_ATOMS
4. PRESERVE_DEPENDENCY_ROOTS
5. ROUTE_TO_P02
6. BUILD_TYPED_STATIONS
7. BUILD_PROCESS_SIGNATURE_CANDIDATES
8. RECONCILE_ORIGINAL_VS_RECONSTRUCTED
9. EMIT_COMPARISON_CANDIDATES
10. STOP_BEFORE_FUSION_AUTHORITY

## Required output families

- finding_atoms
- p02_pool_items
- progression_process_signatures
- transformation_ledger
- reconstruction_audit
- comparison_candidates
- maintenance_gap_candidates

No Safe Finding.
No claim text.
No analyst report text.

## Process signature evaluability rules

Duration:
- requires admitted positive duration candidate;
- zero duration => NOT_APPLICABLE;
- unresolved duration => NOT_EVALUATED.

Route distance:
- requires admitted normalized coordinates and sufficient order;
- unresolved order => route metric NOT_EVALUATED;
- output name must remain Visible Path Length Proxy.

Directness:
- requires visible path proxy + non-zero path length;
- directness is descriptive, not quality.

Station counts:
- station_type + registry version mandatory;
- reflection labels collapse before ACTION_STATION count.

Horizontal→Vertical:
- lateral movement + visible eligible follow-up required;
- no visible follow-up => UNRESOLVED.

Advanced access:
- canonical zone/access registry required.

Terminal conversion:
- process-local visible terminal state required;
- XLSX aggregate shot counts cannot resolve episode conversion.

Opponent intervention:
- explicit visible opponent relation required;
- absence of visible opponent response does not prove no response.

## Comparison candidate schema

Required:
- comparison_question_id
- comparison_unit
- exact_dimensions
- coarsened_dimensions
- test_dimensions
- forbidden_leakage_dimensions
- reference_context
- candidate_context
- reference_outcome
- candidate_outcome
- provenance_root
- dependency_group
- independence_group
- reference_provenance_root
- reference_dependency_group
- reference_independence_group

P02 may emit the candidate but does not classify contradiction.
multi_signal_evidence_fusion_lite_v1 remains authority.

## Transformation ledger reconciliation

For each transformation:

INPUT =
PRESERVED
+ INTENTIONALLY_COLLAPSED
+ EXPLICITLY_EXCLUDED
+ LOST

Derived enrichment is reported separately.

Required:
- invented_semantics_count == 0 for admitted output
- every derived field names transformation_id
- every collapsed atom names collapse reason
- every lost atom names loss reason

## Minimum fixture families

F01 minimal progression episode with duration + zones, no coordinates
Expected:
- station metrics where eligible
- no path/directness metric
- no invented coordinate inference

F02 ordered coordinate-bearing progression episode
Expected:
- visible path proxy evaluable
- directness proxy evaluable
- coordinate_is_tracking=false

F03 same-time ambiguous progression episode
Expected:
- same_time_unordered preserved
- no forced path metric

F04 progression with no visible terminal follow-up
Expected:
- terminal outcome UNRESOLVED
- no failure inference

F05 comparable opposite branch with dependency-separated lineage
Expected:
- comparison candidate emitted
- fusion may later admit COUNTEREVIDENCE

F06 comparable opposite branch sharing dependency root
Expected:
- comparison candidate emitted
- fusion later yields DEPENDENCY_CHALLENGE

F07 aggregate-only progression context
Expected:
- contextual Pool Item allowed
- zero occurrence identities created

F08 grid-sensitive route
Expected:
- GRID_SENSITIVE diagnostic
- finding downgrade/review, not silent promotion

F09 reconstruction atom loss
Expected:
- lost atom surfaced
- reconciliation fails review boundary

F10 invented semantic promotion
Expected:
- affected construct FAIL_CLOSED

## Candidate implementation location

Preferred first option:
a narrowly scoped projection module under the existing rich/current intelligence lane.

Do not create:
- new full-spine runner
- new orchestrator
- new sequence engine
- new dependency engine
- external process-mining runtime dependency

If an existing owner can absorb the projection cleanly, adapt it instead.

## Acceptance

Engineering:
- all fixture families pass
- no sample identity leak
- portability across different match packages
- invented_semantics_count=0

Football information gain:
- duration coverage
- typed station coverage
- route evaluability
- advanced access visibility
- branch visibility
- opponent-response visibility
- comparison candidate coverage
- unresolved burden explicitly reported

Defaults:
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
