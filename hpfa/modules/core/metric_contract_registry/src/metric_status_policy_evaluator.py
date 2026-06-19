"""Metric status policy evaluator.

Candidate stub only. Status is an analysis readiness signal, not a football conclusion.
"""

from __future__ import annotations


def evaluate_metric_status(
    metric: dict,
    column_status: str,
) -> dict[str, str]:
    """Map required-column gate status into metric status policy text."""
    metric_id = str(metric.get("id", "UNKNOWN_METRIC"))
    policy = metric.get("status_policy", {}) or {}

    if column_status == "OK":
        status = "OK"
    elif column_status == "DEGRADED":
        status = "DEGRADED"
    else:
        status = "UNKNOWN"

    return {
        "metric_id": metric_id,
        "status": status,
        "policy_reason": str(policy.get(status, "status policy missing")),
    }
