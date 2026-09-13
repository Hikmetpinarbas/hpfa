from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "DEPENDENCY_AWARE_PARTIAL_ORDER_SIMILARITY_CANDIDATE_ONLY"
PAIR_MATERIALIZATION_MODE = "ELIGIBILITY_GROUP_REPRESENTATIVE_PAIRS"


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


def _signature_tuple(counter: Counter[str]) -> tuple[tuple[str, int], ...] | None:
    if not counter:
        return None
    return tuple(sorted((key, int(value)) for key, value in counter.items() if value > 0)) or None


def _structural_signature(variant: dict[str, Any]) -> tuple[Any, ...] | None:
    """Cheap coarse prefilter only; not proof of topology equivalence."""
    action = _signature_tuple(_counter(variant.get("action_family_signature"), "action_family_candidate"))
    order = _signature_tuple(_order_signature(variant))
    layer = _signature_tuple(_layer_shape_signature(variant))
    if action is None or order is None or layer is None:
        return None
    return (action, order, layer)


def _layer_graph(
    variant: dict[str, Any],
) -> tuple[
    dict[str, tuple[tuple[tuple[str, ...], str], ...]],
    dict[tuple[str, str], tuple[tuple[str, int], ...]],
] | None:
    """Build a relation-preserving layer graph without inventing same-time order."""
    layer_nodes: dict[str, list[tuple[tuple[str, ...], str]]] = defaultdict(list)
    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            return None
        layer = _clean(node.get("time_layer_ref"))
        if not layer:
            return None
        actions = tuple(
            sorted(
                {
                    _clean(value)
                    for value in (node.get("action_family_candidates") or [])
                    if _clean(value)
                }
            )
        )
        if not actions:
            return None
        internal = _clean(node.get("internal_same_time_order")) or "NOT_APPLICABLE"
        if internal not in {"NOT_APPLICABLE", "SAME_TIME_UNORDERED"}:
            return None
        layer_nodes[layer].append((actions, internal))

    if not layer_nodes:
        return None

    labels = {
        layer: tuple(sorted(records))
        for layer, records in layer_nodes.items()
    }
    edge_counters: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for edge in variant.get("edge_relations") or []:
        if not isinstance(edge, dict):
            return None
        source = _clean(edge.get("from_layer_ref"))
        target = _clean(edge.get("to_layer_ref"))
        relation = _clean(edge.get("relation"))
        if not source or not target or not relation:
            return None
        if source not in labels or target not in labels:
            return None
        edge_counters[(source, target)][relation] += 1

    edges = {
        pair: tuple(sorted((relation, int(count)) for relation, count in counter.items()))
        for pair, counter in edge_counters.items()
    }
    return labels, edges


def _layer_invariant(
    layer: str,
    labels: dict[str, tuple[tuple[tuple[str, ...], str], ...]],
    edges: dict[tuple[str, str], tuple[tuple[str, int], ...]],
) -> tuple[Any, ...]:
    incoming: Counter[str] = Counter()
    outgoing: Counter[str] = Counter()
    for (source, target), relation_counts in edges.items():
        if target == layer:
            for relation, count in relation_counts:
                incoming[relation] += count
        if source == layer:
            for relation, count in relation_counts:
                outgoing[relation] += count
    return (
        labels[layer],
        tuple(sorted(incoming.items())),
        tuple(sorted(outgoing.items())),
    )


