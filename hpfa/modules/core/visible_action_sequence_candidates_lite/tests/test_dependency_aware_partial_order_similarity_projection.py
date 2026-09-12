from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.dependency_aware_partial_order_similarity_projection import (
    build_dependency_aware_partial_order_similarity,
)


def _variant(
    variant_id: str,
    *,
    team: str = "team_a",
    period: str | None = "2",
    occurrence_refs=None,
    dependency_refs=None,
    outcome: str = "SAME_TEAM_CONTINUATION_CANDIDATE",
    first_layer_size: int = 2,
):
    occurrence_refs = occurrence_refs or [f"occ_{variant_id}_1", f"occ_{variant_id}_2"]
    dependency_refs = dependency_refs or [f"dep_{variant_id}"]
    node_records = []
    for index in range(first_layer_size):
        node_records.append({
            "trace_ref": f"trace_{variant_id}_{index}",
            "time_layer_ref": f"layer_{variant_id}_a",
            "action_family_candidates": ["PASS"],
            "outcome_candidate": outcome,
            "internal_same_time_order": "SAME_TIME_UNORDERED" if first_layer_size > 1 else "NOT_APPLICABLE",
        })
    node_records.append({
        "trace_ref": f"trace_{variant_id}_last",
        "time_layer_ref": f"layer_{variant_id}_b",
        "action_family_candidates": ["PASS"],
        "outcome_candidate": "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
        "internal_same_time_order": "NOT_APPLICABLE",
    })
    return {
        "partial_order_occurrence_variant_id": variant_id,
        "team_identity_candidate_id": team,
        "period_candidate": period,
        "node_records": node_records,
        "edge_relations": [{
            "from_layer_ref": f"layer_{variant_id}_a",
            "to_layer_ref": f"layer_{variant_id}_b",
            "relation": "BEFORE_CONFIRMED",
        }],
        "action_family_signature": [{"action_family_candidate": "PASS", "count": first_layer_size + 1}],
        "outcome_signature": [
            {"outcome_candidate": outcome, "count": first_layer_size},
            {"outcome_candidate": "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE", "count": 1},
        ],
        "supporting_action_occurrence_candidate_ids": occurrence_refs,
        "dependency_group_refs": dependency_refs,
    }


def _payload(*variants, same_time_policy=False):
    return {
        "partial_order_occurrence_variant_status": "PASS",
        "partial_order_occurrence_variants": list(variants),
        "partial_order_occurrence_variant_count": len(variants),
        "same_timestamp_internal_ordering_allowed": same_time_policy,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _pair(result):
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 1
    return result["dependency_aware_partial_order_similarity_pairs"][0]


def test_shared_origin_structural_match_is_comparable_for_branch_contrast_not_recurrence():
    left = _variant("a", occurrence_refs=["shared_occ", "a2"], dependency_refs=["shared_dep"])
    right = _variant("b", occurrence_refs=["shared_occ", "b2"], dependency_refs=["shared_dep"])
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["structural_exact_match"] is True
    assert pair["pair_state"] == "DEPENDENT_SHARED_ORIGIN_VARIANT_PAIR"
    assert pair["recurrence_candidate_eligible"] is False
    assert pair["comparison_eligibility_state"] == "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST"
    assert pair["comparison_eligible"] is True
    assert pair["comparison_outcome_contrast_allowed"] is True
    assert pair["comparison_requires_review"] is False
    assert pair["shared_occurrence_candidate_count"] == 1
    assert pair["provenance_distinct_for_recurrence_candidate"] is False
    assert pair["dependency_independent_for_recurrence"] is False
    assert pair["statistical_independence_proven"] is False


def test_provenance_distinct_exact_match_is_comparable_without_independence_claim():
    result = build_dependency_aware_partial_order_similarity(_payload(_variant("a"), _variant("b")))
    pair = _pair(result)
    assert pair["structural_exact_match"] is True
    assert pair["pair_state"] == "PROVENANCE_DISTINCT_STRUCTURAL_MATCH_CANDIDATE"
    assert pair["recurrence_candidate_eligible"] is True
    assert pair["comparison_eligible"] is True
    assert pair["dependency_independence_proven_for_recurrence"] is False
    assert pair["statistical_independence_proven"] is False
    assert pair["recurrence_candidate_is_independent_support"] is False
    assert result["recurrence_candidate_eligible_pair_count"] == 1


def test_cross_period_pair_is_pruned_before_pair_materialization():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a", period="1"), _variant("b", period="2"))
    )
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["source_all_possible_pair_count"] == 1
    assert result["comparison_prefilter_pruned_pair_count"] == 1
    assert result["cross_period_pairs_materialized"] is False


def test_missing_period_context_is_reviewed_and_not_materialized():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a", period=None), _variant("b", period="2"))
    )
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["missing_period_variant_count"] == 1
    assert "variant_period_context_missing_before_comparison_admission" in result["review_hits"]


def test_cross_team_pair_is_not_materialized_for_match_local_recurrence():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a", team="team_a"), _variant("b", team="team_b"))
    )
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["source_all_possible_pair_count"] == 1
    assert result["cross_team_pairs_materialized"] is False


def test_outcome_difference_does_not_drive_structural_or_comparison_eligibility():
    left = _variant("a", outcome="SAME_TEAM_CONTINUATION_CANDIDATE")
    right = _variant("b", outcome="NO_VISIBLE_FOLLOW_UP_CANDIDATE")
    result = build_dependency_aware_partial_order_similarity(_payload(left, right))
    pair = _pair(result)
    assert pair["structural_exact_match"] is True
    assert pair["comparison_eligible"] is True
    assert pair["outcome_contrast_state"] == "DIFFERENT_OBSERVED_OUTCOME_SIGNATURE"
    assert pair["outcome_used_in_similarity_decision"] is False
    assert result["outcome_used_in_similarity_decision"] is False
    assert result["outcome_used_only_for_representative_materialization_after_structural_admission"] is True


def test_structure_mismatch_is_pruned_before_pair_materialization():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a", first_layer_size=2), _variant("b", first_layer_size=3))
    )
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["structural_mismatch_pairs_materialized"] is False
    assert result["comparison_prefilter_pruned_pair_count"] == 1


def test_large_exact_group_uses_representative_surface_not_all_pairs():
    variants = [_variant(f"v{index:04d}") for index in range(1000)]
    result = build_dependency_aware_partial_order_similarity(_payload(*variants))
    assert result["status"] == "PASS"
    assert result["source_all_possible_pair_count"] == 499500
    assert result["dependency_aware_partial_order_similarity_group_count"] == 1
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 999
    assert result["comparison_prefilter_pruned_pair_count"] == 498501
    assert result["pair_materialization_mode"] == "ELIGIBILITY_GROUP_REPRESENTATIVE_PAIRS"
    assert result["comparison_admission_precedes_pair_materialization"] is True
    assert all(row["comparison_eligible"] is True for row in result["dependency_aware_partial_order_similarity_pairs"])


def test_same_timestamp_policy_breach_fails_closed():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a"), _variant("b"), same_time_policy=True)
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert "same_timestamp_internal_ordering_policy_breached" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "dependency_aware_partial_order_similarity_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source
