from __future__ import annotations
from typing import Any, Dict, List

from hp_motor import __version__
from hp_motor.config_reader import read_spec
from hp_motor.synthesis.narrative import build_narrative


def generate_report(
    popper_status: str,
    hard_errors: List[str],
    flags: List[str],
    events_summary: Dict[str, Any],
    metrics_raw: Dict[str, Any],
    metrics_adjusted: Dict[str, Any],
    context_flags: List[str],
) -> Dict[str, Any]:
    spec = read_spec()
    ontology_version = spec.get("hp_motor", {}).get("ontology_version", "0.1.0")

    narrative = build_narrative(
        {
            "events_summary": events_summary,
            "metrics_raw": metrics_raw,
            "metrics_adjusted": metrics_adjusted,
            "context_flags": context_flags,
        }
    )

    return {
        "hp_motor_version": __version__,
        "ontology_version": ontology_version,
        "popper": {
            "status": popper_status,
            "hard_errors": hard_errors,
            "flags": flags,
        },
        "events_summary": events_summary,
        "metrics_raw": metrics_raw,
        "metrics_adjusted": metrics_adjusted,
        "context_flags": context_flags,
        "output_standard": narrative,
    }
