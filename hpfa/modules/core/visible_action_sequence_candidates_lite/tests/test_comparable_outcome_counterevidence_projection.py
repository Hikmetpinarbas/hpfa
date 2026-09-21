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
                "first_supported_branch_divergence_id": "d1",
                "anchor_centered_sequence_branch_map_ref": "m1",
                "team_identity_candidate_id": "team-1",
                "period_candidate": 2,
                "shared_anchor_time_layer_ref": "tl1",
                "shared_anchor_time_candidate": 100.0,
                "observed_branch_opportunity_success_numerator": 1,
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
                "observed_branch_opportunity_concentration_warnings": [
                    "SINGLE_SHARED_ANCHOR_CONCENTRATION",
                    "DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES",
                ],
                "branch_profiles": [
                    {
                        "branch_outcome_state": left_outcome,
                        "supporting_visible_sequence_candidate_ids": ["s1"],
                    },
                    {
                        "branch_outcome_state": right_outcome,
                        "supporting_visible_sequence_candidate_ids": ["s2"],
                    },
                ],
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
    assert result["safe_finding_handoff_candidate_count"] == 0


def test_noncomparable_pair_cannot_create_outcome_counterevidence():
    result = build_comparable_outcome_counterevidence(_payload(comparison_eligible=False))
    record = _record(result)
    assert record["comparison_eligible"] is False
    assert record["comparable_outcome_contrast_state"] == "NOT_APPLICABLE_OR_REVIEW_REQUIRED_COMPARISON"
    assert record["comparable_counterevidence_candidate"] is False
    assert result["safe_finding_handoff_candidate_count"] == 0


def test_comparable_pair_with_unresolved_outcome_requires_review():
    result = build_comparable_outcome_counterevidence(
        _payload(right_outcome="OUTCOME_SEMANTIC_NOT_ADMITTED_FOR_DIVERGENCE")
    )
    record = _record(result)
    assert result["status"] == "REVIEW_REQUIRED"
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED"
    assert record["comparable_counterevidence_candidate"] is False
    assert result["review_hits"]
    assert result["safe_finding_handoff_candidate_count"] == 0


def test_missing_variant_sequence_binding_requires_review():
    payload = _payload()
    payload["partial_order_occurrence_variants"][1].pop("sequence_ref")
    result = build_comparable_outcome_counterevidence(payload)
    record = _record(result)
    assert result["status"] == "REVIEW_REQUIRED"
    assert record["comparable_outcome_contrast_state"] == "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED"
    assert result["safe_finding_handoff_candidate_count"] == 0


def test_safe_finding_handoff_is_downgraded_and_keeps_challenge_surface():
    result = build_comparable_outcome_counterevidence(_payload())
    assert result["safe_finding_handoff_candidate_count"] == 1
    assert result["safe_finding_handoff_finding_status_counts"] == {
        "EMIT": 0,
        "DOWNGRADE": 1,
        "ABSTAIN": 0,
    }
    assert result["professional_finding_emitted_count"] == 0
    assert result["safe_finding_handoff_professional_emit_allowed"] is False

    handoff = result["safe_finding_handoff_candidates"][0]
    assert handoff["finding_status"] == "DOWNGRADE"
    assert handoff["professional_finding_emit_allowed"] is False
    assert handoff["what_visible"]["success_branch_count"] == 1
    assert handoff["what_visible"]["failure_branch_count"] == 1
    assert handoff["support"]["visible_success_numerator"] == 1
    assert handoff["support"]["eligible_denominator"] == 2
    assert handoff["support"]["raw_success_rate"] == 0.5
    assert handoff["support"]["admitted_independent_support_count"] == 0
    assert handoff["support"]["dependency_independence_proven"] is False
    assert handoff["counterevidence"]["visible_failure_sequence_refs"] == ["s2"]
    assert handoff["counterevidence"]["comparable_counterexample_pair_count"] == 1
    assert handoff["counterevidence"]["counterexample_pair_count_is_independent_evidence_count"] is False
    assert handoff["counterevidence"]["independent_counterevidence_support_count"] == 0
    assert handoff["counterevidence"]["absence_used_as_counterevidence"] is False
    assert handoff["safe_meaning"] == "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY"
    assert "TRUE_SUCCESS_PROBABILITY" in handoff["forbidden_inference"]
    assert "FAILURE_CAUSE" in handoff["forbidden_inference"]
    assert handoff["uncertainty"]["binomial_interval_allowed"] is False
    assert handoff["uncertainty"]["shrinkage_allowed"] is False
    assert handoff["withdrawal_conditions"]
    assert handoff["safe_finding_handoff_is_professional_finding_truth"] is False
    assert handoff["safe_finding_handoff_is_tactical_truth"] is False
    assert handoff["safe_finding_handoff_is_causal_truth"] is False
    assert handoff["canonical_event_count"] == "UNKNOWN"
    assert handoff["true_action_count"] == "UNKNOWN"
    assert handoff["production_release"] is False


