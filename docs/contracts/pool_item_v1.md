# Pool Item V1

Status: contract-only, no runtime owner yet.

Purpose: represent a pool-local view over one or more Finding Atoms without creating new evidence.

Required identity:
- pool_item_id
- pool_id
- pool_version
- pool_stage: SPECIALIZED | MEZZO | MACRO | FINAL
- input_finding_atom_ids
- input_pool_item_ids
- dependency_roots

Construct contract:
- football_question_id
- construct_id
- construct_definition
- estimand
- eligible_population_definition
- numerator
- denominator
- unit

Indexes:
- scale
- dimensions
- phase_family
- process_stage
- temporal_role

Context:
- comparison_context
- context_completeness
- opponent_context
- game_state

Evidence:
- support_refs
- counterevidence_refs
- dependency_challenge_refs
- non_support_refs
- unresolved_refs
- comparison_admission_status

Reconstruction:
- reconstruction_status
- preserved_atom_count
- collapsed_reflection_count
- enriched_field_count
- lost_atom_refs
- invented_semantics_hits

Output permission:
- pool_status: PASS | DEGRADED | REVIEW_REQUIRED | FAIL_CLOSED | NOT_EVALUATED
- downstream_admission
- claim_ceiling
- forbidden_inferences
- withdrawal_conditions

Rules:
1. Pool Item is a view, not new evidence.
2. Same dependency root remains one evidence root across pools.
3. Every ratio declares numerator and eligible denominator.
4. Pool reconstruction cannot create event identity.
5. Pool coordinator may cluster/summarize but cannot promote tactical truth.
6. Final report consumes Safe Findings / Match Models, not raw atoms.
