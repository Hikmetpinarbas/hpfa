from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "feature_primitive_registry_loader_lite_v1"
CLAIM_SAFETY = "FEATURE_PRIMITIVE_REGISTRY_ONLY"
OUTPUT_JSON = "feature_primitive_registry_lite_v1.json"

INITIAL_FEATURES: list[dict[str, Any]] = [
    {
        "feature_id": "action_family_count",
        "feature_family": "action_volume",
        "required_fields": ["action_family"],
        "required_context": [],
        "required_window_fields": ["action_family_counts"],
        "requires_features": [],
        "report_consumers": ["active_match_analyst_report_lite"],
        "claim_ceiling": "surface_count_candidate",
    },
    {
        "feature_id": "zone_entry_count",
        "feature_family": "territory_surface",
        "required_fields": ["zone_candidate"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["zone_counts"],
        "requires_features": [],
        "report_consumers": ["active_match_analyst_report_lite"],
        "claim_ceiling": "zone_surface_candidate",
    },
    {
        "feature_id": "final_third_entry",
        "feature_family": "progression_territory",
        "required_fields": ["zone_candidate", "x"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["zone_counts"],
        "requires_features": ["zone_entry_count"],
        "report_consumers": ["active_match_analyst_report_lite", "progression_report"],
        "claim_ceiling": "territory_entry_proxy_not_dominance",
    },
    {
        "feature_id": "box_entry",
        "feature_family": "progression_territory",
        "required_fields": ["x", "y"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["zone_counts", "channel_counts"],
        "requires_features": ["zone_entry_count"],
        "report_consumers": ["active_match_analyst_report_lite", "progression_report"],
        "claim_ceiling": "box_entry_proxy_not_control",
    },
    {
        "feature_id": "sequence_length",
        "feature_family": "sequence_surface",
        "required_fields": ["action_family"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["sequence_readiness"],
        "requires_features": ["action_family_count"],
        "report_consumers": ["sequence_feature_bridge_lite"],
        "claim_ceiling": "sequence_candidate_only",
    },
    {
        "feature_id": "sequence_duration",
        "feature_family": "sequence_surface",
        "required_fields": ["minute"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["sequence_readiness"],
        "requires_features": ["sequence_length"],
        "report_consumers": ["sequence_feature_bridge_lite"],
        "claim_ceiling": "sequence_duration_candidate_only",
    },
    {
        "feature_id": "loss_severity",
        "feature_family": "risk_loss_surface",
        "required_fields": ["action_family", "zone_candidate"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["loss_recovery_surface_present", "zone_counts"],
        "requires_features": ["zone_entry_count"],
        "report_consumers": ["active_match_analyst_report_lite", "risk_loss_report"],
        "claim_ceiling": "loss_consequence_proxy_not_player_error",
    },
    {
        "feature_id": "turnover_exposure",
        "feature_family": "risk_loss_surface",
        "required_fields": ["action_family", "team_label"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["loss_recovery_surface_present"],
        "requires_features": ["loss_severity"],
        "report_consumers": ["active_match_analyst_report_lite", "risk_loss_report"],
        "claim_ceiling": "turnover_exposure_candidate_not_causality",
    },
    {
        "feature_id": "event_density_window",
        "feature_family": "density_surface",
        "required_fields": ["action_family"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["context_density"],
        "requires_features": ["action_family_count"],
        "report_consumers": ["rhythm_support_signal_adapter_lite", "active_match_analyst_report_lite"],
        "claim_ceiling": "density_candidate_not_momentum_truth",
    },
    {
        "feature_id": "restart_surface_count",
        "feature_family": "restart_surface",
        "required_fields": ["action_family"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["restart_surface_present"],
        "requires_features": ["action_family_count"],
        "report_consumers": ["active_match_analyst_report_lite", "sequence_feature_bridge_lite"],
        "claim_ceiling": "restart_surface_candidate_only",
    },
    {
        "feature_id": "terminal_action_count",
        "feature_family": "terminal_surface",
        "required_fields": ["action_family"],
        "required_context": ["context_ordinal"],
        "required_window_fields": ["terminal_action_surface_present"],
        "requires_features": ["action_family_count"],
        "report_consumers": ["active_match_analyst_report_lite", "sequence_feature_bridge_lite"],
        "claim_ceiling": "terminal_surface_candidate_only",
    },
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def validate_record(record: dict[str, Any], seen: set[str]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = []
    feature_id = str(record.get("feature_id", "")).strip()
    if not feature_id:
        gaps.append({"feature_id": None, "gap_type": "MISSING_FEATURE_ID", "severity": "FAIL_CLOSED"})
        return None, gaps
    if feature_id in seen:
        gaps.append({"feature_id": feature_id, "gap_type": "DUPLICATE_FEATURE_ID", "severity": "FAIL_CLOSED"})
        return None, gaps
    seen.add(feature_id)

    required_fields = [str(item) for item in _as_list(record.get("required_fields")) if str(item).strip()]
    required_window_fields = [str(item) for item in _as_list(record.get("required_window_fields")) if str(item).strip()]
    missing = []
    if not record.get("feature_family"):
        missing.append("feature_family")
    if not required_fields and not required_window_fields:
        missing.append("required_fields_or_window_fields")
    if not record.get("claim_ceiling"):
        missing.append("claim_ceiling")
    if missing:
        gaps.append({"feature_id": feature_id, "gap_type": "MISSING_REQUIRED_REGISTRY_FIELDS", "missing": missing, "severity": "BLOCKED"})

    readiness_seed = "BLOCKED" if missing else "READY"
    normalized = {
        "feature_id": feature_id,
        "feature_family": str(record.get("feature_family", "UNKNOWN_FEATURE_FAMILY")),
        "required_fields": required_fields,
        "required_context": [str(item) for item in _as_list(record.get("required_context")) if str(item).strip()],
        "required_window_fields": required_window_fields,
        "requires_features": [str(item) for item in _as_list(record.get("requires_features")) if str(item).strip()],
        "report_consumers": [str(item) for item in _as_list(record.get("report_consumers")) if str(item).strip()],
        "readiness_seed": readiness_seed,
        "claim_ceiling": str(record.get("claim_ceiling", "registry_only_no_claim")),
        "claim_safety": "REGISTRY_ONLY_NO_FEATURE_VALUE",
        "feature_value_output_allowed": False,
        "claim_output_allowed": False,
        "allowed_language": ["feature primitive registered", "feature primitive requires readiness validation"],
        "blocked_language_families": [
            "feature_value_as_validated_performance_truth",
            "feature_primitive_as_tactical_truth",
            "density_candidate_as_momentum_truth",
            "territory_entry_as_dominance_or_control",
        ],
    }
    return normalized, gaps


def build_dependency_graph(records: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = sorted(record["feature_id"] for record in records)
    edges: list[dict[str, str]] = []
    for record in records:
        for dep in record.get("requires_features", []):
            edges.append({"type": "requires_feature", "from": record["feature_id"], "to": str(dep)})
    return {"contract_id": "HPFA_FEATURE_PRIMITIVE_DEPENDENCY_GRAPH_V1", "nodes": nodes, "edges": edges}


def load_registry(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source_records = list(records if records is not None else INITIAL_FEATURES)
    seen: set[str] = set()
    registry_records: list[dict[str, Any]] = []
    registry_gaps: list[dict[str, Any]] = []

    for item in source_records:
        normalized, gaps = validate_record(dict(item), seen)
        registry_gaps.extend(gaps)
        if normalized is not None:
            registry_records.append(normalized)

    family_counts = dict(sorted(Counter(record["feature_family"] for record in registry_records).items()))
    readiness_seed_counts = dict(sorted(Counter(record["readiness_seed"] for record in registry_records).items()))
    fail_closed = any(gap.get("severity") == "FAIL_CLOSED" for gap in registry_gaps)
    blocked = any(gap.get("severity") == "BLOCKED" for gap in registry_gaps)

    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED" if fail_closed else "REVIEW_REQUIRED" if blocked else "SMOKE_PASS",
        "claim_safety": CLAIM_SAFETY,
        "registry_record_count": len(registry_records),
        "family_counts": family_counts,
        "readiness_seed_counts": readiness_seed_counts,
        "registry_gaps": registry_gaps,
        "dependency_graph": build_dependency_graph(registry_records),
        "feature_value_output_allowed": False,
        "metric_value_output_allowed": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "registry_records": registry_records,
        "claim_boundary": "feature_primitive_registry_only_no_feature_value_no_claim",
        "release_status": "SMOKE_PASS" if not registry_gaps else "REVIEW_REQUIRED",
    }


def write_registry(out_dir: str | Path, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    root = Path(out_dir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    report = load_registry(records)
    output = root / OUTPUT_JSON
    report["outputs"] = {"json": str(output)}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report
