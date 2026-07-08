from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

FEATURE_SRC = Path(__file__).resolve().parents[2] / "feature_primitive_builder_lite" / "src"
if FEATURE_SRC.exists() and str(FEATURE_SRC) not in sys.path:
    sys.path.insert(0, str(FEATURE_SRC))

try:
    from feature_primitive_registry_loader import load_registry as load_feature_primitive_registry
except Exception:  # pragma: no cover - callers may inject upstream report
    load_feature_primitive_registry = None  # type: ignore[assignment]

MODULE_ID = "metric_candidate_governance_validator_lite_v1"
CLAIM_SAFETY = "METRIC_CANDIDATE_GOVERNANCE_ONLY"
OUTPUT_JSON = "metric_candidate_governance_lite_v1.json"
CLAIM_BOUNDARY = "metric_candidate_governance_only_no_metric_value_no_feature_value_no_claim"

ALLOWED_METRIC_FAMILIES = {
    "action_volume_surface",
    "territory_surface",
    "progression_surface",
    "sequence_surface",
    "risk_loss_surface",
    "density_surface",
    "restart_surface",
    "terminal_surface",
}

INITIAL_METRIC_CANDIDATES: list[dict[str, Any]] = [
    {
        "metric_id": "action_family_volume_candidate",
        "metric_family": "action_volume_surface",
        "requires_feature_primitives": ["action_family_count"],
        "claim_ceiling": "surface_volume_candidate_not_quality_truth",
        "report_consumers": ["active_match_analyst_report_lite"],
    },
    {
        "metric_id": "zone_entry_surface_candidate",
        "metric_family": "territory_surface",
        "requires_feature_primitives": ["zone_entry_count"],
        "claim_ceiling": "zone_surface_candidate_not_control_truth",
        "report_consumers": ["active_match_analyst_report_lite"],
    },
    {
        "metric_id": "final_third_entry_surface_candidate",
        "metric_family": "progression_surface",
        "requires_feature_primitives": ["final_third_entry"],
        "claim_ceiling": "territory_entry_proxy_not_dominance",
        "report_consumers": ["active_match_analyst_report_lite", "progression_report"],
    },
    {
        "metric_id": "box_entry_surface_candidate",
        "metric_family": "progression_surface",
        "requires_feature_primitives": ["box_entry"],
        "claim_ceiling": "box_entry_proxy_not_control",
        "report_consumers": ["active_match_analyst_report_lite", "progression_report"],
    },
    {
        "metric_id": "sequence_length_candidate",
        "metric_family": "sequence_surface",
        "requires_feature_primitives": ["sequence_length"],
        "claim_ceiling": "sequence_candidate_only_not_tactical_intent",
        "report_consumers": ["sequence_feature_bridge_lite"],
    },
    {
        "metric_id": "sequence_duration_candidate",
        "metric_family": "sequence_surface",
        "requires_feature_primitives": ["sequence_duration"],
        "claim_ceiling": "sequence_duration_candidate_only_not_causality",
        "report_consumers": ["sequence_feature_bridge_lite"],
    },
    {
        "metric_id": "loss_surface_exposure_candidate",
        "metric_family": "risk_loss_surface",
        "requires_feature_primitives": ["loss_severity"],
        "claim_ceiling": "loss_consequence_proxy_not_player_error",
        "report_consumers": ["active_match_analyst_report_lite", "risk_loss_report"],
    },
    {
        "metric_id": "turnover_surface_exposure_candidate",
        "metric_family": "risk_loss_surface",
        "requires_feature_primitives": ["turnover_exposure"],
        "claim_ceiling": "turnover_exposure_candidate_not_causality",
        "report_consumers": ["active_match_analyst_report_lite", "risk_loss_report"],
    },
    {
        "metric_id": "event_density_surface_candidate",
        "metric_family": "density_surface",
        "requires_feature_primitives": ["event_density_window"],
        "claim_ceiling": "density_candidate_not_momentum_truth",
        "report_consumers": ["rhythm_support_signal_adapter_lite", "active_match_analyst_report_lite"],
    },
    {
        "metric_id": "restart_surface_volume_candidate",
        "metric_family": "restart_surface",
        "requires_feature_primitives": ["restart_surface_count"],
        "claim_ceiling": "restart_surface_candidate_only",
        "report_consumers": ["active_match_analyst_report_lite", "sequence_feature_bridge_lite"],
    },
    {
        "metric_id": "terminal_action_surface_candidate",
        "metric_family": "terminal_surface",
        "requires_feature_primitives": ["terminal_action_count"],
        "claim_ceiling": "terminal_surface_candidate_only",
        "report_consumers": ["active_match_analyst_report_lite", "sequence_feature_bridge_lite"],
    },
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _feature_registry_report(upstream_report: dict[str, Any] | None) -> dict[str, Any]:
    if upstream_report is not None:
        return upstream_report
    if load_feature_primitive_registry is None:
        return {"module_id": "feature_primitive_registry_loader_lite_v1", "registry_records": []}
    return load_feature_primitive_registry()


def _available_feature_ids(feature_registry: dict[str, Any]) -> set[str]:
    records = feature_registry.get("registry_records") or []
    return {
        str(record.get("feature_id", "")).strip()
        for record in records
        if isinstance(record, dict) and str(record.get("feature_id", "")).strip()
    }


def validate_metric_candidate(
    record: dict[str, Any],
    seen: set[str],
    available_features: set[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = []
    metric_id = str(record.get("metric_id", "")).strip()
    if not metric_id:
        gaps.append({"metric_id": None, "gap_type": "metric_id_missing", "severity": "FAIL_CLOSED"})
        return None, gaps
    if metric_id in seen:
        gaps.append({"metric_id": metric_id, "gap_type": "duplicate_metric_id", "severity": "FAIL_CLOSED"})
        return None, gaps
    seen.add(metric_id)

    metric_family = str(record.get("metric_family", "")).strip()
    required_features = [str(item).strip() for item in _as_list(record.get("requires_feature_primitives")) if str(item).strip()]
    missing_features = [feature_id for feature_id in required_features if feature_id not in available_features]

    if not metric_family:
        gaps.append({"metric_id": metric_id, "gap_type": "metric_family_missing", "severity": "BLOCKED"})
    elif metric_family not in ALLOWED_METRIC_FAMILIES:
        gaps.append({"metric_id": metric_id, "gap_type": "unsupported_metric_family", "metric_family": metric_family, "severity": "BLOCKED"})
    if missing_features:
        gaps.append({"metric_id": metric_id, "gap_type": "required_feature_primitive_missing", "missing_feature_primitives": missing_features, "severity": "BLOCKED"})
    if not record.get("claim_ceiling"):
        gaps.append({"metric_id": metric_id, "gap_type": "claim_ceiling_missing", "severity": "BLOCKED"})
    if record.get("metric_value_output_allowed") is True:
        gaps.append({"metric_id": metric_id, "gap_type": "metric_value_output_requested", "severity": "FAIL_CLOSED"})
    if record.get("feature_value_output_allowed") is True:
        gaps.append({"metric_id": metric_id, "gap_type": "feature_value_output_requested", "severity": "FAIL_CLOSED"})
    if record.get("claim_output_allowed") is True:
        gaps.append({"metric_id": metric_id, "gap_type": "claim_output_requested", "severity": "FAIL_CLOSED"})
    if record.get("canonical_event_count") not in {None, "UNKNOWN"}:
        gaps.append({"metric_id": metric_id, "gap_type": "canonical_event_count_claimed", "severity": "FAIL_CLOSED"})

    readiness = "BLOCKED" if gaps else "READY_FOR_METRIC_BUILDER_CONTRACT"
    normalized = {
        "metric_id": metric_id,
        "metric_family": metric_family or "UNKNOWN_METRIC_FAMILY",
        "requires_feature_primitives": required_features,
        "report_consumers": [str(item).strip() for item in _as_list(record.get("report_consumers")) if str(item).strip()],
        "readiness": readiness,
        "claim_ceiling": str(record.get("claim_ceiling", "metric_candidate_registry_only_no_claim")),
        "claim_safety": "METRIC_CANDIDATE_ONLY_NO_VALUE_NO_CLAIM",
        "feature_value_output_allowed": False,
        "metric_value_output_allowed": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "allowed_language": [
            "metric candidate registered",
            "metric candidate requires governance validation",
            "metric candidate blocked by missing primitive",
            "metric candidate allowed for future builder contract",
        ],
        "blocked_language_families": [
            "metric_candidate_as_validated_performance_truth",
            "metric_candidate_as_tactical_truth",
            "density_metric_as_momentum_truth",
            "territory_metric_as_dominance_or_control",
            "sequence_metric_as_intent_or_causality",
        ],
    }
    return normalized, gaps


def build_dependency_graph(metric_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = sorted(record["metric_id"] for record in metric_candidates)
    edges: list[dict[str, str]] = []
    for record in metric_candidates:
        for feature_id in record.get("requires_feature_primitives", []):
            edges.append({"type": "requires_feature_primitive", "from": record["metric_id"], "to": str(feature_id)})
    return {"contract_id": "HPFA_METRIC_CANDIDATE_DEPENDENCY_GRAPH_V1", "nodes": nodes, "edges": edges}


def build_metric_candidate_governance(
    feature_registry_report: dict[str, Any] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    upstream = _feature_registry_report(feature_registry_report)
    available_features = _available_feature_ids(upstream)
    source_records = list(records if records is not None else INITIAL_METRIC_CANDIDATES)
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    governance_gaps: list[dict[str, Any]] = []

    upstream_checks = {
        "feature_value_output_allowed": "upstream_feature_value_output_requested",
        "metric_value_output_allowed": "upstream_metric_value_output_requested",
        "claim_output_allowed": "upstream_claim_output_requested",
    }
    for field, gap_type in upstream_checks.items():
        if upstream.get(field) is True:
            governance_gaps.append({"metric_id": None, "gap_type": gap_type, "severity": "FAIL_CLOSED"})
    if upstream.get("canonical_event_count") not in {None, "UNKNOWN"}:
        governance_gaps.append({"metric_id": None, "gap_type": "upstream_canonical_event_count_claimed", "severity": "FAIL_CLOSED"})

    for item in source_records:
        normalized, gaps = validate_metric_candidate(dict(item), seen, available_features)
        governance_gaps.extend(gaps)
        if normalized is not None:
            candidates.append(normalized)

    family_counts = dict(sorted(Counter(record["metric_family"] for record in candidates).items()))
    readiness_counts = dict(sorted(Counter(record["readiness"] for record in candidates).items()))
    fail_closed = any(gap.get("severity") == "FAIL_CLOSED" for gap in governance_gaps)
    blocked = any(gap.get("severity") == "BLOCKED" for gap in governance_gaps)

    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED" if fail_closed else "REVIEW_REQUIRED" if blocked else "SMOKE_PASS",
        "claim_safety": CLAIM_SAFETY,
        "metric_candidate_count": len(candidates),
        "family_counts": family_counts,
        "readiness_counts": readiness_counts,
        "governance_gaps": governance_gaps,
        "dependency_graph": build_dependency_graph(candidates),
        "feature_value_output_allowed": False,
        "metric_value_output_allowed": False,
        "claim_output_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "metric_candidates": candidates,
        "claim_boundary": CLAIM_BOUNDARY,
        "upstream_module_id": upstream.get("module_id"),
        "upstream_claim_safety": upstream.get("claim_safety"),
        "upstream_feature_registry_record_count": len(available_features),
        "hard_blocks": [
            "metric_id_missing",
            "duplicate_metric_id",
            "metric_family_missing",
            "required_feature_primitive_missing",
            "claim_ceiling_missing",
            "unsupported_metric_family",
            "metric_value_output_requested",
            "claim_output_requested",
            "canonical_event_count_claimed",
        ],
    }


def write_metric_candidate_governance(
    out_dir: str | Path,
    feature_registry_report: dict[str, Any] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(out_dir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    report = build_metric_candidate_governance(feature_registry_report=feature_registry_report, records=records)
    output = root / OUTPUT_JSON
    report["outputs"] = {"json": str(output)}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report
