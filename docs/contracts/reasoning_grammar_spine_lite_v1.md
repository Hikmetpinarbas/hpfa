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

Primitive-only output may emit primitive candidates and primitive explanations. It must not emit behaviour or pattern candidates until sequence/context gates exist and pass.

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

## Stage Gate

Primitive Grammar Lite may only produce:

- primitive_candidate
- primitive_evidence
- primitive_explanation

The following are gated and must remain blocked in primitive-only runs:

- sequence_candidate
- behaviour_candidate
- pattern_candidate
- identity_candidate
- match_story

A later module may unlock these terms only after explicit sequence/context/pattern gates are implemented, tested and recorded as ACTIVE_MATCH evidence.

## Overclaim Guard

The following language is rejected for this contract:

- ready for deployment
- football ontology is validated
- cognitive state is measured
- pre-motor time is measured from event rows
- mental decline is measured from event rows
- next action is predicted as truth
- Voronoi or pitch-control truth from event-only runtime
- off-ball structure from event-only runtime
- coach intention
- city or culture as runtime evidence

Allowed replacement language:

- candidate
- proxy
- row-level evidence
- event-surface reading
- primitive candidate
- requires later validation
- evidence-only until claim gate

## Claim Boundary

Allowed in Primitive Grammar Lite:

- row-level evidence indicates
- action-family volume suggests
- channel evidence is concentrated in
- primitive candidate
- primitive explanation

Blocked in Primitive Grammar Lite:

- behaviour candidate
- pattern candidate
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
- test_overclaim_guard_blocks_deployment_and_cognitive_truth_language
- test_primitive_only_blocks_behaviour_and_pattern_terms

## Release

SPEC_ONLY until implementation, tests, and ACTIVE_MATCH run evidence exist.
