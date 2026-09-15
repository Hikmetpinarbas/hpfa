from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    build_analyst_output_claim_contract,
)


def _sequence() -> dict:
    return {
        "safe_finding_handoff_professional_emit_allowed": False,
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "professional_finding_emit_allowed": False,
                "evidence_sufficiency": {
                    "state": "INSUFFICIENT_FOR_PROFESSIONAL_EMIT",
                    "blocking_dimensions": ["INDEPENDENT_SUPPORT_NOT_ADMITTED"],
                },
                "forbidden_inference": ["CAUSALITY"],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _admission() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_consumed": True,
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "DOWNGRADE",
                "claim_output_allowed": False,
                "variant_feature_challenge_binding_state": "MATCHED_CHALLENGE_VISIBLE",
                "variant_feature_challenge_family_refs": ["family_1"],
                "variant_feature_challenge_refs": ["vfc_1"],
                "variant_feature_challenge_reason_codes": [
                    "SAMPLE_STRENGTH_UNCALIBRATED"
                ],
                "variant_feature_challenge_counter_scenario_candidates": [
                    "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"
                ],
                "variant_feature_challenge_withdrawal_condition_candidates": [
                    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_DISAPPEARS_IN_ADMITTED_COMPARABLE_CONTEXT"
                ],
                "variant_feature_challenge_coverage_partial": False,
                "variant_feature_challenge_dependency_independence_proven": False,
                "variant_feature_challenge_statistical_independence_proven": False,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_analyst_contract_carries_compact_challenge_provenance_without_claim_inflation() -> None:
    result = build_analyst_output_claim_contract(_sequence(), _admission())

    assert result["variant_feature_challenge_admission_consumed"] is True
    assert result["variant_feature_challenge_is_independent_evidence_vote"] is False
    assert result["variant_feature_challenge_can_authorize_emit"] is False
    assert result["professional_emit_allowed"] is False

    contract = result["analyst_output_contracts"][0]
    assert contract["variant_feature_challenge_binding_state"] == "MATCHED_CHALLENGE_VISIBLE"
    assert contract["variant_feature_challenge_family_refs"] == ["family_1"]
    assert contract["variant_feature_challenge_refs"] == ["vfc_1"]
    assert contract["variant_feature_challenge_reason_codes"] == [
        "SAMPLE_STRENGTH_UNCALIBRATED"
    ]
    assert contract["variant_feature_challenge_counter_scenario_candidates"] == [
        "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"
    ]
    assert contract["variant_feature_challenge_withdrawal_condition_candidates"] == [
        "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_DISAPPEARS_IN_ADMITTED_COMPARABLE_CONTEXT"
    ]
    assert contract["variant_feature_challenge_is_independent_evidence_vote"] is False
    assert contract["variant_feature_challenge_can_authorize_emit"] is False
    assert contract["professional_emit_allowed"] is False
