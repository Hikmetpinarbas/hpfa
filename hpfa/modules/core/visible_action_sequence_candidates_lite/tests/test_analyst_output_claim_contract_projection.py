from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    ANALYST_OUTPUT_CLAIM_SCOPE,
    build_analyst_output_claim_contract,
)


def _payload(raw_rate=0.99):
    return {
        "safe_finding_handoff_professional_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_test",
                "professional_finding_emit_allowed": False,
                "support": {
                    "raw_success_rate": raw_rate,
                    "dependency_independence_proven": False,
                    "statistical_independence_proven": False,
                },
                "counterevidence": {
                    "absence_used_as_counterevidence": False,
                },
                "evidence_sufficiency": {
                    "state": "INSUFFICIENT_FOR_PROFESSIONAL_EMIT",
                    "blocking_dimensions": [
                        "INDEPENDENT_SUPPORT_NOT_ADMITTED",
                        "DEPENDENCY_INDEPENDENCE_NOT_PROVEN",
                    ],
                },
                "forbidden_inference": [
                    "TRUE_SUCCESS_PROBABILITY",
                    "TACTICAL_PATTERN_TRUTH",
                    "CAUSALITY",
                ],
            }
        ],
    }


def _contract(result):
    assert result["analyst_output_contract_count"] == 1
    return result["analyst_output_contracts"][0]


def test_contract_preserves_match_local_claim_ceiling():
    result = build_analyst_output_claim_contract(_payload())
    contract = _contract(result)
    assert result["status"] == "PASS"
    assert contract["claim_scope"] == ANALYST_OUTPUT_CLAIM_SCOPE
    assert contract["professional_emit_allowed"] is False
    assert contract["match_local_observation_may_be_generalized_cross_match"] is False
    assert contract["recommended_lead_in_tr"] == "Bu maçta gözlenen örneklerde"


def test_high_raw_rate_cannot_be_promoted_to_probability():
    result = build_analyst_output_claim_contract(_payload(raw_rate=0.99))
    contract = _contract(result)
    assert contract["raw_rate_may_be_reported_as_observed_sample_description"] is True
    assert contract["raw_rate_may_be_labeled_probability"] is False
    assert "TRUE_SUCCESS_PROBABILITY" in contract["forbidden_claim_families"]


def test_provider_success_semantic_cannot_be_promoted_to_tactical_success():
    contract = _contract(build_analyst_output_claim_contract(_payload()))
    assert contract["provider_outcome_semantic_may_be_labeled_tactical_success"] is False
    assert "TACTICAL_PATTERN_TRUTH" in contract["forbidden_claim_families"]


def test_dependency_blocks_recurrence_language():
    contract = _contract(build_analyst_output_claim_contract(_payload()))
    assert contract["dependent_branches_may_be_labeled_independent_recurrence"] is False
    assert "INDEPENDENT_RECURRENCE_SUPPORT" in contract["forbidden_claim_families"]


def test_absence_and_generated_text_never_become_evidence():
    result = build_analyst_output_claim_contract(_payload())
    contract = _contract(result)
    assert contract["absence_may_be_promoted_to_positive_support"] is False
    assert contract["absence_may_be_promoted_to_counterevidence"] is False
    assert contract["analyst_or_llm_text_is_evidence"] is False
    assert result["analyst_or_llm_text_is_evidence"] is False


def test_truth_policy_breach_fails_closed():
    payload = _payload()
    payload["production_release"] = True
    result = build_analyst_output_claim_contract(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["analyst_output_contract_count"] == 0
    assert "production_release_claimed" in result["hard_block_hits"]


def test_missing_handoff_identity_requires_review():
    payload = _payload()
    payload["safe_finding_handoff_candidates"][0].pop("safe_finding_handoff_candidate_id")
    result = build_analyst_output_claim_contract(payload)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["analyst_output_contract_count"] == 0


def test_no_sample_match_identity_leak():
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/"
        "analyst_output_claim_contract_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Fenerbahçe", "Roma", "09.09.2026", "10.09.2026"):
        assert token not in source


