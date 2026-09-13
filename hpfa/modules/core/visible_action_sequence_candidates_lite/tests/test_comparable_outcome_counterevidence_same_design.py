from hpfa.modules.core.visible_action_sequence_candidates_lite.src.comparable_outcome_counterevidence_projection import (
    build_comparable_outcome_counterevidence,
)


def _payload(left="SUCCESS_SEMANTIC_VISIBLE", right="FAILURE_SEMANTIC_VISIBLE"):
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
        "dependency_aware_partial_order_similarity_pairs": [],
        "first_supported_branch_divergence_candidates": [
            {
                "first_supported_branch_divergence_id": "d1",
                "comparable_set_id": "set1",
                "comparison_question_id": "shared_visible_anchor_branch_contrast_v1",
                "eligible_denominator_frozen_before_divergence_outcome_attachment": True,
                "outcome_used_in_divergence_location": False,
                "anchor_centered_sequence_branch_map_ref": "m1",
                "team_identity_candidate_id": "team-1",
                "period_candidate": "2",
                "shared_anchor_time_layer_ref": "tl1",
                "shared_anchor_time_candidate": 100.0,
                "observed_branch_opportunity_success_numerator": 1,
                "observed_branch_opportunity_failure_numerator": 1,
                "observed_branch_opportunity_unresolved_numerator": 0,
                "observed_branch_opportunity_eligible_denominator": 2,
                "observed_branch_opportunity_raw_success_rate": 0.5,
                "observed_branch_opportunity_total_visible_branch_count": 2,
                "observed_branch_opportunity_actor_spread_count": 2,
                "observed_branch_opportunity_episode_spread_count": "UNKNOWN",
                "observed_branch_opportunity_context_spread_state": "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY",
                "observed_branch_opportunity_admitted_independent_support_count": 0,
                "observed_branch_opportunity_dependency_independence_proven": False,
                "observed_branch_opportunity_statistical_independence_proven": False,
                "observed_branch_opportunity_support_state": "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED",
                "observed_branch_opportunity_concentration_warnings": ["SINGLE_SHARED_ANCHOR_CONCENTRATION"],
                "branch_profiles": [
                    {
                        "branch_id": "b1",
                        "branch_outcome_state": left,
                        "supporting_visible_sequence_candidate_ids": ["s1"],
                    },
                    {
                        "branch_id": "b2",
                        "branch_outcome_state": right,
                        "supporting_visible_sequence_candidate_ids": ["s2"],
                    },
                ],
            }
        ],
    }


def test_branch_safe_finding_uses_same_declared_comparison_design_without_legacy_pair_gate():
    result = build_comparable_outcome_counterevidence(_payload())
    assert result["comparable_outcome_counterevidence_record_count"] == 0
    assert result["branch_comparison_counterevidence_record_count"] == 1
    assert result["safe_finding_handoff_candidate_count"] == 1
    handoff = result["safe_finding_handoff_candidates"][0]
    assert handoff["counterevidence_design"] == "SAME_DECLARED_BRANCH_COMPARISON_DESIGN"
    assert handoff["source_comparable_set_id"] == "set1"
    assert handoff["counterevidence"]["same_design_variation_pair_count"] == 1
    assert handoff["counterevidence"]["comparable_counterexample_pair_count"] == 0
    assert handoff["counterevidence"]["challenge_surface_empty"] is True
    assert "CHALLENGE_SURFACE_EMPTY" in handoff["evidence_sufficiency"]["blocking_dimensions"]
    assert handoff["finding_status"] == "DOWNGRADE"


def test_different_branches_same_visible_outcome_create_same_design_challenge_not_counterevidence_vote():
    result = build_comparable_outcome_counterevidence(
        _payload(left="SUCCESS_SEMANTIC_VISIBLE", right="SUCCESS_SEMANTIC_VISIBLE")
    )
    row = result["branch_comparison_counterevidence_records"][0]
    assert (
        row["branch_comparison_contrast_state"]
        == "SAME_PREFIX_DIFFERENT_BRANCH_SAME_VISIBLE_OUTCOME_CHALLENGE_CANDIDATE"
    )
    assert row["same_design_challenge_candidate"] is True
    assert row["counterevidence_is_independent_support"] is False
    assert result["safe_finding_handoff_candidate_count"] == 0


def test_same_branch_mixed_visible_outcomes_challenge_deterministic_branch_outcome_interpretation():
    payload = _payload()
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence["branch_profiles"] = [
        {
            "branch_id": "b1",
            "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s1"],
        },
        {
            "branch_id": "b1",
            "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s2"],
        },
    ]
    result = build_comparable_outcome_counterevidence(payload)
    row = result["branch_comparison_counterevidence_records"][0]
    assert row["same_branch"] is True
    assert (
        row["branch_comparison_contrast_state"]
        == "SAME_BRANCH_DIFFERENT_VISIBLE_OUTCOME_CHALLENGE_CANDIDATE"
    )
    assert row["same_design_challenge_candidate"] is True
    assert row["counterevidence_is_causal_refutation"] is False


def test_evidence_coverage_uses_frozen_eligible_cases_not_visible_branch_count():
    payload = _payload()
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence["observed_branch_opportunity_eligible_denominator"] = 3
    divergence["observed_branch_opportunity_success_numerator"] = 1
    divergence["observed_branch_opportunity_failure_numerator"] = 1
    divergence["observed_branch_opportunity_unresolved_numerator"] = 1
    divergence["observed_branch_opportunity_total_visible_branch_count"] = 2
    result = build_comparable_outcome_counterevidence(payload)
    profile = result["safe_finding_handoff_candidates"][0]["evidence_sufficiency"]
    coverage = profile["dimensions"]["eligible_case_coverage"]
    assert coverage["eligible_case_count"] == 3
    assert coverage["accounted_case_count"] == 3
    assert coverage["unresolved_outcome_case_count"] == 1
    assert coverage["state"] == "COMPLETE_CASE_ACCOUNTING_WITH_UNRESOLVED_OUTCOMES"
    assert profile["dimensions"]["branch_shape"]["total_visible_branch_count"] == 2
    assert profile["dimensions"]["branch_shape"]["branch_count_is_case_denominator"] is False


def test_outcome_swap_changes_only_attached_contrast_not_comparison_identity_or_truth_locks():
    first = build_comparable_outcome_counterevidence(_payload())
    second = build_comparable_outcome_counterevidence(
        _payload(left="FAILURE_SEMANTIC_VISIBLE", right="SUCCESS_SEMANTIC_VISIBLE")
    )
    a = first["branch_comparison_counterevidence_records"][0]
    b = second["branch_comparison_counterevidence_records"][0]
    assert a["comparable_set_id"] == b["comparable_set_id"] == "set1"
    assert (
        a["source_first_supported_branch_divergence_ref"]
        == b["source_first_supported_branch_divergence_ref"]
        == "d1"
    )
    assert a["outcome_used_in_comparison_admission"] is False
    assert b["outcome_used_in_comparison_admission"] is False
    assert first["absence_is_counterevidence"] is False
    assert first["no_visible_followup_is_failure_truth"] is False
    assert first["counterevidence_independent_support_count"] == 0
