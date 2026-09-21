# Pool Item V1

Status: CONTRACT CANDIDATE. No runtime authority.

## Purpose
A Pool Item is a pool-local governed view over Finding Atoms or upstream Pool Items. It is not new evidence.

## Required fields
- pool_item_id
- pool_id
- pool_version
- pool_stage: SPECIALIZED | MEZZO | MACRO | FINAL
- input_finding_atom_ids
- input_pool_item_ids
- dependency_roots
- football_question_id
- construct_id
- construct_definition
- estimand
- eligible_population_definition
- numerator
- denominator
- unit
- scale
- dimensions
- process_stage
- temporal_role
- comparison_context
- context_completeness
- visible_observation_summary
- support_refs
- counterevidence_refs
- dependency_challenge_refs
- non_support_refs
- unresolved_refs
- comparison_admission_status
- reconstruction_status
- claim_ceiling
- forbidden_inferences
- withdrawal_conditions

## Reconstruction accounting
Every item reports:
- preserved_atom_count
- collapsed_reflection_count
- excluded_atom_count
- lost_atom_count
- enriched_field_count
- invented_semantics_hits

INPUT = PRESERVED + COLLAPSED + EXCLUDED + LOST.
Enrichment is recorded separately and must be reproducible.
INVENTED semantic promotion is not admitted.

## Status
PASS | DEGRADED | REVIEW_REQUIRED | FAIL_CLOSED | NOT_EVALUATED.

## Routing
Downstream producers subscribe only to declared pool slices. Final report producers consume admitted Safe Findings / Match Models, not raw atoms.

## Invariants
- Same atom in multiple pools keeps one dependency root.
- Every ratio exposes numerator and eligible denominator.
- A pool coordinator may summarize/cluster but cannot create tactical, causal, coach-intention or tracking truth.
- Aggregate surfaces cannot create action identity.

canonical_event_count=UNKNOWN
true_action_count=UNKNOWN
production_release=false
