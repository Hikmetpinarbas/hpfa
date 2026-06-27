# HPFA Reasoning Grammar Spine Lite V1

Date: 2026-06-27

Status: SPEC_ONLY

## Purpose

Build the smallest useful bridge from event-row evidence to analyst-facing football reading.

Required spine:

```text
event -> primitive candidate -> sequence candidate -> context -> behaviour candidate -> repeated pattern -> explanation
```

No direct jump from metric to story is allowed.

## Scope

This contract starts with Primitive Grammar Lite only.

Inputs:

- ACTIVE_MATCH identity-compatible runtime
- canonical_event_lite output when available
- postmatch_analyst_report_lite output
- event_window_builder output when available
- axis_integrity_tagger output when available

Outputs, flat under phone output root:

- reasoning_grammar_spine_lite_v1.json
- reasoning_grammar_spine_lite_v1.txt

## Primitive Candidates

Allowed initial candidates:

- pass_surface_candidate
- carry_progression_surface_candidate
- recovery_surface_candidate
- loss_surface_candidate
- terminal_action_surface_candidate
- restart_surface_candidate
- channel_progression_surface_candidate

## Evidence Ladder

Every candidate must expose:

- team
- primitive_candidate
- evidence_count
- zone_support
- channel_support
- confidence: weak / medium / strong
- falsifier
- blocked_claims

## Claim Boundary

Allowed:

- row-level evidence indicates
- action-family volume suggests
- channel evidence is concentrated in
- behaviour candidate
- pattern candidate

Blocked:

- tactical truth
- dominance truth
- possession truth
- phase truth
- sequence truth without sequence gate
- coach intention
- off-ball structure

## Minimality Gate

Do not add a metric unless it improves analyst decision quality.

## Tests

- test_outputs_are_flat_phone_paths
- test_no_tracking_truth_claims
- test_no_metric_to_story_jump
- test_candidates_include_falsifier
- test_no_sample_match_identity_leak

## Release

SPEC_ONLY until implementation, tests, and ACTIVE_MATCH run evidence exist.
