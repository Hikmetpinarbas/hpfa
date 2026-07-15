from __future__ import annotations

from typing import Any

MODULE_ID = "aggregate_event_reconciliation_gate_lite_v1"


def _counts(payload: dict[str, Any], key: str) -> dict[str, int]:
    raw = payload.get(key)
    if not isinstance(raw, dict):
        raise ValueError(f"{key}_must_be_object")
    result: dict[str, int] = {}
    for family, value in raw.items():
        name = str(family).strip().upper()
        if isinstance(value, bool) or not name:
            raise ValueError(f"invalid_{key}")
        try:
            count = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid_{key}") from exc
        if count < 0 or str(count) != str(value).strip():
            raise ValueError(f"invalid_{key}")
        result[name] = count
    return result


def reconcile_aggregate_event_counts(
    classifier_payload: dict[str, Any],
    aggregate_payload: dict[str, Any],
    tolerance_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    surface = _counts(classifier_payload, "base_event_family_counts")
    aggregate = _counts(aggregate_payload, "aggregate_family_counts")
    tolerances = _counts(tolerance_payload or {"family_tolerances": {}}, "family_tolerances")
    rows: list[dict[str, Any]] = []
    blocked: list[str] = []
    review: list[str] = []

    for family in sorted(set(surface) | set(aggregate)):
        surface_count = surface.get(family, 0)
        aggregate_count = aggregate.get(family, 0)
        delta = surface_count - aggregate_count
        allowed = tolerances.get(family, 0)
        if delta == 0:
            status = "EXACT_COUNT_PARITY"
        elif abs(delta) <= allowed:
            status = "REVIEW_REQUIRED_EXPLICIT_TOLERANCE_USED"
            review.append(family)
        else:
            status = "BLOCKED_MATERIAL_COUNT_MISMATCH"
            blocked.append(family)
        rows.append({
            "event_family": family,
            "provisional_surface_count": surface_count,
            "aggregate_count": aggregate_count,
            "signed_delta": delta,
            "absolute_delta": abs(delta),
            "surface_to_aggregate_ratio": None if aggregate_count == 0 else surface_count / aggregate_count,
            "allowed_absolute_delta": allowed,
            "reconciliation_status": status,
        })

    decision = "PASS_EXACT_AGGREGATE_EVENT_COUNT_PARITY"
    if blocked:
        decision = "BLOCKED_AGGREGATE_EVENT_RECONCILIATION"
    elif review:
        decision = "REVIEW_REQUIRED_EXPLICIT_RECONCILIATION_TOLERANCE"

    return {
        "module_id": MODULE_ID,
        "decision_state": decision,
        "family_reconciliation": rows,
        "blocked_families": blocked,
        "review_families": review,
        "tolerance_policy": "ZERO_BY_DEFAULT_EXPLICIT_PER_FAMILY_ONLY",
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
