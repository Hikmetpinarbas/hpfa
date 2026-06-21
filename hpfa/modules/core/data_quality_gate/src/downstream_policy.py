#!/usr/bin/env python3
"""
HPFA Downstream Policy V1

Converts Data Quality Gate V1 report state into explicit downstream permissions.
"""

from __future__ import annotations

from typing import Any, Dict

from gate_report_reader import get_gate_status, get_next_action, validate_gate_report


CLAIM_LAYER_BLOCK_REASON = (
    "Claim layer remains blocked until executable Claim Gate and Football Output Audit exist."
)


class DownstreamPolicyError(PermissionError):
    """Raised when a downstream layer is not allowed by gate policy."""


def is_downstream_allowed(report: Dict[str, Any], layer: str, degraded_mode: bool = False) -> bool:
    validate_gate_report(report)

    normalized_layer = layer.strip().lower()
    status = get_gate_status(report)
    next_action = get_next_action(report)

    if normalized_layer in {"claim", "claim_layer"}:
        return False

    if status == "FAIL_CLOSED":
        return False

    if normalized_layer in {"phase", "sequence", "phase_sequence"}:
        allowed = next_action.get("phase_sequence_allowed")
        if status == "DEGRADED":
            return bool(allowed) and degraded_mode
        return bool(allowed)

    if normalized_layer in {"metric", "metric_layer"}:
        allowed = next_action.get("metric_layer_allowed")
        if allowed == "CONDITIONAL":
            return degraded_mode
        return bool(allowed)

    return False


def assert_downstream_allowed(report: Dict[str, Any], layer: str, degraded_mode: bool = False) -> None:
    if not is_downstream_allowed(report, layer, degraded_mode=degraded_mode):
        status = get_gate_status(report)
        raise DownstreamPolicyError(
            f"Downstream layer blocked by Data Quality Gate policy: "
            f"layer={layer}, status={status}, degraded_mode={degraded_mode}"
        )


def claim_layer_reason() -> str:
    return CLAIM_LAYER_BLOCK_REASON
