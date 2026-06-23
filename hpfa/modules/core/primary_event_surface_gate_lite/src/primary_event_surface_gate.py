from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "primary_event_surface_gate_lite_v1"
CLAIM_SAFETY = "PRIMARY_SURFACE_CANDIDATE_ONLY"
OUTPUT_JSON = "primary_event_surface_gate_lite_v1.json"
OUTPUT_TXT = "primary_event_surface_gate_lite_v1.txt"

AGGREGATE_FORMATS = {"xlsx"}
EVENT_SURFACE_ROLES = {"players", "teams", "goalkeepers"}
PREFERRED_ROLE_ORDER = {"players": 3, "teams": 2, "goalkeepers": 1}


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


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def pct(part: int, total: int) -> float:
    return round((part / total) * 100, 1) if total else 0.0


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def surface_score(surface: dict[str, Any]) -> tuple[float, list[str]]:
    rows = as_int(surface.get("rows_read"))
    event_rows = as_int(surface.get("event_type_coverage_rows"))
    team_rows = as_int(surface.get("team_coverage_rows"))
    coord_rows = as_int(surface.get("coordinate_coverage_rows"))
    role = str(surface.get("source_role") or "").lower()
    fmt = str(surface.get("source_format") or "").lower()
    missing = surface.get("missing_column_families") or []
    risk_flags: list[str] = []

    if fmt in AGGREGATE_FORMATS:
        risk_flags.append("aggregate_surface_excluded")
        return -1.0, risk_flags
    if role not in EVENT_SURFACE_ROLES:
        risk_flags.append("non_event_surface_role")
        return -1.0, risk_flags
    if rows <= 0:
        risk_flags.append("empty_surface")
        return -1.0, risk_flags
    if event_rows <= 0:
        risk_flags.append("missing_event_type_evidence")
    if coord_rows <= 0:
        risk_flags.append("missing_coordinate_evidence")
    if team_rows <= 0:
        risk_flags.append("missing_team_evidence")
    if "player" in missing:
        risk_flags.append("player_column_unresolved")
    if "minute" in missing and "timestamp" in missing:
        risk_flags.append("temporal_columns_unresolved")

    score = 0.0
    score += pct(event_rows, rows) * 0.35
    score += pct(coord_rows, rows) * 0.30
    score += pct(team_rows, rows) * 0.20
    score += PREFERRED_ROLE_ORDER.get(role, 0) * 5.0
    if role == "players" and event_rows > 0 and coord_rows > 0:
        score += 10.0
    if team_rows <= 0:
        score -= 8.0
    if "temporal_columns_unresolved" in risk_flags:
        score -= 10.0
    return round(score, 2), risk_flags


def candidate_from_surface(surface: dict[str, Any]) -> dict[str, Any]:
    rows = as_int(surface.get("rows_read"))
    event_rows = as_int(surface.get("event_type_coverage_rows"))
    team_rows = as_int(surface.get("team_coverage_rows"))
    coord_rows = as_int(surface.get("coordinate_coverage_rows"))
    score, flags = surface_score(surface)
    aggregate = str(surface.get("source_format") or "").lower() in AGGREGATE_FORMATS
    return {
        "source_file": surface.get("source_file"),
        "source_role": surface.get("source_role"),
        "source_format": surface.get("source_format"),
        "rows_read": rows,
        "event_type_coverage_rows": event_rows,
        "team_coverage_rows": team_rows,
        "coordinate_coverage_rows": coord_rows,
        "event_type_coverage_pct": pct(event_rows, rows),
        "team_coverage_pct": pct(team_rows, rows),
        "coordinate_coverage_pct": pct(coord_rows, rows),
        "aggregate_surface_flag": aggregate,
        "missing_column_families": surface.get("missing_column_families") or [],
        "candidate_score": score,
        "candidate_risk_flags": flags,
        "candidate_eligible": score >= 0 and not aggregate and event_rows > 0 and coord_rows > 0,
    }


