from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    build_analyst_output_claim_contract,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
)


def _sequence() -> dict:
    return {
        "safe_finding_handoff_professional_emit_allowed": False,
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "handoff_1",
                "professional_finding_emit_allowed": False,
                "support": {
                    "visible_success_sequence_refs": ["seq_success"],
                    "admitted_independent_support_count": 0,
                    "dependency_independence_proven": False,
                    "statistical_independence_proven": False,
                },
                "counterevidence": {
                    "visible_failure_sequence_refs": ["seq_failure"],
                },
                "evidence_sufficiency": {
                    "state": "DEPENDENCY_LIMITED",
                    "blocking_dimensions": ["INDEPENDENCE_UNPROVEN"],
                },
                "forbidden_inference": ["TACTICAL_PATTERN_TRUTH"],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _base_admission() -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "handoff_1",
                "decision": "EMIT",
                "claim_output_allowed": True,
                "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY",
                "decision_reasons": [],
            }
        ],
        "safe_finding_admission_decision_count": 1,
        "finding_status_counts": {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0},
        "professional_finding_emitted_count": 1,
        "claim_output_allowed_count": 1,
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _challenge() -> dict:
    return {
        "status": "PASS",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "challenge_1",
                "source_process_variant_family_ref": "family_1",
                "challenge_reasons": [],
                "counter_scenario_candidates": [],
                "withdrawal_conditions": [],
                "relevant_coverage_incomplete_variant_count": 0,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            }
        ],
        "professional_finding_emit_allowed": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "unassessed_censoring_can_be_treated_as_failure": False,
        "difference_rows_are_independent_evidence_votes": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variant() -> dict:
    return {
        "status": "PASS",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_count": 20,
                "member_records": [
                    {
                        "sequence_ref": "seq_success",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "sequence_ref": "seq_failure",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                    },
                ],
                "supporting_occurrence_slot_count": 40,
                "unique_supporting_action_occurrence_candidate_count": 12,
                "supporting_occurrence_reuse_slot_count": 28,
                "supporting_occurrence_reuse_state": "OCCURRENCE_REUSE_VISIBLE",
                "occurrence_disjoint_support_cluster_count": 4,
                "occurrence_disjoint_support_cluster_state": "MULTIPLE_OCCURRENCE_DISJOINT_SUPPORT_CLUSTERS_VISIBLE",
                "visible_episode_spread_count": 3,
                "visible_episode_spread_state": "MULTIPLE_VISIBLE_EPISODE_CANDIDATES",
                "success_visible_episode_spread_count": 3,
                "failure_visible_episode_spread_count": 1,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_multi_cluster_multi_episode_spread_cannot_rescue_unproven_independence() -> None:
    adapted = apply_variant_feature_challenge_to_admission(
        _sequence(), _base_admission(), _challenge(), _process_variant()
    )

    assert adapted["status"] == "REVIEW_REQUIRED"
    decision = adapted["safe_finding_admission_decisions"][0]
    assert decision["decision"] == "DOWNGRADE"
    assert decision["claim_output_allowed"] is False
    assert decision["variant_support_multi_occurrence_disjoint_cluster_visible"] is True
    assert decision["variant_support_multi_episode_spread_visible"] is True
    assert decision["variant_support_spread_is_independent_support"] is False
    assert decision["variant_support_spread_is_recurrence_truth"] is False
    assert decision["variant_support_spread_can_increase_support"] is False
    assert decision["variant_support_spread_can_authorize_emit"] is False
    assert "VARIANT_FEATURE_CHALLENGE_DEPENDENCY_INDEPENDENCE_UNPROVEN" in decision["decision_reasons"]
    assert "VARIANT_FEATURE_CHALLENGE_STATISTICAL_INDEPENDENCE_UNPROVEN" in decision["decision_reasons"]

    profile = decision["variant_support_spread_profiles"][0]
    assert profile["member_count"] == 20
    assert profile["supporting_occurrence_slot_count"] == 40
    assert profile["unique_supporting_action_occurrence_candidate_count"] == 12
    assert profile["supporting_occurrence_reuse_slot_count"] == 28
    assert profile["occurrence_disjoint_support_cluster_count"] == 4
    assert profile["visible_episode_spread_count"] == 3
    assert profile["occurrence_disjoint_cluster_count_is_independent_support_count"] is False
    assert profile["episode_spread_count_is_independent_support_count"] is False
    assert profile["episode_spread_is_recurrence_truth"] is False


def test_analyst_output_can_describe_spread_but_never_call_it_independent_recurrence() -> None:
    adapted = apply_variant_feature_challenge_to_admission(
        _sequence(), _base_admission(), _challenge(), _process_variant()
    )
    contract = build_analyst_output_claim_contract(_sequence(), adapted)

    assert contract["professional_emit_allowed"] is False
    assert contract["variant_support_spread_is_independent_support"] is False
    assert contract["variant_support_spread_is_recurrence_truth"] is False
    assert contract["variant_support_spread_can_increase_support"] is False
    assert contract["variant_support_spread_can_authorize_emit"] is False

    row = contract["analyst_output_contracts"][0]
    assert row["safe_finding_admission_decision"] == "DOWNGRADE"
    assert row["professional_emit_allowed"] is False
    assert row["variant_support_multi_occurrence_disjoint_cluster_visible"] is True
    assert row["variant_support_multi_episode_spread_visible"] is True
    assert row["support_spread_may_be_reported_as_observed_match_local_description"] is True
    assert row["variant_support_spread_is_independent_support"] is False
    assert row["variant_support_spread_is_recurrence_truth"] is False
    assert row["variant_support_spread_can_authorize_emit"] is False
    assert row["dependent_branches_may_be_labeled_independent_recurrence"] is False
    profile = row["variant_support_spread_profiles"][0]
    assert profile["occurrence_disjoint_support_cluster_count"] == 4
    assert profile["visible_episode_spread_count"] == 3
