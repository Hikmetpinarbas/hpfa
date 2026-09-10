from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
PRODUCTION_RELEASE = False

REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}

MAPPED_MAPPING_STATUSES = {
    "EXACT_REVIEWED_CANDIDATE",
    "PREFIX_RULE_REVIEWED_CANDIDATE",
    "EXACT_ALIAS_CANDIDATE",
}


def _volume(row: dict[str, Any]) -> int:
    value = row.get("surface_row_volume")
    return int(value) if isinstance(value, int) and value >= 0 else 0


def _format_audit(rows: list[dict[str, Any]], source_format: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("source_format") == source_format]
    volume_known = [row for row in selected if isinstance(row.get("surface_row_volume"), int)]
    surface_volume = sum(_volume(row) for row in volume_known)
    mapped_volume = sum(
        _volume(row)
        for row in volume_known
        if row.get("mapping_status") in MAPPED_MAPPING_STATUSES
    )
    review_volume = sum(
        _volume(row)
        for row in volume_known
        if row.get("mapping_status") in REVIEW_MAPPING_STATUSES
    )
    aggregate_only_volume = sum(
        _volume(row)
        for row in volume_known
        if row.get("downstream_eligibility") == "AGGREGATE_ONLY"
    )
    role_volume: dict[str, int] = defaultdict(int)
    for row in volume_known:
        role_volume[str(row.get("semantic_role_candidate") or "UNRESOLVED")] += _volume(row)

    return {
        "source_format": source_format,
        "label_record_count": len(selected),
        "volume_known_record_count": len(volume_known),
        "surface_label_volume": surface_volume,
        "mapped_semantic_label_volume": mapped_volume,
        "review_required_label_volume": review_volume,
        "aggregate_only_label_volume": aggregate_only_volume,
        "mapped_semantic_label_volume_ratio": (
            mapped_volume / surface_volume if surface_volume else None
        ),
        "semantic_role_label_volume": dict(sorted(role_volume.items())),
        "mapping_status_counts": dict(
            sorted(Counter(str(row.get("mapping_status") or "UNKNOWN") for row in selected).items())
        ),
        "claim_ceiling": "FORMAT_LOCAL_PROVIDER_LABEL_UTILIZATION_AUDIT_ONLY",
    }


def build_provider_semantic_utilization_audit(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("provider_label_records") or []
    if not isinstance(rows, list):
        rows = []

    csv = _format_audit(rows, "csv")
    xml = _format_audit(rows, "xml")
    xlsx = _format_audit(rows, "xlsx")

    return {
        "module_id": "provider_semantic_utilization_audit_v1",
        "status": "PASS",
        "decision": "AUDIT_PROVIDER_LABEL_SEMANTIC_UTILIZATION",
        "csv": csv,
        "xml": xml,
        "xlsx": xlsx,
        "csv_xml_combined_surface_label_volume": (
            csv["surface_label_volume"] + xml["surface_label_volume"]
        ),
        "csv_xml_combined_is_independent_evidence_count": False,
        "cross_format_volume_must_not_be_interpreted_as_action_count": True,
        "does_measure": [
            "format_local_visible_provider_label_volume",
            "format_local_semantic_mapping_utilization",
            "format_local_review_required_volume",
            "format_local_semantic_role_volume",
        ],
        "does_not_measure": [
            "canonical_event_count",
            "true_action_count",
            "independent_evidence_count",
            "episode_utilization",
            "process_utilization",
            "metric_utilization",
            "finding_utilization",
            "tactical_truth",
        ],
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": PRODUCTION_RELEASE,
    }