def evaluate(canonical_event_lite_audit_json: str | Path, identity_gate_json: str | Path | None = None, physical_cost_audit_json: str | Path | None = None) -> dict[str, Any]:
    audit = read_json(canonical_event_lite_audit_json)
    identity = read_json(identity_gate_json) if identity_gate_json else {}
    physical = read_json(physical_cost_audit_json) if physical_cost_audit_json else {}
    surfaces = audit.get("files_read") or []
    candidates = [candidate_from_surface(s) for s in surfaces if isinstance(s, dict)]
    eligible = [c for c in candidates if c.get("candidate_eligible")]
    eligible_sorted = sorted(eligible, key=lambda c: (float(c.get("candidate_score") or 0), int(c.get("rows_read") or 0)), reverse=True)

    selected = eligible_sorted[0] if eligible_sorted else None
    decision = "CANDIDATE_SELECTED" if selected else "UNRESOLVED_REVIEW_REQUIRED"
    candidate_label = selected.get("source_file") if selected else "UNRESOLVED"

    duplicate_clusters = as_int(identity.get("candidate_cluster_count"))
    duplicate_rows = as_int(identity.get("duplicate_risk_candidate_count"))
    if duplicate_clusters > 0 and decision == "CANDIDATE_SELECTED":
        decision = "CANDIDATE_SELECTED_WITH_DUPLICATE_RISK_REVIEW"

    return {
        "module_id": MODULE_ID,
        "status": "PASS" if candidates else "REVIEW_REQUIRED",
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "primary_event_surface_candidate": candidate_label,
        "primary_event_surface_candidate_role": selected.get("source_role") if selected else "UNRESOLVED",
        "candidate_score": selected.get("candidate_score") if selected else None,
        "candidate_evaluation_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "candidate_evaluations": candidates,
        "duplicate_risk_summary": {
            "available": bool(identity),
            "candidate_cluster_count": duplicate_clusters,
            "duplicate_risk_candidate_count": duplicate_rows,
            "decision": identity.get("decision"),
        },
        "physical_cost_surface_summary": {
            "available": bool(physical),
            "record_count": physical.get("record_count"),
            "surface_counts": physical.get("surface_counts"),
            "runtime_event_truth": physical.get("runtime_event_truth"),
        },
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "metric_count_allowed": False,
        "downstream_unlocks": {
            "time_phase_lite": "CANDIDATE_REVIEW_ONLY" if selected else "WAIT",
            "possession_boundary_lite": "WAIT_TEMPORAL_VALIDATION",
            "sequence_candidate_lite": "WAIT_TEMPORAL_VALIDATION",
        },
        "blocked_language_families": [
            "primary_surface_as_event_truth",
            "primary_surface_as_deduplicated_stream",
            "primary_surface_as_complete_event_count",
            "primary_surface_as_possession_truth",
            "primary_surface_as_phase_truth",
            "primary_surface_as_sequence_truth",
            "primary_surface_as_pattern_truth",
        ],
        "required_next_gates": [
            "time/phase lite temporal field check",
            "claim router",
            "football output audit",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA PRIMARY EVENT SURFACE GATE LITE V1",
        "========================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"primary_event_surface_candidate={report.get('primary_event_surface_candidate')}",
        f"primary_event_surface_candidate_role={report.get('primary_event_surface_candidate_role')}",
        f"candidate_score={report.get('candidate_score')}",
        f"candidate_evaluation_count={report.get('candidate_evaluation_count')}",
        f"eligible_candidate_count={report.get('eligible_candidate_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"metric_count_allowed={report.get('metric_count_allowed')}",
        "",
        "[duplicate_risk_summary]",
        json.dumps(report.get("duplicate_risk_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[physical_cost_surface_summary]",
        json.dumps(report.get("physical_cost_surface_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[candidate_evaluations]",
    ]
    for row in report.get("candidate_evaluations", []):
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
    report = evaluate(
        out / "canonical_event_lite_audit_v1.json",
        out / "event_identity_resolution_gate_lite_v1.json",
        out / "physical_cost_surface_audit_v1.json",
    )
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
