from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "selected_event_consequence_surface_lite_v1"
INPUT_MODULE_ID = "selected_action_consequence_surface_lite_v1"
INPUT_FIELD_SEMANTICS_VERSION = "selected_action_consequence_field_semantics_v1_1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
OUTPUTS = {
    "json": "selected_event_consequence_surface_lite_v1.json",
    "summary": "selected_event_consequence_surface_lite_v1.txt",
    "analyst": "selected_event_consequence_surface_analyst_audit_v1.txt",
}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str | Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(code) from exc
    if not isinstance(payload, dict):
        raise ValueError(code)
    return payload


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def validate_input(payload: dict[str, Any]) -> tuple[list[str], list[str], str, list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("input_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("input_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("input_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append("input_hard_blocks_present")
    field_version = clean(payload.get("field_semantics_version"))
    if field_version != INPUT_FIELD_SEMANTICS_VERSION:
        reviews.append("input_field_semantics_version_review_required")
    status = clean(payload.get("module_status") or payload.get("status"))
    if status == "FAIL_CLOSED":
        blocks.append("input_fail_closed")
    elif status != "PASS":
        reviews.append(f"input_status_review:{status or 'UNKNOWN'}")
    binding = clean(payload.get("match_surface_binding_id"))
    if not binding:
        blocks.append("match_surface_binding_missing")
    nodes = payload.get("selected_action_nodes") or []
    consequences = payload.get("selected_action_consequence_candidates") or []
    if not isinstance(nodes, list):
        blocks.append("selected_action_nodes_invalid")
        nodes = []
    if not isinstance(consequences, list):
        blocks.append("selected_action_consequence_candidates_invalid")
        consequences = []
    if payload.get("selected_action_node_count") != len(nodes):
        blocks.append("selected_action_node_count_mismatch")
    if payload.get("selected_action_consequence_candidate_count") != len(consequences):
        blocks.append("selected_action_consequence_count_mismatch")
    node_ids = [clean(node.get("selected_action_node_id")) for node in nodes if isinstance(node, dict)]
    anchor_ids = [clean(row.get("anchor_selected_action_node_id")) for row in consequences if isinstance(row, dict)]
    if not node_ids or len(node_ids) != len(set(node_ids)):
        blocks.append("selected_action_node_id_invalid_or_duplicate")
    if len(anchor_ids) != len(set(anchor_ids)) or set(anchor_ids) != set(node_ids):
        blocks.append("consequence_anchor_coverage_mismatch")
    return sorted(set(blocks)), sorted(set(reviews)), binding, nodes, consequences
