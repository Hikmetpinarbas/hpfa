#!/usr/bin/env python3
"""
HPFA Gate Report Reader V1

Reads Data Quality Gate V1 reports and exposes safe downstream policy inputs.

Authority boundary:
- Does not create event truth.
- Does not validate football claims.
- Does not open claim layer.
- Only reads machine-readable gate_report.json produced by Data Quality Gate V1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


VALID_STATUSES = {"PASS", "DEGRADED", "FAIL_CLOSED"}
REQUIRED_TOP_LEVEL_FIELDS = {
    "tool",
    "status",
    "input",
    "input_format",
    "row_count",
    "valid_row_count",
    "claim_safety",
    "authority_note",
    "next_action",
    "findings",
}


class GateReportError(ValueError):
    """Raised when a gate report is missing or structurally invalid."""


def load_gate_report(path: str | Path) -> Dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        raise GateReportError(f"Gate report not found: {report_path}")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateReportError(f"Gate report is not valid JSON: {report_path}") from exc

    validate_gate_report(report)
    return report


def validate_gate_report(report: Dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(report.keys()))
    if missing:
        raise GateReportError(f"Gate report missing required fields: {missing}")

    status = report.get("status")
    if status not in VALID_STATUSES:
        raise GateReportError(f"Invalid gate status: {status}")

    if report.get("claim_safety") != "NO_FOOTBALL_CLAIMS_EMITTED":
        raise GateReportError("Invalid claim_safety value; downstream must fail closed.")

    next_action = report.get("next_action")
    if not isinstance(next_action, dict):
        raise GateReportError("next_action must be an object.")

    for key in ("phase_sequence_allowed", "metric_layer_allowed", "claim_layer_allowed", "reason"):
        if key not in next_action:
            raise GateReportError(f"next_action missing required field: {key}")

    findings = report.get("findings")
    if not isinstance(findings, list) or not findings:
        raise GateReportError("findings must be a non-empty list.")


def get_gate_status(report: Dict[str, Any]) -> str:
    validate_gate_report(report)
    return str(report["status"])


def get_next_action(report: Dict[str, Any]) -> Dict[str, Any]:
    validate_gate_report(report)
    return dict(report["next_action"])


def get_failed_gates(report: Dict[str, Any]) -> List[str]:
    validate_gate_report(report)
    return [
        str(f.get("gate_id"))
        for f in report["findings"]
        if f.get("status") == "FAIL_CLOSED"
    ]


def get_degraded_reasons(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    validate_gate_report(report)
    return [
        {
            "gate_id": f.get("gate_id"),
            "message": f.get("message"),
            "evidence": f.get("evidence", {}),
        }
        for f in report["findings"]
        if f.get("status") == "DEGRADED"
    ]
