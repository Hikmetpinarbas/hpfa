from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_COMPARABLE_VISIBLE_OUTCOME_COUNTEREVIDENCE_CANDIDATE_ONLY"
VISIBLE_OUTCOME_STATES = {"SUCCESS_SEMANTIC_VISIBLE", "FAILURE_SEMANTIC_VISIBLE"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _variant_sequence_map(payload: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in payload.get("partial_order_occurrence_variants") or []:
        if not isinstance(row, dict):
            continue
        variant_id = _clean(row.get("partial_order_occurrence_variant_id"))
        sequence_ref = _clean(row.get("sequence_ref"))
        if variant_id and sequence_ref:
            out[variant_id] = sequence_ref
    return out


def _sequence_outcome_map(payload: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for divergence in payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(divergence, dict):
            continue
        for branch in divergence.get("branch_profiles") or []:
            if not isinstance(branch, dict):
                continue
            state = _clean(branch.get("branch_outcome_state"))
            if not state:
                continue
            for sequence_ref in branch.get("supporting_visible_sequence_candidate_ids") or []:
                sequence_ref = _clean(sequence_ref)
                if sequence_ref:
                    out[sequence_ref].add(state)
    return out


def _resolved_state(sequence_ref: str, outcomes: dict[str, set[str]]) -> str | None:
    states = outcomes.get(sequence_ref) or set()
    visible = sorted(state for state in states if state in VISIBLE_OUTCOME_STATES)
    return visible[0] if len(visible) == 1 else None


def build_comparable_outcome_counterevidence(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("dependency_aware_partial_order_similarity_status") == "FAIL_CLOSED":
        blocks.append("comparison_projection_fail_closed")
    if sequence_payload.get("first_supported_branch_divergence_status") == "FAIL_CLOSED":
        blocks.append("divergence_projection_fail_closed")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if sequence_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    variant_to_sequence = _variant_sequence_map(sequence_payload)
    sequence_outcomes = _sequence_outcome_map(sequence_payload)
    records: list[dict[str, Any]] = []

    for pair in sequence_payload.get("dependency_aware_partial_order_similarity_pairs") or []:
        if not isinstance(pair, dict):
            continue
        pair_id = _clean(pair.get("partial_order_similarity_pair_id"))
        left_variant = _clean(pair.get("left_variant_ref"))
        right_variant = _clean(pair.get("right_variant_ref"))
        comparison_state = _clean(pair.get("comparison_eligibility_state"))
        comparison_eligible = pair.get("comparison_eligible") is True

        left_sequence = variant_to_sequence.get(left_variant)
        right_sequence = variant_to_sequence.get(right_variant)
        left_outcome = _resolved_state(left_sequence or "", sequence_outcomes) if left_sequence else None
        right_outcome = _resolved_state(right_sequence or "", sequence_outcomes) if right_sequence else None

        if not comparison_eligible:
            contrast_state = "NOT_APPLICABLE_OR_REVIEW_REQUIRED_COMPARISON"
            comparable_counterevidence_candidate = False
        elif not left_sequence or not right_sequence:
            contrast_state = "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED"
            comparable_counterevidence_candidate = False
            reviews.append(f"comparable_variant_sequence_binding_missing:{pair_id}")
        elif left_outcome is None or right_outcome is None:
            contrast_state = "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED"
            comparable_counterevidence_candidate = False
            reviews.append(f"comparable_visible_outcome_semantic_unresolved:{pair_id}")
        elif left_outcome == right_outcome:
            contrast_state = "COMPARABLE_SAME_VISIBLE_OUTCOME"
            comparable_counterevidence_candidate = False
        else:
            contrast_state = "COMPARABLE_DIFFERENT_VISIBLE_OUTCOME_COUNTEREXAMPLE_CANDIDATE"
            comparable_counterevidence_candidate = True

        record_id = "coc_" + _digest(pair_id, left_variant, right_variant, left_outcome, right_outcome)[:24]
        records.append({
            "comparable_outcome_counterevidence_id": record_id,
            "partial_order_similarity_pair_ref": pair_id or None,
            "left_variant_ref": left_variant or None,
            "right_variant_ref": right_variant or None,
            "left_sequence_ref": left_sequence,
            "right_sequence_ref": right_sequence,
            "comparison_eligibility_state": comparison_state or None,
            "comparison_eligible": comparison_eligible,
            "left_visible_outcome_state": left_outcome,
            "right_visible_outcome_state": right_outcome,
            "comparable_outcome_contrast_state": contrast_state,
            "comparable_counterevidence_candidate": comparable_counterevidence_candidate,
            "counterevidence_is_independent_support": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "counterevidence_is_causal_refutation": False,
            "outcome_difference_is_failure_cause_truth": False,
            "outcome_difference_is_tactical_pattern_truth": False,
            "absence_is_counterevidence": False,
            "no_visible_followup_is_failure_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or sequence_payload.get("dependency_aware_partial_order_similarity_status") == "REVIEW_REQUIRED" or sequence_payload.get("first_supported_branch_divergence_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    counts = Counter(_clean(row.get("comparable_outcome_contrast_state")) for row in records)
    return {
        "status": status,
        "comparable_outcome_counterevidence_records": records if not blocks else [],
        "comparable_outcome_counterevidence_record_count": len(records) if not blocks else 0,
        "comparable_outcome_contrast_state_counts": dict(sorted(counts.items())) if not blocks else {},
        "comparison_eligible_record_count": sum(1 for row in records if row.get("comparison_eligible")) if not blocks else 0,
        "comparable_counterevidence_candidate_count": sum(1 for row in records if row.get("comparable_counterevidence_candidate")) if not blocks else 0,
        "counterevidence_independent_support_count": 0,
        "counterevidence_is_independent_support": False,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
        "outcome_difference_is_failure_cause_truth": False,
        "outcome_difference_is_tactical_pattern_truth": False,
        "absence_is_counterevidence": False,
        "no_visible_followup_is_failure_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
