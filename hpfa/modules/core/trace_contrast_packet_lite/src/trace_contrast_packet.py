from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any

MODULE_ID = "trace_contrast_packet_lite_v1"
VARIANT_MODULE_ID = "partial_order_trace_variant_lite_v1"
SIMILARITY_MODULE_ID = "trace_similarity_primitive_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_TRACE_CONTRAST_CANDIDATE_ONLY"
ELIGIBILITY_COMPONENTS = ("action", "order", "context")
SUCCESS_OUTCOMES = {"TERMINAL_OUTCOME_SUPPORT_CANDIDATE"}
FAILURE_OUTCOMES = {"OPPONENT_HANDOVER_CANDIDATE", "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"}
NO_VISIBLE_OUTCOMES = {"NO_VISIBLE_FOLLOW_UP_CANDIDATE"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _status(payload: dict[str, Any]) -> str:
    return _clean(payload.get("status") or payload.get("module_status")).upper() or "UNKNOWN"


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _validate_input(name: str, payload: dict[str, Any], module_id: str) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != module_id:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append(f"{name}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    status = _status(payload)
    if status == "FAIL_CLOSED":
        blocks.append(f"{name}_input_fail_closed")
    elif status == "REVIEW_REQUIRED":
        reviews.append(f"{name}_upstream_review_required")
    elif status != "PASS":
        reviews.append(f"{name}_upstream_status_review:{status}")
    return blocks, reviews


def _validate_eligibility(threshold: Any, weights: dict[str, Any] | None) -> tuple[float | None, dict[str, float], list[str]]:
    blocks: list[str] = []
    try:
        value = float(threshold)
    except (TypeError, ValueError):
        return None, {}, ["eligibility_threshold_invalid"]
    if not math.isfinite(value) or not 0 <= value <= 1:
        blocks.append("eligibility_threshold_out_of_range")
    if not isinstance(weights, dict) or not weights:
        return value, {}, blocks + ["eligibility_weights_required"]
    cleaned: dict[str, float] = {}
    for key, raw in weights.items():
        if key not in ELIGIBILITY_COMPONENTS:
            blocks.append(f"eligibility_component_forbidden:{key}")
            continue
        try:
            number = float(raw)
        except (TypeError, ValueError):
            blocks.append(f"eligibility_weight_invalid:{key}")
            continue
        if not math.isfinite(number):
            blocks.append(f"eligibility_weight_non_finite:{key}")
            continue
        if number < 0:
            blocks.append(f"eligibility_weight_negative:{key}")
            continue
        cleaned[key] = number
    if not any(weight > 0 for weight in cleaned.values()):
        blocks.append("eligibility_positive_weight_required")
    return value, cleaned, sorted(set(blocks))


def _eligibility_score(pair: dict[str, Any], weights: dict[str, float]) -> tuple[float | None, str]:
    values = {
        "action": pair.get("action_similarity"),
        "order": pair.get("order_similarity"),
        "context": pair.get("context_similarity"),
    }
    weighted: list[tuple[float, float]] = []
    for key, weight in weights.items():
        if weight <= 0:
            continue
        raw = values.get(key)
        if raw is None:
            return None, f"INELIGIBLE_MISSING_REQUIRED_COMPONENT:{key}"
        try:
            number = float(raw)
        except (TypeError, ValueError):
            return None, f"INELIGIBLE_INVALID_COMPONENT:{key}"
        if not math.isfinite(number) or not 0 <= number <= 1:
            return None, f"INELIGIBLE_OUT_OF_RANGE_COMPONENT:{key}"
        weighted.append((number, weight))
    denominator = sum(weight for _, weight in weighted)
    if denominator <= 0:
        return None, "INELIGIBLE_NO_WEIGHTED_COMPONENT"
    return round(sum(value * weight for value, weight in weighted) / denominator, 6), "AVAILABLE"


def _outcome_labels(variant: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for row in variant.get("outcome_signature") or []:
        if not isinstance(row, dict):
            continue
        label = _clean(row.get("outcome_candidate"))
        try:
            count = int(row.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if label and count > 0:
            labels.add(label)
    return labels


def _classify(variant: dict[str, Any]) -> tuple[str, str, list[str]]:
    labels = _outcome_labels(variant)
    has_success = bool(labels & SUCCESS_OUTCOMES)
    has_failure = bool(labels & FAILURE_OUTCOMES)
    no_visible = bool(labels & NO_VISIBLE_OUTCOMES)
    has_other = bool(labels - NO_VISIBLE_OUTCOMES)
    if no_visible and not has_other:
        return "NO_VISIBLE_FOLLOWUP", "NO_VISIBLE_FOLLOWUP", sorted(labels)
    if has_success and not has_failure:
        return "SUCCESS", "TERMINAL_SUCCESS_CANDIDATE", sorted(labels)
    if has_failure and not has_success:
        return "FAILURE", "LOSS_TERMINATION", sorted(labels)
    return "DIVERGENCE", "VISIBLE_DIVERGENCE", sorted(labels)


def _variant_occurrence_refs(variant: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for node in variant.get("node_records") or []:
        if not isinstance(node, dict):
            continue
        refs.update(_clean(value) for value in (node.get("occurrence_refs") or []) if _clean(value))
    return refs


def _variant_dependency_refs(variant: dict[str, Any]) -> set[str]:
    return {_clean(value) for value in (variant.get("dependency_group_refs") or []) if _clean(value)}


def _independence_groups(
    eligible_refs: list[str],
    by_variant: dict[str, dict[str, Any]],
) -> tuple[dict[str, str], list[str], int | str, str, list[str]]:
    """Group trace variants by explicit shared occurrence/dependency evidence.

    This proves only duplicate/dependency separation inside the current evidence spine.
    It is not statistical independence and does not imply separate causal mechanisms.
    """
    missing_occurrence = [ref for ref in eligible_refs if not _variant_occurrence_refs(by_variant[ref])]
    if missing_occurrence:
        return {}, [], "UNKNOWN", "NOT_PROVEN_MISSING_OCCURRENCE_BINDING", [
            f"independence_missing_occurrence_binding:{ref}" for ref in missing_occurrence
        ]

    parent = {ref: ref for ref in eligible_refs}

    def find(ref: str) -> str:
        while parent[ref] != ref:
            parent[ref] = parent[parent[ref]]
            ref = parent[ref]
        return ref

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    occurrence_sets = {ref: _variant_occurrence_refs(by_variant[ref]) for ref in eligible_refs}
    dependency_sets = {ref: _variant_dependency_refs(by_variant[ref]) for ref in eligible_refs}
    for idx, a in enumerate(eligible_refs):
        for b in eligible_refs[idx + 1 :]:
            if occurrence_sets[a] & occurrence_sets[b] or dependency_sets[a] & dependency_sets[b]:
                union(a, b)

    components: dict[str, list[str]] = {}
    for ref in eligible_refs:
        components.setdefault(find(ref), []).append(ref)

    mapping: dict[str, str] = {}
    groups: list[str] = []
    for members in sorted((sorted(values) for values in components.values()), key=lambda values: values[0]):
        group = "indgrp_" + _digest(members)[:16]
        groups.append(group)
        for ref in members:
            mapping[ref] = group

    return mapping, sorted(groups), len(groups), "PROVEN_WITHIN_OCCURRENCE_DEPENDENCY_SCOPE", []


def _fail(blocks: list[str], reviews: list[str]) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "decision": "TRACE_CONTRAST_INPUT_REJECTED",
        "trace_contrast_packets": [],
        "trace_contrast_packet_count": 0,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_trace_contrast_packets(
    variant_payload: dict[str, Any],
    similarity_payload: dict[str, Any],
    *,
    minimum_similarity: Any,
    eligibility_weights: dict[str, Any] | None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload, module_id in (
        ("variant", variant_payload, VARIANT_MODULE_ID),
        ("similarity", similarity_payload, SIMILARITY_MODULE_ID),
    ):
        input_blocks, input_reviews = _validate_input(name, payload, module_id)
        blocks.extend(input_blocks)
        reviews.extend(input_reviews)
    if variant_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("variant_same_timestamp_policy_breached")
    if variant_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("variant_source_row_order_policy_breached")

    threshold, weights, weight_blocks = _validate_eligibility(minimum_similarity, eligibility_weights)
    blocks.extend(weight_blocks)
    variants = [row for row in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(row, dict)]
    by_variant = {_clean(row.get("trace_variant_id")): row for row in variants if _clean(row.get("trace_variant_id"))}
    if len(by_variant) != len(variants):
        blocks.append("variant_id_missing_or_duplicate")
    if len(variants) < 2:
        blocks.append("missing_comparator_variant_population")
    for variant_id, variant in by_variant.items():
        if not _outcome_labels(variant):
            blocks.append(f"missing_visible_outcome_evidence:{variant_id}")

    pairs = [row for row in (similarity_payload.get("trace_similarity_pairs") or []) if isinstance(row, dict)]
    pair_map: dict[tuple[str, str], dict[str, Any]] = {}
    for pair in pairs:
        a = _clean(pair.get("trace_a_ref"))
        b = _clean(pair.get("trace_b_ref"))
        if not a or not b or a == b:
            blocks.append("similarity_pair_identity_invalid")
            continue
        key = _pair_key(a, b)
        if key in pair_map:
            blocks.append(f"duplicate_similarity_pair:{key[0]}:{key[1]}")
        pair_map[key] = pair
    ids = sorted(by_variant)
    expected = {_pair_key(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))}
    if expected - set(pair_map):
        blocks.append("missing_similarity_comparator_pairs")
    if set(pair_map) - expected:
        blocks.append("similarity_pairs_reference_unknown_variant")
    if blocks:
        return _fail(blocks, reviews)

    outcomes = {variant_id: _classify(variant) for variant_id, variant in by_variant.items()}
    packets: list[dict[str, Any]] = []
    threshold_value = float(threshold)
    for anchor in ids:
        eligible = [anchor]
        eligibility_evidence: list[dict[str, Any]] = []
        for other in ids:
            if other == anchor:
                continue
            score, state = _eligibility_score(pair_map[_pair_key(anchor, other)], weights)
            is_eligible = score is not None and score >= threshold_value
            eligibility_evidence.append({
                "trace_ref": other,
                "eligibility_similarity": score,
                "eligibility_state": state,
                "eligible": is_eligible,
            })
            if is_eligible:
                eligible.append(other)
        eligible = sorted(set(eligible))

        successful: list[str] = []
        failed: list[str] = []
        divergent: list[str] = []
        no_visible: list[str] = []
        distribution: Counter[str] = Counter()
        states: Counter[str] = Counter()
        for ref in eligible:
            bucket, state, _ = outcomes[ref]
            distribution[bucket] += 1
            states[state] += 1
            {
                "SUCCESS": successful,
                "FAILURE": failed,
                "DIVERGENCE": divergent,
                "NO_VISIBLE_FOLLOWUP": no_visible,
            }[bucket].append(ref)

        dependency_groups = sorted({
            _clean(value)
            for ref in eligible
            for value in (by_variant[ref].get("dependency_group_refs") or [])
            if _clean(value)
        })
        provenance_refs = sorted({
            _clean(value)
            for ref in eligible
            for value in (by_variant[ref].get("provenance_refs") or [])
            if _clean(value)
        })
        independence_mapping, independence_groups, independent_support_count, independence_state, independence_reviews = _independence_groups(
            eligible, by_variant
        )
        reviews.extend(independence_reviews)

        packet_state = "CONTRAST_AVAILABLE"
        if len(eligible) < 2:
            packet_state = "REVIEW_REQUIRED_NO_ELIGIBLE_COMPARATOR"
            reviews.append(f"no_eligible_comparator:{anchor}")

        packets.append({
            "trace_contrast_id": "tcp_" + _digest(anchor, eligible, threshold_value, weights)[:24],
            "anchor_trace_family": anchor,
            "anchor_context": by_variant[anchor].get("context_signature") or {},
            "eligible_trace_refs": eligible,
            "successful_trace_refs": successful,
            "failed_trace_refs": failed,
            "divergent_trace_refs": divergent,
            "no_visible_followup_refs": no_visible,
            "eligible_trace_count": len(eligible),
            "support_count": len(successful),
            "failure_count": len(failed),
            "divergence_count": len(divergent),
            "no_visible_followup_count": len(no_visible),
            "dependency_groups": dependency_groups,
            "independence_groups": independence_groups,
            "independence_group_by_trace_ref": independence_mapping,
            "independent_support_count": independent_support_count,
            "independence_state": independence_state,
            "independence_basis": "MATCH_LOCAL_OCCURRENCE_AND_DEPENDENCY_COMPONENTS_ONLY",
            "independence_is_statistical_independence": False,
            "outcome_distribution": dict(sorted(distribution.items())),
            "variant_distribution": dict(sorted(states.items())),
            "similarity_method": similarity_payload.get("method_version"),
            "similarity_parameters": {
                "minimum_similarity": threshold_value,
                "eligibility_weights": dict(sorted(weights.items())),
                "allowed_components": list(ELIGIBILITY_COMPONENTS),
                "outcome_similarity_used_for_eligibility": False,
            },
            "eligibility_rule": "SAME_RULE_FOR_ALL_OUTCOMES_WEIGHTED_ACTION_ORDER_CONTEXT_ONLY",
            "pair_eligibility_evidence": eligibility_evidence,
            "counterevidence_refs": sorted(set(failed + divergent)),
            "alternative_explanation_refs": [],
            "provenance_refs": provenance_refs,
            "uncertainty": {
                "independence_not_proven": independent_support_count == "UNKNOWN",
                "independence_is_statistical_independence": False,
                "no_visible_followup_is_failure": False,
                "absence_of_evidence_is_counterevidence": False,
                "similarity_threshold_is_objective_truth": False,
            },
            "claim_ceiling": CLAIM_CEILING,
            "withdrawal_condition": (
                "Withdraw or reclassify if occurrence binding, consequence classification, dependency accounting, "
                "or eligibility parameters change materially."
            ),
            "packet_state": packet_state,
            "trace_contrast_does_not_claim_causality": True,
            "trace_contrast_does_not_claim_intention": True,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
        })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "decision": "TRACE_CONTRAST_PACKETS_BUILT",
        "trace_contrast_packets": packets,
        "trace_contrast_packet_count": len(packets),
        "source_trace_variant_count": len(variants),
        "source_similarity_pair_count": len(pairs),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "similarity_method": similarity_payload.get("method_version"),
        "eligibility_threshold": threshold_value,
        "eligibility_weights": dict(sorted(weights.items())),
        "no_visible_followup_is_failure": False,
        "absence_of_evidence_is_counterevidence": False,
        "success_failure_share_eligibility_contract": True,
        "dependent_reflections_are_independent_support": False,
        "independence_is_statistical_independence": False,
        "trace_contrast_does_not_claim_causality": True,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
