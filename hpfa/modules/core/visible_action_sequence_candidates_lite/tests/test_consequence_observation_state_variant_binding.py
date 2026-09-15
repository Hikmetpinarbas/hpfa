from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.grammar_stable_variant_feature_delta_projection import (
    build_grammar_stable_variant_feature_delta,
)


def _sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_success",
                "time_layer_refs": ["s0"],
                "node_records": [{"time_layer_ref": "s0", "occurrence_refs": ["o_success"]}],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "time_layer_refs": ["f0"],
                "node_records": [{"time_layer_ref": "f0", "occurrence_refs": ["o_failure"]}],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variants() -> dict:
    return {
        "status": "PASS",
        "grammar_stable_visible_outcome_variation_family_count": 1,
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "fam_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "grammar_signature_tokens": ["LAYER[PASS]"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "member_records": [
                    {
                        "variant_ref": "v_success",
                        "sequence_ref": "s_success",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "v_failure",
                        "sequence_ref": "s_failure",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
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
                "action_occurrence_candidate_id": "o_success",
                "actor_identity_candidate_ids": ["actor_a"],
                "action_family_candidates": ["PASS"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
                "provider_direction_candidates": ["FORWARD"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
            },
            {
                "action_occurrence_candidate_id": "o_failure",
                "actor_identity_candidate_ids": ["actor_b"],
                "action_family_candidates": ["PASS"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
                "provider_direction_candidates": ["FORWARD"],
                "primary_consequence_candidates": [],
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
            "right_censoring_assessed": False,
        },
        "right_censoring_assessed": False,
        "no_visible_followup_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "projection_is_causal_truth": False,
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o_success",
                "followup_observation_status": "VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
            {
                "action_occurrence_candidate_id": "o_failure",
                "followup_observation_status": "NO_VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_STATE_UNRESOLVED",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "CENSORING_NOT_ASSESSED",
                "consequence_signal_candidates": [],
                "primary_consequence_candidates": ["NO_VISIBLE_FOLLOW_UP_CANDIDATE"],
                "visible_consequence_support": False,
                "terminal_outcome_support_visible": False,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_variant_discrimination_consumes_followup_terminal_and_observation_states() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    assert result["consequence_observation_state_features_consumed"] is True
    assert result["consequence_horizon_definition_state"] == "DECLARED_SOURCE_HORIZON"
    assert result["consequence_horizon_sensitivity_tested"] is False
    assert result["right_censoring_assessed"] is False
    row = result["grammar_stable_variant_feature_delta_records"][0]
    features = {
        item["feature_token"]: item
        for item in row["consequence_feature_difference_candidates"]
    }
    assert "followup_observation_status:VISIBLE_FOLLOWUP" in features
    assert "followup_observation_status:NO_VISIBLE_FOLLOWUP" in features
    assert "observation_status:CENSORING_NOT_ASSESSED" in features
    assert "LAYER[0]::followup_observation_status:NO_VISIBLE_FOLLOWUP" in features
    assert row["no_visible_followup_is_failure"] is False
    assert row["followup_is_terminal_outcome_truth"] is False


def test_no_visible_followup_failure_promotion_fails_closed() -> None:
    consequence = _consequence()
    consequence["no_visible_followup_is_failure"] = True
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), consequence
    )
    assert result["status"] == "FAIL_CLOSED"
    assert "no_visible_followup_failure_lock_breached" in result["hard_block_hits"]
    assert result["grammar_stable_variant_feature_delta_record_count"] == 0


def test_unspecified_consequence_horizon_is_review_not_silent_assumption() -> None:
    consequence = _consequence()
    consequence["source_consequence_horizon"] = {}
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), consequence
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert "consequence_horizon_unspecified" in result["review_hits"]
    assert result["consequence_horizon_definition_state"] == "HORIZON_UNSPECIFIED"


def test_observation_state_difference_is_not_causal_or_counterevidence_truth() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["feature_absence_is_counterevidence"] is False
    assert row["difference_is_failure_cause_truth"] is False
    assert row["ensuing_visible_chain_is_causal_truth"] is False
    assert result["difference_rows_are_independent_evidence_votes"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
