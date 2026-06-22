from __future__ import annotations

from typing import Any

CLAIM_SAFETY = "EVIDENCE_ONLY"


def detect_metric_contradictions(values: dict[str, float]) -> list[dict[str, Any]]:
    """Detect claim-safe metric contradiction/context findings.

    V1 thresholds are uncalibrated heuristics. Findings lower confidence or require
    context; they do not produce report-ready football claims.
    """
    findings: list[dict[str, Any]] = []

    shots = values.get("M_SHOT_COUNT")
    box_actions = values.get("M_ACTIONS_IN_BOX_COUNT")
    if shots is not None and box_actions is not None:
        if shots >= 15 and box_actions <= 5:
            findings.append({
                "rule_id": "R_SHOT_VOLUME_BOX_ACTION_CONTRADICTION",
                "relation": "CONTRADICTS",
                "metrics": ["M_SHOT_COUNT", "M_ACTIONS_IN_BOX_COUNT"],
                "message": "Shot volume is weakly supported by box-action evidence.",
                "claim_effect": "LOWER_CONFIDENCE",
                "claim_safety": CLAIM_SAFETY,
            })

    progression = values.get("M_PROG_PASS_COUNT")
    turnovers = values.get("M_TURNOVER_COUNT")
    if progression is not None and turnovers is not None:
        if progression >= 30 and turnovers >= 25:
            findings.append({
                "rule_id": "R_RISKY_PROGRESSION_CONTEXT",
                "relation": "CONTEXTUALIZES",
                "metrics": ["M_PROG_PASS_COUNT", "M_TURNOVER_COUNT"],
                "message": "Progression volume exists but turnover exposure is elevated.",
                "claim_effect": "REQUIRE_CONTEXT",
                "claim_safety": CLAIM_SAFETY,
            })

    passes = values.get("M_PASS_COUNT")
    sequence_length = values.get("M_SEQUENCE_LENGTH")
    low_value_loop = values.get("M_LOW_VALUE_LOOP_FRACTION")
    if passes is not None and sequence_length is not None and low_value_loop is not None:
        if passes >= 400 and sequence_length >= 8 and low_value_loop >= 0.60:
            findings.append({
                "rule_id": "R_STERILE_CIRCULATION_CONTEXT",
                "relation": "CONTEXTUALIZES",
                "metrics": ["M_PASS_COUNT", "M_SEQUENCE_LENGTH", "M_LOW_VALUE_LOOP_FRACTION"],
                "message": "Possession volume requires low-value loop context before any control claim.",
                "claim_effect": "BLOCK_CONTROL_LANGUAGE",
                "claim_safety": CLAIM_SAFETY,
            })

    return findings
