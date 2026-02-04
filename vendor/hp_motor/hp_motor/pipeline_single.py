from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hp_motor.ingestion.loaders import load_events
from hp_motor.ingestion.normalizers import normalize_events
from hp_motor.library import library_health
from hp_motor.segmentation.set_piece_state import tag_set_piece_state
from hp_motor.segmentation.phase_tagger import tag_phases
from hp_motor.segmentation.possessions import segment_possessions
from hp_motor.segmentation.sequences import segment_sequences
from hp_motor.metrics.factory import compute_raw_metrics
from hp_motor.metrics.validator import validate_metrics
from hp_motor.context.engine import apply_context
from hp_motor.report.generator import generate_report
from hp_motor.report.schema import validate_report


REQUIRED_EVENT_COLUMNS = [
    "match_id",
    "team_id",
    "period",
    "minute",
    "second",
    "event_type",
]


def _popper(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not events:
        return {"status": "BLOCKED", "hard_errors": ["events_table_missing_or_empty"], "flags": []}

    for e in events[:50]:
        sot = str(e.get("sot", "")).upper().strip()
        if sot in {"ERROR", "BROKEN"}:
            return {"status": "BLOCKED", "hard_errors": [f"sot_hard_block:{sot}"], "flags": []}

    missing = [c for c in REQUIRED_EVENT_COLUMNS if all(c not in ev for ev in events)]
    if missing:
        return {"status": "BLOCKED", "hard_errors": [f"missing_required_columns:{missing}"], "flags": []}

    return {"status": "OK", "hard_errors": [], "flags": []}


def run_pipeline(events_path: Path, vendor: str = "generic") -> Dict[str, Any]:
    raw_events = load_events(events_path)
    pop = _popper(raw_events)
    lib_h = library_health()

    if pop["status"] == "BLOCKED":
        report = generate_report(
            popper_status="BLOCKED",
            hard_errors=pop["hard_errors"],
            flags=[],
            events_summary={"n_events": len(raw_events)},
            metrics_raw={},
            metrics_adjusted={},
            context_flags=["library:" + lib_h.status] + lib_h.flags,
        )
        validate_report(report)
        return report

    events = normalize_events(raw_events, vendor=vendor)
    events = tag_set_piece_state(events)
    events = tag_phases(events)

    possessions = segment_possessions(events)
    sequences = segment_sequences(events, possessions)

    # RAW metrics
    metrics_raw = compute_raw_metrics(events)
    metrics_raw.setdefault("meta", {})
    metrics_raw["meta"].update(
        {
            "segmentation": {
                "n_possessions": len(possessions),
                "n_sequences": len(sequences),
            }
        }
    )

    # VALIDATION
    validated_raw, validation_flags = validate_metrics(
        metrics_raw=metrics_raw,
        events_meta={"columns_present": metrics_raw["meta"].get("columns_present", [])},
    )

    # CONTEXT (identity v0)
    metrics_adj, ctx_flags = apply_context(validated_raw)

    context_flags = (
        ["library:" + lib_h.status]
        + lib_h.flags
        + validation_flags
        + ctx_flags
    )

    report = generate_report(
        popper_status=pop["status"],
        hard_errors=[],
        flags=[],
        events_summary={
            "n_events": len(events),
            "n_possessions": len(possessions),
            "n_sequences": len(sequences),
        },
        metrics_raw=validated_raw,
        metrics_adjusted=metrics_adj,
        context_flags=context_flags,
    )
    validate_report(report)
    return report
