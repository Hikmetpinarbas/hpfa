from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.dependency_aware_partial_order_similarity_projection import (
    build_dependency_aware_partial_order_similarity,
)


def _variant(
    variant_id: str,
    *,
    team: str = "team_a",
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
        "period_candidate": "2",
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


def _payload(left, right, *, same_time_policy=False):
    return {
        "partial_order_occurrence_variant_status": "PASS",
        "partial_order_occurrence_variants": [left, right],
        "partial_order_occurrence_variant_count": 2,
        "same_timestamp_internal_ordering_allowed": same_time_policy,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _pair(result):
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 1
    return result["dependency_aware_partial_order_similarity_pairs"][0]


def test_shared_origin_structural_match_is_not_independent_recurrence():
    left = _variant("a", occurrence_refs=["shared_occ", "a2"], dependency_refs=["shared_dep"])
    right = _variant("b", occurrence_refs=["shared_occ", "b2"], dependency_refs=["shared_dep"])
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["structural_exact_match"] is True
    assert pair["pair_state"] == "DEPENDENT_SHARED_ORIGIN_VARIANT_PAIR"
    assert pair["recurrence_candidate_eligible"] is False
    assert pair["shared_occurrence_candidate_count"] == 1
    assert pair["dependency_independent_for_recurrence"] is False


def test_independent_same_team_exact_match_can_be_recurrence_candidate():
    left = _variant("a")
    right = _variant("b")
    result = build_dependency_aware_partial_order_similarity(_payload(left, right))
    pair = _pair(result)
    assert pair["structural_exact_match"] is True
    assert pair["pair_state"] == "INDEPENDENT_STRUCTURAL_MATCH_CANDIDATE"
    assert pair["recurrence_candidate_eligible"] is True
    assert result["recurrence_candidate_eligible_pair_count"] == 1


def test_cross_team_pair_is_not_match_local_recurrence():
    left = _variant("a", team="team_a")
    right = _variant("b", team="team_b")
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["pair_state"] == "NOT_APPLICABLE_CROSS_TEAM_MATCH_LOCAL_RECURRENCE"
    assert pair["recurrence_candidate_eligible"] is False


def test_outcome_difference_does_not_drive_similarity_decision():
    left = _variant("a", outcome="SAME_TEAM_CONTINUATION_CANDIDATE")
    right = _variant("b", outcome="NO_VISIBLE_FOLLOW_UP_CANDIDATE")
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["structural_exact_match"] is True
    assert pair["pair_state"] == "INDEPENDENT_STRUCTURAL_MATCH_CANDIDATE"
    assert pair["outcome_contrast_state"] == "DIFFERENT_OBSERVED_OUTCOME_SIGNATURE"
    assert pair["outcome_used_in_similarity_decision"] is False


def test_layer_shape_difference_prevents_exact_structural_match():
    left = _variant("a", first_layer_size=2)
    right = _variant("b", first_layer_size=3)
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["layer_shape_similarity"] < 1.0
    assert pair["structural_exact_match"] is False
    assert pair["recurrence_candidate_eligible"] is False


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
