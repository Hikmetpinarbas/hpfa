# XLSX Trace Cohort Analyst Presentation V1

## Scope

This contract governs how existing XLSX aggregate entity context may be surfaced in the standard ACTIVE_MATCH analyst report when the rich multiformat lane has already linked that entity candidate to a same-binding trackable-action trace cohort.

No new identity, trace, event, metric, sequence, or reasoning engine is introduced.

## Required relation

The upstream relation must already be:

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY`

and must preserve the same `match_surface_binding_id`, `team_identity_candidate_id`, and `actor_identity_candidate_id` authority used by the current rich multiformat producer.

## Analyst-facing projection

The standard analyst report may expose:

- entity candidate label;
- source role;
- observed XLSX metric-cell count;
- cohort-context state;
- trackable-action trace candidate IDs for navigation;
- deduplicated `action_family_candidates` labels already carried by those same cohort trace refs;
- aggregate cohort-link count;
- trace-candidate reference count;
- review-required count.

The action-family labels are a label-set projection only. They may help the analyst navigate from an aggregate entity profile to the visible action-family candidate surface represented inside the same trace cohort, but they are not frequencies, rates, contribution scores, event counts, or physical-action participation truth.

## Invariants

`trace_candidate_ref_count != canonical_event_count`

`trace_candidate_ref_count != true_action_count`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != individual_action_support`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != action_trace_identity`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != physical_action_truth`

`trace_cohort_action_family_candidate_labels != action_family_frequency`

`trace_cohort_action_family_candidate_labels != player_function_truth`

`trace_cohort_action_family_candidate_labels != individual_action_support`

`trace_cohort_action_family_candidate_labels != physical_action_truth`

`XLSX aggregate support != independent evidence vote`

Candidate identity remains candidate-only. Presence of one or more trace references or one or more action-family candidate labels is navigation/context evidence only and may not promote identity, event, action, sequence, tactical, causality, dominance, intention, player-function, or physical-performance truth.

## Fail-closed projection gate

The analyst-output producer may project action-family candidate labels only when all upstream claim locks are still present:

- `aggregate_support_trace_context_state=TRACE_CANDIDATE_COHORT_CONTEXT_ONLY`;
- `aggregate_support_trace_relation_is_cohort_context_only=true`;
- `aggregate_support_trace_relation_is_individual_action_support=false`;
- `aggregate_support_trace_relation_is_physical_action_truth=false`.

If any of these conditions is missing or claim-upgraded, the action-family label projection must be empty. The analyst-output producer must not reconstruct labels from raw names, XLSX metric values, filenames, or other side channels.

## Claim locks

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

## Failure behavior

If the upstream rich-lane relation is unavailable, mismatched, review-required, or claim-upgraded, the analyst report must not synthesize a replacement trace relation or action-family relation from raw names, filenames, XLSX row order, or metric values.

## Product meaning

The analyst can move from an XLSX entity-context surface to the already-existing same-candidate trace cohort and inspect which action-family candidate labels are present in that cohort without interpreting the aggregate row as support for any single physical action or interpreting the label set as a validated player-function distribution.
