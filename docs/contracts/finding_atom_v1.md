# Finding Atom V1

Status: contract-only, no runtime owner yet.

Purpose: normalize the smallest semantically meaningful, lineage-preserving football-information unit produced by current HPFA modules. A Finding Atom is not a Safe Finding and does not itself create a claim.

Required identity:
- finding_atom_id
- producer_module_id
- producer_output_id
- source_ref_ids
- surface_ref_ids
- observation_ref_ids
- dependency_root
- provenance_root

Required semantics:
- observation_family
- semantic_role
- epistemic_state: DIRECT_OBSERVATION | DERIVED_OBSERVATION | PROXY | MODEL_OUTPUT | HYPOTHESIS | COUNTEREVIDENCE | UNRESOLVED | UNOBSERVABLE
- claim_ceiling
- provider_semantics_status

Football indexes:
- pool_candidates
- scale: MICRO | MEZZO | MACRO
- game_dimensions
- phase_candidates
- episode_candidate_id
- process_candidate_id
- team_candidate
- actor_candidates
- opponent_candidate

Temporal/spatial:
- period_candidate
- start_time_candidate
- end_time_candidate
- duration_candidate
- ordering_state
- same_time_unordered_refs
- start_zone_candidate
- end_zone_candidate
- coordinates only when admitted
- grid_refs

Evidence control:
- support_role
- counterevidence_candidate_state
- dependency_state
- independent_support_vote
- uncertainty_state
- missing_lenses
- review_hits
- hard_block_hits

Transformation:
- transformation_state
- transformation_id
- information_delta_class
- upstream_atom_refs
- reconstruction_parent_id

Rules:
1. One evidence root may emit many semantic facets but not many independent votes.
2. Multi-pool routing does not multiply evidence.
3. Every derived field must name its transformation.
4. Aggregate surfaces cannot create action identity.
5. Same timestamp does not create total order.
6. Coordinate does not become tracking.
7. Provider label does not become tactical truth.
8. Unresolved does not become negative.
9. LLM text is not evidence.
10. INVENTED semantic promotion fails closed for the affected construct.

Canonical defaults:
canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
