from __future__ import annotations

from typing import Any

ANALYST_OUTPUT_CLAIM_SCOPE = "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY"
ADMITTED_PROFESSIONAL_FINDING_SCOPE = "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
NO_CLAIM_SCOPE = "NO_CLAIM_OUTPUT"
RATE_BOUND_CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_OUTCOME_RATE_BOUND_ONLY"
RATE_BOUND_NUMERIC_STATES = {"POINT_IDENTIFIED_OBSERVED_RATE", "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"}

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


def _compact_refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _admission_map(admission_payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str], str | None]:
    if admission_payload is None:
        return {}, [], None
    status = str(admission_payload.get("status") or "").strip().upper()
    if status == "FAIL_CLOSED":
        return {}, [], "safe_finding_admission_fail_closed"
    if status not in {"PASS", "REVIEW_REQUIRED"}:
        return {}, [], f"safe_finding_admission_status_unrecognized:{status or 'UNKNOWN'}"
    if admission_payload.get("production_release") is True:
        return {}, [], "admission_production_release_claimed"
    if admission_payload.get("canonical_event_count") != "UNKNOWN":
        return {}, [], "admission_canonical_event_count_claimed"
    if admission_payload.get("true_action_count") != "UNKNOWN":
        return {}, [], "admission_true_action_count_claimed"

    decisions: dict[str, dict[str, Any]] = {}
    reviews: list[str] = []
    review_required = status == "REVIEW_REQUIRED"
    if review_required:
        reviews.append("safe_finding_admission_review_required")
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
        normalized = dict(row)
        if review_required and str(normalized.get("decision") or "").strip().upper() == "EMIT":
            normalized["decision"] = "ABSTAIN"
            normalized["claim_output_allowed"] = False
            reviews.append(f"emit_blocked_by_review_required_admission:{source_ref}")
        decisions[source_ref] = normalized
    return decisions, reviews, None


