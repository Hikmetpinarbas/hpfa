from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.first_supported_branch_divergence_projection import (
    build_first_supported_branch_divergence,
)


def _sequence_payload() -> dict:
    return {
        "anchor_centered_sequence_branch_map_status": "PASS",
        "anchor_centered_sequence_branch_maps": [
            {
                "anchor_centered_sequence_branch_map_id": "map_a",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "2",
                "anchor_time_layer_ref": "layer_anchor",
                "anchor_time_candidate": 100.0,
                "anchor_action_family_counts": {"PASS": 2},
                "branch_records": [
                    {
                        "branch_direction": "SUCCESSOR",
                        "neighbor_time_layer_ref": "layer_success",
                        "neighbor_time_candidate": 105.0,
                        "neighbor_supporting_action_occurrence_candidate_ids": ["occ_success"],
                        "supporting_visible_sequence_candidate_ids": ["seq_success"],
                    },
                    {
                        "branch_direction": "SUCCESSOR",
                        "neighbor_time_layer_ref": "layer_failure",
                        "neighbor_time_candidate": 108.0,
                        "neighbor_supporting_action_occurrence_candidate_ids": ["occ_failure"],
                        "supporting_visible_sequence_candidate_ids": ["seq_failure"],
                    },
                ],
            }
        ],
        "branch_count_is_recurrence_count": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrence(outcome_success: str = "SUCCESS", outcome_failure: str = "FAILURE") -> dict:
    return {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_success",
                "provider_semantics_binding_status": "PASS",
                "primary_family_candidate": "PASS",
                "actor_identity_candidate_id": "actor_a",
                "team_identity_candidate_id": "team_a",
                "semantic_dimensions": {"outcome_candidate": [outcome_success]},
                "action_occurrence_candidate_is_event_truth": False,
                "validated_event_identity": False,
            },
            {
                "action_occurrence_candidate_id": "occ_failure",
                "provider_semantics_binding_status": "PASS",
                "primary_family_candidate": "PASS",
                "actor_identity_candidate_id": "actor_b",
                "team_identity_candidate_id": "team_a",
                "attributes": {
                    "outcome_candidate": outcome_failure,
                    "direction_candidates": ["FORWARD"],
                    "progression_candidates": ["PROGRESSIVE_CANDIDATE"],
                },
                "action_occurrence_candidate_is_event_truth": False,
                "validated_event_identity": False,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_success_failure_successors_produce_first_supported_divergence() -> None:
    result = build_first_supported_branch_divergence(_sequence_payload(), _occurrence())
    assert result["first_supported_branch_divergence_candidate_count"] == 1
    row = result["first_supported_branch_divergence_candidates"][0]
    assert row["divergence_level"] == "FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR"
    assert row["success_branch_count"] == 1
    assert row["failure_branch_count"] == 1
    assert row["divergence_is_failure_cause_truth"] is False
    assert row["branches_are_independent_recurrence_support"] is False
    assert row["branch_count_is_recurrence_count"] is False


def test_branch_opportunity_yield_is_explicit_and_dependency_qualified() -> None:
    result = build_first_supported_branch_divergence(_sequence_payload(), _occurrence())
    row = result["first_supported_branch_divergence_candidates"][0]
    assert row["observed_branch_opportunity_success_numerator"] == 1
    assert row["observed_branch_opportunity_eligible_denominator"] == 2
    assert row["observed_branch_opportunity_raw_success_rate"] == 0.5
    assert row["observed_branch_opportunity_actor_spread_count"] == 2
    assert row["observed_branch_opportunity_admitted_independent_support_count"] == 0
    assert row["observed_branch_opportunity_dependency_independence_proven"] is False
    assert row["observed_branch_opportunity_statistical_independence_proven"] is False
    assert row["observed_branch_opportunity_support_state"] == "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED"
    assert "DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES" in row[
        "observed_branch_opportunity_concentration_warnings"
    ]
    assert row["observed_branch_opportunity_binomial_interval_allowed"] is False
    assert row["observed_branch_opportunity_shrinkage_allowed"] is False
    assert row["observed_branch_opportunity_raw_rate_is_true_success_probability"] is False
    assert row["observed_branch_opportunity_raw_rate_is_intrinsic_process_efficiency"] is False
    assert result["opportunity_yield_requires_explicit_numerator_denominator"] is True
    assert result["opportunity_yield_dependency_qualified_support_required"] is True


def test_same_outcome_does_not_create_divergence_or_efficiency_claim() -> None:
    result = build_first_supported_branch_divergence(
        _sequence_payload(), _occurrence(outcome_success="SUCCESS", outcome_failure="SUCCESS")
    )
    assert result["first_supported_branch_divergence_candidate_count"] == 0
    assert result["opportunity_yield_is_intrinsic_process_efficiency"] is False


def test_unadmitted_semantics_do_not_create_success_failure_claim() -> None:
    occurrence = _occurrence()
    occurrence["action_occurrence_candidates"][1]["provider_semantics_binding_status"] = "REVIEW_REQUIRED"
    result = build_first_supported_branch_divergence(_sequence_payload(), occurrence)
    assert result["first_supported_branch_divergence_candidate_count"] == 0
    assert result["raw_label_string_matching_is_outcome_truth"] is False


def test_missing_occurrence_reference_is_review_not_fabricated_divergence() -> None:
    occurrence = _occurrence()
    occurrence["action_occurrence_candidates"] = occurrence["action_occurrence_candidates"][:1]
    result = build_first_supported_branch_divergence(_sequence_payload(), occurrence)
    assert result["first_supported_branch_divergence_candidate_count"] == 0
    assert any("occurrence_reference_missing" in value for value in result["review_hits"])


def test_claim_locks_and_no_sample_match_identity_leak() -> None:
    result = build_first_supported_branch_divergence(_sequence_payload(), _occurrence())
    assert result["divergence_is_failure_cause_truth"] is False
    assert result["divergence_is_tactical_truth"] is False
    assert result["branches_are_independent_recurrence_support"] is False
    assert result["opportunity_yield_binomial_interval_allowed"] is False
    assert result["opportunity_yield_shrinkage_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False

    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/first_supported_branch_divergence_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source


def test_upstream_truth_promotion_fail_closes() -> None:
    payload = _sequence_payload()
    payload["canonical_event_count"] = 99
    result = build_first_supported_branch_divergence(payload, _occurrence())
    assert result["status"] == "FAIL_CLOSED"
    assert result["first_supported_branch_divergence_candidate_count"] == 0
