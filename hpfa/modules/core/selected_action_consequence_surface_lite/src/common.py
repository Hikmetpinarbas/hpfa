from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "selected_action_consequence_surface_lite_v1"
INPUT_MODULES = {
    "action": "semantic_role_action_bundle_candidates_lite_v1",
    "taxonomy": "action_bundle_multi_family_review_taxonomy_lite_v1",
    "relation": "cross_role_relation_candidate_resolver_lite_v1",
    "evidence": "evidence_atom_inventory_lite_v1",
}
CANONICAL_EVENT_COUNT = "UNKNOWN"
WINDOW_SECONDS = (5.0, 8.0, 12.0)
MAX_FOLLOW_UP_LAYERS = 3
SUPPORT_ATOM_CLASSES = {"DERIVED_CONSEQUENCE_ATOM", "TERMINAL_OUTCOME_ATOM"}
ROLE_ORDER = {
    "PLAYER_SURFACE_CANDIDATE": 0,
    "GOALKEEPER_SURFACE_CANDIDATE": 1,
    "TEAM_SURFACE_CANDIDATE": 2,
}
OUTPUTS = {
    "json": "selected_action_consequence_surface_lite_v1.json",
    "summary": "selected_action_consequence_surface_lite_v1.txt",
    "analyst": "selected_action_consequence_surface_analyst_audit_v1.txt",
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


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def bundle_core(record: dict[str, Any]) -> tuple[str, ...]:
    return (
        clean(record.get("match_surface_binding_id")),
        clean(record.get("source_role")),
        clean(record.get("team_identity_candidate_id")),
        clean(record.get("actor_identity_candidate_id")),
        clean(record.get("period_candidate")),
        number_key(record.get("start_candidate")),
        number_key(record.get("end_candidate")),
        number_key(record.get("pos_x_candidate")),
        number_key(record.get("pos_y_candidate")),
    )


def support_core(record: dict[str, Any]) -> tuple[str, ...]:
    return (
        clean(record.get("match_surface_binding_id")),
        clean(record.get("source_role")),
        clean(record.get("period_candidate")),
        number_key(record.get("start_candidate")),
        number_key(record.get("end_candidate")),
        number_key(record.get("pos_x_candidate")),
        number_key(record.get("pos_y_candidate")),
    )


def timeline_key(node: dict[str, Any]) -> tuple[Any, ...]:
    period = clean(node.get("period_candidate"))
    try:
        period_key: Any = int(float(period))
    except (TypeError, ValueError):
        period_key = period
    start = number(node.get("start_candidate"))
    end = number(node.get("end_candidate"))
    return (
        period_key,
        float("inf") if start is None else start,
        float("inf") if end is None else end,
        ROLE_ORDER.get(clean(node.get("source_role")), 9),
        clean(node.get("team_identity_candidate_id")),
        clean(node.get("actor_identity_candidate_id")),
        clean(node.get("selected_action_node_id")),
    )


def selection_record(
    bundle: dict[str, Any],
    state: str,
    basis: str,
    relation_id: str | None = None,
    taxonomy_id: str | None = None,
) -> dict[str, Any]:
    fields = (
        "action_bundle_candidate_id",
        "source_role",
        "team_identity_candidate_id",
        "actor_identity_candidate_id",
        "period_candidate",
        "start_candidate",
        "end_candidate",
        "pos_x_candidate",
        "pos_y_candidate",
        "coordinate_evidence_status",
        "action_family_candidate",
        "bundle_status",
    )
    result = {field: bundle.get(field) for field in fields}
    result.update(
        {
            "selection_state": state,
            "selection_basis": basis,
            "supporting_relation_candidate_id": relation_id,
            "supporting_taxonomy_record_id": taxonomy_id,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }
    )
    return result


def validate_inputs(
    action: dict[str, Any],
    taxonomy: dict[str, Any],
    relation: dict[str, Any],
    evidence: dict[str, Any],
) -> tuple[list[str], str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[str] = []
    payloads = {"action": action, "taxonomy": taxonomy, "relation": relation, "evidence": evidence}
    for name, payload in payloads.items():
        if payload.get("module_id") != INPUT_MODULES[name]:
            blocks.append(f"{name}_module_id_mismatch")
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{name}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{name}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{name}_hard_blocks_present")
    bindings = {clean(payload.get("match_surface_binding_id")) for payload in payloads.values()}
    bindings.discard("")
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch")
    binding = next(iter(bindings), "")
    bundles = action.get("action_bundle_candidates") or []
    tax_records = taxonomy.get("multi_family_review_records") or []
    relations = relation.get("resolved_relation_candidates") or []
    atoms = evidence.get("evidence_atoms") or []
    inventories = (
        (bundles, action.get("action_bundle_candidate_count"), "action_bundle"),
        (tax_records, taxonomy.get("multi_family_review_core_count"), "taxonomy_record"),
        (relations, relation.get("resolved_relation_candidate_count"), "relation_record"),
        (atoms, evidence.get("evidence_atom_count"), "evidence_atom"),
    )
    for rows, declared, name in inventories:
        if not isinstance(rows, list):
            blocks.append(f"{name}_inventory_invalid")
        elif declared != len(rows):
            blocks.append(f"{name}_count_mismatch")
    return blocks, binding, bundles, tax_records, relations, atoms
