from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
)


def _trace(trace_id: str, occurrence_id: str, actor_id: str, team_id: str) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "action_family_candidates": ["DUEL"],
        "actor_identity_candidate_id": actor_id,
        "team_identity_candidate_id": team_id,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "12.0",
    }


def _consequence(consequence_id: str, occurrence_id: str, anchor_trace_id: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": consequence_id,
        "anchor_trackable_action_trace_candidate_id": anchor_trace_id,
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "visible_follow_up_trace_ids": ["follow_1"],
        "admitted_after_follow_up_trace_ids": [],
        "consequence_signal_candidates": ["NUMERIC_PROVENANCE_WINDOW_VISIBLE_WITHOUT_AFTER_ADMISSION"],
        "primary_consequence_candidate": "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
        "terminal_outcome_support_visible": False,
        "derived_consequence_support_visible": False,
        "record_status": "REVIEW_REQUIRED",
    }


def test_two_participant_interaction_projects_to_one_occurrence_record() -> None:
    occurrence_id = "aoc_interaction_1"
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 2,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": occurrence_id,
                "occurrence_topology": "TWO_PARTICIPANT_INTERACTION",
                "required_participant_scope": "ACTOR_AND_OPPONENT",
                "binding_state": "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [
            _trace("trace_actor", occurrence_id, "actor_a", "team_a"),
            _trace("trace_opponent", occurrence_id, "actor_b", "team_b"),
        ],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 2,
        "trackable_action_consequence_candidates": [
            _consequence("cons_a", occurrence_id, "trace_actor"),
            _consequence("cons_b", occurrence_id, "trace_opponent"),
        ],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["occurrence_consequence_projection_count"] == 1
    assert payload["source_legacy_trace_candidate_count"] == 2
    record = payload["occurrence_consequence_projections"][0]
    assert record["action_occurrence_candidate_id"] == occurrence_id
    assert record["occurrence_topology"] == "TWO_PARTICIPANT_INTERACTION"
    assert record["supporting_trace_candidate_count"] == 2
    assert record["supporting_consequence_candidate_count"] == 2
    assert record["projection_is_causal_truth"] is False
    assert payload["legacy_trace_records_are_support_evidence_not_action_universe"] is True


def test_projection_count_mismatch_fails_closed() -> None:
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 2,
        "trackable_action_trace_candidate_count": 1,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [_trace("trace_1", "aoc_1", "actor_1", "team_1")],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 1,
        "trackable_action_consequence_candidates": [_consequence("cons_1", "aoc_1", "trace_1")],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["status"] == "FAIL_CLOSED"
    assert "occurrence_projection_count_mismatch" in payload["hard_block_hits"]
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_occurrence_without_consequence_is_preserved_as_review_required() -> None:
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 1,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [_trace("trace_1", "aoc_1", "actor_1", "team_1")],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 0,
        "trackable_action_consequence_candidates": [],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["occurrence_consequence_projection_count"] == 1
    assert payload["occurrence_without_consequence_record_count"] == 1
    assert payload["status"] == "REVIEW_REQUIRED"
    record = payload["occurrence_consequence_projections"][0]
    assert record["record_status"] == "REVIEW_REQUIRED"
    assert record["supporting_consequence_candidate_count"] == 0
