# Sequence Safe Finding Null Claim Locks V1

## Purpose

Rehabilitate the existing `sequence_safe_finding_binding_lite_v1` boundary so an audited recurrence-null contrast cannot gain epistemic strength while being projected into a Safe Finding. This is not a new null, sequence, reasoning, or reporting engine.

## Required upstream identity

When a null contrast payload is supplied, the Safe Finding binding accepts only:

- `contrast_id=recurrence_null_contrast_v1`
- `claim_ceiling=UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY`
- `multiple_testing_corrected=false`
- `significance_claim_allowed=false`
- `tactical_pattern_truth_allowed=false`
- `canonical_event_count=UNKNOWN`
- `true_action_count=UNKNOWN`
- `production_release=false`

Any mismatch is fail-closed before analyst prose is emitted.

## Per-family invariants

For every bound null row:

1. `eligible_trace_refs` must equal the exact admitted trace cohort.
2. `observed_independent_recurrence` must equal the admitted independent-support value, or remain `UNKNOWN` when independence is not admitted.
3. `claim_ceiling` must remain `UNCORRECTED_MATCH_LOCAL_NULL_CONTRAST_CANDIDATE_ONLY`.
4. `multiple_testing_corrected=false` is mandatory.
5. `significance_claim_allowed=false` is mandatory.
6. `tactical_pattern_truth_allowed=false` is mandatory.
7. `causality_allowed=false` is mandatory.
8. A non-empty `withdrawal_condition` is mandatory.
9. Safe Finding publication may preserve null evidence but must set `claim_strengthened=false`.

## Failure policy

Any ceiling mismatch, significance/tactical/causal escalation, fabricated independence, trace-cohort drift, multiple-testing escalation, or missing withdrawal condition is `FAIL_CLOSED` and produces no Safe Finding block for that payload.

## Claim boundary

A low uncorrected empirical tail probability is not multiple-testing-corrected statistical significance. A supplied null contrast is not tactical-pattern truth, coach intention, causality, possession truth, phase truth, or stable team-style truth.

`canonical_event_count=UNKNOWN`
`true_action_count=UNKNOWN`
`production_release=false`

CI SUCCESS is engineering evidence only and is not physical ACTIVE_MATCH acceptance.
