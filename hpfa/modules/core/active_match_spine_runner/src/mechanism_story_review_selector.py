from __future__ import annotations

from typing import Any


def _has_visible_difference(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    return value is not None


def _has_process_context(record: dict[str, Any]) -> bool:
    return bool(record.get("process_context_feature_difference_candidates"))


def _has_consequence_difference(record: dict[str, Any]) -> bool:
    return bool(record.get("consequence_feature_difference_candidates"))


def _eligible(record: dict[str, Any]) -> bool:
    return (
        int(record.get("resolved_variant_count") or 0) > 0
        and int(record.get("success_resolved_variant_count") or 0) > 0
        and int(record.get("failure_resolved_variant_count") or 0) > 0
        and int(record.get("right_censored_variant_count") or 0) == 0
    )


def _priority_band(record: dict[str, Any]) -> str:
    if not _eligible(record):
        return "BLOCKED"
    process_context = _has_process_context(record)
    consequence = _has_consequence_difference(record)
    first_context = _has_visible_difference(record, "first_supported_context_difference_layer_candidate")
    first_consequence = _has_visible_difference(record, "first_supported_consequence_difference_layer_candidate")
    if process_context and consequence and first_context and first_consequence:
        return "P0_REVIEW_RICH"
    if consequence and first_consequence:
        return "P1_REVIEWABLE"
    return "P2_SUPPORTING_CONTEXT"


def _diversity_key(record: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    team = ",".join(sorted(str(v) for v in (record.get("team_identity_candidate_ids") or [])))
    period = ",".join(sorted(str(v) for v in (record.get("period_candidates") or [])))
    grammar = tuple(str(v) for v in (record.get("grammar_signature_tokens") or []))
    return team, period, grammar


def build_mechanism_story_review_shortlist(
    feature_delta_payload: dict[str, Any],
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Build an analyst-attention shortlist without promoting evidence or truth.

    Selection is deterministic and diversity-preserving. It does not score confidence,
    infer causality, or authorize professional output. Evidence sufficiency and analyst
    relevance remain separate; explicit analyst-question relevance is currently unresolved.
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
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_is_truth_ranking": False,
            "selection_can_authorize_emit": False,
            "production_release": False,
        }

    band_order = {
        "P0_REVIEW_RICH": 0,
        "P1_REVIEWABLE": 1,
        "P2_SUPPORTING_CONTEXT": 2,
        "BLOCKED": 3,
    }
    decorated: list[tuple[int, str, dict[str, Any]]] = []
    for row in records:
        band = _priority_band(row)
        candidate_id = str(row.get("grammar_stable_variant_feature_delta_id") or "")
        decorated.append((band_order[band], candidate_id, row))
    decorated.sort(key=lambda item: (item[0], item[1]))

    selected: list[dict[str, Any]] = []
    seen_diversity: set[tuple[str, str, tuple[str, ...]]] = set()
    for _, _, row in decorated:
        band = _priority_band(row)
        if band == "BLOCKED":
            continue
        key = _diversity_key(row)
        if key in seen_diversity:
            continue
        seen_diversity.add(key)
        selected.append({
            "source_mechanism_review_ref": row.get("grammar_stable_variant_feature_delta_id"),
            "source_process_variant_family_ref": row.get("source_process_variant_family_ref"),
            "priority_band": band,
            "team_identity_candidate_ids": list(row.get("team_identity_candidate_ids") or []),
            "period_candidates": list(row.get("period_candidates") or []),
            "grammar_signature_tokens": list(row.get("grammar_signature_tokens") or []),
            "resolved_variant_count": int(row.get("resolved_variant_count") or 0),
            "success_resolved_variant_count": int(row.get("success_resolved_variant_count") or 0),
            "failure_resolved_variant_count": int(row.get("failure_resolved_variant_count") or 0),
            "first_supported_context_difference_layer_candidate": row.get(
                "first_supported_context_difference_layer_candidate"
            ),
            "first_supported_consequence_difference_layer_candidate": row.get(
                "first_supported_consequence_difference_layer_candidate"
            ),
            "process_context_difference_visible": _has_process_context(row),
            "consequence_difference_visible": _has_consequence_difference(row),
            "dependency_independence_proven": row.get("dependency_independence_proven") is True,
            "statistical_independence_proven": row.get("statistical_independence_proven") is True,
            "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
            "selection_role": "ANALYST_REVIEW_ATTENTION_ONLY",
            "selection_is_truth_ranking": False,
            "selection_is_causal_ranking": False,
            "selection_can_authorize_emit": False,
        })
        if len(selected) >= limit:
            break

    return {
        "status": "PASS" if selected else "REVIEW_REQUIRED",
        "reason": None if selected else "no_eligible_mechanism_review_candidates",
        "shortlist": selected,
        "shortlist_count": len(selected),
        "source_candidate_count": len(records),
        "diversity_deduplication_applied": True,
        "analyst_relevance_state": "UNRESOLVED_NO_EXPLICIT_ANALYST_QUESTION",
        "selection_is_truth_ranking": False,
        "selection_is_confidence_score": False,
        "selection_can_authorize_emit": False,
        "mechanism_candidate_is_tactical_plan_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
