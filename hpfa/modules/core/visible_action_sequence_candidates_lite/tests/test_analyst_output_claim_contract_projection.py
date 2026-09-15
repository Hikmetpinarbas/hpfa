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