def test_evidence_sufficiency_profile_is_non_compensatory_and_explains_downgrade():
    result = build_comparable_outcome_counterevidence(_payload())
    assert result["evidence_sufficiency_profile_is_non_compensatory"] is True
    assert result["evidence_sufficiency_numeric_score_allowed"] is False
    assert result["evidence_sufficiency_universal_threshold_allowed"] is False

    profile = result["safe_finding_handoff_candidates"][0]["evidence_sufficiency"]
    assert profile["state"] == "INSUFFICIENT_FOR_PROFESSIONAL_EMIT"
    assert profile["numeric_sufficiency_score"] is None
    assert profile["universal_sufficiency_threshold_used"] is False
    assert profile["dimensions_compensate_each_other"] is False
    assert profile["missing_dimension_is_zero"] is False
    assert profile["coverage_is_generalizability_truth"] is False
    assert profile["high_raw_rate_can_override_dependency_block"] is False
    assert profile["counterexample_pair_count_can_override_independence_block"] is False
    assert profile["dimensions"]["outcome_coverage"]["state"] == "COMPLETE_FOR_VISIBLE_BRANCHES"
    assert profile["dimensions"]["episode_spread"]["state"] == "UNKNOWN"
    assert profile["dimensions"]["challenge_surface"]["pair_count_is_independent_evidence_count"] is False
    assert "INDEPENDENT_SUPPORT_NOT_ADMITTED" in profile["blocking_dimensions"]
    assert "EPISODE_SPREAD_UNKNOWN" in profile["blocking_dimensions"]
    assert "CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN" in profile["blocking_dimensions"]


def test_unknown_visible_branch_coverage_is_unknown_not_zero_or_complete():
    payload = _payload()
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence.pop("observed_branch_opportunity_total_visible_branch_count")
    result = build_comparable_outcome_counterevidence(payload)
    profile = result["safe_finding_handoff_candidates"][0]["evidence_sufficiency"]
    coverage = profile["dimensions"]["outcome_coverage"]
    assert coverage["total_visible_branch_count"] == "UNKNOWN"
    assert coverage["unresolved_visible_branch_count"] == "UNKNOWN"
    assert coverage["state"] == "VISIBLE_OUTCOME_COVERAGE_UNKNOWN"
    assert "OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN" in profile["blocking_dimensions"]


def test_high_raw_rate_cannot_override_dependency_or_coverage_blocks():
    payload = _payload()
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence["observed_branch_opportunity_success_numerator"] = 99
    divergence["observed_branch_opportunity_eligible_denominator"] = 100
    divergence["observed_branch_opportunity_raw_success_rate"] = 0.99
    divergence["observed_branch_opportunity_total_visible_branch_count"] = 100
    result = build_comparable_outcome_counterevidence(payload)
    profile = result["safe_finding_handoff_candidates"][0]["evidence_sufficiency"]
    assert profile["state"] == "INSUFFICIENT_FOR_PROFESSIONAL_EMIT"
    assert profile["high_raw_rate_can_override_dependency_block"] is False
    assert "INDEPENDENT_SUPPORT_NOT_ADMITTED" in profile["blocking_dimensions"]
    assert "DEPENDENCY_INDEPENDENCE_NOT_PROVEN" in profile["blocking_dimensions"]


def test_counterexample_pair_count_never_becomes_evidence_count():
    result = build_comparable_outcome_counterevidence(_payload())
    handoff = result["safe_finding_handoff_candidates"][0]
    assert result["counterexample_pair_count_is_independent_evidence_count"] is False
    assert handoff["counterevidence"]["comparable_counterexample_pair_count"] == 1
    assert handoff["counterevidence"]["independent_counterevidence_support_count"] == 0


