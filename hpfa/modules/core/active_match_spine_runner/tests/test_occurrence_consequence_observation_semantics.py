from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
)


def _trace_payload() -> dict:
    trace = {
        "trackable_action_trace_candidate_id": "trace_1",
        "supporting_action_occurrence_candidate_ids": ["aoc_1"],
        "action_family_candidates": ["PASS"],
        "actor_identity_candidate_id": "actor_1",
        "team_identity_candidate_id": "team_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "11.0",
    }
    return {
        "status": "PASS",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 1,
        "primary_occurrence_trace_candidates": [trace],
        "trackable_action_trace_candidates": [trace],
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
    }


def _consequence_payload(
    *,
    visible: bool = False,
    admitted: bool = False,
    terminal: bool = False,
    include_record: bool = True,
    include_horizon: bool = True,
) -> dict:
    rows = []
    if include_record:
        rows.append(
            {
                "trackable_action_consequence_candidate_id": "cons_1",
                "anchor_trackable_action_trace_candidate_id": "trace_1",
                "supporting_action_occurrence_candidate_ids": ["aoc_1"],
                "visible_follow_up_trace_ids": ["follow_1"] if visible else [],
                "admitted_after_follow_up_trace_ids": ["follow_1"] if admitted else [],
                "consequence_signal_candidates": [],
                "primary_consequence_candidate": (
                    "SAME_TEAM_CONTINUATION_CANDIDATE"
                    if admitted
                    else "NO_VISIBLE_FOLLOW_UP_CANDIDATE"
                ),
                "terminal_outcome_support_visible": terminal,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            }
        )
    payload = {
        "status": "PASS",
        "trackable_action_consequence_candidate_count": len(rows),
        "trackable_action_consequence_candidates": rows,
    }
    if include_horizon:
        payload["window_seconds"] = [5.0, 8.0, 12.0]
        payload["max_follow_up_time_layers"] = 3
    return payload


