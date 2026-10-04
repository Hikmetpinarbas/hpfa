from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

MAX_RELATION_WINDOW_SECONDS = 12.0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        return float(_text(value))
    except (TypeError, ValueError):
        return None


def _provider_time_contract(context_payload: dict[str, Any]) -> dict[str, Any]:
    value = context_payload.get("provider_time_semantic_admission")
    return value if isinstance(value, dict) else {}


def _contract_admitted(context_payload: dict[str, Any]) -> tuple[bool, list[str]]:
    contract = _provider_time_contract(context_payload)
    reasons: list[str] = []
    if context_payload.get("time_admission_status") != "ADMITTED":
        reasons.append("time_admission_status_not_admitted")
    if contract.get("status") != "ADMITTED":
        reasons.append("provider_time_contract_not_admitted")
    if contract.get("time_basis_admission_status") != "ADMITTED":
        reasons.append("time_basis_not_admitted")
    if contract.get("time_basis_candidate") != "ABSOLUTE_MATCH_SECONDS":
        reasons.append("time_basis_not_absolute_match_seconds")
    if contract.get("unit_admission_status") != "ADMITTED":
        reasons.append("time_unit_not_admitted")
    if contract.get("unit_candidate") != "SECOND":
        reasons.append("time_unit_not_second")
    if contract.get("same_timestamp_internal_ordering_allowed") is True:
        reasons.append("same_timestamp_internal_ordering_must_remain_false")
    if contract.get("source_row_order_is_temporal_truth") is True:
        reasons.append("source_row_order_temporal_truth_forbidden")
    return not reasons, reasons


def _relation(a: dict[str, Any], b: dict[str, Any]) -> str:
    """Resolve temporal order from admitted absolute start timestamps only.

    Trackable-action ``end_candidate`` can delimit the visible trace/context window and is
    therefore not admitted as physical action duration. Using overlapping trace windows to
    suppress otherwise ordered start timestamps would convert provenance-window geometry
    into chronology truth. Same timestamps remain explicitly unordered.
    """
    a_start = _number(a.get("start_candidate"))
    b_start = _number(b.get("start_candidate"))
    if a_start is None or b_start is None:
        return "ORDER_INDETERMINATE"
    if a_start < b_start:
        return "AFTER_CONFIRMED"
    if b_start < a_start:
        return "BEFORE_CONFIRMED"
    return "SAME_TIME_UNORDERED"


def bind_temporal_relation_admission(
    trace_payload: dict[str, Any],
    context_payload: dict[str, Any],
) -> dict[str, Any]:
    traces = [
        row
        for row in (trace_payload.get("trackable_action_trace_candidates") or [])
        if isinstance(row, dict)
    ]
    admitted, contract_reasons = _contract_admitted(context_payload)
    payload = dict(trace_payload)
    payload["provider_time_contract_admission_status"] = (
        "ADMITTED" if admitted else "NOT_ADMITTED"
    )
    payload["provider_time_contract_review_reasons"] = contract_reasons
    payload["temporal_relation_admission_records"] = []
    payload["temporal_relation_admission_record_count"] = 0
    payload["temporal_relation_state_counts"] = {}
    payload["temporal_relation_max_window_seconds"] = MAX_RELATION_WINDOW_SECONDS
    payload["numeric_time_relation_requires_admitted_provider_contract"] = True
    payload["temporal_relation_uses_start_timestamp_only"] = True
    payload["trace_end_candidate_used_for_ordering"] = False
    payload["trace_end_candidate_is_physical_action_duration_truth"] = False
    payload["same_timestamp_is_total_order"] = False
    payload["source_row_order_is_temporal_truth"] = False
    payload["cross_period_temporal_relation_admitted"] = False

    if not admitted:
        reviews = list(payload.get("review_hits") or [])
        reviews.append("provider_time_contract_not_admitted_for_trace_relations")
        payload["review_hits"] = sorted(set(reviews))
        if payload.get("status") == "PASS":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
        return payload

    by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_trace_ids: list[str] = []
    for trace in traces:
        trace_id = _text(trace.get("trackable_action_trace_candidate_id"))
        period = _text(trace.get("period_candidate"))
        start = _number(trace.get("start_candidate"))
        end = _number(trace.get("end_candidate"))
        if not trace_id or not period or start is None or end is None or end < start:
            if trace_id:
                invalid_trace_ids.append(trace_id)
            continue
        by_period[period].append(trace)

    records: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    for period, rows in by_period.items():
        rows.sort(
            key=lambda row: (
                _number(row.get("start_candidate")) or 0.0,
                _number(row.get("end_candidate")) or 0.0,
                _text(row.get("trackable_action_trace_candidate_id")),
            )
        )
        for i, anchor in enumerate(rows):
            anchor_start = _number(anchor.get("start_candidate"))
            if anchor_start is None:
                continue
            anchor_id = _text(anchor.get("trackable_action_trace_candidate_id"))
            for candidate in rows[i + 1 :]:
                candidate_start = _number(candidate.get("start_candidate"))
                if candidate_start is None:
                    continue
                if candidate_start - anchor_start > MAX_RELATION_WINDOW_SECONDS:
                    break
                candidate_id = _text(candidate.get("trackable_action_trace_candidate_id"))
                state = _relation(anchor, candidate)
                records.append(
                    {
                        "anchor_trackable_action_trace_candidate_id": anchor_id,
                        "candidate_trackable_action_trace_candidate_id": candidate_id,
                        "period_candidate": period,
                        "relation_state": state,
                        "temporal_basis": "ABSOLUTE_MATCH_SECONDS",
                        "ordering_basis": "START_TIMESTAMP_POINT_CANDIDATE",
                        "unit": "SECOND",
                        "provider_time_contract_rule_id": _provider_time_contract(
                            context_payload
                        ).get("rule_id"),
                        "trace_end_candidate_used_for_ordering": False,
                        "same_timestamp_is_total_order": False,
                        "source_row_order_is_temporal_truth": False,
                        "relation_is_possession_truth": False,
                        "relation_is_sequence_truth": False,
                        "relation_is_causal_truth": False,
                    }
                )
                state_counts[state] += 1

    payload["temporal_relation_admission_records"] = records
    payload["temporal_relation_admission_record_count"] = len(records)
    payload["temporal_relation_state_counts"] = dict(sorted(state_counts.items()))
    payload["temporal_relation_invalid_trace_ids"] = sorted(set(invalid_trace_ids))
    if invalid_trace_ids:
        reviews = list(payload.get("review_hits") or [])
        reviews.append("trace_time_invalid_for_temporal_relation_admission")
        payload["review_hits"] = sorted(set(reviews))
        if payload.get("status") == "PASS":
            payload["status"] = "REVIEW_REQUIRED"
            payload["module_status"] = "REVIEW_REQUIRED"
    return payload
