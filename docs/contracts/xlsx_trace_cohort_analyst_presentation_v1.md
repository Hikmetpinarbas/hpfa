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
- aggregate cohort-link count;
- trace-candidate reference count;
- review-required count.

## Invariants

`trace_candidate_ref_count != canonical_event_count`

`trace_candidate_ref_count != true_action_count`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != individual_action_support`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != action_trace_identity`

`TRACE_CANDIDATE_COHORT_CONTEXT_ONLY != physical_action_truth`

`XLSX aggregate support != independent evidence vote`

Candidate identity remains candidate-only. Presence of one or more trace references is navigation/context evidence only and may not promote identity, event, action, sequence, tactical, causality, dominance, intention, or physical-performance truth.

## Claim locks

- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

## Failure behavior

If the upstream rich-lane relation is unavailable, mismatched, review-required, or claim-upgraded, the analyst report must not synthesize a replacement trace relation from raw names, filenames, XLSX row order, or metric values.

## Product meaning

The analyst can move from an XLSX entity-context surface to the already-existing same-candidate trace cohort for inspection without interpreting the aggregate row as support for any single physical action.
