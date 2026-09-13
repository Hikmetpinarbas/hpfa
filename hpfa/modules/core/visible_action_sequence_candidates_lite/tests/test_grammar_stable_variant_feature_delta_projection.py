from __future__ import annotations

import json

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.grammar_stable_variant_feature_delta_projection import (
    build_grammar_stable_variant_feature_delta,
)


def _sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_success",
                "time_layer_refs": ["l0"],
                "node_records": [
                    {"time_layer_ref": "l0", "occurrence_refs": ["o1"]},
                ],
                "supporting_action_occurrence_candidate_ids": ["o1"],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "time_layer_refs": ["l0"],
                "node_records": [
                    {"time_layer_ref": "l0", "occurrence_refs": ["o2"]},
                ],
                "supporting_action_occurrence_candidate_ids": ["o2"],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _two_layer_sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_success",
                "time_layer_refs": ["s_l0", "s_l1"],
                "node_records": [
                    {"time_layer_ref": "s_l0", "occurrence_refs": ["o1a"]},
                    {"time_layer_ref": "s_l1", "occurrence_refs": ["o1b"]},
                ],
                "supporting_action_occurrence_candidate_ids": ["o1a", "o1b"],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "time_layer_refs": ["f_l0", "f_l1"],
                "node_records": [
                    {"time_layer_ref": "f_l0", "occurrence_refs": ["o2a"]},
                    {"time_layer_ref": "f_l1", "occurrence_refs": ["o2b"]},
                ],
                "supporting_action_occurrence_candidate_ids": ["o2a", "o2b"],
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
                "grammar_signature_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "member_records": [
                    {
                        "variant_ref": "v_success",
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "v_failure",
                        "sequence_ref": "s2",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                    },
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _state(*, missing_failure: bool = False) -> dict:
    rows = [
        {
            "action_occurrence_candidate_id": "o1",
            "actor_identity_candidate_ids": ["actor_success"],
            "action_family_candidates": ["PASS"],
            "occurrence_topology": "SINGLE_ACTOR_ACTION",
            "required_participant_scope": "ACTOR_ONLY",
            "binding_state": "ACTOR_TRACE_VISIBLE_CANDIDATE",
            "provider_direction_candidates": ["FORWARD"],
            "provider_zone_candidates": ["FINAL_THIRD"],
            "provider_outcome_candidates": ["SUCCESS"],
            "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
            "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
            "support_candidates": ["VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT"],
        }
    ]
    if not missing_failure:
        rows.append(
            {
                "action_occurrence_candidate_id": "o2",
                "actor_identity_candidate_ids": ["actor_failure"],
                "action_family_candidates": ["PASS"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "ACTOR_TRACE_VISIBLE_CANDIDATE",
                "provider_direction_candidates": [],
                "provider_zone_candidates": [],
                "provider_outcome_candidates": ["FAILURE"],
                "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "adverse_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "transition_class_candidates": ["VISIBLE_DIRECTIONAL_CONSEQUENCE_TRANSITION_CANDIDATE"],
                "support_candidates": ["VISIBLE_CONSEQUENCE_CANDIDATE_PRESENT"],
            }
        )
    return {
        "status": "PASS",
        "occurrence_state_transition_projections": rows,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _two_layer_state() -> dict:
    rows = []
    for occurrence_id, actor, direction in (
        ("o1a", "actor_a", ["FORWARD"]),
        ("o1b", "actor_success_second", ["FORWARD"]),
        ("o2a", "actor_a", ["FORWARD"]),
        ("o2b", "actor_failure_second", []),
    ):
        rows.append(
            {
                "action_occurrence_candidate_id": occurrence_id,
                "actor_identity_candidate_ids": [actor],
                "action_family_candidates": ["PASS"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "ACTOR_TRACE_VISIBLE_CANDIDATE",
                "provider_direction_candidates": direction,
                "provider_zone_candidates": [],
                "primary_consequence_candidates": [],
                "transition_class_candidates": [],
                "support_candidates": [],
            }
        )
    return {
        "status": "PASS",
        "occurrence_state_transition_projections": rows,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence() -> dict:
    return {
        "status": "PASS",
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o1",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
            {
                "action_occurrence_candidate_id": "o2",
                "consequence_signal_candidates": ["OPPONENT_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _two_layer_consequence() -> dict:
    return {
        "status": "PASS",
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o1a",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
            {
                "action_occurrence_candidate_id": "o1b",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
            {
                "action_occurrence_candidate_id": "o2a",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
            {
                "action_occurrence_candidate_id": "o2b",
                "consequence_signal_candidates": [
                    "OPPONENT_FOLLOW_UP_VISIBLE",
                    "OPPONENT_SHOT_FOLLOW_UP_VISIBLE",
                ],
                "primary_consequence_candidates": ["OPPONENT_HANDOVER_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_same_grammar_different_outcome_exposes_admitted_feature_difference() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    assert result["status"] == "PASS"
    assert result["grammar_stable_variant_feature_delta_record_count"] == 1
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["success_resolved_variant_count"] == 1
    assert row["failure_resolved_variant_count"] == 1
    context = {item["feature_token"]: item for item in row["context_feature_difference_candidates"]}
    assert context["provider_direction_candidates:FORWARD"]["success_visible_numerator"] == 1
    assert context["provider_direction_candidates:FORWARD"]["failure_visible_numerator"] == 0
    assert context["actor_identity_candidate_ids:actor_success"]["success_visible_numerator"] == 1
    consequence = {item["feature_token"]: item for item in row["consequence_feature_difference_candidates"]}
    assert consequence["primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"]["failure_visible_numerator"] == 1
    assert consequence["primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"]["difference_is_failure_cause_truth"] is False


def test_partial_order_layer_discrimination_preserves_first_supported_difference_without_total_order_claim() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _two_layer_sequence(), _process_variants(), _two_layer_state(), _two_layer_consequence()
    )
    row = result["grammar_stable_variant_feature_delta_records"][0]
    context = {item["feature_token"]: item for item in row["context_feature_difference_candidates"]}
    consequence = {item["feature_token"]: item for item in row["consequence_feature_difference_candidates"]}
    assert "LAYER[1]::actor_identity_candidate_ids:actor_failure_second" in context
    assert "LAYER[1]::ensuing_visible_chain:OPPONENT_HANDOVER_PLUS_OPPONENT_SHOT_VISIBLE" in consequence
    assert row["first_supported_context_difference_layer_candidate"] == 1
    assert row["first_supported_consequence_difference_layer_candidate"] == 1
    assert row["partial_order_layer_position_is_total_order_truth"] is False
    assert row["layer_position_does_not_order_same_time_peers"] is True
    assert row["ensuing_visible_chain_is_causal_truth"] is False


def test_right_censoring_is_propagated_as_observation_debt_not_failure() -> None:
    consequence_payload = _consequence()
    consequence_payload["source_consequence_horizon"] = {
        "horizon_definition_state": "DECLARED_SOURCE_HORIZON"
    }
    consequence_payload["right_censoring_assessed"] = True
    success_row, failure_row = consequence_payload["occurrence_consequence_projections"]
    success_row.update({
        "right_censoring_status": "NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
        "right_censoring_assessed": True,
        "right_censored": False,
    })
    failure_row.update({
        "consequence_signal_candidates": [],
        "primary_consequence_candidates": ["NO_VISIBLE_FOLLOW_UP_CANDIDATE"],
        "visible_consequence_support": False,
        "right_censoring_status": "RIGHT_CENSORED_BY_ADMIN_BOUNDARY",
        "right_censoring_assessed": True,
        "right_censored": True,
    })

    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), consequence_payload
    )
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["right_censoring_assessed"] is True
    assert row["right_censored_variant_count"] == 1
    assert row["right_censoring_incomplete_variant_count"] == 0
    assert row["right_censoring_is_failure"] is False
    consequence = {item["feature_token"]: item for item in row["consequence_feature_difference_candidates"]}
    censored = consequence["right_censoring_status:RIGHT_CENSORED_BY_ADMIN_BOUNDARY"]
    assert censored["failure_visible_numerator"] == 1
    assert censored["success_visible_numerator"] == 0
    assert "variant_right_censored_occurrence_present:fam_1" in result["review_hits"]


def test_outcome_semantics_are_partition_labels_not_compared_features() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    rendered = json.dumps(result, ensure_ascii=False)
    assert "provider_outcome_candidates:SUCCESS" not in rendered
    assert "provider_outcome_candidates:FAILURE" not in rendered
    assert result["outcome_used_only_as_partition_label"] is True
    assert result["outcome_used_to_define_features"] is False


def test_missing_feature_surface_is_review_not_negative_evidence() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(missing_failure=True), _consequence()
    )
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["context_coverage_incomplete_variant_count"] == 1
    assert row["feature_absence_is_counterevidence"] is False


def test_no_same_timestamp_first_difference_or_causal_promotion() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["same_timestamp_internal_ordering_used_for_first_difference"] is False
    assert row["difference_is_failure_cause_truth"] is False
    assert row["difference_is_tactical_explanation"] is False
    assert row["independent_recurrence_support_count"] == 0
    assert row["dependency_independence_proven"] is False


def test_truth_and_release_locks_remain_closed() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["difference_rows_are_independent_evidence_votes"] is False
    assert result["ensuing_visible_chain_is_causal_truth"] is False
    assert result["actor_identity_difference_is_player_quality_truth"] is False


def test_claimed_event_truth_fails_closed() -> None:
    bad = _sequence()
    bad["canonical_event_count"] = 2
    result = build_grammar_stable_variant_feature_delta(
        bad, _process_variants(), _state(), _consequence()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["grammar_stable_variant_feature_delta_record_count"] == 0


def test_no_sample_match_identity_leak() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence(), _process_variants(), _state(), _consequence()
    )
    rendered = json.dumps(result, ensure_ascii=False).casefold()
    for forbidden in ("sporting", "roma", "fenerbah", "galatasaray"):
        assert forbidden not in rendered
