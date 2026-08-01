# Micro-Action Phase Overlay V1

Status: IMPLEMENTATION_WRITTEN_LOCAL_BUNDLE_REPLAY_PASS

## Purpose

Prevent a single visible action from being presented as an independent analyst-facing phase when it forms a strongly supported same-sequence A-B-A phase oscillation.

The source event-derived phase segment remains intact. The overlay changes only the analyst-facing phase representation.

## Admission gate

A source segment becomes a `MICRO_ACTION_PHASE_OVERLAY_CANDIDATE` only when all conditions hold:

- refinement decision class is `REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION`;
- previous and following phase classes match;
- middle source phase differs from the matching flanks;
- middle segment has exactly one visible anchor;
- middle segment has a zero-span source interval;
- each flank has at least two visible anchors.

## Representation

For admitted overlays:

```text
source_phase_class_candidate = preserved middle source label
effective_phase_class_candidate = matching flank phase
phase_representation_role = MICRO_ACTION_PHASE_OVERLAY_CANDIDATE
separate_phase_display_allowed = false
```

The context slicer uses the effective phase for analyst-facing phase comparison while retaining the source phase in `source_phase_class_candidate` and `micro_action_source_phase_excursion_candidate`.

## Non-admitted cases

`INSUFFICIENT_ANCHOR_REVIEW_REQUIRED`, protected phase changes, positive-span changes and multi-anchor phase changes remain separate source phase candidates. They are not automatically suppressed.

## ACTIVE_MATCH replay evidence

The uploaded exact-head bundle replay produced:

```text
source_phase_segments=645
A_B_A_phase_oscillations=106
micro_action_overlay_candidates=9
separate_phase_display_suppressed=9
insufficient_anchor_review_cases_preserved=71
source_phase_segments_deleted=0
source_phase_segments_merged=0
hard_block_hits=[]
```

The nine admitted overlays consist of eight single-pass records and one duel record. This is action-level evidence, not tactical intent or phase truth.

## Claim boundary

```text
phase_truth=false
sequence_truth=false
possession_truth=false
tactical_truth=false
off_ball_structure_truth=false
canonical_event_count=UNKNOWN
production_release=false
```
