from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter
from typing import Any

CLAIM_CEILING = "DEPENDENCY_AWARE_PARTIAL_ORDER_SIMILARITY_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _counter(rows: Any, key: str) -> Counter[str]:
    out: Counter[str] = Counter()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        label = _clean(row.get(key))
        try:
            count = int(row.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if label and count > 0:
            out[label] += count
    return out


def _multiset_jaccard(a: Counter[str], b: Counter[str]) -> float | None:
    keys = set(a) | set(b)
    if not keys:
        return None
    denom = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    if denom <= 0:
        return None
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    return round(num / denom, 6)


def _order_signature(variant: dict[str, Any]) -> Counter[str]:
    out: Counter[str] = Counter()
    for edge in variant.get("edge_relations") or []:
        if isinstance(edge, dict):
            relation = _clean(edge.get("relation"))
            if relation:
                out[relation] += 1
    for node in variant.get("node_records") or []:
        if isinstance(node, dict):
            internal = _clean(node.get("internal_same_time_order"))
            if internal and internal != "NOT_APPLICABLE":
                out[internal] += 1
    return out


def _layer_shape_signature(variant: dict[str, Any]) -> Counter[str]:
    by_layer: Counter[str] = Counter()
    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            continue
        layer = _clean(node.get("time_layer_ref"))
        if layer:
            by_layer[layer] += 1
    out: Counter[str] = Counter()
    for size in by_layer.values():
        out[f"LAYER_SIZE_{size}"] += 1
    return out


def _outcome_signature_equal(a: dict[str, Any], b: dict[str, Any]) -> bool | None:
    ca = _counter(a.get("outcome_signature"), "outcome_candidate")
    cb = _counter(b.get("outcome_signature"), "outcome_candidate")
    if not ca or not cb:
        return None
    return ca == cb


def build_dependency_aware_partial_order_similarity(
    variant_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if variant_payload.get("partial_order_occurrence_variant_status") == "FAIL_CLOSED":
        blocks.append("partial_order_variant_projection_fail_closed")
    if variant_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if variant_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if variant_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if variant_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if variant_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    variants = [
        row for row in (variant_payload.get("partial_order_occurrence_variants") or [])
        if isinstance(row, dict)
    ]
    if len(variants) < 2:
        reviews.append("insufficient_partial_order_variants_for_pairwise_similarity")

    pairs: list[dict[str, Any]] = []
    for left, right in itertools.combinations(variants, 2):
        left_id = _clean(left.get("partial_order_occurrence_variant_id"))
        right_id = _clean(right.get("partial_order_occurrence_variant_id"))
        if not left_id or not right_id:
            blocks.append("partial_order_variant_id_missing")
            continue

        left_team = _clean(left.get("team_identity_candidate_id"))
        right_team = _clean(right.get("team_identity_candidate_id"))
        same_team = bool(left_team and right_team and left_team == right_team)

        left_occ = {_clean(v) for v in (left.get("supporting_action_occurrence_candidate_ids") or []) if _clean(v)}
        right_occ = {_clean(v) for v in (right.get("supporting_action_occurrence_candidate_ids") or []) if _clean(v)}
        shared_occ = sorted(left_occ & right_occ)

        left_dep = {_clean(v) for v in (left.get("dependency_group_refs") or []) if _clean(v)}
        right_dep = {_clean(v) for v in (right.get("dependency_group_refs") or []) if _clean(v)}
        shared_dep = sorted(left_dep & right_dep)
        provenance_distinct = not bool(shared_occ or shared_dep)

        action_similarity = _multiset_jaccard(
            _counter(left.get("action_family_signature"), "action_family_candidate"),
            _counter(right.get("action_family_signature"), "action_family_candidate"),
        )
        order_similarity = _multiset_jaccard(_order_signature(left), _order_signature(right))
        layer_shape_similarity = _multiset_jaccard(
            _layer_shape_signature(left), _layer_shape_signature(right)
        )

        structural_exact_match = (
            action_similarity == 1.0
            and order_similarity == 1.0
            and layer_shape_similarity == 1.0
        )
        outcome_equal = _outcome_signature_equal(left, right)

        if not same_team:
            pair_state = "NOT_APPLICABLE_CROSS_TEAM_MATCH_LOCAL_RECURRENCE"
            recurrence_eligible = False
        elif shared_occ or shared_dep:
            pair_state = "DEPENDENT_SHARED_ORIGIN_VARIANT_PAIR"
            recurrence_eligible = False
        elif structural_exact_match:
            pair_state = "PROVENANCE_DISTINCT_STRUCTURAL_MATCH_CANDIDATE"
            recurrence_eligible = True
        else:
            pair_state = "SAME_TEAM_STRUCTURAL_COMPARISON_ONLY"
            recurrence_eligible = False

        if outcome_equal is True:
            outcome_state = "SAME_OBSERVED_OUTCOME_SIGNATURE"
        elif outcome_equal is False:
            outcome_state = "DIFFERENT_OBSERVED_OUTCOME_SIGNATURE"
        else:
            outcome_state = "OUTCOME_COMPARISON_NOT_ELIGIBLE"

        pair_id = "po_sim_" + _digest(left_id, right_id)[:24]
        pairs.append({
            "partial_order_similarity_pair_id": pair_id,
            "left_variant_ref": left_id,
            "right_variant_ref": right_id,
            "left_team_identity_candidate_id": left_team or None,
            "right_team_identity_candidate_id": right_team or None,
            "same_team_comparison": same_team,
            "left_period_candidate": left.get("period_candidate"),
            "right_period_candidate": right.get("period_candidate"),
            "action_structure_similarity": action_similarity,
            "partial_order_similarity": order_similarity,
            "layer_shape_similarity": layer_shape_similarity,
            "structural_exact_match": structural_exact_match,
            "shared_occurrence_candidate_ids": shared_occ,
            "shared_occurrence_candidate_count": len(shared_occ),
            "shared_dependency_group_refs": shared_dep,
            "shared_dependency_group_count": len(shared_dep),
            "provenance_distinct_for_recurrence_candidate": provenance_distinct,
            "dependency_independent_for_recurrence": False,
            "dependency_independence_proven_for_recurrence": False,
            "statistical_independence_proven": False,
            "recurrence_candidate_is_independent_support": False,
            "pair_state": pair_state,
            "recurrence_candidate_eligible": recurrence_eligible,
            "outcome_contrast_state": outcome_state,
            "outcome_used_in_similarity_decision": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "similarity_is_recurrence_truth": False,
            "similarity_is_tactical_pattern_truth": False,
            "similarity_is_causal_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or variant_payload.get("partial_order_occurrence_variant_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    counts = Counter(_clean(row.get("pair_state")) for row in pairs)
    return {
        "status": status,
        "dependency_aware_partial_order_similarity_pairs": pairs if not blocks else [],
        "dependency_aware_partial_order_similarity_pair_count": len(pairs) if not blocks else 0,
        "pair_state_counts": dict(sorted(counts.items())) if not blocks else {},
        "source_partial_order_occurrence_variant_count": len(variants),
        "recurrence_candidate_eligible_pair_count": sum(
            1 for row in pairs if row.get("recurrence_candidate_eligible")
        ) if not blocks else 0,
        "outcome_used_in_similarity_decision": False,
        "dependency_overlap_blocks_recurrence_candidate_eligibility": True,
        "provenance_distinct_is_not_independence_proof": True,
        "recurrence_candidate_is_independent_support": False,
        "cross_team_pairs_are_match_local_recurrence_not_applicable": True,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "similarity_is_recurrence_truth": False,
        "similarity_is_tactical_pattern_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
