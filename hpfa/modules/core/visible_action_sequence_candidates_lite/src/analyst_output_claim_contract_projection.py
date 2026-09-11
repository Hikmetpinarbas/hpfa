from __future__ import annotations

from typing import Any

ANALYST_OUTPUT_CLAIM_SCOPE = "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY"

FORBIDDEN_CLAIM_FAMILIES = [
    "TRUE_SUCCESS_PROBABILITY",
    "INTRINSIC_PROCESS_EFFICIENCY",
    "INDEPENDENT_RECURRENCE_SUPPORT",
    "TACTICAL_PATTERN_TRUTH",
    "COACH_INTENTION",
    "FAILURE_CAUSE",
    "CAUSALITY",
    "CROSS_MATCH_GENERALIZATION",
    "POPULATION_LEVEL_RATE",
]

REQUIRED_QUALIFIERS = [
    "MATCH_LOCAL",
    "OBSERVED_VISIBLE_BRANCHES_ONLY",
    "OUTCOME_SEMANTIC_NOT_TACTICAL_SUCCESS_TRUTH",
    "RAW_RATE_NOT_TRUE_PROBABILITY",
    "DEPENDENT_BRANCHES_NOT_INDEPENDENT_RECURRENCES",
]


def build_analyst_output_claim_contract(
    comparable_outcome_payload: dict[str, Any],
) -> dict[str, Any]:
    """Project Safe Finding handoffs into machine-readable analyst-output limits.

    This stage does not create evidence, strengthen claims, or authorize professional
    findings. It only converts already-derived Safe Finding limits into explicit
    downstream language constraints.
    """
    if comparable_outcome_payload.get("production_release") is True:
        return _fail_closed("production_release_claimed")
    if comparable_outcome_payload.get("canonical_event_count") != "UNKNOWN":
        return _fail_closed("canonical_event_count_claimed")
    if comparable_outcome_payload.get("true_action_count") != "UNKNOWN":
        return _fail_closed("true_action_count_claimed")
    if comparable_outcome_payload.get("safe_finding_handoff_professional_emit_allowed") is not False:
        return _fail_closed("professional_emit_policy_not_locked_false")

    contracts: list[dict[str, Any]] = []
    review_hits: list[str] = []

    for handoff in comparable_outcome_payload.get("safe_finding_handoff_candidates") or []:
        if not isinstance(handoff, dict):
            continue

        handoff_id = str(handoff.get("safe_finding_handoff_candidate_id") or "").strip()
        if not handoff_id:
            review_hits.append("safe_finding_handoff_candidate_id_missing")
            continue

        if handoff.get("professional_finding_emit_allowed") is not False:
            review_hits.append(f"professional_emit_not_locked_false:{handoff_id}")
            continue

        sufficiency = handoff.get("evidence_sufficiency") or {}
        sufficiency_state = str(sufficiency.get("state") or "UNKNOWN")
        blocking_dimensions = sorted(
            {
                str(value).strip()
                for value in (sufficiency.get("blocking_dimensions") or [])
                if str(value).strip()
            }
        )
        forbidden = sorted(
            set(FORBIDDEN_CLAIM_FAMILIES)
            | {
                str(value).strip()
                for value in (handoff.get("forbidden_inference") or [])
                if str(value).strip()
            }
        )

        contracts.append(
            {
                "analyst_output_contract_id": f"aoc_{handoff_id}",
                "source_safe_finding_handoff_ref": handoff_id,
                "claim_scope": ANALYST_OUTPUT_CLAIM_SCOPE,
                "professional_emit_allowed": False,
                "evidence_sufficiency_state": sufficiency_state,
                "blocking_dimensions": blocking_dimensions,
                "required_qualifiers": list(REQUIRED_QUALIFIERS),
                "forbidden_claim_families": forbidden,
                "raw_rate_may_be_reported_as_observed_sample_description": True,
                "raw_rate_may_be_labeled_probability": False,
                "provider_outcome_semantic_may_be_labeled_tactical_success": False,
                "dependent_branches_may_be_labeled_independent_recurrence": False,
                "match_local_observation_may_be_generalized_cross_match": False,
                "absence_may_be_promoted_to_positive_support": False,
                "absence_may_be_promoted_to_counterevidence": False,
                "analyst_or_llm_text_is_evidence": False,
                "language_must_preserve_observation_inference_separation": True,
                "recommended_lead_in_tr": "Bu maçta gözlenen örneklerde",
                "safe_output_meaning": "MATCH_LOCAL_OBSERVED_VISIBLE_VARIATION_ONLY",
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
            }
        )

    status = "REVIEW_REQUIRED" if review_hits else "PASS"
    return {
        "status": status,
        "analyst_output_contracts": contracts,
        "analyst_output_contract_count": len(contracts),
        "professional_emit_allowed": False,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "analyst_or_llm_text_is_evidence": False,
        "review_hits": sorted(set(review_hits)),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_scope": ANALYST_OUTPUT_CLAIM_SCOPE,
    }


def _fail_closed(reason: str) -> dict[str, Any]:
    return {
        "status": "FAIL_CLOSED",
        "analyst_output_contracts": [],
        "analyst_output_contract_count": 0,
        "professional_emit_allowed": False,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "analyst_or_llm_text_is_evidence": False,
        "review_hits": [],
        "hard_block_hits": [reason],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_scope": ANALYST_OUTPUT_CLAIM_SCOPE,
    }
