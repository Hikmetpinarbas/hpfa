# Time-Scale Router Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `time_scale_router_lite_v1`
Claim safety: `TIME_SCALE_CANDIDATE_ONLY`

## Purpose

Route event-window candidates by time-axis and density evidence before sequence, rhythm, signal or analyst synthesis layers consume them.

This module does not create phase truth, possession truth, sequence truth, rhythm truth, tactical truth or dominance truth.

## Upstream dependency

```text
Event Window Builder Lite V1
```

## Input

```text
event_window_builder_lite_v1.json
```

Expected upstream fields:

```text
window_id
window_axis
start_minute/end_minute OR start_index/end_index
surface_row_count
context_density
window_confidence
terminal_action_surface_present
loss_recovery_surface_present
restart_surface_present
claim_allowed=false
```

## Outputs

Flat phone outputs only:

```text
time_scale_router_lite_v1.json
time_scale_router_lite_v1.txt
```

## Routing labels

```text
MINUTE_AXIS_USABLE
MINUTE_AXIS_LOW_DENSITY
EVENT_INDEX_FALLBACK_ONLY
TIME_SURFACE_INSUFFICIENT
REVIEW_REQUIRED
```

## Routed candidate fields

```text
window_id
window_axis
surface_row_count
context_density
window_confidence
time_scale_candidate
signal_density_candidate
routing_decision
routing_reason
terminal_action_surface_present
loss_recovery_surface_present
restart_surface_present
claim_allowed=false
```

## Claim boundary

Always emit:

```text
canonical_event_count=UNKNOWN
deduplicated_event_count=UNKNOWN
phase_truth=false
possession_truth=false
sequence_truth=false
rhythm_truth=false
time_window_truth=false
tactical_truth=false
dominance_truth=false
claim_safety=TIME_SCALE_CANDIDATE_ONLY
```

## Allowed language

```text
time-scale candidate
minute-axis usable candidate
low-density minute candidate
event-index fallback candidate
requires sequence validation
requires rhythm validation
```

## Forbidden language

```text
rhythm state truth
phase truth
possession truth
sequence truth
tactical phase
dominance window
coach intention
```

## Required tests

```text
test_routes_minute_axis_usable_windows
test_routes_low_density_minute_windows
test_routes_event_index_fallback_windows
test_claim_boundaries_remain_false
test_flat_phone_outputs
test_no_sample_match_identity_leak
```