def _challenge_contract(decision_row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(decision_row, dict):
        return {
            "variant_feature_challenge_binding_state": "NOT_AVAILABLE",
            "variant_feature_challenge_family_refs": [],
            "variant_feature_challenge_refs": [],
            "variant_feature_challenge_reason_codes": [],
            "variant_feature_challenge_counter_scenario_candidates": [],
            "variant_feature_challenge_withdrawal_condition_candidates": [],
            "variant_feature_challenge_coverage_partial": False,
            "variant_feature_challenge_dependency_independence_proven": False,
            "variant_feature_challenge_statistical_independence_proven": False,
            "variant_feature_challenge_is_independent_evidence_vote": False,
            "variant_feature_challenge_can_authorize_emit": False,
        }
    return {
        "variant_feature_challenge_binding_state": str(
            decision_row.get("variant_feature_challenge_binding_state") or "NOT_AVAILABLE"
        ),
        "variant_feature_challenge_family_refs": _compact_refs(
            decision_row.get("variant_feature_challenge_family_refs")
        ),
        "variant_feature_challenge_refs": _compact_refs(
            decision_row.get("variant_feature_challenge_refs")
        ),
        "variant_feature_challenge_reason_codes": _compact_refs(
            decision_row.get("variant_feature_challenge_reason_codes")
        ),
        "variant_feature_challenge_counter_scenario_candidates": _compact_refs(
            decision_row.get("variant_feature_challenge_counter_scenario_candidates")
        ),
        "variant_feature_challenge_withdrawal_condition_candidates": _compact_refs(
            decision_row.get("variant_feature_challenge_withdrawal_condition_candidates")
        ),
        "variant_feature_challenge_coverage_partial": (
            decision_row.get("variant_feature_challenge_coverage_partial") is True
        ),
        "variant_feature_challenge_dependency_independence_proven": (
            decision_row.get("variant_feature_challenge_dependency_independence_proven") is True
        ),
        "variant_feature_challenge_statistical_independence_proven": (
            decision_row.get("variant_feature_challenge_statistical_independence_proven") is True
        ),
        "variant_feature_challenge_is_independent_evidence_vote": False,
        "variant_feature_challenge_can_authorize_emit": False,
    }


def _support_spread_contract(decision_row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(decision_row, dict):
        return {
            "variant_support_spread_profiles": [],
            "variant_support_multi_occurrence_disjoint_cluster_visible": False,
            "variant_support_multi_episode_spread_visible": False,
            "variant_support_episode_spread_observed": False,
            "variant_support_episode_spread_max_visible_count": 0,
            "variant_support_episode_spread_resolution_state": "UNRESOLVED",
            "variant_support_episode_spread_resolves_upstream_unknown": False,
            "variant_support_spread_is_independent_support": False,
            "variant_support_spread_is_recurrence_truth": False,
            "variant_support_spread_can_increase_support": False,
            "variant_support_spread_can_authorize_emit": False,
        }

    profiles: list[dict[str, Any]] = []
    for profile in decision_row.get("variant_support_spread_profiles") or []:
        if not isinstance(profile, dict):
            continue
        family_ref = str(profile.get("family_ref") or "").strip()
        if not family_ref:
            continue
        profiles.append({
            "family_ref": family_ref,
            "member_count": int(profile.get("member_count") or 0),
            "supporting_occurrence_slot_count": int(
                profile.get("supporting_occurrence_slot_count") or 0
            ),
            "unique_supporting_action_occurrence_candidate_count": int(
                profile.get("unique_supporting_action_occurrence_candidate_count") or 0
            ),
            "supporting_occurrence_reuse_slot_count": int(
                profile.get("supporting_occurrence_reuse_slot_count") or 0
            ),
            "supporting_occurrence_reuse_state": str(
                profile.get("supporting_occurrence_reuse_state") or "NOT_AVAILABLE"
            ),
            "occurrence_disjoint_support_cluster_count": int(
                profile.get("occurrence_disjoint_support_cluster_count") or 0
            ),
            "occurrence_disjoint_support_cluster_state": str(
                profile.get("occurrence_disjoint_support_cluster_state") or "NOT_AVAILABLE"
            ),
            "visible_episode_spread_count": int(
                profile.get("visible_episode_spread_count") or 0
            ),
            "visible_episode_spread_state": str(
                profile.get("visible_episode_spread_state") or "NOT_AVAILABLE"
            ),
            "success_visible_episode_spread_count": int(
                profile.get("success_visible_episode_spread_count") or 0
            ),
            "failure_visible_episode_spread_count": int(
                profile.get("failure_visible_episode_spread_count") or 0
            ),
            "member_count_is_independent_support_count": False,
            "unique_occurrence_count_is_independent_support_count": False,
            "occurrence_disjoint_cluster_count_is_independent_support_count": False,
            "episode_spread_count_is_independent_support_count": False,
            "occurrence_disjoint_cluster_count_is_recurrence_truth": False,
            "episode_spread_is_recurrence_truth": False,
        })

    return {
        "variant_support_spread_profiles": profiles,
        "variant_support_multi_occurrence_disjoint_cluster_visible": (
            decision_row.get("variant_support_multi_occurrence_disjoint_cluster_visible") is True
        ),
        "variant_support_multi_episode_spread_visible": (
            decision_row.get("variant_support_multi_episode_spread_visible") is True
        ),
        "variant_support_episode_spread_observed": (
            decision_row.get("variant_support_episode_spread_observed") is True
        ),
        "variant_support_episode_spread_max_visible_count": int(
            decision_row.get("variant_support_episode_spread_max_visible_count") or 0
        ),
        "variant_support_episode_spread_resolution_state": str(
            decision_row.get("variant_support_episode_spread_resolution_state") or "UNRESOLVED"
        ),
        "variant_support_episode_spread_resolves_upstream_unknown": (
            decision_row.get("variant_support_episode_spread_resolves_upstream_unknown") is True
        ),
        "variant_support_spread_is_independent_support": False,
        "variant_support_spread_is_recurrence_truth": False,
        "variant_support_spread_can_increase_support": False,
        "variant_support_spread_can_authorize_emit": False,
    }



def _rate_bound_contract(decision_row: dict[str, Any] | None) -> tuple[dict[str, Any], str | None]:
    """Project an already-admitted rate bound without recomputing it downstream."""
    empty = {
        "rate_bound_binding_state": "NOT_AVAILABLE",
        "rate_bound_estimand_id": None,
        "rate_bound_denominator_basis": None,
        "rate_bound_state": "NOT_AVAILABLE",
        "rate_bound_resolved_success_n": None,
        "rate_bound_resolved_failure_n": None,
        "rate_bound_unresolved_eligible_n": None,
        "rate_bound_eligible_total_n": None,
        "rate_bound_lower": None,
        "rate_bound_upper": None,
        "rate_bound_width": None,
        "rate_bound_assumption_set_id": None,
        "rate_bound_matched_process_variant_family_refs": [],
        "rate_bound_is_confidence_interval": False,
        "rate_bound_is_true_probability": False,
        "rate_bound_is_population_rate": False,
        "rate_bound_is_causal_effect": False,
        "rate_bound_can_authorize_emit": False,
        "rate_bound_can_strengthen_claim_ceiling": False,
        "rate_bound_creates_new_evidence": False,
    }
    if not isinstance(decision_row, dict):
        return empty, None
    profile = decision_row.get("consequence_observation_burden_profile")
    if not isinstance(profile, dict):
        return empty, None

    state = str(profile.get("bound_state") or "BOUND_UNRESOLVED").strip().upper()
    family_refs = _compact_refs(profile.get("matched_process_variant_family_refs"))
    contract = {
        **empty,
        "rate_bound_binding_state": "SOURCE_BOUND_NON_NUMERIC",
        "rate_bound_estimand_id": profile.get("estimand_id"),
        "rate_bound_denominator_basis": profile.get("eligible_denominator_basis"),
        "rate_bound_state": state,
        "rate_bound_resolved_success_n": profile.get("resolved_success_n"),
        "rate_bound_resolved_failure_n": profile.get("resolved_failure_n"),
        "rate_bound_unresolved_eligible_n": profile.get("unresolved_eligible_n"),
        "rate_bound_eligible_total_n": profile.get("eligible_total_n"),
        "rate_bound_lower": profile.get("lower_bound"),
        "rate_bound_upper": profile.get("upper_bound"),
        "rate_bound_width": profile.get("bound_width"),
        "rate_bound_assumption_set_id": profile.get("assumption_set_id"),
        "rate_bound_matched_process_variant_family_refs": family_refs,
    }

    unsafe = (
        profile.get("identification_interval_is_confidence_interval") is not False
        or profile.get("rate_bound_is_true_probability") is not False
        or profile.get("rate_bound_is_population_rate") is not False
        or profile.get("rate_bound_is_causal_effect") is not False
        or profile.get("rate_bound_can_authorize_emit") is not False
        or profile.get("rate_bound_can_strengthen_claim_ceiling") is not False
        or profile.get("rate_bound_creates_new_evidence") is not False
    )
    if unsafe:
        return contract, "unsafe_rate_bound_contract"

    if state in RATE_BOUND_NUMERIC_STATES:
        counts = (
            profile.get("resolved_success_n"),
            profile.get("resolved_failure_n"),
            profile.get("unresolved_eligible_n"),
            profile.get("eligible_total_n"),
        )
        if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in counts):
            return contract, "numeric_rate_bound_count_contract_invalid"
        success_n, failure_n, unresolved_n, total_n = counts
        if success_n + failure_n + unresolved_n != total_n:
            return contract, "numeric_rate_bound_denominator_identity_invalid"
        lower = profile.get("lower_bound")
        upper = profile.get("upper_bound")
        width = profile.get("bound_width")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (lower, upper, width)):
            return contract, "numeric_rate_bound_value_contract_invalid"
        if not (0.0 <= float(lower) <= float(upper) <= 1.0):
            return contract, "numeric_rate_bound_order_invalid"
        if abs((float(upper) - float(lower)) - float(width)) > 1e-12:
            return contract, "numeric_rate_bound_width_invalid"
        if profile.get("denominator_membership_admitted") is not True:
            return contract, "numeric_rate_bound_denominator_not_admitted"
        if profile.get("target_outcome_semantics_fixed") is not True:
            return contract, "numeric_rate_bound_target_semantics_unresolved"
        if str(profile.get("claim_ceiling") or "") != RATE_BOUND_CLAIM_CEILING:
            return contract, "numeric_rate_bound_claim_ceiling_invalid"
        if not family_refs:
            return contract, "numeric_rate_bound_family_lineage_missing"
        contract["rate_bound_binding_state"] = "SOURCE_BOUND_NUMERIC"
    return contract, None


