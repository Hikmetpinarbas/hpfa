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


def test_no_visible_followup_is_observation_state_not_failure() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "NO_VISIBLE_FOLLOWUP"
    assert row["observation_status"] == "CENSORING_NOT_ASSESSED"
    assert row["no_visible_followup_is_failure"] is False
    assert row["terminal_status"] == "TERMINAL_STATE_UNRESOLVED"
    assert row["terminal_type"] == "UNKNOWN"
    assert payload["no_visible_followup_is_failure"] is False
    assert payload["right_censoring_assessed"] is False


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
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(visible=True, admitted=True),
    )
    row = payload["occurrence_consequence_projections"][0]
    assert row["followup_observation_status"] == "VISIBLE_FOLLOWUP"
    assert row["process_continuation_status"] == "PROCESS_CONTINUES_VISIBLE_CANDIDATE"
    assert row["observation_status"] == "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON"
    assert row["terminal_status"] == "TERMINAL_STATE_UNRESOLVED"
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
    )
    horizon = declared["source_consequence_horizon"]
    assert horizon["horizon_definition_state"] == "DECLARED_SOURCE_HORIZON"
    assert horizon["maximum_window_seconds"] == 12.0
    assert horizon["max_follow_up_time_layers"] == 3
    assert horizon["horizon_is_construct_definition"] is True
    assert horizon["same_episode_terminal_horizon_assessed"] is False

    unspecified = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(include_horizon=False),
    )
    assert unspecified["source_consequence_horizon"]["horizon_definition_state"] == "HORIZON_UNSPECIFIED"
    assert "consequence_horizon_unspecified" in unspecified["review_hits"]
    assert unspecified["status"] == "REVIEW_REQUIRED"


def test_truth_and_release_locks_remain_closed() -> None:
    payload = build_occurrence_consequence_projection(
        _trace_payload(),
        _consequence_payload(visible=True, admitted=True),
    )
    assert payload["outcome_polarity_emitted"] is False
    assert payload["projection_is_causal_truth"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False
