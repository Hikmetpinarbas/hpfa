# Second Ball Continuation Lite V1

Status: SPEC_ONLY / REVIEW_REQUIRED

## Purpose

Define a future event-only layer for second-ball and continuation reading.

The module asks what happens after a terminal or disrupted action surface:

- shot saved
- shot blocked
- shot off woodwork
- cross cleared
- pass intercepted
- duel outcome
- loose ball surface
- recovery surface

It does not create event truth, possession truth, phase truth or tactical truth.

## Core Question

After the first action is interrupted or completed, who reached the next playable surface and what did it create?

## Core Chain

```text
terminal_or_disrupted_action -> second_ball_surface -> continuation_surface -> consequence_candidate -> claim_gate
```

## Required Inputs

- source_role
- time_bucket
- start_time when available
- end_time when available
- duration when available
- x
- y
- end_x when available
- end_y when available
- team_label
- player_label when available
- action_family
- result_surface
- next_visible_action_family
- next_team_label
- zone_candidate
- lane_candidate
- claim_boundary

## Minimum Outputs

- second_ball_candidate
- continuation_owner_candidate
- continuation_time_delta
- continuation_distance_delta
- continuation_zone_delta
- continuation_result_candidate
- claim_safety_record

## Candidate Result Families

- same_team_continuation_candidate
- opponent_recovery_candidate
- shot_rebound_candidate
- blocked_shot_continuation_candidate
- save_rebound_candidate
- clearance_to_reset_candidate
- interception_to_transition_candidate
- defensive_action_to_build_candidate
- defensive_action_only_candidate
- loose_ball_to_terminal_action_candidate

## Measurement Fields

- time_to_next_surface_sec
- distance_to_next_surface_m
- zone_change_candidate
- lane_change_candidate
- team_retained_surface
- opponent_gained_surface
- new_attack_started_candidate
- transition_started_candidate
- terminal_action_created
- value_proxy_allowed

## Allowed Wording

- second-ball candidate
- continuation owner candidate
- rebound surface
- recovery surface
- consequence proxy
- time-space continuation
- requires validation

## Blocked Wording

- possession truth
- tactical truth
- intent truth
- dominance truth
- control truth
- player quality truth

## Required Tests

- test_second_ball_requires_next_visible_surface
- test_continuation_owner_is_candidate_only
- test_time_delta_requires_temporal_fields
- test_distance_delta_requires_coordinates
- test_defensive_action_does_not_imply_transition_success
- test_value_output_is_proxy_only
- test_blocked_truth_language
- test_no_sample_match_identity_leak

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.
No production release claim.
