from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.comparable_outcome_counterevidence_projection import (
    build_comparable_outcome_counterevidence,
)


def _payload(*, comparison_eligible=True, left_outcome="SUCCESS_SEMANTIC_VISIBLE", right_outcome="FAILURE_SEMANTIC_VISIBLE"):
    return {
        "dependency_aware_partial_order_similarity_status": "PASS",
        "first_supported_branch_divergence_status": "PASS",
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "partial_order_occurrence_variants": [
            {"partial_order_occurrence_variant_id": "v1", "sequence_ref": "s1"},
            {"partial_order_occurrence_variant_id": "v2", "sequence_ref": "s2"},
        ],
        "dependency_aware_partial_order_similarity_pairs": [
            {
                "partial_order_similarity_pair_id": "p1",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "comparison_eligibility_state": "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST" if comparison_eligible else "NOT_COMPARABLE_CROSS_TEAM_MATCH_LOCAL",
                "comparison_eligible": comparison_eligible,
            }
        ],
        "first_supported_branch_divergence_candidates": [
            {
                "branch_profiles": [
                    {
                        "branch_outcome_state": left_outcome,
                        "supporting_visible_sequence_candidate_ids": ["s1"],
                    },
                    {
                        "branch_outcome_state": right_outcome,
                        "supporting_visible_sequence_candidate_ids": ["s2"],
                    },
                ]
            }
        ],
    }


def _record(result):
    assert result["comparable_outcome_counterevidence_record_count"] == 1
    return result["comparable_outcome_counterevidence_records"][0]


def test_comparable_success_failure_pair_is_counterexample_candidate_not_independent_support():
    result = build_comparable_outcome_counterevidence(_payload())
    record = _record(result)
    assert record["comparison_eligible"] is True
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_DIFFERENT_VISIBLE_OUTCOME_COUNTEREXAMPLE_CANDIDATE"
    assert record["comparable_counterevidence_candidate"] is True
    assert record["counterevidence_is_independent_support"] is False
    assert record["dependency_independence_proven"] is False
    assert record["statistical_independence_proven"] is False
    assert record["counterevidence_is_causal_refutation"] is False
    assert record["outcome_difference_is_failure_cause_truth"] is False
    assert result["comparable_counterevidence_candidate_count"] == 1
    assert result["counterevidence_independent_support_count"] == 0


def test_comparable_same_visible_outcome_is_not_counterevidence():
    result = build_comparable_outcome_counterevidence(
        _payload(left_outcome="SUCCESS_SEMANTIC_VISIBLE", right_outcome="SUCCESS_SEMANTIC_VISIBLE")
    )
    record = _record(result)
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_SAME_VISIBLE_OUTCOME"
    assert record["comparable_counterevidence_candidate"] is False


def test_noncomparable_pair_cannot_create_outcome_counterevidence():
    result = build_comparable_outcome_counterevidence(_payload(comparison_eligible=False))
    record = _record(result)
    assert record["comparison_eligible"] is False
    assert record["comparable_outcome_contrast_state"] == "NOT_APPLICABLE_OR_REVIEW_REQUIRED_COMPARISON"
    assert record["comparable_counterevidence_candidate"] is False


def test_comparable_pair_with_unresolved_outcome_requires_review():
    result = build_comparable_outcome_counterevidence(
        _payload(right_outcome="OUTCOME_SEMANTIC_NOT_ADMITTED_FOR_DIVERGENCE")
    )
    record = _record(result)
    assert result["status"] == "REVIEW_REQUIRED"
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED"
    assert record["comparable_counterevidence_candidate"] is False
    assert result["review_hits"]


def test_missing_variant_sequence_binding_requires_review():
    payload = _payload()
    payload["partial_order_occurrence_variants"][1].pop("sequence_ref")
    result = build_comparable_outcome_counterevidence(payload)
    record = _record(result)
    assert result["status"] == "REVIEW_REQUIRED"
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED"


def test_truth_policy_breach_fails_closed():
    payload = _payload()
    payload["production_release"] = True
    result = build_comparable_outcome_counterevidence(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["comparable_outcome_counterevidence_record_count"] == 0
    assert "production_release_claimed" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "comparable_outcome_counterevidence_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source
