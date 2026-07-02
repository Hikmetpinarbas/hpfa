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
        records.append(
            {
                "source_column": column,
                "normalized_column": normalize_column(column),
                "inferred_type": infer_type(values),
                "canonical_key": None,
                "semantic_family": "unknown",
                "mapping_status": "UNKNOWN",
                "evidence_refs": [f"surface_column:{column}"],
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
            record for record in records if record.get("mapping_status") != "HIT"
        ],
        "mapping_coverage": build_mapping_coverage(records),
    }
