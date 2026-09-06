from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any

MODULE_ID = "trace_contrast_packet_lite_v1"
VARIANT_MODULE_ID = "partial_order_trace_variant_lite_v1"
SIMILARITY_MODULE_ID = "trace_similarity_primitive_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_TRACE_CONTRAST_CANDIDATE_ONLY"
ELIGIBILITY_COMPONENTS = ("action", "order", "context")

SUCCESS_OUTCOMES = {"TERMINAL_OUTCOME_SUPPORT_CANDIDATE"}
FAILURE_OUTCOMES = {
    "OPPONENT_HANDOVER_CANDIDATE",
    "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE",
}
NO_VISIBLE_OUTCOMES = {"NO_VISIBLE_FOLLOW_UP_CANDIDATE"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _status(payload: dict[str, Any]) -> str:
    return _clean(payload.get("status") or payload.get("module_status")).upper() or "UNKNOWN"


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


def _validate_eligibility(
    threshold: Any,
    weights: dict[str, Any] | None,
) -> tuple[float | None, dict[str, float], list[str]]:
    blocks: list[str] = []
    try:
        parsed_threshold = float(threshold)
    except (TypeError, ValueError):
        return None, {}, ["eligibility_threshold_invalid"]
    if not math.isfinite(parsed_threshold) or not 0.0 <= parsed_threshold <= 1.0:
        blocks.append("eligibility_threshold_out_of_range")

    if not isinstance(weights, dict) or not weights:
        blocks.append("eligibility_weights_required")
        return parsed_threshold, {}, blocks
    cleaned: dict[str, float] = {}
    for key, value in weights.items():
        if key not in ELIGIBILITY_COMPONENTS:
            blocks.append(f"eligibility_component_forbidden:{key}")
            continue
        try:
            number = float(value)
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
    if not any(value > 0 for value in cleaned.values()):
        blocks.append("eligibility_positive_weight_required")
    return parsed_threshold, cleaned, sorted(set(blocks))


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


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
        value = values.get(key)
        if value is None:
            return None, f"INELIGIBLE_MISSING_REQUIRED_COMPONENT:{key}"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None, f"INELIGIBLE_INVALID_COMPONENT:{key}"
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            return None, f"INELIGIBLE_OUT_OF_RANGE_COMPONENT:{key}"
        weighted.append((number, weight))
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        return None, "INELIGIBLE_NO_WEIGHTED_COMPONENT"
    return round(sum(value * weight for value, weight in weighted) / total_weight, 6), "AVAILABLE"


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


def _classify_outcome(variant: dict[str, Any]) -> tuple[str, str, list[str]]:
    labels = _outcome_labels(variant)
    success = bool(labels & SUCCESS_OUTCOMES)
    failure = bool(labels & FAILURE_OUTCOMES)
    no_visible = bool(labels & NO_VISIBLE_OUTCOMES)
    visible_other = bool(labels - NO_VISIBLE_OUTCOMES)

    if no_visible and not visible_other:
        return "NO_VISIBLE_FOLLOWUP", "NO_VISIBLE_FOLLOWUP", sorted(labels)
    if success and not failure:
        return "SUCCESS", "TERMINAL_SUCCESS_CANDIDATE", sorted(labels)
    if failure and not success:
        return "FAILURE", "LOSS_TERMINATION", sorted(labels)
    return "DIVERGENCE", "VISIBLE_DIVERGENCE", sorted(labels)


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

    threshold, weights, eligibility_blocks = _validate_eligibility(minimum_similarity, eligibility_weights)
    blocks.extend(eligibility_blocks)

    variants = [row for row in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(row, dict)]
    variant_by_id = {
        _clean(row.get("trace_variant_id")): row
        for row in variants
        if _clean(row.get("trace_variant_id"))
    }
    if len(variant_by_id) != len(variants):
        blocks.append("variant_id_missing_or_duplicate")
    if len(variants) < 2:
        blocks.append("missing_comparator_variant_population")

    pairs = [row for row in (similarity_payload.get("trace_similarity_pairs") or []) if isinstance(row, dict)]
    pair_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for pair in pairs:
        a = _clean(pair.get("trace_a_ref"))
        b = _clean(pair.get("trace_b_ref"))
        if not a or not b or a == b:
            blocks.append("similarity_pair_identity_invalid")
            continue
        key = _pair_key(a, b)
        if key in pair_by_key:
            blocks.append(f"duplicate_similarity_pair:{key[0]}:{key[1]}")
        pair_by_key[key] = pair

    variant_ids = sorted(variant_by_id)
    expected_pairs = {
        _pair_key(variant_ids[i], variant_ids[j])
        for i in range(len(variant_ids))
        for j in range(i + 1, len(variant_ids))
    }
    missing_pairs = sorted(expected_pairs - set(pair_by_key))
    extra_pairs = sorted(set(pair_by_key) - expected_pairs)
    if missing_pairs:
        blocks.append("missing_similarity_comparator_pairs")
    if extra_pairs:
        blocks.append("similarity_pairs_reference_unknown_variant")

    if blocks:
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

    outcome_by_variant = {variant_id: _classify_outcome(variant) for variant_id, variant in variant_by_id.items()}
    packets: list[dict[str, Any]] = []
    threshold_value = float(threshold)

    for anchor_id in variant_ids:
        eligible_refs = [anchor_id]
        pair_scores: list[dict[str, Any]] = []
        for other_id in variant_ids:
            if other_id == anchor_id:
                continue
            pair = pair_by_key[_pair_key(anchor_id, other_id)]
            score, score_state = _eligibility_score(pair, weights)
            is_eligible = score is not None and score >= threshold_value
            pair_scores.append({
                "trace_ref": other_id,
                "eligibility_similarity": score,
                "eligibility_state": score_state,
                "eligible": is_eligible,
            })
            if is_eligible:
                eligible_refs.append(other_id)

        successful: list[str] = []
        failed: list[str] = []
        divergent: list[str] = []
        no_visible: list[str] = []
        outcome_distribution: Counter[str] = Counter()
        outcome_state_distribution: Counter[str] = Counter()
        for trace_ref in eligible_refs:
            bucket, state, _ = outcome_by_variant[trace_ref]
            outcome_distribution[bucket] += 1
            outcome_state_distribution[state] += 1
            if bucket == "SUCCESS":
                successful.append(trace_ref)
            elif bucket == "FAILURE":
                failed.append(trace_ref)
            elif bucket == "DIVERGENCE":
                divergent.append(trace_ref)
            else:
                no_visible.append(trace_ref)

        dependency_groups = sorted({
            _clean(value)
            for trace_ref in eligible_refs
            for value in (variant_by_id[trace_ref].get("dependency_group_refs") or [])
            if _clean(value)
        })
        provenance_refs = sorted({
            _clean(value)
            for trace_ref in eligible_refs
            for value in (variant_by_id[trace_ref].get("provenance_refs") or [])
            if _clean(value)
        })
        if len(eligible_refs) < 2:
            packet_state = "REVIEW_REQUIRED_NO_ELIGIBLE_COMPARATOR"
            reviews.append(f"no_eligible_comparator:{anchor_id}")
        else:
            packet_state = "CONTRAST_AVAILABLE"

        packets.append({
            "trace_contrast_id": "tcp_" + _digest(anchor_id, eligible_refs, threshold_value, weights)[:24],
            "anchor_trace_family": anchor_id,
            "anchor_context": variant_by_id[anchor_id].get("context_signature") or {},
            "eligible_trace_refs": eligible_refs,
            "successful_trace_refs": successful,
            "failed_trace_refs": failed,
            "divergent_trace_refs": divergent,
            "no_visible_followup_refs": no_visible,
            "eligible_trace_count": len(eligible_refs),
            "support_count": len(successful),
            "failure_count": len(failed),
            "divergence_count": len(divergent),
            "no_visible_followup_count": len(no_visible),
            "dependency_groups": dependency_groups,
            "independence_groups": [],
            "independent_support_count": "UNKNOWN",
            "outcome_distribution": dict(sorted(outcome_distribution.items())),
            "variant_distribution": dict(sorted(outcome_state_distribution.items())),
            "similarity_method": similarity_payload.get("method_version"),
            "similarity_parameters": {
                "minimum_similarity": threshold_value,
                "eligibility_weights": dict(sorted(weights.items())),
                "allowed_components": list(ELIGIBILITY_COMPONENTS),
                "outcome_similarity_used_for_eligibility": False,
            },
            "eligibility_rule": "SAME_RULE_FOR_ALL_OUTCOMES_WEIGHTED_ACTION_ORDER_CONTEXT_ONLY",
            "pair_eligibility_evidence": pair_scores,
            "counterevidence_refs": sorted(set(failed + divergent)),
            "alternative_explanation_refs": [],
            "provenance_refs": provenance_refs,
            "uncertainty": {
                "independence_not_proven": True,
                "no_visible_followup_is_failure": False,
                "absence_of_evidence_is_counterevidence": False,
                "similarity_threshold_is_objective_truth": False,
            },
            "claim_ceiling": CLAIM_CEILING,
            "withdrawal_condition": "Withdraw or reclassify if occurrence binding, consequence classification, dependency accounting, or eligibility parameters change materially.",
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
        "trace_contrast_does_not_claim_causality": True,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
