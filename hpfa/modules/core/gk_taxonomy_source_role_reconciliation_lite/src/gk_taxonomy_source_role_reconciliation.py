from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "gk_taxonomy_source_role_reconciliation_lite_v1"
CLAIM_SAFETY = "SOURCE_ROLE_RECONCILIATION_ONLY"
OUTPUT_JSON = "gk_taxonomy_source_role_reconciliation_lite_v1.json"
OUTPUT_TXT = "gk_taxonomy_source_role_reconciliation_lite_v1.txt"

IDENTITY_REVIEW_JSON = "identity_review_resolution_lite_v1.json"
SOURCE_CONFLICT_JSON = "source_conflict_registry_lite_v1.json"

BLOCKED_CLAIMS = [
    "source role truth",
    "goalkeeper taxonomy truth",
    "deduplicated event truth",
    "canonical event count",
    "phase truth",
    "possession truth",
    "sequence truth",
]

SOURCE_ROLE_BLOCKERS = {"SOURCE_ROLE_CONFLICT", "NO_SUPPORTED_SURFACES"}


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


def roles(candidate: dict[str, Any]) -> set[str]:
    return {str(item).lower() for item in (candidate.get("source_roles") or [])}


def is_gk_player_overlap(candidate: dict[str, Any]) -> bool:
    found = roles(candidate)
    return "goalkeepers" in found and "players" in found


def gk_player_candidates(identity_review: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in identity_review.get("review_candidates") or []:
        if not isinstance(item, dict) or not is_gk_player_overlap(item):
            continue
        out.append({
            "cluster_id": item.get("cluster_id"),
            "strategy": item.get("strategy"),
            "duplicate_risk_level": item.get("duplicate_risk_level"),
            "source_roles": item.get("source_roles") or [],
            "source_row_count": as_int(item.get("source_row_count")),
            "review_reason": item.get("review_reason"),
            "taxonomy_review_reason": "goalkeeper_player_source_role_overlap",
            "claim_allowed": False,
        })
    return out


def source_role_support_blockers(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    out: list[dict[str, Any]] = []
    for item in payload.get("conflicts") or []:
        if isinstance(item, dict) and str(item.get("conflict_class")) in SOURCE_ROLE_BLOCKERS:
            out.append(item)
    return out


def identity_review_fail_closed(identity_review: dict[str, Any]) -> bool:
    status = str(identity_review.get("status") or "")
    decision = str(identity_review.get("decision") or "")
    return status == "FAIL_CLOSED" or decision.startswith("FAIL_CLOSED")


def build_reconciliation(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    identity_review = read_json(input_path / IDENTITY_REVIEW_JSON)
    source_conflict = read_json(input_path / SOURCE_CONFLICT_JSON)

    status = "FAIL_CLOSED"
    decision = "FAIL_CLOSED_NO_IDENTITY_REVIEW"
    blockers: list[str] = []
    signals: list[str] = []
    candidates: list[dict[str, Any]] = []

    if identity_review is None:
        blockers.append("no_identity_review_output")
    else:
        candidates = gk_player_candidates(identity_review)
        support_blockers = source_role_support_blockers(source_conflict)
        if identity_review_fail_closed(identity_review):
            status = "FAIL_CLOSED"
            decision = "FAIL_CLOSED_IDENTITY_REVIEW_INPUT"
            blockers.append("identity_review_fail_closed")
        elif support_blockers:
            status = "REVIEW_REQUIRED"
            decision = "SOURCE_ROLE_SUPPORT_CONFLICT_REMAINS"
            blockers.append("source_role_support_conflict_present")
        elif candidates:
            status = "REVIEW_REQUIRED"
            decision = "GK_PLAYER_ROLE_OVERLAP_REVIEW_REQUIRED"
            blockers.append("gk_player_source_role_overlap_present")
            signals.append("gk_player_overlap_candidates_present")
        else:
            status = "PASS"
            decision = "NO_GK_PLAYER_OVERLAP_DETECTED"
            signals.append("no_gk_player_overlap_detected")

    affected_rows = sum(as_int(item.get("source_row_count")) for item in candidates)
    downstream_value = "WAIT" if status != "PASS" else "SOURCE_ROLE_REVIEW_CLEAR"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "identity_review_available": identity_review is not None,
        "source_conflict_registry_available": source_conflict is not None,
        "gk_player_overlap_cluster_count": len(candidates),
        "gk_player_overlap_row_count": affected_rows,
        "gk_player_overlap_candidates": candidates,
        "blocking_reasons": blockers,
        "review_signals": sorted(set(signals)),
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "source_role_truth": False,
        "gk_taxonomy_truth": False,
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "downstream_gate": {
            "identity_review_resolution": downstream_value,
            "primary_surface_review_resolution": downstream_value,
            "time_phase_lite": "WAIT",
            "possession_boundary_lite": "WAIT",
            "sequence_candidate_lite": "WAIT",
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA GK TAXONOMY SOURCE ROLE RECONCILIATION LITE V1",
        "====================================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_dir={report.get('input_dir')}",
        f"identity_review_available={report.get('identity_review_available')}",
        f"source_conflict_registry_available={report.get('source_conflict_registry_available')}",
        f"gk_player_overlap_cluster_count={report.get('gk_player_overlap_cluster_count')}",
        f"gk_player_overlap_row_count={report.get('gk_player_overlap_row_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"source_role_truth={report.get('source_role_truth')}",
        f"gk_taxonomy_truth={report.get('gk_taxonomy_truth')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"production_binding_allowed={report.get('production_binding_allowed')}",
        "",
        "[blocking_reasons]",
    ]
    for item in report.get("blocking_reasons", []):
        lines.append(f"- {item}")
    lines.extend(["", "[review_signals]"])
    for item in report.get("review_signals", []):
        lines.append(f"- {item}")
    lines.extend(["", "[downstream_gate]", json.dumps(report.get("downstream_gate"), ensure_ascii=False, sort_keys=True), "", "[gk_player_overlap_candidates]"])
    for item in report.get("gk_player_overlap_candidates", [])[:50]:
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_reconciliation(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
