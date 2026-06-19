"""Metric definition confidence audit.

Candidate stub only.
"""

from __future__ import annotations


def audit_definition_confidence(metric: dict, minimum: float = 0.75) -> dict[str, object]:
    metric_id = str(metric.get("id", "UNKNOWN_METRIC"))
    raw_value = metric.get("definition_confidence", 0)
    try:
        confidence = float(raw_value)
    except (TypeError, ValueError):
        confidence = 0.0

    if confidence >= minimum:
        status = "OK"
        reason = "definition confidence meets minimum"
    elif confidence > 0:
        status = "DEGRADED"
        reason = "definition confidence below minimum"
    else:
        status = "UNKNOWN"
        reason = "definition confidence missing or invalid"

    return {
        "metric_id": metric_id,
        "status": status,
        "definition_confidence": confidence,
        "minimum": minimum,
        "reason": reason,
    }
