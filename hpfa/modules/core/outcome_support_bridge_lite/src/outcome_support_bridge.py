from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "outcome_support_bridge_lite_v1"
VERSION = "1.0.2"
CANONICAL_EVENT_COUNT = "UNKNOWN"
INPUT_MODULES = {
    "selected_action": "selected_action_consequence_surface_lite_v1",
    "selected_event": "selected_event_consequence_surface_lite_v1",
    "sequence": "eventonly_sequence_consequence_engine_lite_v1",
}
OUTPUTS = {
    "json": "outcome_support_bridge_lite_v1.json",
    "summary": "outcome_support_bridge_summary_v1.txt",
    "analyst": "outcome_support_bridge_analyst_audit_v1.txt",
    "conflicts": "outcome_support_bridge_conflict_report_v1.json",
}
ALLOWED_STATUSES = {"PASS", "SMOKE_PASS", "REVIEW_REQUIRED"}
RESOLVED_VISIBLE = {
    "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
    "RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE",
    "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
    "FAILED_VISIBLE_CONSEQUENCE_CANDIDATE",
}
SEQUENCE_STATUSES = {"PASS_CANDIDATE", "REVIEW_REQUIRED_CANDIDATE"}
LINEAGE_FIELDS = (
    "match_surface_binding_id",
    "team_identity_candidate_id",
    "actor_identity_candidate_id",
    "source_role",
    "period_candidate",
)
NONEMPTY_LINEAGE_FIELDS = {
    "match_surface_binding_id",
    "team_identity_candidate_id",
    "source_role",
    "period_candidate",
}
ACTOR_BOUND_ROLES = {"PLAYER_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE"}
TERMINAL_ATOM_CLASS = "TERMINAL_OUTCOME_ATOM"
DERIVED_ATOM_CLASS = "DERIVED_CONSEQUENCE_ATOM"


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: str | Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(code) from exc
    if not isinstance(value, dict):
        raise ValueError(code)
    return value


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _guard(name: str, payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != INPUT_MODULES[name]:
        blocks.append(f"{name}_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append(f"{name}_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{name}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{name}_hard_blocks_present")
    status = clean(payload.get("module_status") or payload.get("status"))
    if status not in ALLOWED_STATUSES:
        blocks.append(f"{name}_status_invalid:{status or 'UNKNOWN'}")
    elif status != "PASS":
        reviews.append(f"{name}_status_review:{status}")
    return blocks, reviews


def _rows(
    payload: dict[str, Any], key: str, count_key: str, code: str
) -> tuple[list[dict[str, Any]], list[str]]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        return [], [f"{code}_inventory_invalid"]
    blocks: list[str] = []
    if payload.get(count_key) != len(raw):
        blocks.append(f"{code}_count_mismatch")
    if any(not isinstance(row, dict) for row in raw):
        blocks.append(f"{code}_record_invalid")
    return [row for row in raw if isinstance(row, dict)], blocks


def _index(
    rows: list[dict[str, Any]], key: str, code: str
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result: dict[str, dict[str, Any]] = {}
    blocks: list[str] = []
    for position, row in enumerate(rows):
        item_id = clean(row.get(key))
        if not item_id or item_id in result:
            blocks.append(f"{code}_id_invalid_or_duplicate:{item_id or position}")
        else:
            result[item_id] = row
    return result, blocks


def _lineage_conflicts(
    node: dict[str, Any], event: dict[str, Any], binding: str
) -> list[str]:
    conflicts: list[str] = []
    node_id = clean(node.get("selected_action_node_id"))
    event_anchor = clean(event.get("anchor_selected_action_node_id"))
    if not node_id:
        conflicts.append("selected_action_node_id_missing")
    if not event_anchor:
        conflicts.append("anchor_selected_action_node_id_missing")
    if node_id and event_anchor and node_id != event_anchor:
        conflicts.append("selected_action_node_id_mismatch")

    for field in LINEAGE_FIELDS:
        left_present = field in node
        right_present = field in event
        if not left_present:
            conflicts.append(f"{field}_missing_on_selected_action")
        if not right_present:
            conflicts.append(f"{field}_missing_on_selected_event")
        if not left_present or not right_present:
            continue

        left = clean(node.get(field))
        right = clean(event.get(field))
        if field in NONEMPTY_LINEAGE_FIELDS:
            if not left:
                conflicts.append(f"{field}_empty_on_selected_action")
            if not right:
                conflicts.append(f"{field}_empty_on_selected_event")
        if left != right:
            conflicts.append(f"{field}_mismatch")
        if field == "match_surface_binding_id":
            if left != binding:
                conflicts.append("selected_action_match_surface_binding_payload_mismatch")
            if right != binding:
                conflicts.append("selected_event_match_surface_binding_payload_mismatch")

    role = clean(node.get("source_role"))
    event_role = clean(event.get("source_role"))
    for side, record, source_role in (
        ("selected_action", node, role),
        ("selected_event", event, event_role),
    ):
        if "actor_identity_candidate_id" not in record:
            if source_role in ACTOR_BOUND_ROLES:
                conflicts.append(
                    f"actor_identity_candidate_id_missing_for_{side}_role"
                )
            continue
        raw_actor = record.get("actor_identity_candidate_id")
        actor = clean(raw_actor)
        if raw_actor is not None and not actor:
            conflicts.append(f"actor_identity_candidate_id_blank_on_{side}")
        if source_role in ACTOR_BOUND_ROLES and not actor:
            conflicts.append(f"actor_identity_candidate_id_missing_for_{side}_role")

    if "consequence_class_candidate" not in event:
        conflicts.append("consequence_class_candidate_missing_on_selected_event")
    elif not clean(event.get("consequence_class_candidate")):
        conflicts.append("consequence_class_candidate_empty_on_selected_event")
    return conflicts


def _support_atom_state(
    node: dict[str, Any],
) -> tuple[list[str], dict[str, int], bool, bool, list[str]]:
    conflicts: list[str] = []
    atom_ids_raw = node.get("supporting_evidence_atom_ids")
    if not isinstance(atom_ids_raw, list):
        conflicts.append("supporting_evidence_atom_inventory_invalid")
        atom_ids_raw = []
    cleaned_ids = [clean(value) for value in atom_ids_raw if clean(value)]
    if len(cleaned_ids) != len(set(cleaned_ids)):
        conflicts.append("supporting_evidence_atom_id_duplicate")
    atom_ids = sorted(set(cleaned_ids))

    counts_raw = node.get("support_atom_class_counts")
    counts: dict[str, int] = {}
    if not isinstance(counts_raw, dict):
        conflicts.append("support_atom_class_counts_invalid")
    else:
        for raw_key, raw_value in counts_raw.items():
            key = clean(raw_key)
            if (
                not key
                or isinstance(raw_value, bool)
                or not isinstance(raw_value, int)
                or raw_value < 0
            ):
                conflicts.append(f"support_atom_class_count_invalid:{key or 'EMPTY'}")
                continue
            counts[key] = raw_value
    if sum(counts.values()) != len(atom_ids):
        conflicts.append("support_atom_count_id_mismatch")

    terminal_raw = node.get("terminal_outcome_support_visible")
    derived_raw = node.get("derived_consequence_support_visible")
    if not isinstance(terminal_raw, bool):
        conflicts.append("terminal_outcome_support_visible_not_boolean")
    if not isinstance(derived_raw, bool):
        conflicts.append("derived_consequence_support_visible_not_boolean")
    terminal_flag = terminal_raw is True
    derived_flag = derived_raw is True
    terminal_count = counts.get(TERMINAL_ATOM_CLASS, 0)
    derived_count = counts.get(DERIVED_ATOM_CLASS, 0)

    if terminal_flag and terminal_count == 0:
        conflicts.append("terminal_support_flag_without_matching_atom_class")
    if not terminal_flag and terminal_count > 0:
        conflicts.append("terminal_atom_class_without_support_flag")
    if derived_flag and derived_count == 0:
        conflicts.append("derived_support_flag_without_matching_atom_class")
    if not derived_flag and derived_count > 0:
        conflicts.append("derived_atom_class_without_support_flag")

    terminal = terminal_flag and terminal_count > 0
    derived = derived_flag and derived_count > 0
    return atom_ids, dict(sorted(counts.items())), terminal, derived, conflicts


def _classify(
    terminal: bool,
    derived: bool,
    visible: bool,
    sequence: bool,
    conflicts: list[str],
) -> tuple[str, str, bool]:
    if conflicts:
        return "CONFLICTED_OUTCOME_SUPPORT", "CONFLICTED", False
    source_count = sum((terminal, derived, visible, sequence))
    if source_count >= 2:
        return "MULTI_SOURCE_COMPATIBLE_OUTCOME_SUPPORT", "SUPPORTED_CANDIDATE", True
    if terminal:
        return "EXPLICIT_TERMINAL_OUTCOME_SUPPORT", "SUPPORTED_CANDIDATE", True
    if derived:
        return "EXPLICIT_DERIVED_CONSEQUENCE_SUPPORT", "SUPPORTED_CANDIDATE", True
    if visible:
        return "VISIBLE_CONSEQUENCE_SUPPORT_ONLY", "SUPPORTED_CANDIDATE", True
    if sequence:
        return "SEQUENCE_TRACE_SUPPORT_ONLY", "SUPPORT_ONLY", False
    return "OUTCOME_SUPPORT_UNAVAILABLE", "UNAVAILABLE", False


def build_outcome_support_bridge(
    selected_action: dict[str, Any],
    selected_event: dict[str, Any],
    sequence_consequence: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    named_payloads = (
        ("selected_action", selected_action),
        ("selected_event", selected_event),
        ("sequence", sequence_consequence),
    )
    for name, payload in named_payloads:
        item_blocks, item_reviews = _guard(name, payload)
        blocks.extend(item_blocks)
        reviews.extend(item_reviews)

    payload_bindings: dict[str, str] = {}
    for name, payload in named_payloads:
        if "match_surface_binding_id" not in payload:
            blocks.append(f"{name}_match_surface_binding_missing")
            payload_bindings[name] = ""
            continue
        value = clean(payload.get("match_surface_binding_id"))
        if not value:
            blocks.append(f"{name}_match_surface_binding_empty")
        payload_bindings[name] = value

    binding = next((value for value in payload_bindings.values() if value), "")
    if len(set(payload_bindings.values())) != 1:
        blocks.append(f"input_match_surface_binding_mismatch:{payload_bindings}")
    if not binding:
        blocks.append("match_surface_binding_missing")

    nodes, node_blocks = _rows(
        selected_action,
        "selected_action_nodes",
        "selected_action_node_count",
        "selected_action_node",
    )
    events, event_blocks = _rows(
        selected_event,
        "selected_event_consequence_candidates",
        "selected_event_consequence_candidate_count",
        "selected_event_consequence",
    )
    blocks.extend(node_blocks + event_blocks)
    node_by_id, node_index_blocks = _index(
        nodes, "selected_action_node_id", "selected_action_node"
    )
    blocks.extend(node_index_blocks)

    event_by_anchor: dict[str, dict[str, Any]] = {}
    event_ids: set[str] = set()
    for position, event in enumerate(events):
        event_id = clean(event.get("selected_event_consequence_candidate_id"))
        anchor_id = clean(event.get("anchor_selected_action_node_id"))
        if not event_id or event_id in event_ids:
            blocks.append(
                f"selected_event_candidate_id_invalid_or_duplicate:{event_id or position}"
            )
            continue
        event_ids.add(event_id)
        if not anchor_id or anchor_id in event_by_anchor:
            blocks.append(
                f"selected_event_anchor_invalid_or_duplicate:{anchor_id or position}"
            )
            continue
        event_by_anchor[anchor_id] = event

    missing = sorted(set(node_by_id) - set(event_by_anchor))
    extra = sorted(set(event_by_anchor) - set(node_by_id))
    if missing:
        blocks.append(f"selected_event_coverage_missing:{len(missing)}")
    if extra:
        blocks.append(f"selected_event_orphan_anchor:{len(extra)}")

    metric_rows = sequence_consequence.get("metric_records")
    sequence_index: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(metric_rows, list):
        blocks.append("sequence_metric_inventory_invalid")
        metric_rows = []
    if sequence_consequence.get("metric_record_count") != len(metric_rows):
        blocks.append("sequence_metric_count_mismatch")
    for position, metric in enumerate(metric_rows):
        if not isinstance(metric, dict):
            blocks.append(f"sequence_metric_record_invalid:{position}")
            continue
        anchors = metric.get("evidence_anchor_node_ids")
        if not isinstance(anchors, list):
            blocks.append(f"sequence_metric_anchor_inventory_invalid:{position}")
            continue
        if clean(metric.get("status")) not in SEQUENCE_STATUSES:
            continue
        metric_id = clean(metric.get("metric_record_id")) or digest(
            metric.get("metric_id"), position
        )
        for raw_id in anchors:
            node_id = clean(raw_id)
            if node_id not in node_by_id:
                blocks.append(
                    f"sequence_metric_anchor_reference_missing:{metric_id}:{node_id or 'NONE'}"
                )
                continue
            sequence_index.setdefault(node_id, []).append(
                {
                    "metric_record_id": metric_id,
                    "metric_id": clean(metric.get("metric_id")),
                    "status": clean(metric.get("status")),
                    "claim_ceiling": clean(metric.get("claim_ceiling")) or None,
                }
            )
    if sequence_index:
        reviews.append("sequence_metric_evidence_anchor_support_is_partial_by_design")

    records: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for node_id in sorted(node_by_id):
        node = node_by_id[node_id]
        event = event_by_anchor.get(node_id, {})
        record_conflicts = (
            _lineage_conflicts(node, event, binding)
            if event
            else ["selected_event_missing"]
        )
        atom_ids, atom_counts, terminal, derived, atom_conflicts = _support_atom_state(
            node
        )
        record_conflicts.extend(atom_conflicts)
        visible_class = clean(event.get("consequence_class_candidate"))
        visible = visible_class in RESOLVED_VISIBLE
        sequence_rows = sequence_index.get(node_id, [])
        sequence = bool(sequence_rows)
        classification, support_status, promotion = _classify(
            terminal,
            derived,
            visible,
            sequence,
            record_conflicts,
        )
        sources: list[str] = []
        if terminal:
            sources.append("EXPLICIT_TERMINAL_ATOM_LINEAGE")
        if derived:
            sources.append("EXPLICIT_DERIVED_ATOM_LINEAGE")
        if visible:
            sources.append("SELECTED_EVENT_VISIBLE_CONSEQUENCE")
        if sequence:
            sources.append("SEQUENCE_METRIC_EVIDENCE_ANCHOR_SUPPORT")

        unique_conflicts = sorted(set(record_conflicts))
        record = {
            "outcome_support_bridge_record_id": "osb_" + digest(binding, node_id)[:24],
            "match_surface_binding_id": binding or None,
            "selected_action_node_id": node_id,
            "selected_event_consequence_candidate_id": event.get(
                "selected_event_consequence_candidate_id"
            ),
            "team_identity_candidate_id": node.get("team_identity_candidate_id"),
            "actor_identity_candidate_id": node.get("actor_identity_candidate_id"),
            "source_role": node.get("source_role"),
            "period_candidate": node.get("period_candidate"),
            "action_family_candidates": node.get("action_family_candidates") or [],
            "supporting_evidence_atom_ids": atom_ids,
            "support_atom_class_counts": atom_counts,
            "terminal_outcome_support_visible": terminal,
            "derived_consequence_support_visible": derived,
            "visible_consequence_class_candidate": event.get(
                "consequence_class_candidate"
            ),
            "visible_zone_delta_class": event.get("zone_delta_class"),
            "visible_turnover_window_class": event.get("turnover_window_class"),
            "visible_retention_after_action_status": event.get(
                "retention_after_action_status"
            ),
            "sequence_metric_evidence_anchor_support": sequence_rows,
            "support_sources": sources,
            "outcome_support_classification": classification,
            "downstream_outcome_support_status": support_status,
            "downstream_promotion_allowed": promotion,
            "conflict_reasons": unique_conflicts,
            "terminal_outcome_truth": False,
            "sequence_trace_truth": False,
            "causality_truth": False,
            "possession_truth": False,
            "tactical_truth": False,
            "claim_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        }
        records.append(record)
        if unique_conflicts:
            conflicts.append(
                {
                    "outcome_support_bridge_record_id": record[
                        "outcome_support_bridge_record_id"
                    ],
                    "selected_action_node_id": node_id,
                    "conflict_reasons": unique_conflicts,
                }
            )

    class_counts = Counter(row["outcome_support_classification"] for row in records)
    support_counts = Counter(
        row["downstream_outcome_support_status"] for row in records
    )
    if class_counts.get("OUTCOME_SUPPORT_UNAVAILABLE"):
        reviews.append("outcome_support_unavailable_records_present")
    if conflicts:
        reviews.append("conflicted_outcome_support_records_present")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "version": VERSION,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_module_ids": dict(INPUT_MODULES),
        "outcome_support_bridge_records": records,
        "outcome_support_bridge_record_count": len(records),
        "outcome_support_classification_counts": dict(sorted(class_counts.items())),
        "downstream_outcome_support_status_counts": dict(sorted(support_counts.items())),
        "conflict_record_count": len(conflicts),
        "conflict_records": conflicts,
        "source_selected_action_node_count": len(nodes),
        "source_selected_event_consequence_candidate_count": len(events),
        "sequence_supported_anchor_count": len(sequence_index),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "metric_rate_output_allowed": False,
        "terminal_outcome_truth": False,
        "sequence_trace_truth": False,
        "progression_truth": False,
        "line_break_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "causality_truth": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "outcome_support_bridge_record_count",
        "outcome_support_classification_counts",
        "downstream_outcome_support_status_counts",
        "sequence_supported_anchor_count",
        "conflict_record_count",
        "hard_block_hits",
        "review_hits",
    )
    lines = ["HPFA OUTCOME SUPPORT BRIDGE LITE V1"] + [
        f"{key}={payload.get(key)}" for key in keys
    ]
    return "\n".join(
        lines + ["canonical_event_count=UNKNOWN", "production_release=false"]
    ) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — OUTCOME SUPPORT BRIDGE LITE V1",
        "",
        "Ne görüldü?",
        "Selected-action anchors were joined to explicit class-matched atom support, selected-event visible consequence candidates and sequence-metric evidence-anchor support.",
        "",
        "Nerede görüldü?",
        f"match_surface_binding_id={payload.get('match_surface_binding_id')}",
        f"record_count={payload.get('outcome_support_bridge_record_count')}",
        "",
        "Hangi evidence destekliyor?",
        f"classification_counts={payload.get('outcome_support_classification_counts')}",
        f"sequence_supported_anchor_count={payload.get('sequence_supported_anchor_count')}",
        f"conflict_record_count={payload.get('conflict_record_count')}",
        "",
        "Analist için güvenli anlamı nedir?",
        "Explicit terminal and derived support require their matching evidence-atom classes and complete per-record lineage. Sequence support alone cannot create terminal outcome truth or downstream promotion.",
        "These records do not prove possession, sequence truth, causality, progression quality, tactical intent or player quality.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    paths["conflicts"].write_text(
        json.dumps(
            {
                "module_id": MODULE_ID,
                "match_surface_binding_id": payload.get("match_surface_binding_id"),
                "conflict_record_count": payload.get("conflict_record_count"),
                "conflict_records": payload.get("conflict_records"),
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "production_release": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-action-consequence", required=True)
    parser.add_argument("--selected-event-consequence", required=True)
    parser.add_argument("--sequence-consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        payload = build_outcome_support_bridge(
            load_json(
                args.selected_action_consequence, "selected_action_input_invalid"
            ),
            load_json(args.selected_event_consequence, "selected_event_input_invalid"),
            load_json(args.sequence_consequence, "sequence_consequence_input_invalid"),
        )
        write_outputs(payload, args.out)
    except ValueError as exc:
        print(f"FAIL_CLOSED:{exc}")
        return 2
    print(summary(payload), end="")
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
