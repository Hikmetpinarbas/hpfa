from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.grammar_stable_variant_feature_delta_projection import (
    build_grammar_stable_variant_feature_delta,
)


def _sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_recovery_response",
                "time_layer_refs": ["r0"],
                "node_records": [
                    {"time_layer_ref": "r0", "occurrence_refs": ["o_recovery_response"]}
                ],
            },
            {
                "partial_order_occurrence_variant_id": "v_opponent_takeover",
                "time_layer_refs": ["t0"],
                "node_records": [
                    {"time_layer_ref": "t0", "occurrence_refs": ["o_opponent_takeover"]}
                ],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variants() -> dict:
    return {
        "status": "PASS",
        "grammar_stable_visible_outcome_variation_family_count": 0,
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "fam_breakdown",
                "same_grammar_visible_outcome_variation_observed": False,
                "grammar_signature_tokens": ["LAYER[TURNOVER]"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "member_records": [
                    {
                        "variant_ref": "v_recovery_response",
                        "sequence_ref": "s_recovery_response",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "v_opponent_takeover",
                        "sequence_ref": "s_opponent_takeover",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _state() -> dict:
    return {
        "status": "PASS",
        "occurrence_state_transition_projections": [
            {
                "action_occurrence_candidate_id": "o_recovery_response",
                "actor_identity_candidate_ids": ["actor_a"],
                "action_family_candidates": ["TURNOVER"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
                "primary_consequence_candidates": [
                    "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
                ],
            },
            {
                "action_occurrence_candidate_id": "o_opponent_takeover",
                "actor_identity_candidate_ids": ["actor_b"],
                "action_family_candidates": ["TURNOVER"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
                "primary_consequence_candidates": [
                    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
                ],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence() -> dict:
    return {
        "status": "PASS",
        "source_consequence_horizon": {
            "horizon_definition_state": "DECLARED_SOURCE_HORIZON",
            "horizon_basis": "FIXED_TIME_WITH_LAYER_CAP_VISIBLE_TRACE_SEARCH",
            "window_seconds": [5.0, 8.0, 12.0],
            "maximum_window_seconds": 12.0,
            "max_follow_up_time_layers": 3,
            "right_censoring_assessed": True,
        },
        "right_censoring_assessed": True,
        "no_visible_followup_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "projection_is_causal_truth": False,
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o_recovery_response",
                "followup_observation_status": "VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON",
                "consequence_signal_candidates": [
                    "SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE"
                ],
                "primary_consequence_candidates": [
                    "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE"
                ],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "right_censoring_assessed": True,
                "right_censoring_status": "NOT_RIGHT_CENSORED",
            },
            {
                "action_occurrence_candidate_id": "o_opponent_takeover",
                "followup_observation_status": "VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_BREAK_VISIBLE_CANDIDATE",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON",
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": [
                    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
                ],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "right_censoring_assessed": True,
                "right_censoring_status": "NOT_RIGHT_CENSORED",
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_same_grammar_breakdown_variants_can_contrast_visible_consequence_without_provider_outcome_split() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )

    assert result["grammar_stable_consequence_contrast_record_count"] == 1
    row = result["grammar_stable_consequence_contrast_records"][0]
    assert row["source_process_variant_family_ref"] == "fam_breakdown"
    assert row["consequence_variant_state"] == "GRAMMAR_STABLE_VISIBLE_CONSEQUENCE_VARIATION"
    assert row["provider_outcome_partition_required"] is False
    assert row["visible_consequence_classes"] == [
        "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
        "RECOVERY_RESPONSE_AFTER_BREAKDOWN_CANDIDATE",
    ]
    assert row["consequence_variation_is_success_failure_truth"] is False
    assert row["consequence_variation_is_causal_truth"] is False
    assert row["consequence_variation_is_tactical_truth"] is False
    assert row["independent_recurrence_support_count"] == 0
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_visible_followup_does_not_become_failure_in_consequence_contrast() -> None:
    consequence = _consequence()
    consequence["occurrence_consequence_projections"][1].update(
        {
            "followup_observation_status": "NO_VISIBLE_FOLLOWUP",
            "process_continuation_status": "PROCESS_STATE_UNRESOLVED",
            "observation_status": "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP",
            "consequence_signal_candidates": [],
            "primary_consequence_candidates": ["NO_VISIBLE_FOLLOW_UP_CANDIDATE"],
            "visible_consequence_support": False,
            "right_censoring_status": "COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP",
        }
    )

    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), consequence
    )
    row = result["grammar_stable_consequence_contrast_records"][0]

    assert "NO_VISIBLE_FOLLOW_UP_CANDIDATE" in row["visible_consequence_classes"]
    assert row["no_visible_followup_is_failure"] is False
    assert row["consequence_variation_is_success_failure_truth"] is False