def test_truth_policy_breach_fails_closed():
    payload = _payload()
    payload["production_release"] = True
    result = build_comparable_outcome_counterevidence(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["comparable_outcome_counterevidence_record_count"] == 0
    assert result["safe_finding_handoff_candidate_count"] == 0
    assert "production_release_claimed" in result["hard_block_hits"]


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "comparable_outcome_counterevidence_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source


def test_safe_finding_handoff_exposes_unresolved_observed_defeat_and_typed_withdrawal_rules():
    result = build_comparable_outcome_counterevidence(_payload())
    assert result["safe_finding_handoff_candidate_count"] == 1
    handoff = result["safe_finding_handoff_candidates"][0]
    contract = handoff["typed_defeat_contract"]

    assert contract["observed_defeat_type"] == "DEFEAT_TYPE_UNRESOLVED"
    assert contract["observed_target_component_ref"] is None
    assert contract["rebut_without_explicit_target_allowed"] is False
    assert contract["defeat_is_causal_refutation"] is False
    assert contract["defeat_can_authorize_emit"] is False
    assert contract["defeat_can_strengthen_claim_ceiling"] is False
    assert contract["defeat_creates_new_evidence"] is False

    rules = {row["condition_code"]: row for row in contract["conditional_withdrawal_rules"]}
    assert rules["WITHDRAW_IF_SHARED_ANCHOR_ADMISSION_INVALIDATED"]["defeat_type"] == "UNDERMINE"
    assert rules["WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED"]["defeat_type"] == "UNDERCUT"
    assert all(row["withdrawal_effect"] in {"ABSTAIN", "REVIEW_REQUIRED"} for row in rules.values())


def test_canonical_evidence_direction_separates_counterevidence_from_dependency_challenge():
    result = build_comparable_outcome_counterevidence(_payload())
    record = _record(result)

    assert record["canonical_evidence_direction_class"] == "COUNTEREVIDENCE"
    assert record["canonical_evidence_target_construct"] == (
        "STRUCTURAL_RECURRENCE_VISIBLE_OUTCOME_CONSISTENCY"
    )
    assert record["dependency_challenge_present"] is True
    assert "SHARED_ORIGIN_COMPARISON_DESIGN" in record["dependency_challenge_reason_codes"]
    assert record["dependency_challenge_changes_evidence_direction"] is False
    assert record["independent_evidence_vote_allowed"] is False
    assert result["legacy_canonical_evidence_direction_counts"]["COUNTEREVIDENCE"] == 1
    assert result["legacy_dependency_challenge_record_count"] == 1
    assert result["dependency_challenge_is_evidence_direction"] is False


def test_same_visible_outcome_is_canonical_support_not_counterevidence():
    result = build_comparable_outcome_counterevidence(
        _payload(
            left_outcome="SUCCESS_SEMANTIC_VISIBLE",
            right_outcome="SUCCESS_SEMANTIC_VISIBLE",
        )
    )
    record = _record(result)

    assert record["canonical_evidence_direction_class"] == "SUPPORT"
    assert record["comparable_counterevidence_candidate"] is False
    assert record["non_support_is_counterevidence"] is False


def test_unresolved_outcome_is_canonical_unresolved_not_failure():
    result = build_comparable_outcome_counterevidence(
        _payload(right_outcome="OUTCOME_SEMANTIC_NOT_ADMITTED_FOR_DIVERGENCE")
    )
    record = _record(result)

    assert record["canonical_evidence_direction_class"] == "UNRESOLVED"
    assert record["unresolved_is_failure"] is False
    assert result["legacy_canonical_evidence_direction_counts"]["UNRESOLVED"] == 1


def test_ineligible_comparison_is_not_evaluated_not_counterevidence():
    result = build_comparable_outcome_counterevidence(_payload(comparison_eligible=False))
    record = _record(result)

    assert record["canonical_evidence_direction_class"] == "NOT_EVALUATED"
    assert record["comparable_counterevidence_candidate"] is False


def test_branch_different_branch_same_outcome_is_non_support_not_counterevidence():
    payload = _payload(
        left_outcome="SUCCESS_SEMANTIC_VISIBLE",
        right_outcome="SUCCESS_SEMANTIC_VISIBLE",
    )
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence["comparable_set_id"] = "set_1"
    divergence["comparison_question_id"] = "shared_visible_anchor_branch_contrast_v1"
    divergence["eligible_denominator_frozen_before_divergence_outcome_attachment"] = True
    divergence["outcome_used_in_divergence_location"] = False
    divergence["branch_profiles"] = [
        {
            "branch_id": "branch_a",
            "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s1"],
        },
        {
            "branch_id": "branch_b",
            "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s2"],
        },
    ]

    result = build_comparable_outcome_counterevidence(payload)
    assert result["branch_comparison_counterevidence_record_count"] == 1
    record = result["branch_comparison_counterevidence_records"][0]

    assert record["canonical_evidence_direction_class"] == "NON_SUPPORT"
    assert record["canonical_evidence_target_component"] == (
        "BETWEEN_BRANCH_VISIBLE_OUTCOME_DISCRIMINATION"
    )
    assert record["same_design_challenge_candidate"] is True
    assert record["non_support_is_counterevidence"] is False
    assert record["dependency_challenge_state"] == "NOT_EVALUATED_IN_BRANCH_RECORD"
    assert result["branch_canonical_evidence_direction_counts"]["NON_SUPPORT"] == 1


def test_branch_same_branch_different_outcome_is_canonical_counterevidence():
    payload = _payload()
    divergence = payload["first_supported_branch_divergence_candidates"][0]
    divergence["comparable_set_id"] = "set_1"
    divergence["comparison_question_id"] = "shared_visible_anchor_branch_contrast_v1"
    divergence["eligible_denominator_frozen_before_divergence_outcome_attachment"] = True
    divergence["outcome_used_in_divergence_location"] = False
    divergence["branch_profiles"] = [
        {
            "branch_id": "branch_a",
            "branch_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s1"],
        },
        {
            "branch_id": "branch_a",
            "branch_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
            "supporting_visible_sequence_candidate_ids": ["s2"],
        },
    ]

    result = build_comparable_outcome_counterevidence(payload)
    assert result["branch_comparison_counterevidence_record_count"] == 1
    record = result["branch_comparison_counterevidence_records"][0]

    assert record["canonical_evidence_direction_class"] == "COUNTEREVIDENCE"
    assert record["canonical_evidence_target_component"] == (
        "WITHIN_BRANCH_VISIBLE_OUTCOME_STABILITY"
    )
    assert record["same_design_challenge_candidate"] is True
    assert record["independent_evidence_vote_allowed"] is False
