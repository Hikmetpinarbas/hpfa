from __future__ import annotations

from typing import Any


NUMERIC_BOUND_STATES = {"POINT_IDENTIFIED_OBSERVED_RATE", "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"}


def _has_visible_difference(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    return value is not None


def _has_process_context(record: dict[str, Any]) -> bool:
    return bool(record.get("process_context_feature_difference_candidates"))


def _has_consequence_difference(record: dict[str, Any]) -> bool:
    return bool(record.get("consequence_feature_difference_candidates"))


def _bound_signature(contract: dict[str, Any]) -> tuple[Any, ...]:
    return (
        contract.get("rate_bound_estimand_id"),
        contract.get("rate_bound_denominator_basis"),
        contract.get("rate_bound_state"),
        contract.get("rate_bound_resolved_success_n"),
        contract.get("rate_bound_resolved_failure_n"),
        contract.get("rate_bound_unresolved_eligible_n"),
        contract.get("rate_bound_eligible_total_n"),
        contract.get("rate_bound_lower"),
        contract.get("rate_bound_upper"),
        contract.get("rate_bound_width"),
        contract.get("rate_bound_assumption_set_id"),
    )


def _bound_by_family(analyst_output_claim_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(analyst_output_claim_payload, dict):
        return {}
    if str(analyst_output_claim_payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in analyst_output_claim_payload.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            continue
        if row.get("rate_bound_binding_state") != "SOURCE_BOUND_NUMERIC":
            continue
        if str(row.get("rate_bound_state") or "") not in NUMERIC_BOUND_STATES:
            continue
        if row.get("rate_bound_can_authorize_emit") is not False:
            continue
        if row.get("rate_bound_can_strengthen_claim_ceiling") is not False:
            continue
        for family_ref in row.get("rate_bound_matched_process_variant_family_refs") or []:
            ref = str(family_ref or "").strip()
            if ref:
                grouped.setdefault(ref, []).append(row)

    result: dict[str, dict[str, Any]] = {}
    for family_ref, rows in grouped.items():
        signatures = {_bound_signature(row) for row in rows}
        if len(signatures) == 1:
            result[family_ref] = rows[0]
    return result


def _eligibility_state(record: dict[str, Any], bound_by_family: dict[str, dict[str, Any]]) -> str:
    if not (
        int(record.get("resolved_variant_count") or 0) > 0
        and int(record.get("success_resolved_variant_count") or 0) > 0
        and int(record.get("failure_resolved_variant_count") or 0) > 0
    ):
        return "BLOCKED_INSUFFICIENT_RESOLVED_OUTCOMES"
    if int(record.get("right_censored_variant_count") or 0) == 0:
        return "ELIGIBLE_RESOLVED"
    family_ref = str(record.get("source_process_variant_family_ref") or "").strip()
    if family_ref and family_ref in bound_by_family:
        return "BOUND_AWARE_REVIEW_ONLY"
    return "BLOCKED_CENSORING_UNBOUNDED"


def _priority_band(record: dict[str, Any], bound_by_family: dict[str, dict[str, Any]]) -> str:
    eligibility = _eligibility_state(record, bound_by_family)
    if eligibility.startswith("BLOCKED_"):
        return eligibility
    if eligibility == "BOUND_AWARE_REVIEW_ONLY":
        return "BOUND_AWARE_REVIEW_ONLY"
    process_context = _has_process_context(record)
    consequence = _has_consequence_difference(record)
    first_context = _has_visible_difference(record, "first_supported_context_difference_layer_candidate")
    first_consequence = _has_visible_difference(record, "first_supported_consequence_difference_layer_candidate")
    if process_context and consequence and first_context and first_consequence:
        return "P0_REVIEW_RICH"
    if consequence and first_consequence:
        return "P1_REVIEWABLE"
    return "P2_SUPPORTING_CONTEXT"


def _review_support_state(record: dict[str, Any]) -> str:
    episode_spread = int(record.get("visible_episode_spread_count") or 0)
    occurrence_clusters = int(record.get("occurrence_disjoint_support_cluster_count") or 0)
    divergence_count = int(record.get("supported_branch_divergence_binding_count") or 0)
    success_failure_divergence_count = int(
        record.get("success_failure_supported_branch_divergence_count") or 0
    )
    if episode_spread >= 2 and occurrence_clusters >= 2 and success_failure_divergence_count > 0:
        return "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if episode_spread >= 2 and success_failure_divergence_count > 0:
        return "MULTI_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if episode_spread >= 2 and divergence_count > 0:
        return "MULTI_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST"
    if success_failure_divergence_count > 0:
        return "SINGLE_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE"
    if divergence_count > 0:
        return "SINGLE_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST"
    return "DIVERGENCE_SUPPORT_UNRESOLVED"


def _diversity_key(record: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    team = ",".join(sorted(str(v) for v in (record.get("team_identity_candidate_ids") or [])))
    period = ",".join(sorted(str(v) for v in (record.get("period_candidates") or [])))
    grammar = tuple(str(v) for v in (record.get("grammar_signature_tokens") or []))
    return team, period, grammar


def build_mechanism_story_review_shortlist(
    feature_delta_payload: dict[str, Any],
    *,
    analyst_output_claim_payload: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Build an analyst-attention shortlist without promoting evidence or truth.

    Censoring may remain review-visible only when the same process-family has an
    already-admitted, source-bound numeric identification interval. This selector never
    recomputes bounds, scores confidence, or authorizes professional output.
    """
    if limit < 1:
        limit = 1
    records = [
        row
        for row in (feature_delta_payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(row, dict)
    ]
    if not records:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "no_mechanism_review_candidates",
            "shortlist": [],
            "shortlist_count": 0,
            "source_candidate_count": 0,
            "bounded_review_only_count": 0,
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_is_truth_ranking": False,
            "selection_can_authorize_emit": False,
            "production_release": False,
        }

    bounds = _bound_by_family(analyst_output_claim_payload)
    band_order = {
        "P0_REVIEW_RICH": 0,
        "P1_REVIEWABLE": 1,
        "P2_SUPPORTING_CONTEXT": 2,
        "BOUND_AWARE_REVIEW_ONLY": 3,
        "BLOCKED_CENSORING_UNBOUNDED": 4,
        "BLOCKED_INSUFFICIENT_RESOLVED_OUTCOMES": 5,
    }
    support_order = {
        "MULTI_EPISODE_OCCURRENCE_DISJOINT_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 0,
        "MULTI_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 1,
        "MULTI_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST": 2,
        "SINGLE_EPISODE_SUCCESS_FAILURE_DIVERGENCE_VISIBLE": 3,
        "SINGLE_EPISODE_DIVERGENCE_VISIBLE_NO_SUCCESS_FAILURE_CONTRAST": 4,
        "DIVERGENCE_SUPPORT_UNRESOLVED": 5,
    }
    decorated: list[tuple[int, int, str, dict[str, Any]]] = []
    for row in records:
        band = _priority_band(row, bounds)
        support_state = _review_support_state(row)
        candidate_id = str(row.get("grammar_stable_variant_feature_delta_id") or "")
        decorated.append((band_order[band], support_order[support_state], candidate_id, row))
    decorated.sort(key=lambda item: (item[0], item[1], item[2]))

    selected: list[dict[str, Any]] = []
    seen_diversity: set[tuple[str, str, tuple[str, ...]]] = set()
    for _, _, _, row in decorated:
        eligibility = _eligibility_state(row, bounds)
        band = _priority_band(row, bounds)
        if eligibility.startswith("BLOCKED_"):
            continue
        key = _diversity_key(row)
        if key in seen_diversity:
            continue
        seen_diversity.add(key)
        family_ref = str(row.get("source_process_variant_family_ref") or "").strip()
        bound = bounds.get(family_ref) if eligibility == "BOUND_AWARE_REVIEW_ONLY" else None
        selected.append({
            "source_mechanism_review_ref": row.get("grammar_stable_variant_feature_delta_id"),
            "source_process_variant_family_ref": row.get("source_process_variant_family_ref"),
            "priority_band": band,
            "story_eligibility_state": eligibility,
            "team_identity_candidate_ids": list(row.get("team_identity_candidate_ids") or []),
            "period_candidates": list(row.get("period_candidates") or []),
            "grammar_signature_tokens": list(row.get("grammar_signature_tokens") or []),
            "resolved_variant_count": int(row.get("resolved_variant_count") or 0),
            "success_resolved_variant_count": int(row.get("success_resolved_variant_count") or 0),
            "failure_resolved_variant_count": int(row.get("failure_resolved_variant_count") or 0),
            "right_censored_variant_count": int(row.get("right_censored_variant_count") or 0),
            "rate_bound_state": bound.get("rate_bound_state") if bound else None,
            "rate_bound_lower": bound.get("rate_bound_lower") if bound else None,
            "rate_bound_upper": bound.get("rate_bound_upper") if bound else None,
            "rate_bound_width": bound.get("rate_bound_width") if bound else None,
            "rate_bound_source_analyst_output_contract_ref": (
                bound.get("analyst_output_contract_id") if bound else None
            ),
            "first_supported_context_difference_layer_candidate": row.get(
                "first_supported_context_difference_layer_candidate"
            ),
            "first_supported_consequence_difference_layer_candidate": row.get(
                "first_supported_consequence_difference_layer_candidate"
            ),
            "process_context_difference_visible": _has_process_context(row),
            "consequence_difference_visible": _has_consequence_difference(row),
            "review_support_state": _review_support_state(row),
            "visible_episode_spread_count": int(row.get("visible_episode_spread_count") or 0),
            "success_visible_episode_spread_count": int(
                row.get("success_visible_episode_spread_count") or 0
            ),
            "failure_visible_episode_spread_count": int(
                row.get("failure_visible_episode_spread_count") or 0
            ),
            "occurrence_disjoint_support_cluster_count": int(
                row.get("occurrence_disjoint_support_cluster_count") or 0
            ),
            "supported_branch_divergence_binding_count": int(
                row.get("supported_branch_divergence_binding_count") or 0
            ),
            "success_failure_supported_branch_divergence_count": int(
                row.get("success_failure_supported_branch_divergence_count") or 0
            ),
            "episode_spread_count_is_independent_support_count": False,
            "occurrence_disjoint_cluster_count_is_independent_support_count": False,
            "review_support_state_is_truth_ranking": False,
            "dependency_independence_proven": row.get("dependency_independence_proven") is True,
            "statistical_independence_proven": row.get("statistical_independence_proven") is True,
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_role": "ANALYST_REVIEW_ATTENTION_ONLY",
            "selection_is_truth_ranking": False,
            "selection_is_causal_ranking": False,
            "selection_is_confidence_score": False,
            "selection_can_authorize_emit": False,
            "bound_can_authorize_emit": False,
            "bound_can_strengthen_claim_ceiling": False,
        })
        if len(selected) >= limit:
            break

    return {
        "status": "PASS" if selected else "REVIEW_REQUIRED",
        "reason": None if selected else "no_eligible_mechanism_review_candidates",
        "shortlist": selected,
        "shortlist_count": len(selected),
        "source_candidate_count": len(records),
        "bounded_review_only_count": sum(
            row.get("story_eligibility_state") == "BOUND_AWARE_REVIEW_ONLY" for row in selected
        ),
        "diversity_deduplication_applied": True,
        "review_support_attention_compression_applied": True,
        "review_support_attention_order_is_truth_ranking": False,
        "episode_spread_count_is_independent_support_count": False,
        "occurrence_disjoint_cluster_count_is_independent_support_count": False,
        "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
        "selection_is_truth_ranking": False,
        "selection_is_confidence_score": False,
        "selection_can_authorize_emit": False,
        "bound_recomputed_in_selector": False,
        "bound_width_is_confidence_score": False,
        "mechanism_candidate_is_tactical_plan_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
