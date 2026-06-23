from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "surface_inventory_interpretation_gate_lite_v1"
CLAIM_SAFETY = "ANALYST_SAFE_SURFACE_COUNT_LANGUAGE_ONLY"
OUTPUT_JSON = "surface_inventory_interpretation_gate_lite_v1.json"
OUTPUT_TXT = "surface_inventory_interpretation_gate_lite_v1.txt"

COUNT_RISK_FLAGS = [
    "large_surface_inventory_count",
    "multi_surface_overlap_risk",
    "primary_event_surface_unresolved",
    "deduplicated_event_count_unknown",
    "event_count_claim_not_allowed",
    "pattern_structure_not_yet_built",
]

BLOCKED_LANGUAGE_FAMILIES = [
    "event_total_language",
    "validated_stream_language",
    "row_count_to_team_state_language",
    "row_count_to_pattern_truth_language",
    "row_count_to_phase_or_possession_language",
]


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}:{exc}", "path": str(path)}


def build_gate(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    p2 = read_json(root / "canonical_event_lite_audit_v1.json")
    p3 = read_json(root / "team_binding_lite_audit_v1.json")
    bridge = read_json(root / "fitness_tactical_bridge_lite_v1.json")

    surface_total = p2.get("surface_row_inventory_total") or p2.get("canonical_lite_row_count_deprecated") or p2.get("canonical_lite_row_count")
    event_allowed = bool(p2.get("event_count_claim_allowed", False))
    primary_surface = p2.get("primary_event_surface_candidate", "UNRESOLVED")
    dedup_count = p2.get("deduplicated_event_count", "UNKNOWN")

    surface_summary = {
        "available": not p2.get("_missing") and not p2.get("_error"),
        "surface_row_inventory_total": surface_total,
        "surface_role_row_counts": p2.get("surface_role_row_counts", {}),
        "canonical_event_count": p2.get("canonical_event_count", "UNKNOWN"),
        "deduplicated_event_count": dedup_count,
        "primary_event_surface_candidate": primary_surface,
        "event_count_claim_allowed": event_allowed,
    }
    identity_summary = {
        "available": not p3.get("_missing") and not p3.get("_error"),
        "team_entity_count": p3.get("team_entity_count"),
        "player_entity_count": p3.get("player_entity_count"),
        "unresolved_team_rows": p3.get("unresolved_team_rows"),
        "uses_surface_inventory_semantics": "surface_row_inventory_total" in p3,
    }
    bridge_summary = {
        "available": not bridge.get("_missing") and not bridge.get("_error"),
        "status": bridge.get("status"),
        "candidate_count": len(bridge.get("cross_surface_review_candidates", [])) if isinstance(bridge.get("cross_surface_review_candidates"), list) else None,
    }

    return {
        "module_id": MODULE_ID,
        "status": "PASS" if surface_summary["available"] else "REVIEW_REQUIRED",
        "claim_safety": CLAIM_SAFETY,
        "surface_inventory_summary": surface_summary,
        "identity_binding_summary": identity_summary,
        "bridge_summary": bridge_summary,
        "analyst_safe_count_language": [
            "ACTIVE_MATCH has readable multi-surface row inventory.",
            "This inventory is not a deduplicated event count.",
            "Pattern structure is not built from row inventory alone.",
            "Primary event surface remains unresolved until a later gate.",
        ],
        "pattern_structure_status": "NOT_BUILT_REQUIRES_LATER_GATES",
        "count_risk_flags": COUNT_RISK_FLAGS,
        "blocked_language_families": BLOCKED_LANGUAGE_FAMILIES,
        "required_next_gates": [
            "primary event surface gate",
            "time/phase lite",
            "possession boundary lite",
            "sequence candidate gate",
            "claim router",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA SURFACE INVENTORY INTERPRETATION GATE LITE V1",
        "====================================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"pattern_structure_status={report.get('pattern_structure_status')}",
        "",
        "[surface_inventory_summary]",
        json.dumps(report.get("surface_inventory_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[identity_binding_summary]",
        json.dumps(report.get("identity_binding_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[bridge_summary]",
        json.dumps(report.get("bridge_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[analyst_safe_count_language]",
    ]
    for item in report.get("analyst_safe_count_language", []):
        lines.append(f"- {item}")
    lines.extend(["", "[count_risk_flags]"])
    for item in report.get("count_risk_flags", []):
        lines.append(f"- {item}")
    lines.extend(["", "[blocked_language_families]"])
    for item in report.get("blocked_language_families", []):
        lines.append(f"- {item}")
    lines.extend(["", "[required_next_gates]"])
    for item in report.get("required_next_gates", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(output_root: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(output_root)
    out.mkdir(parents=True, exist_ok=True)
    report = build_gate(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
