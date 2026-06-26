# Axis Integrity Tagger Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING
Module id: `axis_integrity_tagger_lite_v1`
Claim safety: `AXIS_INTEGRITY_CANDIDATE_ONLY`

## Purpose

Assess which analytical axes are available enough for downstream candidate modules.

This module does not create phase truth, possession truth, sequence truth, rhythm truth, tactical truth or dominance truth.

## Donor scan evidence

```text
Donor scan performed: yes
Repos searched: HP-Motor, HP-Engine
Useful hits: phase_tagger.py, STEP13_TEMPO_MOMENTS.py, hp_temporal_engine.py
Adapted ideas: no-guessing when time axis is missing, axis availability checks, candidate-only permissions
ADAPT_NOT_COPY confirmed: true
```

## Inputs

```text
time_scale_router_lite_v1.json
event_window_builder_lite_v1.json
minimum_viable_context_lite_v1.json
```

## Outputs

Flat phone outputs only:

```text
axis_integrity_tagger_lite_v1.json
axis_integrity_tagger_lite_v1.txt
```

## Axis fields

```text
minute_axis_status
second_axis_status
event_index_axis_status
space_axis_status
team_axis_status
action_family_axis_status
axis_integrity_score
downstream_time_allowed
downstream_phase_candidate_allowed
downstream_sequence_candidate_allowed
downstream_rhythm_candidate_allowed
claim_allowed=false
```

## Status labels

```text
AXIS_AVAILABLE
AXIS_PARTIAL
AXIS_MISSING
AXIS_UNKNOWN
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
claim_safety=AXIS_INTEGRITY_CANDIDATE_ONLY
```

## Required tests

```text
test_detects_available_minute_axis
test_marks_missing_time_axis_as_not_allowed
test_detects_space_team_action_axes
test_claim_boundaries_remain_false
test_flat_phone_outputs
test_no_sample_match_identity_leak
```