def _admission_with_numeric_bound(*, unsafe_emit=False):
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_test",
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
                "consequence_observation_burden_profile": {
                    "bound_state": "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE",
                    "estimand_id": "MATCH_LOCAL_VISIBLE_PROCESS_OUTCOME_RATE",
                    "eligible_denominator_basis": "UNIQUE_OBSERVABLE_PROCESS_VARIANT_FAMILY_MEMBER_SEQUENCE_REFS",
                    "resolved_success_n": 4,
                    "resolved_failure_n": 1,
                    "unresolved_eligible_n": 2,
                    "eligible_total_n": 7,
                    "lower_bound": 4 / 7,
                    "upper_bound": 6 / 7,
                    "bound_width": 2 / 7,
                    "assumption_set_id": "BINARY_VISIBLE_OUTCOME_KNOWN_ELIGIBLE_DENOMINATOR_WORST_CASE_UNRESOLVED_V1",
                    "denominator_membership_admitted": True,
                    "target_outcome_semantics_fixed": True,
                    "matched_process_variant_family_refs": ["family_test"],
                    "identification_interval_is_confidence_interval": False,
                    "rate_bound_is_true_probability": False,
                    "rate_bound_is_population_rate": False,
                    "rate_bound_is_causal_effect": False,
                    "rate_bound_can_authorize_emit": unsafe_emit,
                    "rate_bound_can_strengthen_claim_ceiling": False,
                    "rate_bound_creates_new_evidence": False,
                    "claim_ceiling": "MATCH_LOCAL_VISIBLE_OUTCOME_RATE_BOUND_ONLY",
                },
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_source_bound_numeric_rate_bound_is_projected_without_recomputation():
    result = build_analyst_output_claim_contract(_payload(), _admission_with_numeric_bound())
    contract = _contract(result)

    assert result["status"] == "PASS"
    assert result["partial_identification_rate_bound_projected"] is True
    assert result["partial_identification_rate_bound_recomputed_downstream"] is False
    assert contract["rate_bound_binding_state"] == "SOURCE_BOUND_NUMERIC"
    assert contract["rate_bound_state"] == "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"
    assert contract["rate_bound_resolved_success_n"] == 4
    assert contract["rate_bound_resolved_failure_n"] == 1
    assert contract["rate_bound_unresolved_eligible_n"] == 2
    assert contract["rate_bound_eligible_total_n"] == 7
    assert contract["rate_bound_lower"] == 4 / 7
    assert contract["rate_bound_upper"] == 6 / 7
    assert contract["rate_bound_width"] == 2 / 7
    assert contract["rate_bound_matched_process_variant_family_refs"] == ["family_test"]
    assert contract["rate_bound_is_confidence_interval"] is False
    assert contract["rate_bound_can_authorize_emit"] is False
    assert contract["rate_bound_can_strengthen_claim_ceiling"] is False
    assert contract["rate_bound_creates_new_evidence"] is False


def test_unsafe_rate_bound_contract_fails_closed():
    result = build_analyst_output_claim_contract(
        _payload(),
        _admission_with_numeric_bound(unsafe_emit=True),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["analyst_output_contract_count"] == 0
    assert any("unsafe_rate_bound_contract" in value for value in result["hard_block_hits"])


def test_typed_defeat_profile_is_projected_without_claim_strengthening():
    admission = {
        "status": "REVIEW_REQUIRED",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_test",
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
                "typed_defeat_profile": {
                    "binding_state": "SOURCE_BOUND_TYPED_DEFEAT_CONTRACT",
                    "observed_defeat_state": "UNRESOLVED_NO_EXPLICIT_CLAIM_COMPONENT_TARGET",
                    "observed_defeat_type": "DEFEAT_TYPE_UNRESOLVED",
                    "observed_target_component_type": None,
                    "observed_target_component_ref": None,
                    "observed_source_counterevidence_refs": ["counter_1"],
                    "conditional_withdrawal_rules": [
                        {
                            "condition_code": "WITHDRAW_IF_BINDING_INVALIDATED",
                            "defeat_type": "UNDERCUT",
                            "target_component_type": "INFERENCE_WARRANT",
                            "target_component_ref": "sfh_test",
                            "withdrawal_effect": "ABSTAIN",
                        }
                    ],
                    "defeat_can_authorize_emit": False,
                    "defeat_can_strengthen_claim_ceiling": False,
                    "defeat_creates_new_evidence": False,
                    "defeat_is_causal_refutation": False,
                    "defeat_is_independent_support": False,
                    "withdrawal_effect_can_strengthen_claim": False,
                },
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    result = build_analyst_output_claim_contract(_payload(), admission)
    contract = _contract(result)

    assert contract["typed_defeat_binding_state"] == "SOURCE_BOUND_TYPED_DEFEAT_CONTRACT"
    assert contract["typed_defeat_observed_type"] == "DEFEAT_TYPE_UNRESOLVED"
    assert contract["typed_defeat_source_counterevidence_refs"] == ["counter_1"]
    assert contract["typed_withdrawal_rule_count"] == 1
    assert contract["typed_defeat_can_authorize_emit"] is False
    assert contract["typed_defeat_can_strengthen_claim_ceiling"] is False
    assert contract["typed_defeat_creates_new_evidence"] is False
    assert result["typed_defeat_contract_projected"] is True
