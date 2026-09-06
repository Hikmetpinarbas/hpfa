from __future__ import annotations

import itertools
import math
from collections import Counter
from typing import Any

MODULE_ID = "trace_similarity_primitive_lite_v1"
INPUT_MODULE_ID = "partial_order_trace_variant_lite_v1"
METHOD_VERSION = "TRACE_SIMILARITY_PRIMITIVE_V1.0.0"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "TRACE_SIMILARITY_CANDIDATE_ONLY"
COMPONENTS = ("action", "order", "context", "outcome", "spatial", "timing")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _counter_from_signature(rows: Any, key: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        label = _clean(row.get(key))
        try:
            count = int(row.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if label and count > 0:
            result[label] += count
    return result


def _multiset_jaccard(a: Counter[str], b: Counter[str]) -> float | None:
    keys = set(a) | set(b)
    if not keys:
        return None
    numerator = sum(min(a.get(key, 0), b.get(key, 0)) for key in keys)
    denominator = sum(max(a.get(key, 0), b.get(key, 0)) for key in keys)
    return None if denominator <= 0 else round(numerator / denominator, 6)


def _order_counter(variant: dict[str, Any]) -> tuple[Counter[str], bool]:
    counter: Counter[str] = Counter()
    indeterminate = False
    for edge in variant.get("edge_relations") or []:
        if not isinstance(edge, dict):
            continue
        relation = _clean(edge.get("relation"))
        if relation == "ORDER_INDETERMINATE":
            indeterminate = True
        elif relation:
            counter[relation] += 1
    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            continue
        relation = _clean(node.get("internal_same_time_order"))
        if relation == "SAME_TIME_UNORDERED":
            counter[relation] += 1
    return counter, indeterminate


def _context_similarity(a: dict[str, Any], b: dict[str, Any]) -> tuple[float | None, str, list[str]]:
    context_a = a.get("context_signature") if isinstance(a.get("context_signature"), dict) else {}
    context_b = b.get("context_signature") if isinstance(b.get("context_signature"), dict) else {}
    fields = sorted(
        key
        for key in set(context_a) & set(context_b)
        if _clean(context_a.get(key)) and _clean(context_b.get(key))
    )
    if not fields:
        return None, "NOT_ELIGIBLE_NO_SHARED_ADMITTED_CONTEXT", []
    matches = sum(_clean(context_a.get(key)) == _clean(context_b.get(key)) for key in fields)
    return round(matches / len(fields), 6), "AVAILABLE", fields


def _validate_weights(weights: dict[str, Any] | None) -> tuple[dict[str, float], list[str]]:
    if weights is None:
        return {}, []
    blocks: list[str] = []
    cleaned: dict[str, float] = {}
    for key, value in weights.items():
        if key not in COMPONENTS:
            blocks.append(f"unknown_similarity_weight:{key}")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            blocks.append(f"invalid_similarity_weight:{key}")
            continue
        if not math.isfinite(number):
            blocks.append(f"non_finite_similarity_weight:{key}")
            continue
        if number < 0:
            blocks.append(f"negative_similarity_weight:{key}")
            continue
        cleaned[key] = number
    if weights and not cleaned:
        blocks.append("no_valid_similarity_weights")
    return cleaned, sorted(set(blocks))


def _composite(component_values: dict[str, float | None], weights: dict[str, float]) -> tuple[float | None, dict[str, float], str]:
    if not weights:
        return None, {}, "NOT_COMPUTED_EXPLICIT_WEIGHTS_REQUIRED"
    eligible = {
        key: weight
        for key, weight in weights.items()
        if weight > 0 and component_values.get(key) is not None
    }
    total = sum(eligible.values())
    if total <= 0:
        return None, {}, "NOT_COMPUTED_NO_WEIGHTED_ELIGIBLE_COMPONENT"
    normalized_raw = {key: weight / total for key, weight in sorted(eligible.items())}
    value = sum((component_values[key] or 0.0) * normalized_raw[key] for key in normalized_raw)
    normalized_reported = {key: round(weight, 6) for key, weight in normalized_raw.items()}
    return round(value, 6), normalized_reported, "AVAILABLE_EXPLICIT_WEIGHTS"


def build_trace_similarity_primitive(
    variant_payload: dict[str, Any],
    *,
    weights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if variant_payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("partial_order_variant_module_id_mismatch")
    status = _clean(variant_payload.get("status")).upper()
    if status == "FAIL_CLOSED" or variant_payload.get("hard_block_hits"):
        blocks.append("partial_order_variant_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append("partial_order_variant_upstream_review_required")
    if variant_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if variant_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("true_action_count_claimed")
    if variant_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if variant_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_policy_breached")
    if variant_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_policy_breached")

    explicit_weights, weight_blocks = _validate_weights(weights)
    blocks.extend(weight_blocks)
    variants = [row for row in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(row, dict)]
    if len(variants) < 2:
        reviews.append("insufficient_variant_pairs_for_similarity")

    pairs: list[dict[str, Any]] = []
    if not blocks:
        for a, b in itertools.combinations(sorted(variants, key=lambda row: _clean(row.get("trace_variant_id"))), 2):
            a_ref = _clean(a.get("trace_variant_id"))
            b_ref = _clean(b.get("trace_variant_id"))
            if not a_ref or not b_ref:
                blocks.append("trace_variant_id_missing")
                continue

            action = _multiset_jaccard(
                _counter_from_signature(a.get("action_family_signature"), "action_family_candidate"),
                _counter_from_signature(b.get("action_family_signature"), "action_family_candidate"),
            )
            outcome = _multiset_jaccard(
                _counter_from_signature(a.get("outcome_signature"), "outcome_candidate"),
                _counter_from_signature(b.get("outcome_signature"), "outcome_candidate"),
            )
            order_a, indeterminate_a = _order_counter(a)
            order_b, indeterminate_b = _order_counter(b)
            if indeterminate_a or indeterminate_b:
                order = None
                order_state = "ORDER_COMPONENT_INDETERMINATE_NOT_INVENTED"
            else:
                order = _multiset_jaccard(order_a, order_b)
                order_state = "AVAILABLE" if order is not None else "NOT_ELIGIBLE_NO_ORDER_RELATIONS"
            context, context_state, context_fields = _context_similarity(a, b)

            component_values: dict[str, float | None] = {
                "action": action,
                "order": order,
                "context": context,
                "outcome": outcome,
                "spatial": None,
                "timing": None,
            }
            composite, normalized_weights, composite_state = _composite(component_values, explicit_weights)
            component_states = {
                "action": "AVAILABLE" if action is not None else "NOT_ELIGIBLE_EMPTY_SIGNATURE",
                "order": order_state,
                "context": context_state,
                "outcome": "AVAILABLE" if outcome is not None else "NOT_ELIGIBLE_EMPTY_SIGNATURE",
                "spatial": "NOT_ELIGIBLE_V1_NO_ADMITTED_COMPARABLE_SPATIAL_COMPONENT",
                "timing": "NOT_ELIGIBLE_V1_NO_ADMITTED_COMPARABLE_TIMING_COMPONENT",
            }
            pairs.append({
                "trace_a_ref": a_ref,
                "trace_b_ref": b_ref,
                "action_similarity": action,
                "order_similarity": order,
                "context_similarity": context,
                "outcome_similarity": outcome,
                "spatial_similarity_if_eligible": None,
                "timing_similarity_if_eligible": None,
                "composite_similarity": composite,
                "weights": normalized_weights,
                "requested_weights": explicit_weights,
                "composite_state": composite_state,
                "similarity_vector": component_values,
                "component_states": component_states,
                "context_fields_compared": context_fields,
                "method_version": METHOD_VERSION,
                "method_is_symmetric": True,
                "missing_component_policy": "MISSING_OR_INELIGIBLE_IS_NULL_NEVER_ZERO",
                "weight_sensitivity_available": True,
                "weights_are_universal_football_truth": False,
                "unknown_order_is_total_order": False,
                "tracking_feature_used": False,
                "video_feature_used": False,
                "similarity_is_tactical_identity_truth": False,
                "similarity_is_causal_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    if blocks:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "TRACE_SIMILARITY_INPUT_REJECTED",
            "trace_similarity_pairs": [],
            "trace_similarity_pair_count": 0,
            "hard_block_hits": sorted(set(blocks)),
            "review_hits": sorted(set(reviews)),
            "method_version": METHOD_VERSION,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "TRACE_SIMILARITY_PAIRS_BUILT",
        "trace_similarity_pairs": pairs,
        "trace_similarity_pair_count": len(pairs),
        "source_trace_variant_count": len(variants),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "method_version": METHOD_VERSION,
        "method_is_symmetric": True,
        "missing_component_policy": "MISSING_OR_INELIGIBLE_IS_NULL_NEVER_ZERO",
        "composite_requires_explicit_weights": True,
        "weight_sensitivity_available": True,
        "tracking_feature_used": False,
        "video_feature_used": False,
        "similarity_is_tactical_identity_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