def _topology_exact_match(left: dict[str, Any], right: dict[str, Any]) -> bool | None:
    """Exact labeled-layer graph isomorphism; layer refs themselves carry no identity."""
    left_graph = _layer_graph(left)
    right_graph = _layer_graph(right)
    if left_graph is None or right_graph is None:
        return None

    left_labels, left_edges = left_graph
    right_labels, right_edges = right_graph
    if len(left_labels) != len(right_labels):
        return False
    if sum(len(value) for value in left_labels.values()) != sum(len(value) for value in right_labels.values()):
        return False
    if Counter(left_edges.values()) != Counter(right_edges.values()):
        return False

    left_invariants = {layer: _layer_invariant(layer, left_labels, left_edges) for layer in left_labels}
    right_invariants = {layer: _layer_invariant(layer, right_labels, right_edges) for layer in right_labels}
    if Counter(left_invariants.values()) != Counter(right_invariants.values()):
        return False

    candidates: dict[str, list[str]] = {
        layer: sorted(
            other
            for other, invariant in right_invariants.items()
            if invariant == left_invariants[layer]
        )
        for layer in left_labels
    }
    if any(not values for values in candidates.values()):
        return False

    ordered_left = sorted(left_labels, key=lambda layer: (len(candidates[layer]), repr(left_invariants[layer]), layer))
    mapping: dict[str, str] = {}
    used_right: set[str] = set()

    def compatible(left_layer: str, right_layer: str) -> bool:
        if left_edges.get((left_layer, left_layer), ()) != right_edges.get((right_layer, right_layer), ()):
            return False
        for assigned_left, assigned_right in mapping.items():
            if left_edges.get((left_layer, assigned_left), ()) != right_edges.get((right_layer, assigned_right), ()):
                return False
            if left_edges.get((assigned_left, left_layer), ()) != right_edges.get((assigned_right, right_layer), ()):
                return False
        return True

    def search(position: int) -> bool:
        if position >= len(ordered_left):
            return True
        left_layer = ordered_left[position]
        for right_layer in candidates[left_layer]:
            if right_layer in used_right:
                continue
            if not compatible(left_layer, right_layer):
                continue
            mapping[left_layer] = right_layer
            used_right.add(right_layer)
            if search(position + 1):
                return True
            used_right.remove(right_layer)
            mapping.pop(left_layer, None)
        return False

    return search(0)


