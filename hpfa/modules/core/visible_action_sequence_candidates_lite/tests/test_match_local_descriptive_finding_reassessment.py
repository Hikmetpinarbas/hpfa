from safe_finding_admission_current_v1 import reassess_match_local_descriptive_findings


def _payload():
    return {
        "status": "REVIEW_REQUIRED",
        "safe_finding_admission_decisions": [{
            "source_safe_finding_handoff_ref": "sfh_1",
            "decision": "DOWNGRADE",
            "claim_output_allowed": False,
            "decision_reasons": [
                "CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN",
                "DEPENDENCY_GROUP_BURDEN_UNRESOLVED",
                "DEPENDENCY_INDEPENDENCE_NOT_PROVEN",
                "INDEPENDENT_SUPPORT_NOT_ADMITTED",
                "REFLECTION_DEPENDENCY_PRESENT_NO_INDEPENDENT_VOTE",
                "SHARED_ANCHOR_DEPENDENCY_BURDEN",
                "STATISTICAL_INDEPENDENCE_NOT_PROVEN",
                "VARIANT_FEATURE_CHALLENGE_DEPENDENCY_INDEPENDENCE_UNPROVEN",
                "VARIANT_FEATURE_CHALLENGE_STATISTICAL_INDEPENDENCE_UNPROVEN",
            "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_SENSITIVE",
            ],
            "eligible_denominator": 4,
            "resolved_outcome_case_count": 4,
            "unresolved_outcome_case_count": 0,
            "actor_spread_count": 3,
            "single_actor_concentration": False,
            "typed_defeat_target_unresolved": False,
            "variant_feature_challenge_binding_state": "MATCHED_CHALLENGE_VISIBLE",
            "variant_feature_challenge_coverage_partial": False,
            "variant_support_multi_occurrence_disjoint_cluster_visible": True,
            "variant_support_multi_episode_spread_visible": True,
            "variant_support_episode_spread_observed": True,
            "variant_support_episode_spread_max_visible_count": 3,
            "variant_support_spread_profiles": [{
                "occurrence_disjoint_support_cluster_count": 3,
                "visible_episode_spread_count": 3,
                "success_visible_episode_spread_count": 2,
                "failure_visible_episode_spread_count": 1,
            }],
            "branch_preoutcome_context_enrichment": {
                "state": "PRE_BRANCH_CONTEXT_ENRICHED_GAME_STATE_AND_PROCESS",
                "branch_comparison_context_complete": True,
            },
        }],
        "professional_finding_emitted_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_strict_multi_episode_candidate_becomes_match_local_descriptive_finding_only():
    out = reassess_match_local_descriptive_findings(_payload())
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert row["match_local_descriptive_finding_admitted"] is True
    assert row["match_local_descriptive_finding_scope"] == "MATCH_LOCAL_OBSERVED_MECHANISM_FINDING_ONLY"
    assert row["statistical_generalization_allowed"] is False
    assert row["causal_inference_allowed"] is False
    assert row["tactical_truth_allowed"] is False
    assert out["match_local_descriptive_finding_admitted_count"] == 1
    assert out["professional_finding_emitted_count"] == 0


def test_unresolved_horizon_blocks_descriptive_admission():
    payload = _payload()
    payload["safe_finding_admission_decisions"][0]["decision_reasons"].append(
        "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_UNRESOLVED"
    )
    out = reassess_match_local_descriptive_findings(payload)
    assert out["safe_finding_admission_decisions"][0]["match_local_descriptive_finding_admitted"] is False