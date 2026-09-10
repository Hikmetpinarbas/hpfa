from __future__ import annotations

from typing import Any

MODULE_ID = "rich_construct_metric_governance_guard_v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return " ".join(_text(value).casefold().replace("%", " percent ").replace("_", " ").split())


def _admitted_alignment_rows(metric_governance: dict[str, Any]) -> list[dict[str, Any]]:
    alignment = metric_governance.get("aggregate_definition_alignment") or {}
    return [
        row
        for row in alignment.get("alignment_rows", []) or []
        if isinstance(row, dict)
        and row.get("alignment_decision") == "DEFINITION_ALIGNMENT_CANDIDATE"
        and row.get("metric_definition_bound") is True
        and row.get("aggregate_label_observed") is True
        and row.get("rate_calculation_admitted") is not False
    ]


def assess_rich_construct_candidate(
    candidate: dict[str, Any],
    metric_governance: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed for aggregate-backed rich constructs without admitted metric semantics.

    This gate does not promote metric truth or cross-format independence. It only
    prevents label-navigation candidates from entering downstream C4 as if an
    aggregate definition had already been admitted.
    """
    input_metrics = [
        row for row in candidate.get("input_metrics", []) or [] if isinstance(row, dict)
    ]
    aggregate_inputs = [
        row
        for row in input_metrics
        if _text(row.get("source_surface")) == "xlsx_entity_metric_row_projection_lite_v1"
    ]

    if not aggregate_inputs:
        return {
            "module_id": MODULE_ID,
            "status": "NOT_APPLICABLE",
            "admitted": True,
            "reason": "no_xlsx_aggregate_input",
            "aggregate_input_count": 0,
            "matched_alignment_count": 0,
            "construct_truth": False,
            "aggregate_equivalence_truth": False,
            "same_provider_multiformat_is_independent_support": False,
            "production_release": False,
        }

    if str(metric_governance.get("status") or "").upper() == "FAIL_CLOSED":
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "admitted": False,
            "reason": "metric_governance_fail_closed",
            "aggregate_input_count": len(aggregate_inputs),
            "matched_alignment_count": 0,
            "construct_truth": False,
            "aggregate_equivalence_truth": False,
            "same_provider_multiformat_is_independent_support": False,
            "production_release": False,
        }

    alignment_rows = _admitted_alignment_rows(metric_governance)
    alignment_labels = {
        _normalized(row.get("aggregate_label") or row.get("normalized_aggregate_label"))
        for row in alignment_rows
        if _normalized(row.get("aggregate_label") or row.get("normalized_aggregate_label"))
    }

    matched = 0
    unmatched_labels: list[str] = []
    for row in aggregate_inputs:
        raw_label = _text(row.get("raw_metric_label"))
        if _normalized(raw_label) in alignment_labels:
            matched += 1
        else:
            unmatched_labels.append(raw_label)

    admitted = matched == len(aggregate_inputs) and bool(aggregate_inputs)
    return {
        "module_id": MODULE_ID,
        "status": "PASS" if admitted else "REVIEW_REQUIRED",
        "admitted": admitted,
        "reason": "aggregate_definition_alignment_admitted" if admitted else "aggregate_metric_semantic_authority_missing",
        "aggregate_input_count": len(aggregate_inputs),
        "matched_alignment_count": matched,
        "unmatched_aggregate_labels": unmatched_labels,
        "construct_truth": False,
        "aggregate_equivalence_truth": False,
        "same_provider_multiformat_is_independent_support": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
