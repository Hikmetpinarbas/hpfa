from __future__ import annotations
from typing import Any, Dict

REQUIRED_TOP_KEYS = ["hp_motor_version","ontology_version","popper","events_summary","metrics_raw","metrics_adjusted","context_flags","output_standard"]

def validate_report(report: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_TOP_KEYS if k not in report]
    if missing:
        raise ValueError(f"Report schema missing keys: {missing}")
    if "status" not in report.get("popper", {}):
        raise ValueError("Report schema: popper.status missing")
