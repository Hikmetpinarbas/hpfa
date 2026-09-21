# Finding Atom V1

Status: CONTRACT CANDIDATE. No runtime authority.

## Purpose
A Finding Atom is the smallest semantically meaningful, lineage-preserving HPFA information unit that may be routed to one or more football pools without multiplying evidence.

## Required identity
- finding_atom_id
- producer_module_id
- producer_output_id
- source_ref_ids
- surface_ref_ids
- observation_ref_ids
- dependency_root
- provenance_root

## Required semantics
- observation_family
- semantic_role
- epistemic_state: DIRECT_OBSERVATION | DERIVED_OBSERVATION | PROXY | MODEL_OUTPUT | HYPOTHESIS | UNRESOLVED
- claim_ceiling
- provider_semantics_status

## Football indexes
- team_candidate
- actor_candidates
- opponent_candidate
- episode_candidate_id
- process_candidate_id
- phase_candidates
- pool_candidates
- scale: MICRO | MEZZO | MACRO
- game_dimensions

## Temporal / spatial / relation
Atoms may carry admitted period/time, duration, same-time unordered refs, zones, coordinates, channels, action family/facets, relation candidates and station refs. Missing values remain missing.

## Evidence control
- support_role
- counterevidence_candidate_state
- dependency_state
- independent_support_vote
- uncertainty_state
- missing_lenses
- review_hits
- hard_block_hits

## Transformation state
RAW | NORMALIZED | SEMANTICALLY_ENRICHED | COLLAPSED_DEPENDENCY | RECONSTRUCTED | COMPARABLE | SYNTHESIZED | DEGRADED | WITHDRAWN

Every derived field must name its transformation_id and upstream atom refs.

## Invariants
1. One evidence root may expose many semantic facets but never many independent votes.
2. Pool membership is routing metadata, not evidence multiplication.
3. ROW != EVENT TRUTH.
4. AGGREGATE != ACTION IDENTITY.
5. SAME TIMESTAMP != TOTAL ORDER.
6. COORDINATE != TRACKING.
7. MODEL OUTPUT != FACT.
8. ABSENCE != COUNTEREVIDENCE.
9. LLM text is never an evidence atom.
10. An atom cannot silently increase its claim ceiling.

## Reconstruction delta
PRESERVED | ENRICHED | COLLAPSED | DEGRADED | LOST | INVENTED | AMBIGUOUS.

INVENTED semantic promotion fails closed for the affected construct.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