def _outcome_materialization_signature(variant: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    return _signature_tuple(_counter(variant.get("outcome_signature"), "outcome_candidate")) or (("UNRESOLVED", 0),)


def _pair_key(left_index: int, right_index: int) -> tuple[int, int]:
    return (left_index, right_index) if left_index < right_index else (right_index, left_index)


def _add_star_pairs(indices: list[int], out: set[tuple[int, int]]) -> None:
    ordered = sorted(set(indices))
    if len(ordered) < 2:
        return
    anchor = ordered[0]
    for index in ordered[1:]:
        out.add(_pair_key(anchor, index))


def _candidate_pair_indices(variants: list[dict[str, Any]]) -> tuple[set[tuple[int, int]], list[dict[str, Any]], dict[str, int]]:
    """Build the legacy-bounded pair surface, then only remove topology-invalid pairs.

    Same-team, same-period, coarse-signature equality remains a cheap prefilter. The exact
    legacy representative pair set is materialized first. Relation-preserving topology then
    acts only as a downward filter: it may remove or preserve a pair, but can never create a
    new pair. Outcome signatures still select representatives only after coarse admission and
    never decide comparison eligibility.
    """
    groups: dict[tuple[str, str, tuple[Any, ...]], list[int]] = defaultdict(list)
    missing_team = 0
    missing_period = 0
    structural_unresolved = 0

    for index, variant in enumerate(variants):
        team = _clean(variant.get("team_identity_candidate_id"))
        period = _clean(variant.get("period_candidate"))
        signature = _structural_signature(variant)
        if not team:
            missing_team += 1
            continue
        if not period:
            missing_period += 1
            continue
        if signature is None:
            structural_unresolved += 1
            continue
        groups[(team, period, signature)].append(index)

    admitted_pair_indices: set[tuple[int, int]] = set()
    comparison_groups: list[dict[str, Any]] = []
    topology_mismatch_pair_pruned_count = 0
    topology_unresolved_pair_count = 0
    coarse_signature_topology_split_group_count = 0

    for (team, period, signature), indices in sorted(
        groups.items(),
        key=lambda item: (item[0][0], item[0][1], repr(item[0][2])),
    ):
        ordered = sorted(indices, key=lambda idx: _clean(variants[idx].get("partial_order_occurrence_variant_id")))
        if len(ordered) < 2:
            continue

        coarse_pair_indices: set[tuple[int, int]] = set()

        _add_star_pairs(ordered, coarse_pair_indices)

        by_outcome: dict[tuple[tuple[str, int], ...], list[int]] = defaultdict(list)
        for index in ordered:
            by_outcome[_outcome_materialization_signature(variants[index])].append(index)
        outcome_representatives: list[int] = []
        for outcome_indices in by_outcome.values():
            _add_star_pairs(outcome_indices, coarse_pair_indices)
            outcome_representatives.append(sorted(outcome_indices)[0])
        for left, right in itertools.combinations(sorted(outcome_representatives), 2):
            coarse_pair_indices.add(_pair_key(left, right))

        occurrence_members: dict[str, list[int]] = defaultdict(list)
        dependency_members: dict[str, list[int]] = defaultdict(list)
        for index in ordered:
            variant = variants[index]
            for value in variant.get("supporting_action_occurrence_candidate_ids") or []:
                cleaned = _clean(value)
                if cleaned:
                    occurrence_members[cleaned].append(index)
            for value in variant.get("dependency_group_refs") or []:
                cleaned = _clean(value)
                if cleaned:
                    dependency_members[cleaned].append(index)
        for member_indices in occurrence_members.values():
            _add_star_pairs(member_indices, coarse_pair_indices)
        for member_indices in dependency_members.values():
            _add_star_pairs(member_indices, coarse_pair_indices)

        group_topology_mismatch = False
        group_topology_unresolved = False
        for left_index, right_index in sorted(coarse_pair_indices):
            topology_match = _topology_exact_match(
                variants[left_index],
                variants[right_index],
            )
            if topology_match is True:
                admitted_pair_indices.add(_pair_key(left_index, right_index))
            elif topology_match is False:
                topology_mismatch_pair_pruned_count += 1
                group_topology_mismatch = True
            else:
                topology_unresolved_pair_count += 1
                group_topology_unresolved = True

        if group_topology_mismatch:
            coarse_signature_topology_split_group_count += 1

        member_refs = [
            _clean(variants[index].get("partial_order_occurrence_variant_id"))
            for index in ordered
        ]
        group_id = "po_group_" + _digest(team, period, signature)[:24]
        comparison_groups.append({
            "comparison_group_id": group_id,
            "team_identity_candidate_id": team,
            "period_candidate": period,
            "member_variant_refs": member_refs,
            "member_variant_count": len(ordered),
            "coarse_partial_order_signature_match_required": True,
            "coarse_signature_is_exact_equivalence_proof": False,
            "relation_preserving_topology_filter_applied": True,
            "topology_filter_can_create_new_pair": False,
            "topology_filter_only_removes_or_preserves_coarse_prefilter_pairs": True,
            "structural_exact_equivalence_proven_for_all_materialized_pairs": (
                not group_topology_unresolved
            ),
            "coarse_signature_group_contains_topology_mismatch": group_topology_mismatch,
            "outcome_used_in_comparison_admission": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "comparison_group_is_process_identity_truth": False,
            "comparison_group_is_tactical_pattern_truth": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    diagnostics = {
        "missing_team_variant_count": missing_team,
        "missing_period_variant_count": missing_period,
        "structural_signature_unresolved_variant_count": structural_unresolved,
        "topology_unresolved_pair_count": topology_unresolved_pair_count,
        "topology_mismatch_pair_pruned_count": topology_mismatch_pair_pruned_count,
        "coarse_signature_topology_split_group_count": coarse_signature_topology_split_group_count,
        "admitted_structural_comparison_group_count": len(comparison_groups),
    }
    return admitted_pair_indices, comparison_groups, diagnostics


def _comparison_eligibility(
    *,
    same_team: bool,
    left_period: str,
    right_period: str,
    structural_exact_match: bool,
    shared_origin: bool,
) -> tuple[str, bool, bool, bool]:
    if not same_team:
        return "NOT_COMPARABLE_CROSS_TEAM_MATCH_LOCAL", False, False, False
    if not left_period or not right_period:
        return "INDETERMINATE_MISSING_PERIOD_CONTEXT", False, False, True
    if left_period != right_period:
        return "PARTIALLY_COMPARABLE_REVIEW_REQUIRED_CROSS_PERIOD", False, False, True
    if shared_origin and structural_exact_match:
        return "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST", True, True, False
    if shared_origin:
        return "PARTIALLY_COMPARABLE_REVIEW_REQUIRED_SHARED_ORIGIN_STRUCTURE_MISMATCH", False, False, True
    if structural_exact_match:
        return "COMPARABLE_FOR_MATCH_LOCAL_RECURRENCE_CANDIDATE_INDEPENDENCE_UNPROVEN", True, True, False
    return "PARTIALLY_COMPARABLE_REVIEW_REQUIRED_STRUCTURE_MISMATCH", False, False, True


def _build_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    left_id = _clean(left.get("partial_order_occurrence_variant_id"))
    right_id = _clean(right.get("partial_order_occurrence_variant_id"))
    if not left_id or not right_id:
        return None

    left_team = _clean(left.get("team_identity_candidate_id"))
    right_team = _clean(right.get("team_identity_candidate_id"))
    same_team = bool(left_team and right_team and left_team == right_team)
    left_period = _clean(left.get("period_candidate"))
    right_period = _clean(right.get("period_candidate"))
    same_period = bool(left_period and right_period and left_period == right_period)

    left_occ = {_clean(v) for v in (left.get("supporting_action_occurrence_candidate_ids") or []) if _clean(v)}
    right_occ = {_clean(v) for v in (right.get("supporting_action_occurrence_candidate_ids") or []) if _clean(v)}
    shared_occ = sorted(left_occ & right_occ)
    left_dep = {_clean(v) for v in (left.get("dependency_group_refs") or []) if _clean(v)}
    right_dep = {_clean(v) for v in (right.get("dependency_group_refs") or []) if _clean(v)}
    shared_dep = sorted(left_dep & right_dep)
    shared_origin = bool(shared_occ or shared_dep)
    provenance_distinct = not shared_origin

    action_similarity = _multiset_jaccard(
        _counter(left.get("action_family_signature"), "action_family_candidate"),
        _counter(right.get("action_family_signature"), "action_family_candidate"),
    )
    order_similarity = _multiset_jaccard(_order_signature(left), _order_signature(right))
    layer_shape_similarity = _multiset_jaccard(_layer_shape_signature(left), _layer_shape_signature(right))
    coarse_signature_match = (
        action_similarity == 1.0
        and order_similarity == 1.0
        and layer_shape_similarity == 1.0
    )
    topology_match = _topology_exact_match(left, right) if coarse_signature_match else False
    structural_exact_match = topology_match is True
    outcome_equal = _outcome_signature_equal(left, right)

    comparison_state, comparison_eligible, outcome_contrast_allowed, comparison_requires_review = (
        _comparison_eligibility(
            same_team=same_team,
            left_period=left_period,
            right_period=right_period,
            structural_exact_match=structural_exact_match,
            shared_origin=shared_origin,
        )
    )

    if not same_team:
        pair_state = "NOT_APPLICABLE_CROSS_TEAM_MATCH_LOCAL_RECURRENCE"
        recurrence_eligible = False
    elif not left_period or not right_period:
        pair_state = "SAME_TEAM_PERIOD_CONTEXT_INDETERMINATE"
        recurrence_eligible = False
    elif not same_period:
        pair_state = "SAME_TEAM_CROSS_PERIOD_COMPARISON_REVIEW_REQUIRED"
        recurrence_eligible = False
    elif shared_origin:
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
    return {
        "partial_order_similarity_pair_id": pair_id,
        "left_variant_ref": left_id,
        "right_variant_ref": right_id,
        "left_team_identity_candidate_id": left_team or None,
        "right_team_identity_candidate_id": right_team or None,
        "same_team_comparison": same_team,
        "left_period_candidate": left.get("period_candidate"),
        "right_period_candidate": right.get("period_candidate"),
        "same_period_comparison": same_period,
        "action_structure_similarity": action_similarity,
        "partial_order_similarity": order_similarity,
        "layer_shape_similarity": layer_shape_similarity,
        "coarse_partial_order_signature_match": coarse_signature_match,
        "relation_preserving_topology_match": topology_match,
        "structural_exact_equivalence_proven": structural_exact_match,
        "structural_exact_match": structural_exact_match,
        "coarse_signature_is_exact_equivalence_proof": False,
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
        "comparison_eligibility_state": comparison_state,
        "comparison_eligible": comparison_eligible,
        "comparison_outcome_contrast_allowed": outcome_contrast_allowed,
        "comparison_requires_review": comparison_requires_review,
        "comparison_is_process_identity_truth": False,
        "comparison_is_route_family_truth": False,
        "comparison_is_same_tactical_situation_truth": False,
        "provider_label_equality_is_comparability_proof": False,
        "same_action_family_is_sufficient_for_comparability": False,
        "missing_spatial_context_is_counterevidence": False,
        "outcome_contrast_state": outcome_state,
        "outcome_used_in_similarity_decision": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "similarity_is_recurrence_truth": False,
        "similarity_is_tactical_pattern_truth": False,
        "similarity_is_causal_truth": False,
        "claim_ceiling": CLAIM_CEILING,
    }


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

    all_pair_count = len(variants) * max(len(variants) - 1, 0) // 2
    pair_indices, comparison_groups, diagnostics = _candidate_pair_indices(variants)
    if diagnostics["missing_period_variant_count"]:
        reviews.append("variant_period_context_missing_before_comparison_admission")
    if diagnostics["topology_unresolved_pair_count"]:
        reviews.append("variant_topology_unresolved_before_comparison_admission")

    pairs: list[dict[str, Any]] = []
    if not blocks:
        for left_index, right_index in sorted(pair_indices):
            pair = _build_pair(variants[left_index], variants[right_index])
            if pair is None:
                blocks.append("partial_order_variant_id_missing")
                break
            if (
                pair.get("comparison_eligible") is not True
                or pair.get("structural_exact_match") is not True
                or pair.get("relation_preserving_topology_match") is not True
            ):
                blocks.append("comparison_prefilter_contract_breached")
                break
            pairs.append(pair)

    if blocks:
        status = "FAIL_CLOSED"
        pairs = []
        comparison_groups = []
    elif reviews or variant_payload.get("partial_order_occurrence_variant_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    counts = Counter(_clean(row.get("pair_state")) for row in pairs)
    comparison_counts = Counter(_clean(row.get("comparison_eligibility_state")) for row in pairs)
    materialized_pair_count = len(pairs)
    return {
        "status": status,
        "dependency_aware_partial_order_similarity_pairs": pairs,
        "dependency_aware_partial_order_similarity_pair_count": materialized_pair_count,
        "dependency_aware_partial_order_similarity_groups": comparison_groups,
        "dependency_aware_partial_order_similarity_group_count": len(comparison_groups),
        "pair_state_counts": dict(sorted(counts.items())),
        "comparison_eligibility_state_counts": dict(sorted(comparison_counts.items())),
        "comparison_eligible_pair_count": sum(1 for row in pairs if row.get("comparison_eligible")),
        "source_partial_order_occurrence_variant_count": len(variants),
        "source_all_possible_pair_count": all_pair_count,
        "comparison_prefilter_materialized_pair_count": materialized_pair_count,
        "comparison_prefilter_pruned_pair_count": max(all_pair_count - materialized_pair_count, 0),
        "pair_materialization_mode": PAIR_MATERIALIZATION_MODE,
        "comparison_admission_precedes_pair_materialization": True,
        "coarse_signature_is_only_prefilter": True,
        "structural_exact_match_requires_relation_preserving_topology": True,
        "cross_team_pairs_materialized": False,
        "cross_period_pairs_materialized": False,
        "structural_mismatch_pairs_materialized": False,
        "topology_mismatch_pairs_materialized": False,
        "topology_filter_can_create_new_pair": False,
        "topology_filter_only_removes_or_preserves_coarse_prefilter_pairs": True,
        **diagnostics,
        "recurrence_candidate_eligible_pair_count": sum(
            1 for row in pairs if row.get("recurrence_candidate_eligible")
        ),
        "outcome_used_in_similarity_decision": False,
        "outcome_used_only_for_representative_materialization_after_structural_admission": True,
        "dependency_overlap_blocks_recurrence_candidate_eligibility": True,
        "provenance_distinct_is_not_independence_proof": True,
        "recurrence_candidate_is_independent_support": False,
        "cross_team_pairs_are_match_local_recurrence_not_applicable": True,
        "same_action_family_is_sufficient_for_comparability": False,
        "provider_label_equality_is_comparability_proof": False,
        "comparison_is_process_identity_truth": False,
        "comparison_is_same_tactical_situation_truth": False,
        "missing_spatial_context_is_counterevidence": False,
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
