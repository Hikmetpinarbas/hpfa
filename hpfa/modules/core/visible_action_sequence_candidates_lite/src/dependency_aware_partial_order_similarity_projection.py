from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "DEPENDENCY_AWARE_PARTIAL_ORDER_SIMILARITY_CANDIDATE_ONLY"
COMPARABLE_SET_CLAIM_CEILING = "QUESTION_CONDITIONED_OUTCOME_BLIND_PROCESS_COMPARABLE_SET_CANDIDATE_ONLY"
PAIR_MATERIALIZATION_MODE = "ELIGIBILITY_GROUP_REPRESENTATIVE_PAIRS"
DIMENSION_REGISTRY_VERSION = "comparison_dimension_registry_v1"
DIMENSION_REGISTRY_V1 = {
    "team": {"allowed_roles": {"EXACT", "TEST"}, "forbidden": False},
    "period": {"allowed_roles": {"EXACT", "TEST"}, "forbidden": False},
    "partial_order_structure": {"allowed_roles": {"EXACT"}, "forbidden": False},
    "dependency_root": {"allowed_roles": {"DEPENDENCY_GATE"}, "forbidden": False},
    "outcome_signature": {"allowed_roles": {"FORBIDDEN"}, "forbidden": True},
    "downstream_visible_outcome": {"allowed_roles": {"FORBIDDEN"}, "forbidden": True},
    "terminal_consequence": {"allowed_roles": {"FORBIDDEN"}, "forbidden": True},
}
DEFAULT_COMPARISON_QUESTION_CONTRACT = {
    "comparison_question_id": "match_local_structural_recurrence_v1",
    "construct_id": "MATCH_LOCAL_STRUCTURAL_RECURRENCE_CANDIDATE",
    "observation_unit": "PARTIAL_ORDER_OCCURRENCE_VARIANT",
    "dimension_registry_version": DIMENSION_REGISTRY_VERSION,
    "question_profile_version": "1.0.0",
    "football_question": "Which same-team, same-period partial-order variants are structurally comparable before visible outcome is read?",
    "analysis_scale": "PARTIAL_ORDER_OCCURRENCE_VARIANT",
    "candidate_universe": "CURRENT_MATCH_PARTIAL_ORDER_OCCURRENCE_VARIANTS",
    "anchor_process_family": "STRUCTURAL_PARTIAL_ORDER_FAMILY_CANDIDATE",
    "comparison_target": "MATCH_LOCAL_VISIBLE_VARIANT_CONTRAST",
    "required_exact_dimensions": ["team", "period", "partial_order_structure"],
    "required_coarsened_dimensions": [],
    "allowed_test_dimensions": [],
    "optional_similarity_dimensions": [],
    "forbidden_leakage_dimensions": ["outcome_signature", "downstream_visible_outcome", "terminal_consequence"],
    "required_observation_capabilities": ["TEAM_IDENTITY", "PERIOD_CONTEXT", "PARTIAL_ORDER_STRUCTURE"],
    "optional_observation_capabilities": [],
    "consequence_horizon": "ATTACH_ONLY_AFTER_COMPARABLE_SET_FREEZE",
    "minimum_support_rule": "AT_LEAST_TWO_ELIGIBLE_CASES",
    "minimum_spread_rule": "DESCRIBE_SPREAD_DO_NOT_INFER_INDEPENDENCE",
    "claim_ceiling": COMPARABLE_SET_CLAIM_CEILING,
}


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
        if isinstance(node, dict):
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
    labels = {layer: tuple(sorted(records)) for layer, records in layer_nodes.items()}
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
    return labels[layer], tuple(sorted(incoming.items())), tuple(sorted(outgoing.items()))


def _topology_exact_match(left: dict[str, Any], right: dict[str, Any]) -> bool | None:
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
    candidates = {
        layer: sorted(
            other
            for other, invariant in right_invariants.items()
            if invariant == left_invariants[layer]
        )
        for layer in left_labels
    }
    if any(not values for values in candidates.values()):
        return False
    ordered_left = sorted(
        left_labels,
        key=lambda layer: (len(candidates[layer]), repr(left_invariants[layer]), layer),
    )
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


