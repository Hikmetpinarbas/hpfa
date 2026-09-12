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
                "supporting_action_occurrence_candidate_ids": ["o1"],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "supporting_action_occurrence_candidate_ids": ["o2"],
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
    consequence = {item["feature_token"]: item for item in row["consequence_feature_difference_candidates"]}
    assert consequence["primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"]["failure_visible_numerator"] == 1
    assert consequence["primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"]["difference_is_failure_cause_truth"] is False


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
