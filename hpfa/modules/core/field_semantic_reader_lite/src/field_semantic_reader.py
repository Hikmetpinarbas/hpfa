from __future__ import annotations

from typing import Any


SEMANTIC_FAMILIES = {
    "event",
    "actor",
    "time",
    "space",
    "action",
    "outcome",
    "context",
    "metric",
    "support",
    "unknown",
}

MAPPING_STATUSES = {"HIT", "MISS", "WEAK", "AMBIGUOUS", "UNKNOWN"}

FIELD_HINTS = {
    "period": ("time", "READY", ["sequence", "context"]),
    "half": ("time", "READY", ["sequence", "context"]),
    "minute": ("time", "READY", ["temporal", "context"]),
    "second": ("time", "READY", ["temporal", "context"]),
    "timestamp": ("time", "READY", ["temporal", "context"]),
    "time": ("time", "READY_WITH_PROXY", ["temporal", "context"]),
    "team": ("actor", "READY", ["team_binding"]),
    "team_id": ("actor", "READY", ["team_binding"]),
    "player": ("actor", "READY", ["player_surface"]),
    "player_id": ("actor", "READY", ["player_surface"]),
    "action": ("action", "READY", ["action_family", "audit"]),
    "event_type": ("action", "READY", ["action_family", "audit"]),
    "outcome": ("outcome", "READY", ["consequence", "audit"]),
    "x": ("space", "READY_WITH_PROXY", ["spatial", "feature"]),
    "y": ("space", "READY_WITH_PROXY", ["spatial", "feature"]),
    "start_x": ("space", "READY", ["spatial", "feature"]),
    "start_y": ("space", "READY", ["spatial", "feature"]),
    "end_x": ("space", "READY", ["spatial", "feature"]),
    "end_y": ("space", "READY", ["spatial", "feature"]),
    "source_file": ("support", "READY", ["audit"]),
    "provider": ("support", "READY_WITH_PROXY", ["audit"]),
}


def normalize_column(name: Any) -> str:
    return str(name or "").strip().lower().replace(" ", "_")


def infer_type(values: list[Any]) -> str:
    sample = [value for value in values if value not in (None, "")]
    if not sample:
        return "unknown"

    lowered = [str(value).strip().lower() for value in sample]
    bool_tokens = {"true", "false", "yes", "no", "0", "1"}
    if all(value in bool_tokens for value in lowered):
        return "bool"

    try:
        for value in sample:
            float(value)
        return "number"
    except Exception:
        return "string"


def classify_field(normalized_column: str) -> dict[str, Any]:
    family, state, modules = FIELD_HINTS.get(normalized_column, ("unknown", "REVIEW_REQUIRED", ["audit"]))
    return {
        "semantic_family": family,
        "decision_state_seed": state,
        "required_for_modules": modules,
        "missingness_status": "PRESENT",
        "authority_status": "SURFACE_ONLY",
        "downstream_fail_action": "AUDIT_ONLY" if family == "unknown" else "ALLOW_CANDIDATE",
        "claim_boundary": "surface_candidate",
    }


def build_field_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for column in row.keys():
            if column not in seen:
                seen.add(column)
                columns.append(column)

    records: list[dict[str, Any]] = []

    for column in columns:
        values = [row.get(column) for row in rows]
        normalized = normalize_column(column)
        field_class = classify_field(normalized)
        records.append(
            {
                "source_column": column,
                "normalized_column": normalized,
                "inferred_type": infer_type(values),
                "canonical_key": None,
                "semantic_family": field_class["semantic_family"],
                "mapping_status": "UNKNOWN",
                "evidence_refs": [f"surface_column:{column}"],
                "required_for_modules": field_class["required_for_modules"],
                "missingness_status": field_class["missingness_status"],
                "authority_status": field_class["authority_status"],
                "downstream_fail_action": field_class["downstream_fail_action"],
                "claim_boundary": field_class["claim_boundary"],
                "decision_state_seed": field_class["decision_state_seed"],
            }
        )

    return records


def build_mapping_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    mapped = sum(1 for record in records if record.get("mapping_status") == "HIT")
    unmapped = total - mapped

    return {
        "mapped_fields": mapped,
        "unmapped_fields": unmapped,
        "coverage_ratio": mapped / total if total else 0.0,
    }


def build_surface(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = build_field_records(rows)

    return {
        "module_id": "field_semantic_reader_lite_v1",
        "status": "REVIEW_REQUIRED",
        "surface_inventory": {
            "surface_row_count": len(rows),
            "surface_column_count": len(records),
            "canonical_event_count": "UNKNOWN",
        },
        "field_semantic_records": records,
        "row_semantic_nuclei": [],
        "unmapped_field_candidates": [
            record for record in records if record.get("semantic_family") == "unknown"
        ],
        "mapping_coverage": build_mapping_coverage(records),
    }