def build_analyst_output_claim_contract(
    comparable_outcome_payload: dict[str, Any],
    admission_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project admitted Safe Findings into machine-readable analyst-output limits.

    With no admission payload this preserves the legacy fail-safe behavior: no
    professional finding may emit. When the compact Safe Finding admission micro-gear
    is provided, only an explicit EMIT decision from a PASS admission envelope may open
    a defeasible match-local professional finding. REVIEW_REQUIRED is preserved as review
    debt and can never be laundered into professional output. Variant-feature challenge
    and support-spread metadata are carried only as compact provenance/qualification;
    they create no evidence and cannot authorize EMIT. Late-bound episode spread may
    resolve only a stale upstream UNKNOWN label and never independence or recurrence.
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

        challenge_contract = _challenge_contract(decision_row)
        support_spread_contract = _support_spread_contract(decision_row)
        rate_bound_contract, rate_bound_block = _rate_bound_contract(decision_row)
        if rate_bound_block:
            return _fail_closed(f"{rate_bound_block}:{handoff_id}")
        episode_spread_unknown_resolved = (
            support_spread_contract["variant_support_episode_spread_observed"] is True
        )
        if episode_spread_unknown_resolved:
            blocking_dimensions = [
                value for value in blocking_dimensions if value != "EPISODE_SPREAD_UNKNOWN"
            ]
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
                "upstream_episode_spread_unknown_resolved_by_late_bound_variant_family": (
                    episode_spread_unknown_resolved
                ),
                "required_qualifiers": list(REQUIRED_QUALIFIERS),
                "forbidden_claim_families": forbidden,
                **challenge_contract,
                **support_spread_contract,
                **rate_bound_contract,
                "support_spread_may_be_reported_as_observed_match_local_description": (
                    decision != "ABSTAIN"
                ),
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
        "variant_feature_challenge_admission_consumed": (
            isinstance(admission_payload, dict)
            and admission_payload.get("variant_feature_challenge_consumed") is True
        ),
        "safe_finding_admission_decision_counts": decision_counts,
        "professional_emit_allowed": emitted_count > 0,
        "professional_emit_allowed_count": emitted_count,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "variant_feature_challenge_is_independent_evidence_vote": False,
        "variant_feature_challenge_can_authorize_emit": False,
        "variant_support_spread_is_independent_support": False,
        "variant_support_spread_is_recurrence_truth": False,
        "variant_support_spread_can_increase_support": False,
        "variant_support_spread_can_authorize_emit": False,
        "partial_identification_rate_bound_projected": any(
            row.get("rate_bound_binding_state") != "NOT_AVAILABLE" for row in contracts
        ),
        "partial_identification_rate_bound_recomputed_downstream": False,
        "partial_identification_rate_bound_can_authorize_emit": False,
        "partial_identification_rate_bound_can_strengthen_claim_ceiling": False,
        "partial_identification_rate_bound_creates_new_evidence": False,
        "late_bound_episode_spread_can_only_resolve_stale_unknown": True,
        "review_required_admission_can_authorize_emit": False,
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
        "variant_feature_challenge_admission_consumed": False,
        "safe_finding_admission_decision_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0, "NOT_EVALUATED": 0},
        "professional_emit_allowed": False,
        "professional_emit_allowed_count": 0,
        "cross_match_generalization_allowed": False,
        "probability_language_allowed_from_raw_rate": False,
        "tactical_success_language_allowed_from_provider_outcome_semantic": False,
        "independent_recurrence_language_allowed_for_dependent_branches": False,
        "variant_feature_challenge_is_independent_evidence_vote": False,
        "variant_feature_challenge_can_authorize_emit": False,
        "variant_support_spread_is_independent_support": False,
        "variant_support_spread_is_recurrence_truth": False,
        "variant_support_spread_can_increase_support": False,
        "variant_support_spread_can_authorize_emit": False,
        "partial_identification_rate_bound_projected": False,
        "partial_identification_rate_bound_recomputed_downstream": False,
        "partial_identification_rate_bound_can_authorize_emit": False,
        "partial_identification_rate_bound_can_strengthen_claim_ceiling": False,
        "partial_identification_rate_bound_creates_new_evidence": False,
        "late_bound_episode_spread_can_only_resolve_stale_unknown": True,
        "review_required_admission_can_authorize_emit": False,
        "analyst_or_llm_text_is_evidence": False,
        "claim_contract_creates_new_evidence": False,
        "review_hits": [],
        "hard_block_hits": [reason],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_scope": ANALYST_OUTPUT_CLAIM_SCOPE,
    }
