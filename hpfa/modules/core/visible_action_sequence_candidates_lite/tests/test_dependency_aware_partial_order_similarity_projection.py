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


def _topology_variant(variant_id: str, edges: list[tuple[int, int]]):
    layers = [f"layer_{variant_id}_{index}" for index in range(4)]
    return {
        "partial_order_occurrence_variant_id": variant_id,
        "team_identity_candidate_id": "team_a",
        "period_candidate": "2",
        "node_records": [
            {
                "trace_ref": f"trace_{variant_id}_{index}",
                "time_layer_ref": layer,
                "action_family_candidates": ["PASS"],
                "outcome_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "internal_same_time_order": "NOT_APPLICABLE",
            }
            for index, layer in enumerate(layers)
        ],
        "edge_relations": [
            {
                "from_layer_ref": layers[source],
                "to_layer_ref": layers[target],
                "relation": "BEFORE_CONFIRMED",
            }
            for source, target in edges
        ],
        "action_family_signature": [{"action_family_candidate": "PASS", "count": 4}],
        "outcome_signature": [{"outcome_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE", "count": 4}],
        "supporting_action_occurrence_candidate_ids": [f"occ_{variant_id}_{index}" for index in range(4)],
        "dependency_group_refs": [f"dep_{variant_id}"],
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


def _period_test_contract():
    return {
        "comparison_question_id": "half_to_half_process_evolution_v1",
        "football_question": "Does the same visible process family branch differently across periods?",
        "analysis_scale": "PARTIAL_ORDER_OCCURRENCE_VARIANT",
        "candidate_universe": "CURRENT_MATCH_PARTIAL_ORDER_OCCURRENCE_VARIANTS",
        "anchor_process_family": "STRUCTURAL_PARTIAL_ORDER_FAMILY_CANDIDATE",
        "comparison_target": "PERIOD_VARIATION",
        "required_exact_dimensions": ["team", "partial_order_structure"],
        "required_coarsened_dimensions": [],
        "allowed_test_dimensions": ["period"],
        "optional_similarity_dimensions": [],
        "forbidden_leakage_dimensions": ["outcome_signature", "terminal_consequence"],
        "required_observation_capabilities": ["TEAM_IDENTITY", "PERIOD_CONTEXT", "PARTIAL_ORDER_STRUCTURE"],
        "optional_observation_capabilities": [],
        "consequence_horizon": "ATTACH_ONLY_AFTER_COMPARABLE_SET_FREEZE",
        "minimum_support_rule": "AT_LEAST_TWO_ELIGIBLE_CASES",
        "minimum_spread_rule": "DESCRIBE_SPREAD_DO_NOT_INFER_INDEPENDENCE",
        "claim_ceiling": "QUESTION_CONDITIONED_OUTCOME_BLIND_PROCESS_COMPARABLE_SET_CANDIDATE_ONLY",
    }


def _pair(result):
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 1
    return result["dependency_aware_partial_order_similarity_pairs"][0]


def test_shared_origin_structural_match_is_comparable_for_branch_contrast_not_recurrence():
    left = _variant("a", occurrence_refs=["shared_occ", "a2"], dependency_refs=["shared_dep"])
    right = _variant("b", occurrence_refs=["shared_occ", "b2"], dependency_refs=["shared_dep"])
    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))
    assert pair["coarse_partial_order_signature_match"] is True
    assert pair["relation_preserving_topology_match"] is True
    assert pair["structural_exact_equivalence_proven"] is True
    assert pair["structural_exact_match"] is True
    assert pair["coarse_signature_is_exact_equivalence_proof"] is False
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
    assert pair["relation_preserving_topology_match"] is True
    assert pair["pair_state"] == "PROVENANCE_DISTINCT_STRUCTURAL_MATCH_CANDIDATE"
    assert pair["recurrence_candidate_eligible"] is True
    assert pair["comparison_eligible"] is True
    assert pair["dependency_independence_proven_for_recurrence"] is False
    assert pair["statistical_independence_proven"] is False
    assert pair["recurrence_candidate_is_independent_support"] is False
    assert result["recurrence_candidate_eligible_pair_count"] == 1


def test_comparable_set_freezes_outcome_blind_eligible_denominator():
    left = _variant("a", outcome="SAME_TEAM_CONTINUATION_CANDIDATE")
    right = _variant("b", outcome="NO_VISIBLE_FOLLOW_UP_CANDIDATE")
    result = build_dependency_aware_partial_order_similarity(_payload(left, right))

    assert result["process_comparison_question_contract_status"] == "PASS"
    assert result["process_comparable_set_count"] == 1
    comparable_set = result["process_comparable_sets"][0]
    assert comparable_set["eligible_case_count"] == 2
    assert comparable_set["eligible_denominator_frozen_before_outcome_attachment"] is True
    assert comparable_set["outcome_used_in_eligibility"] is False
    assert comparable_set["outcome_used_in_pair_materialization"] is False
    assert comparable_set["comparable_set_is_finding"] is False
    assert result["eligible_denominator_frozen_before_outcome_attachment"] is True
    assert result["outcome_used_in_comparison_admission"] is False
    assert result["outcome_used_in_pair_materialization"] is False