def _dimension_set(contract: dict[str, Any], key: str) -> set[str]:
    aliases = {
        "team_identity_candidate_id": "team",
        "period_candidate": "period",
        "structural_topology": "partial_order_structure",
    }
    return {
        aliases.get(_clean(value), _clean(value))
        for value in (contract.get(key) or [])
        if _clean(value)
    }


def _comparison_contract(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    supplied = payload.get("process_comparison_question_contract")
    if supplied is None:
        contract = json.loads(json.dumps(DEFAULT_COMPARISON_QUESTION_CONTRACT))
    elif not isinstance(supplied, dict):
        return {}, ["comparison_question_contract_not_object"], []
    else:
        contract = json.loads(json.dumps(supplied))

    required_fields = (
        "comparison_question_id",
        "football_question",
        "analysis_scale",
        "required_exact_dimensions",
        "required_coarsened_dimensions",
        "allowed_test_dimensions",
        "forbidden_leakage_dimensions",
        "required_observation_capabilities",
        "claim_ceiling",
    )
    for field in required_fields:
        if field not in contract or contract.get(field) is None:
            blocks.append(f"comparison_question_contract_missing:{field}")
    for field in ("comparison_question_id", "football_question", "analysis_scale", "claim_ceiling"):
        if field in contract and not _clean(contract.get(field)):
            blocks.append(f"comparison_question_contract_empty:{field}")
    for field in (
        "required_exact_dimensions",
        "required_coarsened_dimensions",
        "allowed_test_dimensions",
        "forbidden_leakage_dimensions",
        "required_observation_capabilities",
    ):
        if field in contract and not isinstance(contract.get(field), list):
            blocks.append(f"comparison_question_contract_not_list:{field}")

    exact = _dimension_set(contract, "required_exact_dimensions")
    coarsened = _dimension_set(contract, "required_coarsened_dimensions")
    tested = _dimension_set(contract, "allowed_test_dimensions")
    if tested & exact:
        blocks.append("comparison_question_test_dimension_exact_match_overlap")
    if tested & coarsened:
        blocks.append("comparison_question_test_dimension_coarsened_match_overlap")
    forbidden = {
        _clean(value)
        for value in (contract.get("forbidden_leakage_dimensions") or [])
        if _clean(value)
    }
    if not any("outcome" in value.lower() or "consequence" in value.lower() for value in forbidden):
        reviews.append("comparison_question_outcome_leakage_dimension_not_declared")
    forbidden_exact = sorted(forbidden & exact)
    forbidden_coarsened = sorted(forbidden & coarsened)
    if forbidden_exact:
        blocks.append(
            "comparison_question_forbidden_leakage_exact_match_overlap:"
            + ",".join(forbidden_exact)
        )
    if forbidden_coarsened:
        blocks.append(
            "comparison_question_forbidden_leakage_coarsened_match_overlap:"
            + ",".join(forbidden_coarsened)
        )

    declared_roles = {
        "EXACT": exact,
        "COARSENED": coarsened,
        "TEST": tested,
        "FORBIDDEN": forbidden,
    }
    for role, dimensions in declared_roles.items():
        for dimension in sorted(dimensions):
            registry = DIMENSION_REGISTRY_V1.get(dimension)
            if registry is None:
                blocks.append(f"comparison_question_dimension_unregistered:{dimension}")
                continue
            allowed_roles = registry.get("allowed_roles") or set()
            if role not in allowed_roles:
                blocks.append(f"comparison_question_dimension_role_not_allowed:{dimension}:{role}")
            if registry.get("forbidden") is True and role != "FORBIDDEN":
                blocks.append(f"comparison_question_forbidden_dimension_used_for_admission:{dimension}:{role}")

    if _clean(contract.get("dimension_registry_version")) not in {"", DIMENSION_REGISTRY_VERSION}:
        blocks.append("comparison_question_dimension_registry_version_mismatch")
    contract["dimension_registry_version"] = DIMENSION_REGISTRY_VERSION
    return contract, blocks, reviews


def _pair_key(left_index: int, right_index: int) -> tuple[int, int]:
    return (left_index, right_index) if left_index < right_index else (right_index, left_index)


def _add_star_pairs(indices: list[int], out: set[tuple[int, int]]) -> None:
    ordered = sorted(set(indices))
    if len(ordered) < 2:
        return
    anchor = ordered[0]
    for index in ordered[1:]:
        out.add(_pair_key(anchor, index))


def _candidate_pair_indices(
    variants: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[set[tuple[int, int]], list[dict[str, Any]], dict[str, int]]:
    tested = _dimension_set(contract, "allowed_test_dimensions")
    period_is_test = "period" in tested
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
        period_key = "__TEST_DIMENSION_PERIOD__" if period_is_test else period
        groups[(team, period_key, signature)].append(index)

    admitted_pair_indices: set[tuple[int, int]] = set()
    comparison_groups: list[dict[str, Any]] = []
    topology_mismatch_pair_pruned_count = 0
    topology_unresolved_pair_count = 0
    coarse_signature_topology_split_group_count = 0

    for (team, period_key, signature), indices in sorted(
        groups.items(),
        key=lambda item: (item[0][0], item[0][1], repr(item[0][2])),
    ):
        ordered = sorted(
            indices,
            key=lambda idx: _clean(variants[idx].get("partial_order_occurrence_variant_id")),
        )
        if len(ordered) < 2:
            continue

        coarse_pair_indices: set[tuple[int, int]] = set()
        _add_star_pairs(ordered, coarse_pair_indices)

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
        group_admitted_pairs: set[tuple[int, int]] = set()
        for left_index, right_index in sorted(coarse_pair_indices):
            topology_match = _topology_exact_match(variants[left_index], variants[right_index])
            if topology_match is True:
                pair_key = _pair_key(left_index, right_index)
                admitted_pair_indices.add(pair_key)
                group_admitted_pairs.add(pair_key)
            elif topology_match is False:
                topology_mismatch_pair_pruned_count += 1
                group_topology_mismatch = True
            else:
                topology_unresolved_pair_count += 1
                group_topology_unresolved = True

        if group_topology_mismatch:
            coarse_signature_topology_split_group_count += 1

        eligible_indices = sorted({index for pair in group_admitted_pairs for index in pair})
        eligible_refs = [
            _clean(variants[index].get("partial_order_occurrence_variant_id"))
            for index in eligible_indices
        ]
        member_refs = [
            _clean(variants[index].get("partial_order_occurrence_variant_id"))
            for index in ordered
        ]
        group_id = "po_group_" + _digest(
            team,
            period_key,
            signature,
            contract.get("comparison_question_id"),
        )[:24]
        comparison_groups.append({
            "comparison_group_id": group_id,
            "comparison_question_id": contract.get("comparison_question_id"),
            "question_profile_version": contract.get("question_profile_version") or "1.0.0",
            "question_profile_hash": question_profile_hash,
            "profile_frozen_before_outcome_attachment": True,
            "team_identity_candidate_id": team,
            "period_candidate": None if period_is_test else period_key,
            "period_is_test_dimension": period_is_test,
            "member_variant_refs": member_refs,
            "member_variant_count": len(ordered),
            "eligible_member_variant_refs": eligible_refs,
            "eligible_case_count": len(eligible_refs),
            "coarse_partial_order_signature_match_required": True,
            "coarse_signature_is_exact_equivalence_proof": False,
            "relation_preserving_topology_filter_applied": True,
            "topology_filter_can_create_new_pair": False,
            "topology_filter_only_removes_or_preserves_coarse_prefilter_pairs": True,
            "structural_exact_equivalence_proven_for_all_materialized_pairs": not group_topology_unresolved,
            "coarse_signature_group_contains_topology_mismatch": group_topology_mismatch,
            "outcome_used_in_comparison_admission": False,
            "outcome_used_in_pair_materialization": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "comparison_group_is_process_identity_truth": False,
            "comparison_group_is_tactical_pattern_truth": False,
            "claim_ceiling": COMPARABLE_SET_CLAIM_CEILING,
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
    contract: dict[str, Any],
) -> tuple[str, bool, bool, bool, str]:
    tested = _dimension_set(contract, "allowed_test_dimensions")
    period_is_test = "period" in tested
    if not same_team:
        return "NOT_COMPARABLE_CROSS_TEAM_MATCH_LOCAL", False, False, False, "INELIGIBLE"
    if not left_period or not right_period:
        return "INDETERMINATE_MISSING_PERIOD_CONTEXT", False, False, True, "REVIEW_REQUIRED"
    if left_period != right_period and not period_is_test:
        return "PARTIALLY_COMPARABLE_REVIEW_REQUIRED_CROSS_PERIOD", False, False, True, "INELIGIBLE"
    if not structural_exact_match:
        return "PARTIALLY_COMPARABLE_REVIEW_REQUIRED_STRUCTURE_MISMATCH", False, False, True, "REVIEW_REQUIRED"
    if left_period != right_period and period_is_test:
        return "COMPARABLE_FOR_DECLARED_PERIOD_TEST_DIMENSION", True, True, False, "STRICT_ELIGIBLE"
    if shared_origin:
        return "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST", True, True, False, "STRICT_ELIGIBLE"
    return (
        "COMPARABLE_FOR_MATCH_LOCAL_RECURRENCE_CANDIDATE_INDEPENDENCE_UNPROVEN",
        True,
        True,
        False,
        "STRICT_ELIGIBLE",
    )


def _build_pair(
    left: dict[str, Any],
    right: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any] | None:
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

    left_occ = {
        _clean(value)
        for value in (left.get("supporting_action_occurrence_candidate_ids") or [])
        if _clean(value)
    }
    right_occ = {
        _clean(value)
        for value in (right.get("supporting_action_occurrence_candidate_ids") or [])
        if _clean(value)
    }
    shared_occ = sorted(left_occ & right_occ)
    left_dep = {
        _clean(value)
        for value in (left.get("dependency_group_refs") or [])
        if _clean(value)
    }
    right_dep = {
        _clean(value)
        for value in (right.get("dependency_group_refs") or [])
        if _clean(value)
    }
    shared_dep = sorted(left_dep & right_dep)
    shared_origin = bool(shared_occ or shared_dep)
    provenance_distinct = not shared_origin

    action_similarity = _multiset_jaccard(
        _counter(left.get("action_family_signature"), "action_family_candidate"),
        _counter(right.get("action_family_signature"), "action_family_candidate"),
    )
    order_similarity = _multiset_jaccard(_order_signature(left), _order_signature(right))
    layer_shape_similarity = _multiset_jaccard(
        _layer_shape_signature(left),
        _layer_shape_signature(right),
    )
    coarse_signature_match = (
        action_similarity == 1.0
        and order_similarity == 1.0
        and layer_shape_similarity == 1.0
    )
    topology_match = _topology_exact_match(left, right) if coarse_signature_match else False
    structural_exact_match = topology_match is True
    outcome_equal = _outcome_signature_equal(left, right)

    (
        comparison_state,
        comparison_eligible,
        outcome_contrast_allowed,
        comparison_requires_review,
        eligibility_grade,
    ) = _comparison_eligibility(
        same_team=same_team,
        left_period=left_period,
        right_period=right_period,
        structural_exact_match=structural_exact_match,
        shared_origin=shared_origin,
        contract=contract,
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

    if comparison_eligible:
        canonical_comparison_state = "ELIGIBLE"
        canonical_reasons = [comparison_state]
    elif not left_period or not right_period:
        canonical_comparison_state = "CONTEXT_UNRESOLVED"
        canonical_reasons = [comparison_state]
    elif not same_team or not structural_exact_match or (left_period != right_period and "period" not in _dimension_set(contract, "allowed_test_dimensions")):
        canonical_comparison_state = "CONTEXT_MISMATCH"
        canonical_reasons = [comparison_state]
    else:
        canonical_comparison_state = "NOT_EVALUATED"
        canonical_reasons = [comparison_state]

    pair_id = "po_sim_" + _digest(left_id, right_id)[:24]
    return {
        "partial_order_similarity_pair_id": pair_id,
        "comparison_question_id": contract.get("comparison_question_id"),
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
        "canonical_comparison_state": canonical_comparison_state,
        "canonical_comparison_state_reasons": canonical_reasons,
        "eligible_for_outcome_attachment": canonical_comparison_state == "ELIGIBLE",
        "process_comparison_eligibility_grade": eligibility_grade,
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
        "outcome_used_in_comparison_admission": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "similarity_is_recurrence_truth": False,
        "similarity_is_tactical_pattern_truth": False,
        "similarity_is_causal_truth": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _build_comparable_sets(
    groups: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    variant_by_id = {
        _clean(row.get("partial_order_occurrence_variant_id")): row
        for row in variants
        if _clean(row.get("partial_order_occurrence_variant_id"))
    }
    sets: list[dict[str, Any]] = []
    for group in groups:
        members = [
            _clean(value)
            for value in (group.get("eligible_member_variant_refs") or [])
            if _clean(value)
        ]
        if len(members) < 2:
            continue
        dependency_refs = {
            _clean(dependency_ref)
            for member in members
            for dependency_ref in (variant_by_id.get(member, {}).get("dependency_group_refs") or [])
            if _clean(dependency_ref)
        }
        periods = sorted({
            _clean(variant_by_id.get(member, {}).get("period_candidate"))
            for member in members
            if _clean(variant_by_id.get(member, {}).get("period_candidate"))
        })
        teams = sorted({
            _clean(variant_by_id.get(member, {}).get("team_identity_candidate_id"))
            for member in members
            if _clean(variant_by_id.get(member, {}).get("team_identity_candidate_id"))
        })
        question_profile_hash = _digest(contract)
        set_id = "pcs_" + _digest(contract.get("comparison_question_id"), members)[:24]
        sets.append({
            "comparable_set_id": set_id,
            "comparison_question_id": contract.get("comparison_question_id"),
            "team": teams[0] if len(teams) == 1 else None,
            "analysis_scale": contract.get("analysis_scale"),
            "anchor_process_family": contract.get("anchor_process_family"),
            "eligibility_grade": "STRICT_ELIGIBLE",
            "member_process_candidate_ids": members,
            "eligible_case_count": len(members),
            "materialized_pair_count_is_eligible_denominator": False,
            "unique_dependency_group_count": len(dependency_refs),
            "required_exact_dimensions": list(contract.get("required_exact_dimensions") or []),
            "required_coarsened_dimensions": list(contract.get("required_coarsened_dimensions") or []),
            "allowed_test_dimensions": list(contract.get("allowed_test_dimensions") or []),
            "resolved_context": {
                "team_identity_candidate_ids": teams,
                "period_candidates": periods,
            },
            "unresolved_context": [],
            "prefix_support_summary": "STRUCTURAL_EXACT_RELATION_PRESERVING_TOPOLOGY_CANDIDATE",
            "partial_order_state": "SAME_TIME_UNORDERED_PRESERVED",
            "censoring_burden": "NOT_EVALUATED_BEFORE_OUTCOME_ATTACHMENT",
            "dependency_burden": "DEPENDENCY_INDEPENDENCE_NOT_PROVEN",
            "episode_spread": "UNKNOWN",
            "actor_spread": "UNKNOWN",
            "context_spread": {"period_count": len(periods)},
            "eligible_denominator_frozen_before_outcome_attachment": True,
            "outcome_used_in_eligibility": False,
            "outcome_used_in_pair_materialization": False,
            "comparable_set_is_finding": False,
            "comparable_set_is_process_identity_truth": False,
            "comparable_set_is_tactical_pattern_truth": False,
            "comparable_set_is_causal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": contract.get("claim_ceiling") or COMPARABLE_SET_CLAIM_CEILING,
        })
    return sets


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

    contract, contract_blocks, contract_reviews = _comparison_contract(variant_payload)
    blocks.extend(contract_blocks)
    reviews.extend(contract_reviews)

    variants = [
        row
        for row in (variant_payload.get("partial_order_occurrence_variants") or [])
        if isinstance(row, dict)
    ]
    if len(variants) < 2:
        reviews.append("insufficient_partial_order_variants_for_pairwise_similarity")

    all_pair_count = len(variants) * max(len(variants) - 1, 0) // 2
    if contract:
        pair_indices, comparison_groups, diagnostics = _candidate_pair_indices(variants, contract)
    else:
        pair_indices, comparison_groups, diagnostics = set(), [], {
            "missing_team_variant_count": 0,
            "missing_period_variant_count": 0,
            "structural_signature_unresolved_variant_count": 0,
            "topology_unresolved_pair_count": 0,
            "topology_mismatch_pair_pruned_count": 0,
            "coarse_signature_topology_split_group_count": 0,
            "admitted_structural_comparison_group_count": 0,
        }
    if diagnostics["missing_period_variant_count"]:
        reviews.append("variant_period_context_missing_before_comparison_admission")
    if diagnostics["topology_unresolved_pair_count"]:
        reviews.append("variant_topology_unresolved_before_comparison_admission")

    pairs: list[dict[str, Any]] = []
    if not blocks:
        for left_index, right_index in sorted(pair_indices):
            pair = _build_pair(variants[left_index], variants[right_index], contract)
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

    comparable_sets = (
        _build_comparable_sets(comparison_groups, variants, contract)
        if not blocks
        else []
    )

    if blocks:
        status = "FAIL_CLOSED"
        pairs = []
        comparison_groups = []
        comparable_sets = []
    elif reviews or variant_payload.get("partial_order_occurrence_variant_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    counts = Counter(_clean(row.get("pair_state")) for row in pairs)
    comparison_counts = Counter(_clean(row.get("comparison_eligibility_state")) for row in pairs)
    canonical_comparison_counts = Counter(_clean(row.get("canonical_comparison_state")) for row in pairs)
    materialized_pair_count = len(pairs)
    tested = _dimension_set(contract, "allowed_test_dimensions") if contract else set()

    return {
        "status": status,
        "process_comparison_question_contract": contract,
        "comparison_dimension_registry_version": DIMENSION_REGISTRY_VERSION,
        "question_profile_hash": _digest(contract) if contract else None,
        "profile_frozen_before_outcome_attachment": True,
        "process_comparison_question_contract_status": (
            "FAIL_CLOSED"
            if contract_blocks
            else "REVIEW_REQUIRED"
            if contract_reviews
            else "PASS"
        ),
        "process_comparable_sets": comparable_sets,
        "process_comparable_set_count": len(comparable_sets),
        "eligible_denominator_frozen_before_outcome_attachment": True,
        "dependency_aware_partial_order_similarity_pairs": pairs,
        "dependency_aware_partial_order_similarity_pair_count": materialized_pair_count,
        "dependency_aware_partial_order_similarity_groups": comparison_groups,
        "dependency_aware_partial_order_similarity_group_count": len(comparison_groups),
        "pair_state_counts": dict(sorted(counts.items())),
        "comparison_eligibility_state_counts": dict(sorted(comparison_counts.items())),
        "canonical_comparison_state_counts": dict(sorted(canonical_comparison_counts.items())),
        "comparison_eligible_pair_count": sum(1 for row in pairs if row.get("comparison_eligible")),
        "source_partial_order_occurrence_variant_count": len(variants),
        "source_all_possible_pair_count": all_pair_count,
        "comparison_prefilter_materialized_pair_count": materialized_pair_count,
        "comparison_prefilter_pruned_pair_count": max(all_pair_count - materialized_pair_count, 0),
        "pair_materialization_mode": PAIR_MATERIALIZATION_MODE,
        "pair_materialization_count_is_eligible_denominator": False,
        "comparison_admission_precedes_pair_materialization": True,
        "coarse_signature_is_only_prefilter": True,
        "structural_exact_match_requires_relation_preserving_topology": True,
        "cross_team_pairs_materialized": False,
        "cross_period_pairs_materialized": (
            "period" in tested
            and any(not row.get("same_period_comparison") for row in pairs)
        ),
        "structural_mismatch_pairs_materialized": False,
        "topology_mismatch_pairs_materialized": False,
        "topology_filter_can_create_new_pair": False,
        "topology_filter_only_removes_or_preserves_coarse_prefilter_pairs": True,
        **diagnostics,
        "recurrence_candidate_eligible_pair_count": sum(
            1 for row in pairs if row.get("recurrence_candidate_eligible")
        ),
        "outcome_used_in_similarity_decision": False,
        "outcome_used_in_comparison_admission": False,
        "outcome_used_in_pair_materialization": False,
        "outcome_used_only_for_representative_materialization_after_structural_admission": False,
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
