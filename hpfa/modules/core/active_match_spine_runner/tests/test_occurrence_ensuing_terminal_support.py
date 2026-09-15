from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
)


def _trace_payload() -> dict:
    traces = [
        {
            "trackable_action_trace_candidate_id": "t1",
            "supporting_action_occurrence_candidate_ids": ["o1"],
            "action_family_candidates": ["PASS"],
            "actor_identity_candidate_id": "a1",
            "team_identity_candidate_id": "team_a",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "period_candidate": "1",
            "start_candidate": "10.0",
            "end_candidate": "11.0",
        },
        {
            "trackable_action_trace_candidate_id": "t2",
            "supporting_action_occurrence_candidate_ids": ["o2"],
            "action_family_candidates": ["SHOT"],
            "actor_identity_candidate_id": "a2",
            "team_identity_candidate_id": "team_b",
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "period_candidate": "1",
            "start_candidate": "15.0",
            "end_candidate": "16.0",
        },
    ]
    return {
        "status": "PASS",
        "current_occurrence_candidate_count": 2,
        "primary_occurrence_trace_candidates": traces,
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": 2,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "o1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            },
            {
                "action_occurrence_candidate_id": "o2",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            },
        ],
    }


def _consequence_payload() -> dict:
    return {
        "status": "PASS",
        "window_seconds": [5.0, 8.0, 12.0],
        "max_follow_up_time_layers": 3,
        "trackable_action_consequence_candidate_count": 2,
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "c1",
                "anchor_trackable_action_trace_candidate_id": "t1",
                "supporting_action_occurrence_candidate_ids": ["o1"],
                "visible_follow_up_trace_ids": ["t2"],
                "admitted_after_follow_up_trace_ids": ["t2"],
                "consequence_signal_candidates": ["OPPONENT_SHOT_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidate": "OPPONENT_HANDOVER_CANDIDATE",
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            },
            {
                "trackable_action_consequence_candidate_id": "c2",
                "anchor_trackable_action_trace_candidate_id": "t2",
                "supporting_action_occurrence_candidate_ids": ["o2"],
                "visible_follow_up_trace_ids": [],
                "admitted_after_follow_up_trace_ids": [],
                "consequence_signal_candidates": ["TERMINAL_OUTCOME_SUPPORT_VISIBLE"],
                "primary_consequence_candidate": "TERMINAL_OUTCOME_SUPPORT_CANDIDATE",
                "terminal_outcome_support_visible": True,
                "derived_consequence_support_visible": True,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            },
        ],
    }


def test_admitted_followup_can_expose_ensuing_terminal_support_without_causal_promotion() -> None:
    payload = build_occurrence_consequence_projection(_trace_payload(), _consequence_payload())
    assert payload["status"] == "PASS"
    first = next(
        row for row in payload["occurrence_consequence_projections"]
        if row["action_occurrence_candidate_id"] == "o1"
    )
    assert first["ensuing_terminal_support_trace_ids"] == ["t2"]
    assert first["ensuing_derived_consequence_support_trace_ids"] == ["t2"]
    assert first["ensuing_terminal_support_visible"] is True
    assert first["ensuing_derived_consequence_support_visible"] is True
    assert first["ensuing_support_relation_basis"] == "ADMITTED_AFTER_FOLLOW_UP_TRACE_ONLY"
    assert first["ensuing_terminal_support_is_causal_truth"] is False
    assert first["ensuing_terminal_support_is_anchor_terminal_state_truth"] is False
    assert payload["occurrence_with_ensuing_terminal_support_count"] == 1
    assert payload["occurrence_with_ensuing_derived_consequence_support_count"] == 1
    assert payload["ensuing_support_uses_admitted_after_only"] is True
    assert payload["projection_is_causal_truth"] is False


def test_numeric_visible_followup_without_after_admission_does_not_create_ensuing_support() -> None:
    consequence = _consequence_payload()
    consequence["trackable_action_consequence_candidates"][0]["admitted_after_follow_up_trace_ids"] = []
    payload = build_occurrence_consequence_projection(_trace_payload(), consequence)
    first = next(
        row for row in payload["occurrence_consequence_projections"]
        if row["action_occurrence_candidate_id"] == "o1"
    )
    assert first["ensuing_terminal_support_trace_ids"] == []
    assert first["ensuing_terminal_support_visible"] is False
    assert first["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert first["observation_status"] == "ORDER_INDETERMINATE"


def test_duplicate_consequence_anchor_trace_fails_closed() -> None:
    consequence = _consequence_payload()
    duplicate = dict(consequence["trackable_action_consequence_candidates"][1])
    duplicate["trackable_action_consequence_candidate_id"] = "c3"
    consequence["trackable_action_consequence_candidates"].append(duplicate)
    consequence["trackable_action_consequence_candidate_count"] = 3
    payload = build_occurrence_consequence_projection(_trace_payload(), consequence)
    assert payload["status"] == "FAIL_CLOSED"
    assert "duplicate_consequence_anchor_trace_id" in payload["hard_block_hits"]
    assert payload["occurrence_consequence_projections"] == []
    assert payload["production_release"] is False
