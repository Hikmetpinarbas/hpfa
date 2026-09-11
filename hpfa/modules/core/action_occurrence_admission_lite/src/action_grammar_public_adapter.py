from __future__ import annotations

from typing import Any

from hpfa.modules.core.action_occurrence_admission_lite.src.intra_actor_action_grammar import (
    build_intra_actor_action_grammar_candidates,
)


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def bind_intra_actor_action_grammar(
    occurrence_payload: dict[str, Any],
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    """Extend the current occurrence product with same-actor semantic grammar candidates.

    This adapter is deliberately downstream-safe: the existing interaction candidates are preserved,
    new candidates carry an explicit SINGLE_ACTOR_ACTION topology, and any semantic contradiction or
    failed provider binding stays review-required instead of being silently reported as PASS.
    """
    if occurrence_payload.get("status") == "FAIL_CLOSED":
        return occurrence_payload

    grammar = build_intra_actor_action_grammar_candidates(
        action_payload,
        evidence_payload,
        registry,
    )
    existing = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    grammar_candidates = [
        row
        for row in grammar.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    combined = existing + grammar_candidates

    occurrence_payload["action_occurrence_candidates"] = combined
    occurrence_payload["action_occurrence_candidate_count"] = len(combined)
    occurrence_payload["interaction_occurrence_candidate_count"] = len(existing)
    occurrence_payload["intra_actor_action_grammar_candidate_count"] = len(grammar_candidates)
    occurrence_payload["intra_actor_action_grammar_candidates"] = grammar_candidates
    occurrence_payload["intra_actor_action_grammar_rejected_provider_semantics_binding_count"] = int(
        grammar.get("rejected_provider_semantics_binding_count") or 0
    )
    occurrence_payload["intra_actor_action_grammar_contradictory_semantics_count"] = int(
        grammar.get("contradictory_semantics_count") or 0
    )
    occurrence_payload["same_timestamp_alone_is_merge_authority"] = False
    occurrence_payload["cross_bundle_action_grammar_merge_allowed"] = False

    class_counts: dict[str, int] = {}
    interaction_counts: dict[str, int] = {}
    for candidate in combined:
        admission_class = _clean(candidate.get("admission_class"))
        interaction = _clean(candidate.get("interaction_type"))
        if admission_class:
            class_counts[admission_class] = class_counts.get(admission_class, 0) + 1
        if interaction:
            interaction_counts[interaction] = interaction_counts.get(interaction, 0) + 1
    occurrence_payload["admission_class_counts"] = dict(sorted(class_counts.items()))
    occurrence_payload["interaction_type_counts"] = dict(sorted(interaction_counts.items()))

    existing_rejected_provider = int(
        occurrence_payload.get("candidate_rejected_provider_semantics_binding_count") or 0
    )
    grammar_rejected_provider = int(
        grammar.get("rejected_provider_semantics_binding_count") or 0
    )
    total_rejected_provider = existing_rejected_provider + grammar_rejected_provider
    occurrence_payload["candidate_rejected_provider_semantics_binding_count"] = total_rejected_provider

    reviews = list(occurrence_payload.get("review_hits") or [])
    reviews.extend(grammar.get("review_hits") or [])
    if total_rejected_provider:
        reviews.append("candidate_rejected_provider_semantics_binding")
        occurrence_payload["provider_semantics_binding_status"] = "REVIEW_REQUIRED"
    elif combined:
        occurrence_payload["provider_semantics_binding_status"] = "PASS"
    elif occurrence_payload.get("provider_semantics_binding_status") == "FAIL_CLOSED":
        pass
    else:
        occurrence_payload["provider_semantics_binding_status"] = "PASS"

    occurrence_payload["review_hits"] = sorted(set(_clean(value) for value in reviews if _clean(value)))
    if grammar.get("review_hits") and occurrence_payload.get("status") != "FAIL_CLOSED":
        occurrence_payload["status"] = "REVIEW_REQUIRED"
        occurrence_payload["module_status"] = "REVIEW_REQUIRED"

    occurrence_payload["canonical_event_count"] = "UNKNOWN"
    occurrence_payload["true_action_count"] = "UNKNOWN"
    occurrence_payload["production_release"] = False
    return occurrence_payload
