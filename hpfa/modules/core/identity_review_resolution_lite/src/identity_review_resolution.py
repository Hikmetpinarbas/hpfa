from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "identity_review_resolution_lite_v1"
CLAIM_SAFETY = "IDENTITY_REVIEW_RESOLUTION_ONLY"
OUTPUT_JSON = "identity_review_resolution_lite_v1.json"
OUTPUT_TXT = "identity_review_resolution_lite_v1.txt"
IDENTITY_GATE_JSON = "event_identity_resolution_gate_lite_v1.json"
SOURCE_CONFLICT_JSON = "source_conflict_registry_lite_v1.json"
PRIMARY_RESOLUTION_JSON = "primary_surface_review_resolution_lite_v1.json"

BLOCKED_CLAIMS = ["deduplicated event truth", "deduplicated event count", "clean event stream", "validated identity truth", "merged event truth", "phase truth", "possession truth", "sequence truth"]
BLOCKING_SOURCE_CLASSES = {"NO_SUPPORTED_SURFACES", "SOURCE_ROLE_CONFLICT"}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


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


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def conflict_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [item for item in (payload or {}).get("conflicts", []) if isinstance(item, dict)]


def source_support_blockers(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in conflicts if str(item.get("conflict_class")) in BLOCKING_SOURCE_CLASSES]


def review_candidates(identity: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in (identity.get("duplicate_cluster_candidates") or [])[:200]:
        if not isinstance(item, dict):
            continue
        out.append({
            "cluster_id": item.get("cluster_id"),
            "strategy": item.get("strategy"),
            "duplicate_risk_level": item.get("duplicate_risk_level"),
            "source_roles": item.get("source_roles") or [],
            "source_row_count": item.get("source_row_count"),
            "review_reason": item.get("review_reason"),
            "provenance": item.get("provenance") or [],
            "deduplicated_event_truth": False,
            "claim_allowed": False,
        })
    return out


def unresolved_identity_gate(identity: dict[str, Any]) -> bool:
    return as_int(identity.get("unresolved_candidate_count")) > 0


def build_resolution(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    identity = read_json(input_path / IDENTITY_GATE_JSON)
    source_conflicts = conflict_list(read_json(input_path / SOURCE_CONFLICT_JSON))
    primary_resolution = read_json(input_path / PRIMARY_RESOLUTION_JSON)

    blockers: list[str] = []
    signals: list[str] = []
    decision = "FAIL_CLOSED_NO_IDENTITY_GATE"
    candidates: list[dict[str, Any]] = []
    cluster_count = row_count = unresolved_count = 0

    if identity is None:
        blockers.append("no_identity_gate_output")
    else:
        cluster_count = as_int(identity.get("candidate_cluster_count"))
        row_count = as_int(identity.get("duplicate_risk_candidate_count"))
        unresolved_count = as_int(identity.get("unresolved_candidate_count"))
        candidates = review_candidates(identity)
        if cluster_count > 0 or row_count > 0:
            signals.append("identity_overlap_candidates_present")
        elif unresolved_identity_gate(identity):
            signals.append("identity_unresolved_insufficient_fields")
        else:
            signals.append("no_identity_overlap_detected")

        if source_support_blockers(source_conflicts):
            decision = "UNRESOLVED_SOURCE_SUPPORT_CONFLICTS_REMAIN"
            blockers.append("source_support_blockers_present")
        elif cluster_count > 0 or row_count > 0:
            decision = "UNRESOLVED_IDENTITY_OVERLAP_REMAINS"
            blockers.append("identity_overlap_candidates_present")
        elif unresolved_identity_gate(identity):
            decision = "UNRESOLVED_IDENTITY_INSUFFICIENT_FIELDS"
            blockers.append("identity_unresolved_insufficient_fields")
        else:
            decision = "NO_IDENTITY_OVERLAP_DETECTED"

    if primary_resolution:
        primary_decision = str(primary_resolution.get("decision") or "")
        if primary_decision:
            signals.append(f"primary_resolution={primary_decision}")

    status = "FAIL_CLOSED" if decision == "FAIL_CLOSED_NO_IDENTITY_GATE" else "REVIEW_REQUIRED"
    if decision == "NO_IDENTITY_OVERLAP_DETECTED":
        status = "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "identity_gate_available": identity is not None,
        "source_conflict_registry_available": bool(source_conflicts),
        "primary_resolution_available": primary_resolution is not None,
        "candidate_cluster_count": cluster_count,
        "duplicate_risk_candidate_count": row_count,
        "unresolved_candidate_count": unresolved_count,
        "review_candidate_count": len(candidates),
        "review_candidates": candidates,
        "blocking_reasons": blockers,
        "review_signals": sorted(set(signals)),
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "identity_resolution_truth": False,
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "downstream_gate": {"primary_surface_review_resolution": "WAIT" if status != "PASS" else "IDENTITY_REVIEW_CLEAR", "time_phase_lite": "WAIT", "possession_boundary_lite": "WAIT", "sequence_candidate_lite": "WAIT"},
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = ["HPFA IDENTITY REVIEW RESOLUTION LITE V1", "========================================", f"status={report.get('status')}", f"decision={report.get('decision')}", f"claim_safety={report.get('claim_safety')}", f"input_dir={report.get('input_dir')}", f"identity_gate_available={report.get('identity_gate_available')}", f"candidate_cluster_count={report.get('candidate_cluster_count')}", f"duplicate_risk_candidate_count={report.get('duplicate_risk_candidate_count')}", f"unresolved_candidate_count={report.get('unresolved_candidate_count')}", f"review_candidate_count={report.get('review_candidate_count')}", f"canonical_event_count={report.get('canonical_event_count')}", f"deduplicated_event_count={report.get('deduplicated_event_count')}", f"identity_resolution_truth={report.get('identity_resolution_truth')}", f"event_count_claim_allowed={report.get('event_count_claim_allowed')}", f"production_binding_allowed={report.get('production_binding_allowed')}", "", "[blocking_reasons]"]
    lines += [f"- {item}" for item in report.get("blocking_reasons", [])]
    lines += ["", "[review_signals]"] + [f"- {item}" for item in report.get("review_signals", [])]
    lines += ["", "[downstream_gate]", json.dumps(report.get("downstream_gate"), ensure_ascii=False, sort_keys=True), "", "[review_candidates]"]
    lines += [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in report.get("review_candidates", [])[:50]]
    lines += ["", "[blocked_claims]"] + [f"- {item}" for item in report.get("blocked_claims", [])] + [""]
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
