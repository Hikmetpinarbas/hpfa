# Sequence Intelligence Lite V1

Status: SPEC_ONLY / REVIEW_REQUIRED

## Purpose

Define a future event-only chain reading layer for HPFA.

This layer reads how visible actions connect across time, space, team, player, action family and outcome surface.

It is not production release and it does not produce tactical truth.

## Core Chain

```text
event atom -> continuation candidate -> opponent surface -> consequence candidate -> claim gate
```

## Required Inputs

- source role
- time bucket
- duration when available
- x and y
- end x and end y when available
- zone candidate
- lane candidate
- team label
- player label when available
- action family
- previous visible action family
- next visible action family
- terminal surface
- claim boundary

## Minimum Outputs

- action_chain_atom
- continuation_candidate
- opponent_surface_candidate
- consequence_candidate
- option_group_candidate
- claim_safety_record

## Option Candidate Families

- forward_pass_to_carry_candidate
- regain_to_progression_candidate
- carry_to_box_entry_candidate
- wide_access_to_cross_candidate
- central_combination_candidate
- restart_to_terminal_action_candidate
- turnover_to_shot_candidate
- defensive_action_to_build_candidate
- defensive_action_to_transition_candidate
- defensive_action_only_candidate

## Candidate Support Fields

- attempts
- terminal_action_count
- shot_surface_count
- box_entry_surface_count
- turnover_surface_count
- opponent_surface_count
- transition_started_count
- value_proxy_sum_when_allowed

## Allowed Wording

- visible chain candidate
- option candidate
- repeated chain family
- consequence proxy
- opponent surface
- support level
- requires validation

## Blocked Wording

- tactical truth
- control truth
- intent truth
- style truth from one match
- player quality truth

## Required Tests

- test_chain_requires_time_space_action
- test_continuation_requires_ordered_atoms
- test_opponent_surface_requires_linked_chain
- test_option_group_remains_candidate
- test_efficiency_score_is_proxy_only
- test_blocked_truth_language
- test_no_sample_match_identity_leak

## Release Status

SPEC_ONLY / REVIEW_REQUIRED.

No production release claim.
