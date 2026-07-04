from __future__ import annotations

from typing import Any

MODULE_ID = "canonical_mapping_report_lite_v1"
REQUIRED_SEMANTIC_FIELDS = {"event.action", "event.team", "event.minute"}


def build_report(field_surface: dict[str, Any], provider_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    records = field_surface.get("field_semantic_records", []) or []
    provider_records = (provider_registry or {}).get("records", []) or []
    alias_by_normalized = {
        record.get("normalized_alias"): record
        for record in provider_records
        if isinstance(record, dict)
    }

    mapping_records: list[dict[str, Any]] = []
    mapped_keys: set[str] = set()
    preserved_unmapped: list[dict[str, Any]] = []

    for record in records:
        normalized = record.get("normalized_column")
        alias = alias_by_normalized.get(normalized)
        canonical_key = alias.get("canonical_key_candidate") if alias else record.get("canonical_key")
        status = "CANDIDATE_HIT" if canonical_key else "UNMAPPED_PRESERVED"
        if canonical_key:
            mapped_keys.add(str(canonical_key))
        mapping_record = {
            "source_column": record.get("source_column"),
            "normalized_column": normalized,
            "semantic_family": record.get("semantic_family", "unknown"),
            "canonical_key_candidate": canonical_key,
            "mapping_status": status,
            "rule_id": alias.get("rule_id") if alias else None,
            "alias_reliability": alias.get("alias_reliability") if alias else "UNKNOWN",
            "runtime_verified": False,
            "claim_boundary": "canonical_mapping_candidate_not_truth",
        }
        mapping_records.append(mapping_record)
        if status == "UNMAPPED_PRESERVED":
            preserved_unmapped.append(mapping_record)

    missing_required = sorted(REQUIRED_SEMANTIC_FIELDS - mapped_keys)

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if missing_required or preserved_unmapped else "SMOKE_PASS",
        "runtime_verified": False,
        "surface_inventory": {
            "surface_field_count": len(records),
            "canonical_event_count": "UNKNOWN",
        },
        "mapping_records": mapping_records,
        "mapped_field_count": len(mapped_keys),
        "unmapped_preserved_count": len(preserved_unmapped),
        "missing_required_fields": missing_required,
        "preserved_unmapped_fields": preserved_unmapped,
        "claim_boundary": "mapping_report_only",
    }
