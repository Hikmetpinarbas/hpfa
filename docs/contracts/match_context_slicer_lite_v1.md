# Match Context Slicer Lite V1

Status: IMPLEMENTATION_WRITTEN_EXECUTION_PENDING

## Purpose

Bind the current Sportsbase-derived action, phase and phase-refinement surfaces to an event-only post-match context axis.

The node answers:

- which period and derived minute bucket contains the phase segment;
- what event-derived score-state candidate existed before the segment;
- whether the segment begins at the same timestamp as a visible goal candidate;
- whether the segment is restart or non-restart context;
- which phase-refinement decision applies.

## Inputs

```text
selected_action_consequence_surface_lite_v1.json
event_derived_phase_state_lite_v1.json
phase_aware_sequence_refinement_lite_v1.json
```

All inputs must share the same match-surface binding. Counts, identities, time values and upstream hard blocks are reconciled before output.

## Time model

`start_candidate` and phase start/end values are treated as source-second candidates. Football minute and 15-minute buckets are derived displays, never primitive source truth.

The current Sportsbase match exposes a cumulative cross-period axis. A second period that moves behind the first-period axis fails closed instead of receiving a guessed offset.

## Goal and score context

A goal-context candidate requires all three visible signals on one selected action node:

```text
SHOT action family
terminal_outcome_support_visible=true
normalized support label includes goals
```

This supports a score-state candidate; it does not create canonical goal truth or scoreboard truth. A phase beginning at exactly the same timestamp is marked `SAME_TIME_GOAL_CONTEXT_REVIEW_REQUIRED` because no artificial within-timestamp order is allowed.

## Preserved unknowns

The current upstream input does not expose an admitted card or substitution surface. Therefore:

```text
card_state=UNKNOWN_NO_VALIDATED_CARD_SURFACE_IN_CURRENT_INPUT
lineup_state=UNKNOWN_NO_VALIDATED_SUBSTITUTION_SURFACE_IN_CURRENT_INPUT
```

No zero-card or unchanged-lineup default is permitted.

## Outputs

```text
match_context_slicer_lite_v1.json
match_context_slicer_lite_v1.txt
match_context_slicer_analyst_audit_v1.txt
```

Phone outputs remain flat under `/sdcard/Download/HPFA` or `/storage/emulated/0/Download/HPFA`.

## Claim boundary

```text
scoreboard_truth=false
phase_truth=false
sequence_truth=false
possession_truth=false
tactical_truth=false
off_ball_structure_truth=false
canonical_event_count=UNKNOWN
production_release=false
```

## Required validation

- deterministic focused tests;
- upstream phase-refinement compatibility;
- contract JSON validation;
- shell syntax validation;
- no sample-match identity leak;
- exact-head ACTIVE_MATCH execution and flat phone bundle.