def test_nonisomorphic_same_histogram_not_exact_match():
    path = _topology_variant("path", [(0, 1), (1, 2), (2, 3)])
    star = _topology_variant("star", [(0, 1), (0, 2), (0, 3)])

    result = build_dependency_aware_partial_order_similarity(_payload(path, star))

    assert result["status"] == "PASS"
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["source_all_possible_pair_count"] == 1
    assert result["comparison_prefilter_pruned_pair_count"] == 1
    assert result["coarse_signature_topology_split_group_count"] == 1
    assert result["topology_mismatch_pair_pruned_count"] == 1
    assert result["topology_mismatch_pairs_materialized"] is False
    assert result["coarse_signature_is_only_prefilter"] is True
    assert result["structural_exact_match_requires_relation_preserving_topology"] is True


def test_topology_filter_is_downward_only_and_does_not_create_new_pairs():
    path = _topology_variant("a_path", [(0, 1), (1, 2), (2, 3)])
    star_one = _topology_variant("b_star", [(0, 1), (0, 2), (0, 3)])
    star_two = _topology_variant("c_star", [(0, 1), (0, 2), (0, 3)])

    result = build_dependency_aware_partial_order_similarity(_payload(path, star_one, star_two))

    assert result["source_all_possible_pair_count"] == 3
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["topology_mismatch_pair_pruned_count"] == 2
    assert result["topology_filter_can_create_new_pair"] is False
    assert result["topology_filter_only_removes_or_preserves_coarse_prefilter_pairs"] is True


def test_isomorphic_topology_with_different_layer_refs_remains_exact_match():
    left = _topology_variant("left", [(0, 1), (1, 2), (2, 3)])
    right = _topology_variant("right", [(0, 1), (1, 2), (2, 3)])

    pair = _pair(build_dependency_aware_partial_order_similarity(_payload(left, right)))

    assert pair["coarse_partial_order_signature_match"] is True
    assert pair["relation_preserving_topology_match"] is True
    assert pair["structural_exact_equivalence_proven"] is True
    assert pair["structural_exact_match"] is True


def test_cross_period_pair_is_pruned_before_pair_materialization_by_default():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a", period="1"), _variant("b", period="2"))
    )
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["source_all_possible_pair_count"] == 1
    assert result["comparison_prefilter_pruned_pair_count"] == 1
    assert result["cross_period_pairs_materialized"] is False


def test_period_test_dimension_allows_cross_period_comparison_without_recurrence_promotion():
    payload = _payload(_variant("a", period="1"), _variant("b", period="2"))
    payload["process_comparison_question_contract"] = _period_test_contract()
    result = build_dependency_aware_partial_order_similarity(payload)
    pair = _pair(result)

    assert result["status"] == "PASS"
    assert pair["comparison_eligibility_state"] == "COMPARABLE_FOR_DECLARED_PERIOD_TEST_DIMENSION"
    assert pair["process_comparison_eligibility_grade"] == "STRICT_ELIGIBLE"
    assert pair["comparison_eligible"] is True
    assert pair["same_period_comparison"] is False
    assert pair["recurrence_candidate_eligible"] is False
    assert result["cross_period_pairs_materialized"] is True
    assert result["process_comparable_set_count"] == 1
    assert result["process_comparable_sets"][0]["resolved_context"]["period_candidates"] == ["1", "2"]
    assert result["process_comparable_sets"][0]["allowed_test_dimensions"] == ["period"]


def test_test_dimension_cannot_also_be_required_exact_match():
    payload = _payload(_variant("a", period="1"), _variant("b", period="2"))
    contract = _period_test_contract()
    contract["required_exact_dimensions"] = ["team", "period", "partial_order_structure"]
    payload["process_comparison_question_contract"] = contract

    result = build_dependency_aware_partial_order_similarity(payload)

    assert result["status"] == "FAIL_CLOSED"
    assert result["process_comparison_question_contract_status"] == "FAIL_CLOSED"
    assert result["process_comparable_set_count"] == 0
    assert "comparison_question_test_dimension_exact_match_overlap" in result["hard_block_hits"]


def test_forbidden_outcome_leakage_cannot_be_exact_match_key():
    payload = _payload(_variant("a"), _variant("b"))
    contract = _period_test_contract()
    contract["required_exact_dimensions"] = [
        "team",
        "partial_order_structure",
        "outcome_signature",
    ]
    payload["process_comparison_question_contract"] = contract

    result = build_dependency_aware_partial_order_similarity(payload)

    assert result["status"] == "FAIL_CLOSED"
    assert result["process_comparison_question_contract_status"] == "FAIL_CLOSED"
    assert result["process_comparable_set_count"] == 0
    assert (
        "comparison_question_forbidden_leakage_exact_match_overlap:outcome_signature"
        in result["hard_block_hits"]
    )


