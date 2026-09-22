from __future__ import annotations

from copy import deepcopy

import trackable_action_consequence_candidates_current_v1 as current


def _trace(trace_id: str, *, team: str, start: float, families: list[str]) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "team_identity_candidate_id": team,
        "start_candidate": start,
        "action_family_candidates": families,
    }


def _payload(primary: str, admitted_ids: list[str]) -> dict:
    return {
        "status": "PASS",
        "module_status": "PASS",
        "hard_block_hits": [],
        "review_hits": [],
        "trackable_action_consequence_candidates": [
            {
                "anchor_trackable_action_trace_candidate_id": "anchor",
                "admitted_after_follow_up_trace_ids": admitted_ids,
                "primary_consequence_candidate": primary,
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            }
        ],
        "primary_consequence_candidate_counts": {primary: 1},
        "review_required_consequence_candidate_count": 0,
        "classified_consequence_candidate_count": 1,
    }


def test_first_eligible_followup_is_not_replaced_by_later_shot_presence() -> None:
    trace_payload = {
        "trackable_action_trace_candidates": [
            _trace("anchor", team="A", start=10.0, families=["TURNOVER"]),
            _trace("opp_pass", team="B", start=11.0, families=["PASS"]),
            _trace("same_shot", team="A", start=14.0, families=["SHOT"]),
        ]
    }
    out = current._bind_first_eligible_vs_horizon_semantics(
        _payload("SHOT_FOLLOW_UP_CANDIDATE", ["opp_pass", "same_shot"]),
        trace_payload,
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["legacy_horizon_mixed_primary_consequence_candidate"] == "SHOT_FOLLOW_UP_CANDIDATE"
    assert row["primary_consequence_candidate"] == "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
    assert row["first_eligible_follow_up_trace_ids"] == ["opp_pass"]
    assert row["first_eligible_action_family_candidates"] == ["PASS"]
    assert row["first_eligible_team_relation"] == "OPPONENT"
    assert row["admitted_horizon_action_family_candidates_by_team_relation"] == {
        "SAME_TEAM": ["SHOT"],
        "OPPONENT": ["PASS"],
        "UNKNOWN": [],
    }
    assert row["target_consequence_within_horizon"] is None
    assert row["target_consequence_query_state"] == "NOT_SPECIFIED_BY_CONSTRUCT"
    assert row["horizon_family_presence_is_target_consequence_truth"] is False
    assert out["first_eligible_primary_reclassification_count"] == 1
    assert out["target_consequence_result_emitted"] is False
    assert row["time_to_first_admitted_visible_state_change_seconds_candidate"] == 1.0
    assert row["time_to_first_admitted_visible_state_change_observation_state"] == "OBSERVED_ADMITTED_AFTER"
    assert row["time_to_first_admitted_visible_state_change_is_physical_advantage_window_truth"] is False
    profile = out["time_to_first_admitted_visible_state_change_profile"]
    assert profile["eligible_observed_n"] == 1
    assert profile["median_seconds_candidate"] == 1.0
    assert profile["distribution_is_descriptive_not_first_passage_model"] is True
    assert profile["global_5_8_12_window_is_production_threshold"] is False


def test_same_time_first_layer_stays_unordered_and_mixed() -> None:
    trace_payload = {
        "trackable_action_trace_candidates": [
            _trace("anchor", team="A", start=20.0, families=["PASS"]),
            _trace("same_pass", team="A", start=21.0, families=["PASS"]),
            _trace("opp_recovery", team="B", start=21.0, families=["RECOVERY"]),
        ]
    }
    out = current._bind_first_eligible_vs_horizon_semantics(
        _payload("SAME_TEAM_CONTINUATION_CANDIDATE", ["same_pass", "opp_recovery"]),
        trace_payload,
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["first_eligible_consequence_binding_state"] == "SAME_TIME_UNORDERED_FIRST_LAYER"
    assert row["first_eligible_follow_up_trace_ids"] == ["opp_recovery", "same_pass"]
    assert row["first_eligible_team_relation"] == "MIXED"
    assert row["primary_consequence_candidate"] == "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    assert row["same_timestamp_first_layer_internal_ordering_allowed"] is False
    assert row["record_status"] == "REVIEW_REQUIRED"
    assert out["review_required_consequence_candidate_count"] == 1
    assert row["time_to_first_admitted_visible_state_change_seconds_candidate"] == 1.0
    assert row["time_to_first_admitted_visible_state_change_observation_state"] == "OBSERVED_ADMITTED_AFTER"


def test_no_admitted_after_followup_does_not_invent_first_or_target_result() -> None:
    trace_payload = {
        "trackable_action_trace_candidates": [
            _trace("anchor", team="A", start=30.0, families=["SHOT"]),
        ]
    }
    original = _payload("TERMINAL_OUTCOME_SUPPORT_CANDIDATE", [])
    original["trackable_action_consequence_candidates"][0]["terminal_outcome_support_visible"] = True
    out = current._bind_first_eligible_vs_horizon_semantics(deepcopy(original), trace_payload)
    row = out["trackable_action_consequence_candidates"][0]

    assert row["primary_consequence_candidate"] == "TERMINAL_OUTCOME_SUPPORT_CANDIDATE"
    assert row["first_eligible_consequence_binding_state"] == "NO_ADMITTED_AFTER_FOLLOWUP"
    assert row["first_eligible_follow_up_trace_ids"] == []
    assert row["first_eligible_team_relation"] == "NONE"
    assert row["target_consequence_within_horizon"] is None
    assert row["target_consequence_query_required_for_target_claim"] is True
    assert row["diagnostic_horizon_family_presence_can_authorize_claim"] is False
    assert row["time_to_first_admitted_visible_state_change_seconds_candidate"] is None
    assert row["time_to_first_admitted_visible_state_change_observation_state"] == "NO_ADMITTED_AFTER_FOLLOWUP"
    assert out["time_to_first_admitted_visible_state_change_profile"]["observation_state_counts"]["NO_ADMITTED_AFTER_FOLLOWUP"] == 1


def test_time_profile_uses_median_and_keeps_no_followup_out_of_observed_distribution() -> None:
    trace_payload = {
        "trackable_action_trace_candidates": [
            _trace("a1", team="A", start=10.0, families=["PASS"]),
            _trace("f1", team="A", start=11.0, families=["PASS"]),
            _trace("a2", team="A", start=20.0, families=["PASS"]),
            _trace("f2", team="A", start=24.0, families=["PASS"]),
            _trace("a3", team="A", start=30.0, families=["PASS"]),
        ]
    }
    payload = {
        "status": "PASS",
        "module_status": "PASS",
        "hard_block_hits": [],
        "review_hits": [],
        "trackable_action_consequence_candidates": [
            {
                "anchor_trackable_action_trace_candidate_id": "a1",
                "admitted_after_follow_up_trace_ids": ["f1"],
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            },
            {
                "anchor_trackable_action_trace_candidate_id": "a2",
                "admitted_after_follow_up_trace_ids": ["f2"],
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            },
            {
                "anchor_trackable_action_trace_candidate_id": "a3",
                "admitted_after_follow_up_trace_ids": [],
                "primary_consequence_candidate": "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            },
        ],
        "primary_consequence_candidate_counts": {},
        "review_required_consequence_candidate_count": 0,
        "classified_consequence_candidate_count": 3,
    }

    out = current._bind_first_eligible_vs_horizon_semantics(payload, trace_payload)
    profile = out["time_to_first_admitted_visible_state_change_profile"]

    assert profile["eligible_observed_n"] == 2
    assert profile["distribution_values_seconds_candidate"] == [1.0, 4.0]
    assert profile["median_seconds_candidate"] == 2.5
    assert profile["observation_state_counts"]["NO_ADMITTED_AFTER_FOLLOWUP"] == 1
    assert profile["right_censoring_model_applied"] is False
    assert profile["no_admitted_after_is_failure"] is False
    assert profile["graphability_state"] == "GRAPH_READY_WITH_REVIEW"


def test_missing_followup_trace_keeps_semantics_unresolved_instead_of_guessing() -> None:
    trace_payload = {
        "trackable_action_trace_candidates": [
            _trace("anchor", team="A", start=40.0, families=["TURNOVER"]),
        ]
    }
    out = current._bind_first_eligible_vs_horizon_semantics(
        _payload("SHOT_FOLLOW_UP_CANDIDATE", ["missing_trace"]),
        trace_payload,
    )
    row = out["trackable_action_consequence_candidates"][0]

    assert row["first_eligible_consequence_binding_state"] == "UNRESOLVED_TRACE_LINEAGE"
    assert row["primary_consequence_candidate"] == "SHOT_FOLLOW_UP_CANDIDATE"
    assert out["first_eligible_semantics_unresolved_record_count"] == 1
    assert "first_eligible_consequence_semantics_unresolved" in out["review_hits"]
    assert row["time_to_first_admitted_visible_state_change_seconds_candidate"] is None
    assert row["time_to_first_admitted_visible_state_change_observation_state"] == "UNRESOLVED_TRACE_LINEAGE"