def _episode_payload(
    boundary_second: float,
    *,
    review_debt_count: int = 0,
    review_reason: str | None = None,
    same_time_collision: bool = False,
) -> dict:
    review_refs = (
        [{"context_id": "ctx_admin", "reason": review_reason}]
        if review_reason
        else []
    )
    return {
        "status": "REVIEW_REQUIRED",
        "administrative_boundary_candidates": [
            {
                "administrative_boundary_candidate_id": "aeb_half",
                "boundary_type": "HALFTIME",
                "period_candidate": "1",
                "second_candidate": boundary_second,
                "review_debt_count": review_debt_count,
                "review_debt_refs": review_refs,
                "same_time_visible_layer_collision": same_time_collision,
                "boundary_can_split_same_time_visible_layer": False,
                "boundary_is_football_action_truth": False,
                "boundary_is_phase_truth": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_no_visible_followup_without_boundary_is_unresolved_not_failure() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert row["observation_status"] == "CENSORING_NOT_ASSESSED"
    assert row["no_visible_followup_is_failure"] is False
    assert row["terminal_status"] == "TERMINAL_STATE_UNRESOLVED"
    assert row["right_censoring_assessed"] is False
    assert payload["right_censoring_assessed"] is False


def test_complete_admin_horizon_allows_no_visible_followup_observation_state() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(30.0),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "NO_VISIBLE_FOLLOWUP"
    assert row["observation_status"] == "COMPLETE_TO_HORIZON"
    assert row["right_censoring_status"] == "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP"
    assert row["right_censoring_assessed"] is True
    assert row["right_censored"] is False
    assert row["declared_horizon_fully_observable"] is True
    assert row["seconds_to_observation_boundary_min"] == 20.0
    assert payload["right_censoring_assessed"] is True
    assert payload["complete_to_declared_horizon_no_admitted_followup_count"] == 1
    assert row["no_visible_followup_is_failure"] is False


def test_admin_boundary_before_full_horizon_marks_right_censoring_not_failure() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(18.0),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "FOLLOWUP_CENSORED"
    assert row["observation_status"] == "RIGHT_CENSORED"
    assert row["right_censoring_status"] == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY"
    assert row["right_censoring_assessed"] is True
    assert row["right_censored"] is True
    assert row["declared_horizon_fully_observable"] is False
    assert row["seconds_to_observation_boundary_min"] == 8.0
    assert row["admitted_followup_horizon_sensitivity_tested"] is False
    assert row["admitted_followup_horizon_sensitivity_state"] == "HORIZON_SENSITIVITY_CENSORED"
    assert payload["right_censored_occurrence_count"] == 1
    assert row["no_visible_followup_is_failure"] is False


def test_unspecified_boundary_review_debt_keeps_censoring_unresolved() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(18.0, review_debt_count=1),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert row["observation_status"] == "CENSORING_UNRESOLVED"
    assert row["right_censoring_status"] == "CENSORING_UNRESOLVED_END_BOUNDARY_REVIEW_DEBT"
    assert row["right_censoring_assessed"] is False
    assert payload["right_censoring_assessed"] is False
    assert "right_censoring_unresolved_occurrence_present" in payload["review_hits"]


def test_serialization_only_boundary_review_debt_does_not_block_censoring_assessment() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(
            18.0,
            review_debt_count=3,
            review_reason="visible_field_serialization_discrepancy",
        ),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["right_censoring_status"] == "RIGHT_CENSORED_BY_ADMIN_BOUNDARY"
    assert row["right_censoring_assessed"] is True
    assert row["right_censored"] is True
    assert row["observation_boundary_review_reasons"] == [
        "visible_field_serialization_discrepancy"
    ]
    assert row["administrative_boundary_reflections_are_independent_evidence_votes"] is False
    assert payload["administrative_boundary_reflections_are_independent_evidence_votes"] is False


def test_numeric_visible_followup_without_admitted_order_stays_unresolved() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(visible=True),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert row["observation_status"] == "ORDER_INDETERMINATE"
    assert row["followup_is_terminal_outcome_truth"] is False


def test_admitted_after_followup_is_visible_but_not_terminal_truth() -> None:
    trace_payload = _trace_payload()
    follow = {
        "trackable_action_trace_candidate_id": "follow_1",
        "action_family_candidates": ["PASS"],
        "actor_identity_candidate_id": "actor_2",
        "team_identity_candidate_id": "team_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "14.0",
        "end_candidate": "15.0",
    }
    trace_payload["trackable_action_trace_candidates"].append(follow)
    trace_payload["trackable_action_trace_candidate_count"] = 2
    payload = build_occurrence_consequence_projection(
        trace_payload,
        _consequence_payload(visible=True, admitted=True),
        _episode_payload(18.0),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "VISIBLE_FOLLOWUP"
    assert row["process_continuation_status"] == "PROCESS_CONTINUES_VISIBLE_CANDIDATE"
    assert row["observation_status"] == "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON"
    assert row["terminal_status"] == "TERMINAL_STATE_UNRESOLVED"
    assert row["right_censoring_status"] == "NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"
    assert row["right_censoring_assessed"] is True
    assert row["followup_is_terminal_outcome_truth"] is False


def test_terminal_support_does_not_invent_terminal_type() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(terminal=True),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["terminal_status"] == "TERMINAL_SUPPORT_VISIBLE_TYPE_UNRESOLVED"
    assert row["terminal_type"] == "UNKNOWN"
    assert row["terminal_support_is_terminal_type_truth"] is False
    assert payload["competing_terminal_outcomes_assessed"] is False


def test_missing_consequence_record_is_source_coverage_unresolved_not_failure() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(include_record=False),
        _episode_payload(30.0),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "FOLLOWUP_UNRESOLVED"
    assert row["observation_status"] == "SOURCE_COVERAGE_INSUFFICIENT"
    assert row["no_visible_followup_is_failure"] is False
    assert payload["status"] == "REVIEW_REQUIRED"


def test_horizon_is_explicit_construct_definition_and_missing_horizon_reviews() -> None:
    declared = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(30.0),
    )
    horizon = declared["source_consequence_horizon"]
    assert horizon["horizon_definition_state"] == "DECLARED_SOURCE_HORIZON"
    assert horizon["maximum_window_seconds"] == 12.0
    assert horizon["max_follow_up_time_layers"] == 3
    assert horizon["horizon_is_construct_definition"] is True
    assert horizon["same_episode_terminal_horizon_assessed"] is False
    assert horizon["right_censoring_assessed"] is True

    unspecified = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(include_horizon=False),
        _episode_payload(30.0),
    )
    assert unspecified["source_consequence_horizon"]["horizon_definition_state"] == "HORIZON_UNSPECIFIED"
    assert "consequence_horizon_unspecified" in unspecified["review_hits"]
    assert unspecified["status"] == "REVIEW_REQUIRED"


def test_truth_and_release_locks_remain_closed() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
        _episode_payload(30.0),
    )
    assert payload["outcome_polarity_emitted"] is False
    assert payload["projection_is_causal_truth"] is False
    assert payload["administrative_boundary_is_football_action_truth"] is False
    assert payload["administrative_boundary_is_phase_truth"] is False
    assert payload["administrative_boundary_orders_same_time_action"] is False
    assert payload["administrative_boundary_reflections_are_independent_evidence_votes"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False
