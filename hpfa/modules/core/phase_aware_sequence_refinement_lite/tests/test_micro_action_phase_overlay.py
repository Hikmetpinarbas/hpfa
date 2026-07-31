from __future__ import annotations

from hpfa.modules.core.phase_aware_sequence_refinement_lite.src.micro_action_phase_overlay import (
    MICRO_ACTION_ROLE,
    apply_effective_phase_to_context_slices,
    apply_micro_action_phase_overlay,
)


def _segment(segment_id: str, phase: str, anchors: int, start: float, end: float):
    return {
        "event_derived_phase_segment_id": segment_id,
        "phase_class_candidate": phase,
        "visible_anchor_count": anchors,
        "start_time_candidate": start,
        "end_time_candidate": end,
    }


def test_single_anchor_zero_span_aba_becomes_overlay_without_deletion():
    phase = {
        "event_derived_phase_segments": [
            _segment("a1", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 2, 1.0, 2.0),
            _segment("b", "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE", 1, 3.0, 3.0),
            _segment("a2", "BUILD_UP_VISIBLE_PHASE_CANDIDATE", 3, 4.0, 6.0),
        ]
    }
    refinement = {
        "phase_refinement_decisions": [
            {
                "source_event_derived_phase_segment_id": "b",
                "previous_phase_segment_id": "a1",
                "following_phase_segment_id": "a2",
                "phase_class_candidate": "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE",
                "decision_class": "REFINEMENT_CANDIDATE_SINGLE_ANCHOR_OSCILLATION",
            }
        ],
        "hard_block_hits": [],
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
    }
    out = apply_micro_action_phase_overlay(phase, refinement)
    decision = out["phase_refinement_decisions"][0]
    assert decision["effective_phase_class_candidate"] == "BUILD_UP_VISIBLE_PHASE_CANDIDATE"
    assert decision["phase_representation_role"] == MICRO_ACTION_ROLE
    assert decision["separate_phase_display_allowed"] is False
    assert decision["micro_action_overlay_candidate"] is True
    assert out["micro_action_overlay_candidate_count"] == 1
    assert out["source_phase_segments_preserved"] is True
    assert out["hard_block_hits"] == []


def test_review_bounded_or_non_candidate_segment_remains_separate():
    phase = {
        "event_derived_phase_segments": [
            _segment("b", "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE", 1, 3.0, 3.0)
        ]
    }
    refinement = {
        "phase_refinement_decisions": [
            {
                "source_event_derived_phase_segment_id": "b",
                "phase_class_candidate": "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE",
                "decision_class": "INSUFFICIENT_ANCHOR_REVIEW_REQUIRED",
            }
        ],
        "hard_block_hits": [],
    }
    out = apply_micro_action_phase_overlay(phase, refinement)
    decision = out["phase_refinement_decisions"][0]
    assert decision["effective_phase_class_candidate"] == "FINAL_THIRD_VISIBLE_PHASE_CANDIDATE"
    assert decision["separate_phase_display_allowed"] is True
    assert decision["micro_action_overlay_candidate"] is False
    assert out["micro_action_overlay_candidate_count"] == 0


def test_context_uses_effective_phase_and_keeps_source_phase():
    refinement = {
        "phase_refinement_decisions": [
            {
                "source_event_derived_phase_segment_id": "b",
                "effective_phase_class_candidate": "BUILD_UP_VISIBLE_PHASE_CANDIDATE",
                "phase_representation_role": MICRO_ACTION_ROLE,
                "separate_phase_display_allowed": False,
            }
        ]
    }
    context = {
        "match_context_slices": [
            {
                "source_event_derived_phase_segment_id": "b",
                "phase_class_candidate": "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE",
            }
        ],
        "hard_block_hits": [],
    }
    out = apply_effective_phase_to_context_slices(refinement, context)
    item = out["match_context_slices"][0]
    assert item["source_phase_class_candidate"] == "MIDDLE_PROGRESSION_VISIBLE_PHASE_CANDIDATE"
    assert item["phase_class_candidate"] == "BUILD_UP_VISIBLE_PHASE_CANDIDATE"
    assert item["separate_phase_display_allowed"] is False
    assert out["micro_action_overlay_context_slice_count"] == 1
