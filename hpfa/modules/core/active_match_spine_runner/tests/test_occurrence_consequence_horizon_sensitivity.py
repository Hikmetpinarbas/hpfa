from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
)


def _trace(trace_id: str, occurrence_id: str | None, start: float) -> dict:
    row = {
        "trackable_action_trace_candidate_id": trace_id,
        "action_family_candidates": ["PASS"],
        "actor_identity_candidate_id": f"actor_{trace_id}",
        "team_identity_candidate_id": "team_a",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": str(start),
        "end_candidate": str(start + 0.5),
    }
    if occurrence_id:
        row["supporting_action_occurrence_candidate_ids"] = [occurrence_id]
    return row


def _consequence(occurrence_id: str, admitted_after: list[str]) -> dict:
    return {
        "trackable_action_consequence_candidate_id": "cons_anchor",
        "anchor_trackable_action_trace_candidate_id": "trace_anchor",
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "visible_follow_up_trace_ids": list(admitted_after),
        "admitted_after_follow_up_trace_ids": list(admitted_after),
        "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"] if admitted_after else [],
        "primary_consequence_candidate": (
            "SAME_TEAM_CONTINUATION_CANDIDATE"
            if admitted_after
            else "NO_VISIBLE_FOLLOW_UP_CANDIDATE"
        ),
        "terminal_outcome_support_visible": False,
        "derived_consequence_support_visible": False,
        "record_status": "PASS_CANDIDATE_CLASSIFICATION",
    }


def _payload(follow_start: float | None) -> tuple[dict, dict]:
    occurrence_id = "aoc_1"
    anchor = _trace("trace_anchor", occurrence_id, 10.0)
    traces = [anchor]
    admitted: list[str] = []
    if follow_start is not None:
        traces.append(_trace("trace_follow", None, follow_start))
        admitted = ["trace_follow"]
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": len(traces),
        "primary_occurrence_trace_candidates": [anchor],
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": occurrence_id,
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": traces,
    }
    consequence_payload = {
        "status": "PASS",
        "trackable_action_consequence_candidate_count": 1,
        "trackable_action_consequence_candidates": [
            _consequence(occurrence_id, admitted)
        ],
        "window_seconds": [5.0, 8.0, 12.0],
        "max_follow_up_time_layers": 3,
    }
    return trace_payload, consequence_payload


def _episode_payload(boundary_second: float) -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "administrative_boundary_candidates": [
            {
                "administrative_boundary_candidate_id": "aeb_half",
                "boundary_type": "HALFTIME",
                "period_candidate": "1",
                "second_candidate": boundary_second,
                "review_debt_count": 0,
                "same_time_visible_layer_collision": False,
                "boundary_can_split_same_time_visible_layer": False,
                "boundary_is_football_action_truth": False,
                "boundary_is_phase_truth": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_admitted_followup_can_be_horizon_sensitive_without_becoming_terminal_truth() -> None:
    trace_payload, consequence_payload = _payload(16.0)
    result = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    row = result["occurrence_consequence_projections"][0]
    assert row["admitted_followup_horizon_sensitivity_tested"] is True
    assert row["admitted_followup_horizon_sensitive"] is True
    assert row["admitted_followup_horizon_sensitivity_state"] == "SENSITIVE_ACROSS_DECLARED_WINDOWS"
    assert row["admitted_followup_horizon_profile"] == [
        {
            "window_seconds": 5.0,
            "admitted_after_followup_trace_count": 0,
            "admitted_after_followup_present": False,
        },
        {
            "window_seconds": 8.0,
            "admitted_after_followup_trace_count": 1,
            "admitted_after_followup_present": True,
        },
        {
            "window_seconds": 12.0,
            "admitted_after_followup_trace_count": 1,
            "admitted_after_followup_present": True,
        },
    ]
    assert row["admitted_followup_horizon_profile_is_terminal_outcome_truth"] is False
    assert row["admitted_followup_horizon_profile_is_causal_truth"] is False
    assert result["admitted_followup_horizon_sensitive_occurrence_count"] == 1
    assert "admitted_followup_horizon_sensitive_occurrence_present" in result["review_hits"]


def test_no_followup_without_observation_end_cannot_be_called_horizon_stable() -> None:
    trace_payload, consequence_payload = _payload(None)
    result = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    row = result["occurrence_consequence_projections"][0]
    assert row["admitted_followup_horizon_sensitivity_tested"] is False
    assert row["admitted_followup_horizon_sensitive"] is False
    assert row["admitted_followup_horizon_sensitivity_state"] == "HORIZON_SENSITIVITY_UNRESOLVED_BY_CENSORING"
    assert row["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert row["observation_status"] == "CENSORING_NOT_ASSESSED"
    assert row["no_visible_followup_is_failure"] is False
    assert row["right_censoring_assessed"] is False


def test_no_followup_is_stable_only_when_declared_horizon_was_observable() -> None:
    trace_payload, consequence_payload = _payload(None)
    result = build_occurrence_consequence_projection(
        trace_payload,
        consequence_payload,
        _episode_payload(30.0),
    )

    row = result["occurrence_consequence_projections"][0]
    assert row["admitted_followup_horizon_sensitivity_tested"] is True
    assert row["admitted_followup_horizon_sensitive"] is False
    assert row["admitted_followup_horizon_sensitivity_state"] == "STABLE_ACROSS_DECLARED_WINDOWS"
    assert row["followup_observation_status"] == "NO_VISIBLE_FOLLOWUP"
    assert row["observation_status"] == "COMPLETE_TO_HORIZON"
    assert row["right_censoring_assessed"] is True
    assert row["no_visible_followup_is_failure"] is False


def test_missing_followup_trace_time_keeps_horizon_sensitivity_unresolved() -> None:
    trace_payload, consequence_payload = _payload(16.0)
    trace_payload["trackable_action_trace_candidates"] = [
        trace_payload["trackable_action_trace_candidates"][0]
    ]
    result = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    row = result["occurrence_consequence_projections"][0]
    assert row["admitted_followup_horizon_sensitivity_tested"] is False
    assert row["admitted_followup_horizon_sensitivity_state"] == "HORIZON_SENSITIVITY_UNRESOLVED"
    assert result["admitted_followup_horizon_sensitivity_unresolved_occurrence_count"] == 1
    assert "admitted_followup_horizon_sensitivity_unresolved" in result["review_hits"]


def test_horizon_grid_is_construct_definition_not_sequence_or_causal_truth() -> None:
    trace_payload, consequence_payload = _payload(13.0)
    result = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert result["source_consequence_horizon"]["horizon_is_construct_definition"] is True
    assert result["admitted_followup_horizon_profile_uses_after_confirmed_only"] is True
    assert result["admitted_followup_horizon_sensitivity_is_terminal_outcome_truth"] is False
    assert result["projection_is_sequence_truth"] is False
    assert result["projection_is_causal_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
