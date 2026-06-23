from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "primary_surface_review_resolution_lite_v1"
CLAIM_SAFETY = "PRIMARY_SURFACE_REVIEW_RESOLUTION_ONLY"
OUTPUT_JSON = "primary_surface_review_resolution_lite_v1.json"
OUTPUT_TXT = "primary_surface_review_resolution_lite_v1.txt"

PRIMARY_GATE_JSON = "primary_event_surface_gate_lite_v1.json"
SOURCE_CONFLICT_JSON = "source_conflict_registry_lite_v1.json"
IDENTITY_GATE_JSON = "event_identity_resolution_gate_lite_v1.json"

BLOCKED_CLAIMS = [
    "primary event truth",
    "canonical event count",
    "deduplicated event count",
    "complete event stream",
    "validated event truth",
    "phase truth",
    "possession truth",
    "sequence truth",
    "tactical truth",
]

BLOCKING_CONFLICT_CLASSES = {
    "NO_SUPPORTED_SURFACES",
    "SOURCE_ROLE_CONFLICT",
}

TOP_CANDIDATE_BLOCKING_CLASSES = {
    "UNMAPPED_EVENT_SURFACE",
    "REVIEW_REQUIRED_SOURCE",
}

NON_BLOCKING_REVIEW_CLASSES = {
    "EVENT_LIKE_VS_AGGREGATE_SUPPORT",
    "SCHEMA_DIVERGENCE_BY_ROLE",
    "ROW_COUNT_DISCREPANCY_BY_ROLE",
    "PRIMARY_SURFACE_UNRESOLVED",
    "METRIC_FAMILY_COUNT_NOT_VALUE",
}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner  # type: ignore
    return spine_runner


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def gate_candidate(primary: dict[str, Any]) -> dict[str, Any] | None:
    candidate = primary.get("top_candidate_for_review")
    if isinstance(candidate, dict) and candidate.get("source_file"):
        return candidate
    if primary.get("decision") == "CANDIDATE_SELECTED" and primary.get("primary_event_surface_candidate") not in {None, "UNRESOLVED"}:
        return {
            "source_file": primary.get("primary_event_surface_candidate"),
            "source_role": primary.get("primary_event_surface_candidate_role"),
            "source_format": None,
            "candidate_score": primary.get("candidate_score"),
        }
    return None


def conflict_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    values = payload.get("conflicts") or []
    return [item for item in values if isinstance(item, dict)]


def source_file_of(conflict: dict[str, Any]) -> str | None:
    evidence = conflict.get("evidence") or {}
    value = evidence.get("source_file")
    return str(value) if value else None


def candidate_has_blocking_conflict(candidate: dict[str, Any], conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_file = str(candidate.get("source_file") or "")
    out = []
    for item in conflicts:
        cls = str(item.get("conflict_class"))
        if cls in TOP_CANDIDATE_BLOCKING_CLASSES and source_file_of(item) == source_file:
            out.append(item)
    return out


def global_blocking_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in conflicts if str(item.get("conflict_class")) in BLOCKING_CONFLICT_CLASSES]


def identity_overlap_present(primary: dict[str, Any], identity: dict[str, Any] | None) -> bool:
    reasons = set(primary.get("unresolved_reasons") or [])
    if "overlap_candidates_present" in reasons:
        return True
    if identity:
        for key in ["candidate_cluster_count", "duplicate_risk_candidate_count"]:
            try:
                if int(identity.get(key) or 0) > 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def build_resolution(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    primary = read_json(input_path / PRIMARY_GATE_JSON)
    conflicts_payload = read_json(input_path / SOURCE_CONFLICT_JSON)
    identity = read_json(input_path / IDENTITY_GATE_JSON)

    blocking_reasons: list[str] = []
    review_signals: list[str] = []
    decision = "UNRESOLVED_REVIEW_REQUIRED"
    candidate: dict[str, Any] | None = None
    source_conflicts = conflict_list(conflicts_payload)

    if primary is None:
        decision = "FAIL_CLOSED_NO_PRIMARY_GATE"
        blocking_reasons.append("no_primary_gate_output")
    else:
        candidate = gate_candidate(primary)
        unresolved_reasons = list(primary.get("unresolved_reasons") or [])
        review_signals.extend(unresolved_reasons)
        if candidate is None:
            decision = "FAIL_CLOSED_NO_REVIEW_CANDIDATE"
            blocking_reasons.append("no_review_candidate")
        elif primary.get("decision") == "CANDIDATE_SELECTED":
            decision = "ALREADY_CANDIDATE_SELECTED_BY_GATE"
        else:
            global_blockers = global_blocking_conflicts(source_conflicts)
            candidate_blockers = candidate_has_blocking_conflict(candidate, source_conflicts)
            if identity_overlap_present(primary, identity):
                decision = "UNRESOLVED_IDENTITY_CONFLICTS_REMAIN"
                blocking_reasons.append("identity_overlap_candidates_present")
            elif global_blockers:
                decision = "UNRESOLVED_SOURCE_CONFLICTS_REMAIN"
                blocking_reasons.append("global_source_conflict")
            elif candidate_blockers:
                decision = "UNRESOLVED_SOURCE_CONFLICTS_REMAIN"
                blocking_reasons.append("top_candidate_has_source_conflict")
            else:
                decision = "RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW"

    for item in source_conflicts:
        cls = str(item.get("conflict_class"))
        if cls in NON_BLOCKING_REVIEW_CLASSES and cls.lower() not in review_signals:
            review_signals.append(cls.lower())

    status = "FAIL_CLOSED" if decision.startswith("FAIL_CLOSED") else "REVIEW_REQUIRED"
    if decision in {"ALREADY_CANDIDATE_SELECTED_BY_GATE", "RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW"}:
        status = "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "primary_gate_available": primary is not None,
        "source_conflict_registry_available": conflicts_payload is not None,
        "identity_gate_available": identity is not None,
        "review_candidate": candidate,
        "blocking_reasons": blocking_reasons,
        "review_signals": sorted(set(review_signals)),
        "source_conflict_count": len(source_conflicts),
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "downstream_gate": {
            "time_phase_lite": "CANDIDATE_REVIEW_ONLY" if status == "PASS" else "WAIT",
            "possession_boundary_lite": "WAIT",
            "sequence_candidate_lite": "WAIT",
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA PRIMARY SURFACE REVIEW RESOLUTION LITE V1",
        "================================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_dir={report.get('input_dir')}",
        f"primary_gate_available={report.get('primary_gate_available')}",
        f"source_conflict_registry_available={report.get('source_conflict_registry_available')}",
        f"identity_gate_available={report.get('identity_gate_available')}",
        f"source_conflict_count={report.get('source_conflict_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"production_binding_allowed={report.get('production_binding_allowed')}",
        "",
        "[review_candidate]",
        json.dumps(report.get("review_candidate"), ensure_ascii=False, sort_keys=True),
        "",
        "[blocking_reasons]",
    ]
    for item in report.get("blocking_reasons", []):
        lines.append(f"- {item}")
    lines.extend(["", "[review_signals]"])
    for item in report.get("review_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "[downstream_gate]", json.dumps(report.get("downstream_gate"), ensure_ascii=False, sort_keys=True), "", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_resolution(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
