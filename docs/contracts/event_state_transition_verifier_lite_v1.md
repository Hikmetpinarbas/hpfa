# Event State Transition Verifier Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `event_state_transition_verifier_lite_v1`
Claim safety: `EVENT_STATE_TRANSITION_EVIDENCE_ONLY`

## Purpose

Verify whether visible event-family order contains transition-plausibility issues.

This module does not create complete event truth, phase truth, possession truth, sequence truth, player error truth, referee error truth, or tactical truth.

## Inputs

Required review gates:

```text
primary_surface_review_resolution_lite_v1.json
identity_review_resolution_lite_v1.json
gk_taxonomy_source_role_reconciliation_lite_v1.json
```

Optional event surface:

```text
primary_event_surface_gate_lite_v1.json
```

If upstream gates remain `WAIT`, `FAIL_CLOSED` or `REVIEW_REQUIRED`, this module must not evaluate event-order truth. It must emit a wait/review blocker.

## Outputs

Flat phone outputs only:

```text
event_state_transition_verifier_lite_v1.json
event_state_transition_verifier_lite_v1.txt
```

## States

```text
dead_ball
in_play
possession_active
possession_reset
shot_terminal
turnover
restart
unknown
```

## Decisions

```text
FAIL_CLOSED_MISSING_INPUTS
WAIT_UPSTREAM_REVIEW_BLOCKERS
NO_EVENT_SURFACE_AVAILABLE
NO_TRANSITION_ISSUES_DETECTED
TRANSITION_REVIEW_REQUIRED
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
event_state_truth=false
phase_truth=false
possession_truth=false
sequence_truth=false
event_count_claim_allowed=false
production_binding_allowed=false
claim_safety=EVENT_STATE_TRANSITION_EVIDENCE_ONLY
```

## Candidate transition issues

```text
illegal_continuation_after_shot_terminal
restart_cluster_review
unknown_state_density_review
```

These are review candidates only.

## Required tests

```text
test_missing_inputs_fail_closed
test_upstream_review_blocker_waits
test_no_event_surface_available
test_no_transition_issues_detected
test_shot_terminal_continuation_review_required
test_no_truth_claims
test_flat_phone_outputs
test_nested_phone_output_directory_rejected
test_no_sample_match_identity_leak
```