def test_forbidden_outcome_leakage_cannot_be_coarsened_match_key():
    payload = _payload(_variant("a"), _variant("b"))
    contract = _period_test_contract()
    contract["required_coarsened_dimensions"] = ["terminal_consequence"]
    payload["process_comparison_question_contract"] = contract

    result = build_dependency_aware_partial_order_similarity(payload)

    assert result["status"] == "FAIL_CLOSED"
    assert result["process_comparable_set_count"] == 0
    assert (
        "comparison_question_forbidden_leakage_coarsened_match_overlap:terminal_consequence"
        in result["hard_block_hits"]
    )


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
    assert pair["outcome_used_in_comparison_admission"] is False
    assert result["outcome_used_in_similarity_decision"] is False
    assert result["outcome_used_in_comparison_admission"] is False
    assert result["outcome_used_in_pair_materialization"] is False
    assert result["outcome_used_only_for_representative_materialization_after_structural_admission"] is False


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
    assert result["coarse_signature_is_only_prefilter"] is True
    assert result["structural_exact_match_requires_relation_preserving_topology"] is True
    assert result["topology_filter_can_create_new_pair"] is False
    assert result["process_comparable_set_count"] == 1
    assert result["process_comparable_sets"][0]["eligible_case_count"] == 1000
    assert all(row["comparison_eligible"] is True for row in result["dependency_aware_partial_order_similarity_pairs"])


def test_same_timestamp_policy_breach_fails_closed():
    result = build_dependency_aware_partial_order_similarity(
        _payload(_variant("a"), _variant("b"), same_time_policy=True)
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["dependency_aware_partial_order_similarity_pair_count"] == 0
    assert result["process_comparable_set_count"] == 0
    assert "same_timestamp_internal_ordering_policy_breached" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "dependency_aware_partial_order_similarity_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source


def test_unregistered_declared_dimension_fails_closed():
    payload = _payload(_variant("a"), _variant("b"))
    contract = _period_test_contract()
    contract["required_exact_dimensions"] = ["team", "partial_order_structure", "score_state"]
    contract["allowed_test_dimensions"] = ["period"]
    payload["process_comparison_question_contract"] = contract

    result = build_dependency_aware_partial_order_similarity(payload)

    assert result["status"] == "FAIL_CLOSED"
    assert result["process_comparable_set_count"] == 0
    assert "comparison_question_dimension_unregistered:score_state" in result["hard_block_hits"]


def test_default_pair_exposes_canonical_comparison_state_without_changing_eligibility():
    result = build_dependency_aware_partial_order_similarity(_payload(_variant("a"), _variant("b")))
    pair = _pair(result)

    assert pair["comparison_eligible"] is True
    assert pair["canonical_comparison_state"] == "ELIGIBLE"
    assert pair["eligible_for_outcome_attachment"] is True
    assert result["canonical_comparison_state_counts"]["ELIGIBLE"] == 1


def test_comparable_set_freezes_profile_hash_before_outcome_attachment():
    result = build_dependency_aware_partial_order_similarity(_payload(_variant("a"), _variant("b")))
    comparable_set = result["process_comparable_sets"][0]

    assert result["comparison_dimension_registry_version"] == "comparison_dimension_registry_v1"
    assert result["profile_frozen_before_outcome_attachment"] is True
    assert isinstance(result["question_profile_hash"], str)
    assert len(result["question_profile_hash"]) == 64
    assert comparable_set["profile_frozen_before_outcome_attachment"] is True
    assert comparable_set["question_profile_hash"] == result["question_profile_hash"]


def test_materialized_pair_count_is_not_eligible_case_denominator():
    variants = [_variant(f"v{index}") for index in range(4)]
    result = build_dependency_aware_partial_order_similarity(_payload(*variants))

    assert result["dependency_aware_partial_order_similarity_pair_count"] == 3
    assert result["process_comparable_sets"][0]["eligible_case_count"] == 4
    assert result["pair_materialization_count_is_eligible_denominator"] is False
    assert result["process_comparable_sets"][0]["materialized_pair_count_is_eligible_denominator"] is False


def test_dimension_registry_version_mismatch_fails_closed():
    payload = _payload(_variant("a"), _variant("b"))
    contract = _period_test_contract()
    contract["dimension_registry_version"] = "future_registry_v999"
    payload["process_comparison_question_contract"] = contract

    result = build_dependency_aware_partial_order_similarity(payload)

    assert result["status"] == "FAIL_CLOSED"
    assert "comparison_question_dimension_registry_version_mismatch" in result["hard_block_hits"]
