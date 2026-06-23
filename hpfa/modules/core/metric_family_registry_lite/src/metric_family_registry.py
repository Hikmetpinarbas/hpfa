from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "metric_family_registry_lite_v1"
CLAIM_SAFETY = "METRIC_FAMILY_REGISTRY_ONLY"
OUTPUT_JSON = "metric_family_registry_lite_v1.json"
OUTPUT_TXT = "metric_family_registry_lite_v1.txt"

FAMILIES = [
    "PROGRESSION_FAMILY",
    "FINAL_THIRD_ACCESS_FAMILY",
    "BOX_ACCESS_FAMILY",
    "SHOT_THREAT_FAMILY",
    "POSSESSION_SUPPORT_FAMILY",
    "BALL_RETENTION_FAMILY",
    "PRESSURE_DUEL_FAMILY",
    "RECOVERY_DEFENSIVE_ACTION_FAMILY",
    "GOALKEEPER_RESTART_FAMILY",
    "PHYSICAL_COST_FAMILY",
    "REPORT_CONTEXT_FAMILY",
    "EFFICIENCY_FAMILY",
    "FUSION_READINESS_FAMILY",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def primary_unresolved(primary: dict[str, Any]) -> bool:
    return primary.get("primary_event_surface_candidate") in (None, "", "UNRESOLVED") or primary.get("decision") == "UNRESOLVED_REVIEW_REQUIRED"


def record(metric_family: str, metric_name: str, source_surface_class: str, source_module: str, status: str, gates: list[str]) -> dict[str, Any]:
    return {
        "metric_family": metric_family,
        "metric_name": metric_name,
        "source_surface_class": source_surface_class,
        "source_module": source_module,
        "required_upstream_gates": gates,
        "calculation_status": status,
        "claim_safety": "REGISTRY_ONLY_NO_METRIC_VALUE",
        "allowed_language": [
            "metric family registered",
            "metric candidate requires gate validation",
        ],
        "blocked_language_families": [
            "metric_value_as_validated_performance_truth",
            "metric_family_as_tactical_truth",
            "physical_cost_value_as_event_count",
            "efficiency_candidate_as_causality",
        ],
    }


def build_registry(out_dir: str | Path) -> dict[str, Any]:
    root = Path(out_dir).expanduser().resolve(strict=False)
    canonical = read_json(root / "canonical_event_lite_audit_v1.json")
    primary = read_json(root / "primary_event_surface_gate_lite_v1.json")
    physical = read_json(root / "physical_cost_surface_audit_v1.json")
    identity = read_json(root / "event_identity_resolution_gate_lite_v1.json")

    is_primary_unresolved = primary_unresolved(primary)
    event_status = "WAIT_PRIMARY_SURFACE_REVIEW" if is_primary_unresolved else "READY_FOR_CANDIDATE_CALCULATION"
    temporal_needed = "WAIT_TEMPORAL_BINDING"
    records: list[dict[str, Any]] = []

    progression_metrics = [
        "progressive_pass_surface_candidate",
        "progressive_carry_surface_candidate",
        "forward_coordinate_delta_candidate",
        "zone_advancement_candidate",
        "channel_advancement_candidate",
    ]
    for name in progression_metrics:
        records.append(record("PROGRESSION_FAMILY", name, "EVENT_SURFACE", "canonical_event_lite", event_status, ["primary surface review resolution", "claim router"]))

    for family, names in {
        "FINAL_THIRD_ACCESS_FAMILY": ["final_third_entry_candidate", "final_third_volume_candidate"],
        "BOX_ACCESS_FAMILY": ["box_entry_candidate", "box_touch_surface_candidate"],
        "SHOT_THREAT_FAMILY": ["shot_surface_candidate", "shot_zone_candidate"],
        "PRESSURE_DUEL_FAMILY": ["duel_pressure_surface_candidate"],
        "RECOVERY_DEFENSIVE_ACTION_FAMILY": ["recovery_surface_candidate", "defensive_action_surface_candidate"],
        "GOALKEEPER_RESTART_FAMILY": ["goalkeeper_restart_surface_candidate"],
    }.items():
        for name in names:
            records.append(record(family, name, "EVENT_SURFACE", "canonical_event_lite", event_status, ["primary surface review resolution", "claim router"]))

    physical_counts = physical.get("metric_family_counts") or {}
    if physical_counts:
        for name in sorted(physical_counts.keys()):
            records.append(record("PHYSICAL_COST_FAMILY", name, "PHYSICAL_COST_SURFACE", "event_physical_cost_surface_lite", "READY_FOR_CANDIDATE_CALCULATION", ["physical cost surface", "claim router"]))
    else:
        records.append(record("PHYSICAL_COST_FAMILY", "physical_cost_metric_family_pending", "PHYSICAL_COST_SURFACE", "event_physical_cost_surface_lite", "WAIT_PHYSICAL_COST_BINDING", ["physical cost surface"]))

    for name in ["report_context_candidate", "official_metric_context_candidate"]:
        records.append(record("REPORT_CONTEXT_FAMILY", name, "REPORT_METRIC_SURFACE", "event_physical_cost_surface_lite", "REGISTRY_ONLY", ["claim router"]))

    efficiency_names = [
        "progression_per_physical_cost_candidate",
        "shot_threat_per_physical_cost_candidate",
        "box_access_per_physical_cost_candidate",
        "recovery_per_physical_cost_candidate",
    ]
    for name in efficiency_names:
        records.append(record("EFFICIENCY_FAMILY", name, "FUSION_SURFACE_CANDIDATE", "metric_family_registry_lite", "WAIT_PRIMARY_SURFACE_REVIEW" if is_primary_unresolved else temporal_needed, ["event metric family", "physical cost family", "time binding", "claim router"]))

    records.append(record("FUSION_READINESS_FAMILY", "event_utility_cost_fusion_readiness", "FUSION_SURFACE_CANDIDATE", "metric_family_registry_lite", "WAIT_PRIMARY_SURFACE_REVIEW" if is_primary_unresolved else "WAIT_TEMPORAL_BINDING", ["primary surface review resolution", "time binding", "claim router"]))

    family_counts: dict[str, int] = {}
    for item in records:
        family_counts[item["metric_family"]] = family_counts.get(item["metric_family"], 0) + 1

    return {
        "module_id": MODULE_ID,
        "status": "PASS",
        "claim_safety": CLAIM_SAFETY,
        "registry_record_count": len(records),
        "family_counts": family_counts,
        "primary_surface_state": {
            "available": bool(primary),
            "decision": primary.get("decision"),
            "primary_event_surface_candidate": primary.get("primary_event_surface_candidate"),
            "top_candidate_for_review": primary.get("top_candidate_for_review"),
        },
        "identity_state": {
            "available": bool(identity),
            "candidate_cluster_count": identity.get("candidate_cluster_count"),
            "metric_count_allowed": identity.get("metric_count_allowed"),
        },
        "physical_cost_state": {
            "available": bool(physical),
            "record_count": physical.get("record_count"),
            "surface_counts": physical.get("surface_counts"),
        },
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "metric_value_output_allowed": False,
        "efficiency_calculation_allowed": False,
        "registry_records": records,
        "blocked_language_families": [
            "metric_value_as_validated_performance_truth",
            "metric_family_as_tactical_truth",
            "physical_cost_value_as_event_count",
            "efficiency_candidate_as_causality",
        ],
        "required_next_gates": [
            "primary surface review resolution",
            "time binding",
            "metric primitive contract",
            "claim router",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA METRIC FAMILY REGISTRY LITE V1",
        "===================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"registry_record_count={report.get('registry_record_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"metric_value_output_allowed={report.get('metric_value_output_allowed')}",
        f"efficiency_calculation_allowed={report.get('efficiency_calculation_allowed')}",
        "",
        "[family_counts]",
    ]
    for key, value in sorted((report.get("family_counts") or {}).items()):
        lines.append(f"{key}={value}")
    lines.extend(["", "[primary_surface_state]", json.dumps(report.get("primary_surface_state", {}), ensure_ascii=False, sort_keys=True), "", "[registry_records]"])
    for row in report.get("registry_records", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_language_families]"])
    for item in report.get("blocked_language_families", []):
        lines.append(f"- {item}")
    lines.extend(["", "[required_next_gates]"])
    for item in report.get("required_next_gates", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_registry(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
