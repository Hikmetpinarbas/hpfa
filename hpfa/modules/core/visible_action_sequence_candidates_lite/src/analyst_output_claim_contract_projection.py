from __future__ import annotations

from typing import Any

ANALYST_OUTPUT_CLAIM_SCOPE = "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY"
ADMITTED_PROFESSIONAL_FINDING_SCOPE = "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
NO_CLAIM_SCOPE = "NO_CLAIM_OUTPUT"

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


def _admission_map(admission_payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str], str | None]:
    if admission_payload is None:
        return {}, [], None
    if admission_payload.get("status") == "FAIL_CLOSED":
        return {}, [], "safe_finding_admission_fail_closed"
    if admission_payload.get("production_release") is True:
        return {}, [], "admission_production_release_claimed"
    if admission_payload.get("canonical_event_count") != "UNKNOWN":
        return {}, [], "admission_canonical_event_count_claimed"
    if admission_payload.get("true_action_count") != "UNKNOWN":
        return {}, [], "admission_true_action_count_claimed"

    decisions: dict[str, dict[str, Any]] = {}
    reviews: list[str] = []
    for row in admission_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict):
            reviews.append("admission_row_not_object")
            continue
        source_ref = str(row.get("source_safe_finding_handoff_ref") or "").strip()
        if not source_ref:
            reviews.append("admission_source_ref_missing")
            continue
        if source_ref in decisions:
            return {}, reviews, f"duplicate_admission_decision:{source_ref}"
        decisions[source_ref] = row
    return decisions, reviews, None


def build_analyst_output_claim_contract(
    comparable_outcome_payload: dict[str, Any],
    admission_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project admitted Safe Findings into machine-readable analyst-output limits.

    With no admission payload this preserves the legacy fail-safe behavior: no
    professional finding may emit. When the compact Safe Finding admission micro-gear
    is provided, only an explicit EMIT decision may open a defeasible match-local
    professional finding. This stage creates no evidence and never strengthens the
    underlying football claim ceiling.
    """
    if comparable_outcome_payload.get("production_release") is True:
        return _fail_closed("production_release_claimed")
    if comparable_outcome_payload.get("canonical_event_count") != "UNKNOWN":
        return _fail_closed("canonical_event_count_claimed")
    if comparable_outcome_payload.get("true_action_count") != "UNKNOWN":
        return _fail_closed("true_action_count_claimed")
    if comparable_outcome_payload.get("safe_finding_handoff_professional_emit_allowed") is not False:
        return _fail_closed("professional_emit_policy_not_locked_false")

    admission_by_ref, admission_reviews, admission_block = _admission_map(admission_payload)
    if admission_block:
        return _fail_closed(admission_block)

    contracts: list[dict[str, Any]] = []
    review_hits: list[str] = list(admission_reviews)
    decision_counts = {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0, "NOT_EVALUATED": 0}

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

        decision_row = admission_by_ref.get(handoff_id) if admission_payload is not None else None
        if admission_payload is None:
            decision = "NOT_EVALUATED"
            professional_emit_allowed = False
            claim_scope = ANALYST_OUTPUT_CLAIM_SCOPE
        elif decision_row is None:
            decision = "ABSTAIN"
            professional_emit_allowed = False
            claim_scope = NO_CLAIM_SCOPE
            review_hits.append(f"admission_decision_missing:{handoff_id}")
        else:
            decision = str(decision_row.get("decision") or "").strip().upper()
            if decision not in {"EMIT", "DOWNGRADE", "ABSTAIN"}:
                decision = "ABSTAIN"
                review_hits.append(f"admission_decision_unrecognized:{handoff_id}")
            professional_emit_allowed = (
                decision == "EMIT" and decision_row.get("claim_output_allowed") is True
            )
            if decision == "EMIT" and not professional_emit_allowed:
                decision = "ABSTAIN"
                review_hits.append(f"emit_without_claim_output_admission:{handoff_id}")
            claim_scope = (
                ADMITTED_PROFESSIONAL_FINDING_SCOPE
                if professional_emit_allowed
                else NO_CLAIM_SCOPE if decision == "ABSTAIN" else ANALYST_OUTPUT_CLAIM_SCOPE
            )

        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        contracts.append(
            {
                "analyst_output_contract_id": f"aoc_{handoff_id}",
                "source_safe_finding_handoff_ref": handoff_id,
                "claim_scope": claim_scope,
                "safe_finding_admission_decision": decision,
                "professional_emit_allowed": professional_emit_allowed,
                "evidence_sufficiency_state": sufficiency_state,
                "blocking_dimensions": blocking_dimensions,
                "required_qualifiers": list(REQUIRED_QUALIFIERS),
                "forbidden_claim_families": forbidden,
                "raw_rate_may_be_reported_as_observed_sample_description": decision != "ABSTAIN",
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

    emitted_count = sum(1 for row in contracts if row.get("professional_emit_allowed") is True)
    status = "REVIEW_REQUIRED" if review_hits else "PASS"
    return {
        "status": status,
        "analyst_output_contracts": contracts,
        "analyst_output_contract_count": len(contracts),
        "safe_finding_admission_consumed": admission_payload is not None,
        "safe_finding_admission_decision_counts": decision_counts,
        "professional_emit_allowed": emitted_count > 0,
        "professional_emit_allowed_count": emitted_count,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "analyst_or_llm_text_is_evidence": False,
        "claim_contract_creates_new_evidence": False,
        "review_hits": sorted(set(review_hits)),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_scope": (
            ADMITTED_PROFESSIONAL_FINDING_SCOPE
            if emitted_count > 0
            else ANALYST_OUTPUT_CLAIM_SCOPE
        ),
    }


def _fail_closed(reason: str) -> dict[str, Any]:
    return {
        "status": "FAIL_CLOSED",
        "analyst_output_contracts": [],
        "analyst_output_contract_count": 0,
        "safe_finding_admission_consumed": False,
        "safe_finding_admission_decision_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0, "NOT_EVALUATED": 0},
        "professional_emit_allowed": False,
        "professional_emit_allowed_count": 0,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "analyst_or_llm_text_is_evidence": False,
        "claim_contract_creates_new_evidence": False,
        "review_hits": [],
        "hard_block_hits": [reason],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_scope": ANALYST_OUTPUT_CLAIM_SCOPE,
    }
