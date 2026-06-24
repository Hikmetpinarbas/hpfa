from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MODULE_ID = "event_state_transition_verifier_lite_v1"
CLAIM_SAFETY = "EVENT_STATE_TRANSITION_EVIDENCE_ONLY"
OUTPUT_JSON = "event_state_transition_verifier_lite_v1.json"
OUTPUT_TXT = "event_state_transition_verifier_lite_v1.txt"

PRIMARY_REVIEW_JSON = "primary_surface_review_resolution_lite_v1.json"
IDENTITY_REVIEW_JSON = "identity_review_resolution_lite_v1.json"
GK_RECON_JSON = "gk_taxonomy_source_role_reconciliation_lite_v1.json"
PRIMARY_GATE_JSON = "primary_event_surface_gate_lite_v1.json"

BLOCKED_CLAIMS = [
    "complete event truth",
    "clean possession truth",
    "validated sequence truth",
    "player error truth",
    "referee error truth",
    "phase truth",
    "tactical truth",
]


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


def gate_blocks(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return True
    status = str(payload.get("status") or "")
    decision = str(payload.get("decision") or "")
    if status in {"FAIL_CLOSED", "REVIEW_REQUIRED", "WAIT"}:
        return True
    if decision.startswith("UNRESOLVED") or decision.startswith("FAIL_CLOSED"):
        return True
    return False


def candidate_source_file(primary_gate: dict[str, Any] | None) -> str | None:
    if not primary_gate:
        return None
    for key in ["top_candidate_for_review", "review_candidate"]:
        value = primary_gate.get(key)
        if isinstance(value, dict) and value.get("source_file"):
            return str(value.get("source_file"))
    value = primary_gate.get("primary_event_surface_candidate")
    if value and value != "UNRESOLVED":
        return str(value)
    return None


def normalize_state(text: str) -> str:
    value = text.lower()
    has_shot = any(token in value for token in ["shot", "save"])
    if "goal kick" in value:
        return "restart"
    if has_shot:
        return "shot_terminal"
    if "goal" in value and "goal kick" not in value:
        return "shot_terminal"
    if any(token in value for token in ["corner", "throw", "free kick", "restart", "kick off"]):
        return "restart"
    if any(token in value for token in ["loss", "turnover", "interception", "dispossessed"]):
        return "turnover"
    if any(token in value for token in ["pass", "carry", "dribble", "duel", "recovery", "challenge"]):
        return "possession_active"
    if any(token in value for token in ["foul", "offside"]):
        return "dead_ball"
    return "unknown"


def row_text(row: dict[str, Any]) -> str:
    keys = ["action_family", "event_family", "event_type", "type", "action", "name", "subtype"]
    return " ".join(str(row.get(k) or "") for k in keys)


def read_csv_surface(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(dict(row))
    return rows


def flatten_xml_row(elem: ET.Element) -> dict[str, Any]:
    payload = dict(elem.attrib)
    payload.setdefault("name", elem.tag)
    for child in list(elem):
        text = (child.text or "").strip()
        if text:
            payload.setdefault(child.tag, text)
            if child.tag.lower() in {"action", "event", "event_type", "type", "name", "subtype"}:
                payload.setdefault("event_type", text)
    text = (elem.text or "").strip()
    if text:
        payload.setdefault("event_type", text)
    return payload


def read_xml_surface(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return rows
    elements = [elem for elem in root.iter() if elem is not root and (dict(elem.attrib) or list(elem) or (elem.text or "").strip())]
    containers = [elem for elem in elements if list(elem)]
    source = containers if containers else elements
    for idx, elem in enumerate(source):
        if idx >= limit:
            break
        rows.append(flatten_xml_row(elem))
    return rows


def read_surface(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_surface(path, limit)
    if suffix == ".xml":
        return read_xml_surface(path, limit)
    return []


def transition_issues(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    states = [normalize_state(row_text(row)) for row in rows]
    issues: list[dict[str, Any]] = []
    for idx in range(max(0, len(states) - 1)):
        cur_state = states[idx]
        next_state = states[idx + 1]
        if cur_state == "shot_terminal" and next_state == "possession_active":
            issues.append({"issue_class": "illegal_continuation_after_shot_terminal", "row_index": idx, "next_row_index": idx + 1, "claim_allowed": False})
        if cur_state == "restart" and next_state == "restart":
            issues.append({"issue_class": "restart_cluster_review", "row_index": idx, "next_row_index": idx + 1, "claim_allowed": False})
    unknown_count = sum(1 for item in states if item == "unknown")
    if states and unknown_count / len(states) > 0.50:
        issues.append({"issue_class": "unknown_state_density_review", "unknown_state_count": unknown_count, "row_count": len(states), "claim_allowed": False})
    return issues[:200]


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_path = Path(input_dir).expanduser().resolve(strict=False)
    primary_review = read_json(input_path / PRIMARY_REVIEW_JSON)
    identity_review = read_json(input_path / IDENTITY_REVIEW_JSON)
    gk_recon = read_json(input_path / GK_RECON_JSON)
    primary_gate = read_json(input_path / PRIMARY_GATE_JSON)

    blockers: list[str] = []
    if primary_review is None or identity_review is None or gk_recon is None:
        decision = "FAIL_CLOSED_MISSING_INPUTS"
        status = "FAIL_CLOSED"
        blockers.append("missing_required_review_gate")
        rows: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []
        source_file = None
    elif gate_blocks(primary_review) or gate_blocks(identity_review) or gate_blocks(gk_recon):
        decision = "WAIT_UPSTREAM_REVIEW_BLOCKERS"
        status = "REVIEW_REQUIRED"
        blockers.append("upstream_review_blockers_present")
        rows = []
        issues = []
        source_file = candidate_source_file(primary_gate)
    else:
        source_file = candidate_source_file(primary_gate)
        surface_path = input_path / source_file if source_file else Path("")
        rows = read_surface(surface_path) if source_file else []
        if not rows:
            decision = "NO_EVENT_SURFACE_AVAILABLE"
            status = "REVIEW_REQUIRED"
            blockers.append("no_event_surface_available")
            issues = []
        else:
            issues = transition_issues(rows)
            decision = "TRANSITION_REVIEW_REQUIRED" if issues else "NO_TRANSITION_ISSUES_DETECTED"
            status = "REVIEW_REQUIRED" if issues else "PASS"
            if issues:
                blockers.append("transition_review_candidates_present")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": decision,
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_path),
        "candidate_source_file": source_file,
        "rows_evaluated": len(rows),
        "transition_issue_count": len(issues),
        "transition_issues": issues,
        "blocking_reasons": blockers,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_state_truth": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "downstream_gate": {"time_phase_lite": "WAIT", "possession_boundary_lite": "WAIT", "sequence_candidate_lite": "WAIT"},
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT STATE TRANSITION VERIFIER LITE V1",
        "=============================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_dir={report.get('input_dir')}",
        f"candidate_source_file={report.get('candidate_source_file')}",
        f"rows_evaluated={report.get('rows_evaluated')}",
        f"transition_issue_count={report.get('transition_issue_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"event_state_truth={report.get('event_state_truth')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        "",
        "[blocking_reasons]",
    ]
    for item in report.get("blocking_reasons", []):
        lines.append(f"- {item}")
    lines.extend(["", "[transition_issues]"])
    for item in report.get("transition_issues", [])[:50]:
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
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
    report = build_report(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
