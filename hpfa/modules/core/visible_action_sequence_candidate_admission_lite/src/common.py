from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "visible_action_sequence_candidate_admission_lite_v1"
ACTION_MODULE_ID = "selected_action_consequence_surface_lite_v1"
EVENT_MODULE_ID = "selected_event_consequence_surface_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
MAX_GAP_SECONDS = 12.0
PRIMARY_ROLES = {"PLAYER_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE"}
TEAM_ROLE = "TEAM_SURFACE_CANDIDATE"
UNRESOLVED_CONSEQUENCE = "UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"
OUTPUTS = {
    "json": "visible_action_sequence_candidate_admission_lite_v1.json",
    "summary": "visible_action_sequence_candidate_admission_lite_v1.txt",
    "analyst": "visible_action_sequence_candidate_admission_analyst_audit_v1.txt",
}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def number(value: Any) -> float | None:
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return None


def number_key(value: Any) -> str:
    parsed = number(value)
    return f"{parsed:.6f}" if parsed is not None else clean(value)


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def period_sort_key(value: Any) -> tuple[int, str]:
    text = clean(value)
    try:
        return int(float(text)), text
    except (TypeError, ValueError):
        return 10**9, text


def node_sort_key(node: dict[str, Any]) -> tuple[Any, ...]:
    return (
        period_sort_key(node.get("period_candidate")),
        float("inf") if number(node.get("start_candidate")) is None else number(node.get("start_candidate")),
        clean(node.get("team_identity_candidate_id")),
        clean(node.get("actor_identity_candidate_id")),
        clean(node.get("source_role")),
        clean(node.get("selected_action_node_id")),
    )


def is_primary_node(node: dict[str, Any]) -> bool:
    return (
        clean(node.get("source_role")) in PRIMARY_ROLES
        and clean(node.get("actor_identity_applicability")) == "APPLICABLE_BOUND_CANDIDATE"
        and bool(clean(node.get("actor_identity_candidate_id")))
    )


def is_team_context_node(node: dict[str, Any]) -> bool:
    return clean(node.get("source_role")) == TEAM_ROLE
