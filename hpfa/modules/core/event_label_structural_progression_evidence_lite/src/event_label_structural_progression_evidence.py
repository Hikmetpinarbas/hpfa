from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "event_label_structural_progression_evidence_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
INPUT_MODULES = {
    "provider_labels": "provider_label_value_semantics_lite_v1",
    "action_bundles": "semantic_role_action_bundle_candidates_lite_v1",
    "selected_action": "selected_action_consequence_surface_lite_v1",
    "selected_event": "selected_event_consequence_surface_lite_v1",
    "sequence_consequence": "eventonly_sequence_consequence_engine_lite_v1",
    "aggregate_alignment": "aggregate_definition_alignment_lite_v1",
}
OUTPUTS = {
    "json": "event_label_structural_progression_evidence_lite_v1.json",
    "summary": "event_label_structural_progression_evidence_lite_v1.txt",
    "analyst": "event_label_structural_progression_evidence_analyst_audit_v1.txt",
}
EXACT_MAPPING_STATUSES = {"EXACT_REVIEWED_CANDIDATE", "EXACT_ALIAS_CANDIDATE"}
PREFIX_MAPPING_STATUSES = {"PREFIX_RULE_REVIEWED_CANDIDATE"}
AMBIGUOUS_MAPPING_STATUSES = {"TOKEN_FALLBACK_REVIEW_REQUIRED", "CONFLICT_REVIEW_REQUIRED"}
RESOLVED_DIRECTIONS = {"ATTACK_TOWARD_HIGH_X_CANDIDATE", "ATTACK_TOWARD_LOW_X_CANDIDATE"}
PRODUCER_DIRECTION_SUPPORT_MAP = {"PASS_SHOT_CONCENTRATION_CANDIDATE": "SUPPORTED_CANDIDATE"}
NEGATIVE_GEOMETRY_CLASSES = {"RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE", "LOSS_OR_HANDOVER_CANDIDATE"}
BOX_GAIN_CLASSES = {"BOX_ACCESS_CANDIDATE", "CENTRAL_DEEP_BOX_ENTRY_CANDIDATE"}
UNRESOLVED_MARKERS = ("UNRESOLVED", "REVIEW_REQUIRED", "UNKNOWN")
PROGRESSION_METRICS = {
    "progression_to_final_third_support",
    "progression_to_box_entry_support",
    "progression_to_shot_support",
}
SUCCESS_OUTCOMES = {
    "SUCCESS",
    "SUCCESSFUL_CANDIDATE",
    "ACCURATE",
    "ACCURATE_CANDIDATE",
    "WON",
    "WON_CANDIDATE",
}
FAILURE_OUTCOMES = {
    "FAILURE",
    "FAILURE_CANDIDATE",
    "UNSUCCESSFUL",
    "UNSUCCESSFUL_CANDIDATE",
    "INACCURATE",
    "INACCURATE_CANDIDATE",
    "LOST",
    "LOST_CANDIDATE",
    "FAILED",
    "FAILED_CANDIDATE",
}


def clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


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


def _is_unresolved(value: Any) -> bool:
    text = clean(value).upper()
    return any(marker in text for marker in UNRESOLVED_MARKERS)


def _input_guard(name: str, payload: dict[str, Any]) -> tuple[list[str], list[str]]:
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
    if status == "FAIL_CLOSED":
        blocks.append(f"{name}_fail_closed")
    elif status not in {"PASS", "SMOKE_PASS"}:
        reviews.append(f"{name}_status_review:{status or 'UNKNOWN'}")
    return blocks, reviews


def _records(
    payload: dict[str, Any], key: str, declared_key: str, code: str
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return [], [f"{code}_inventory_invalid"]
    blocks: list[str] = []
    if payload.get(declared_key) != len(rows):
        blocks.append(f"{code}_count_mismatch")
    if any(not isinstance(row, dict) for row in rows):
        blocks.append(f"{code}_record_invalid")
        rows = [row for row in rows if isinstance(row, dict)]
    return rows, blocks


def _label_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (clean(row.get("source_role")), clean(row.get("normalized_label")))
        if all(key):
            index.setdefault(key, []).append(row)
    return index


def _provider_matches(
    source_role: str,
    anchor_labels: list[str],
    index: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    labels = {clean(value) for value in anchor_labels if clean(value)}
    matches = [row for label in labels for row in index.get((clean(source_role), label), [])]
    deduped: dict[str, dict[str, Any]] = {}
    for row in matches:
        record_id = clean(row.get("record_id")) or digest(
            row.get("source_role"),
            row.get("normalized_label"),
            row.get("mapping_status"),
            row.get("rule_id"),
        )
        deduped[record_id] = row
    return list(deduped.values())


def _provider_support(matches: list[dict[str, Any]]) -> tuple[str, str]:
    statuses = {clean(row.get("mapping_status")) for row in matches}
    if statuses & AMBIGUOUS_MAPPING_STATUSES:
        return "UNKNOWN", "LABEL_AMBIGUOUS"
    if statuses & EXACT_MAPPING_STATUSES:
        return "EXACT_REVIEWED_RULE", ""
    if statuses & PREFIX_MAPPING_STATUSES:
        return "PREFIX_REVIEWED_RULE", ""
    return "UNKNOWN", "LABEL_UNKNOWN"


def _anchor_label_lineage(
    node: dict[str, Any],
    bundle_by_id: dict[str, dict[str, Any]],
    binding: str,
) -> tuple[list[str], list[str], list[str]]:
    raw_ids = node.get("selected_action_bundle_candidate_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return [], [], ["action_anchor_bundle_lineage_missing"]
    labels: set[str] = set()
    resolved_ids: list[str] = []
    blocks: list[str] = []
    node_role = clean(node.get("source_role"))
    for raw_id in raw_ids:
        bundle_id = clean(raw_id)
        if not bundle_id or bundle_id not in bundle_by_id:
            blocks.append(f"action_anchor_bundle_reference_missing:{bundle_id or 'NONE'}")
            continue
        bundle = bundle_by_id[bundle_id]
        if clean(bundle.get("match_surface_binding_id")) != binding:
            blocks.append(f"action_anchor_bundle_binding_mismatch:{bundle_id}")
        if clean(bundle.get("source_role")) != node_role:
            blocks.append(f"action_anchor_bundle_role_mismatch:{bundle_id}")
        resolved_ids.append(bundle_id)
        for value in bundle.get("normalized_labels") or []:
            if clean(value):
                labels.add(clean(value))
    return sorted(labels), sorted(set(resolved_ids)), blocks


def _direction_record(event: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any] | None:
    team = clean(event.get("team_identity_candidate_id"))
    period = clean(event.get("period_candidate"))
    for row in frame.get("team_period_attack_direction_candidates") or []:
        if isinstance(row, dict) and clean(row.get("team_identity_candidate_id")) == team and clean(row.get("period_candidate")) == period:
            return row
    return None


def _axis_eligibility(event: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    direction = _direction_record(event, frame)
    raw_support = clean((direction or {}).get("attack_direction_support_status"))
    gate_support = PRODUCER_DIRECTION_SUPPORT_MAP.get(raw_support, "UNSUPPORTED_OR_UNRESOLVED")
    direction_candidate = clean((direction or {}).get("attack_direction_candidate"))
    bounds = clean(frame.get("coordinate_bounds_status"))
    scale = clean(frame.get("coordinate_scale_candidate"))
    zone_status = clean(event.get("zone_delta_status"))
    if (
        bounds == "PASS_CANDIDATE_BOUNDS"
        and direction_candidate in RESOLVED_DIRECTIONS
        and gate_support == "SUPPORTED_CANDIDATE"
        and zone_status == "PASS_CANDIDATE_CLASSIFICATION"
    ):
        state = "AXIS_ELIGIBLE_CANDIDATE"
    elif "CONFLICT" in raw_support or "CONFLICT" in direction_candidate or "OUTSIDE" in bounds:
        state = "AXIS_CONFLICTED"
    elif scale and "UNRESOLVED" not in scale and bounds == "PASS_CANDIDATE_BOUNDS":
        state = "AXIS_PARTIALLY_ELIGIBLE"
    elif not scale or "UNRESOLVED" in scale:
        state = "COORDINATE_UNAVAILABLE"
    else:
        state = "AXIS_UNRESOLVED"
    coordinate_support = (
        "SUPPORTED_CANDIDATE"
        if state == "AXIS_ELIGIBLE_CANDIDATE"
        else "CONFLICTED"
        if state == "AXIS_CONFLICTED"
        else "UNAVAILABLE"
    )
    return {
        "axis_eligibility_state": state,
        "coordinate_scale_candidate": scale or None,
        "coordinate_bounds_status": bounds or None,
        "team_period_attack_direction_candidate": direction_candidate or None,
        "producer_attack_direction_support_status": raw_support or None,
        "attack_direction_support_status": gate_support,
        "coordinate_support": coordinate_support,
        "signed_forward_delta_allowed": state == "AXIS_ELIGIBLE_CANDIDATE",
        "validated_attack_direction_truth": False,
    }


def _duration_support(node: dict[str, Any]) -> str:
    try:
        start = float(node.get("start_candidate"))
        end = float(node.get("end_candidate"))
    except (TypeError, ValueError):
        return "UNAVAILABLE"
    return "SUPPORTED_CANDIDATE" if start >= 0 and end >= start else "CONFLICTED"


def _outcome_support(node: dict[str, Any]) -> str:
    if node.get("terminal_outcome_support_visible") is True:
        return "SUPPORTED_CANDIDATE"
    if node.get("derived_consequence_support_visible") is True:
        return "SUPPORTED_CANDIDATE"
    return "UNAVAILABLE"


def _consequence_support(event: dict[str, Any]) -> str:
    value = clean(event.get("consequence_class_candidate"))
    return "UNAVAILABLE" if not value or _is_unresolved(value) else "SUPPORTED_CANDIDATE"


def _alignment_support(
    matches: list[dict[str, Any]], alignment_rows: list[dict[str, Any]]
) -> tuple[str, list[str], list[str]]:
    record_ids = {clean(row.get("record_id")) for row in matches if clean(row.get("record_id"))}
    if not record_ids:
        return "NOT_AVAILABLE", [], ["missing_provider_record_lineage"]
    definition_ids: list[str] = []
    reasons: set[str] = set()
    for row in alignment_rows:
        support_ids = {
            clean(record_id)
            for support in row.get("semantic_support") or []
            if isinstance(support, dict)
            for record_id in support.get("record_ids") or []
            if clean(record_id)
        }
        if not record_ids & support_ids:
            continue
        if clean(row.get("definition_id")):
            definition_ids.append(clean(row.get("definition_id")))
        decision = clean(row.get("alignment_decision"))
        reasons.add(
            "definition_and_occurrence_semantics_alignment_candidate"
            if decision == "DEFINITION_ALIGNMENT_CANDIDATE"
            else "definition_alignment_review_required"
        )
        for hit in row.get("alignment_hits") or []:
            if isinstance(hit, dict) and clean(hit.get("code")):
                reasons.add(clean(hit.get("code")))
    if not definition_ids:
        return "NOT_AVAILABLE", [], ["no_aggregate_semantic_lineage_match"]
    if reasons == {"definition_and_occurrence_semantics_alignment_candidate"}:
        return "SUPPORT_ONLY", sorted(set(definition_ids)), sorted(reasons)
    return "UNRESOLVED", sorted(set(definition_ids)), sorted(reasons)


def _label_progression_profile(matches: list[dict[str, Any]]) -> dict[str, Any]:
    progression = sorted({clean(row.get("progression_candidate")) for row in matches if clean(row.get("progression_candidate"))})
    outcomes = sorted({clean(row.get("outcome_candidate")).upper() for row in matches if clean(row.get("outcome_candidate"))})
    progressive = any(value not in {"NONE", "NOT_APPLICABLE", "UNKNOWN"} for value in progression)
    successful = any(value in SUCCESS_OUTCOMES for value in outcomes)
    unsuccessful = any(value in FAILURE_OUTCOMES for value in outcomes)
    return {
        "provider_progression_label_candidate": progression,
        "provider_outcome_candidates": outcomes,
        "provider_progression_label_present": progressive,
        "provider_successful_outcome_candidate": successful,
        "provider_unsuccessful_outcome_candidate": unsuccessful,
        "provider_outcome_conflicted": successful and unsuccessful,
    }


def _verification(
    provider_support: str,
    pre_status: str,
    profile: dict[str, Any],
    event: dict[str, Any],
    dimensions: dict[str, str],
) -> tuple[str, str]:
    if pre_status:
        return pre_status, "DOWNSTREAM_BLOCKED_REVIEW_REQUIRED"
    if provider_support not in {"EXACT_REVIEWED_RULE", "PREFIX_REVIEWED_RULE"}:
        return "LABEL_UNKNOWN", "DOWNSTREAM_BLOCKED_REVIEW_REQUIRED"
    if profile["provider_outcome_conflicted"]:
        return "LABEL_AMBIGUOUS", "DOWNSTREAM_BLOCKED_REVIEW_REQUIRED"
    zone_delta = clean(event.get("zone_delta_class"))
    if (
        profile["provider_progression_label_present"]
        and profile["provider_successful_outcome_candidate"]
        and zone_delta in NEGATIVE_GEOMETRY_CLASSES
        and dimensions["coordinate_support"] == "SUPPORTED_CANDIDATE"
    ):
        return "LABEL_CONFLICTED", "LABEL_CONFLICTED_AND_DOWNSTREAM_BLOCKED"
    independent = sum(value in {"SUPPORTED_CANDIDATE", "SUPPORT_ONLY"} for value in dimensions.values())
    if independent == 0:
        return "LABEL_ONLY", "COMPONENT_ONLY_FALLBACK"
    if independent >= 2:
        return "LABEL_SUPPORTED", "DOWNSTREAM_ELIGIBLE_CANDIDATE"
    return "LABEL_PARTIALLY_SUPPORTED", "COMPONENT_ONLY_FALLBACK"


def _structural_progression(
    verification_status: str,
    axis_state: str,
    event: dict[str, Any],
    consequence_support: str,
    outcome_support: str,
) -> tuple[str, list[str]]:
    zone_delta = clean(event.get("zone_delta_class"))
    evidence = [zone_delta] if zone_delta else []
    if consequence_support == "SUPPORTED_CANDIDATE":
        evidence.append(clean(event.get("consequence_class_candidate")))
    if verification_status in {"LABEL_UNKNOWN", "LABEL_AMBIGUOUS", "LABEL_CONFLICTED"}:
        return "PROGRESSION_CONTEXT_UNRESOLVED", evidence
    if zone_delta == "NO_ZONE_CHANGE_CANDIDATE":
        return "CIRCULATION_CANDIDATE", evidence
    if zone_delta == "RESET_OR_BACKWARD_ZONE_CHANGE_CANDIDATE":
        return "PROGRESSION_CONTEXT_UNRESOLVED", evidence
    if axis_state != "AXIS_ELIGIBLE_CANDIDATE":
        return "PROGRESSION_CONTEXT_UNRESOLVED", evidence
    if zone_delta == "ZONE_GAIN_CANDIDATE":
        if verification_status == "LABEL_SUPPORTED" and consequence_support == "SUPPORTED_CANDIDATE":
            return "STRUCTURAL_PROGRESSION_CANDIDATE", evidence
        return "TERRITORIAL_ADVANCEMENT_CANDIDATE", evidence
    if zone_delta == "THIRD_BREAK_CANDIDATE":
        return ("DEEP_ADVANCEMENT_CANDIDATE" if outcome_support == "SUPPORTED_CANDIDATE" else "TERRITORIAL_ADVANCEMENT_CANDIDATE"), evidence
    if zone_delta in BOX_GAIN_CLASSES:
        return ("BOX_PENETRATION_CANDIDATE" if outcome_support == "SUPPORTED_CANDIDATE" else "TERRITORIAL_ADVANCEMENT_CANDIDATE"), evidence
    return "PROGRESSION_CONTEXT_UNRESOLVED", evidence


def _persistence(event: dict[str, Any]) -> str:
    source = clean(event.get("false_progression_candidate"))
    zone_delta = clean(event.get("zone_delta_class"))
    if source == "FALSE_PROGRESSION_CANDIDATE":
        return "FALSE_PROGRESSION_CANDIDATE"
    if zone_delta in BOX_GAIN_CLASSES and source in {
        "VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE",
        "ZONE_GAIN_WITH_CONSTRUCTIVE_SUPPORT_BEFORE_HANDOVER_CANDIDATE",
    }:
        return "TERMINAL_PROGRESSION_CANDIDATE"
    mapping = {
        "VISIBLE_ZONE_GAIN_RETAINED_CANDIDATE": "VISIBLE_PROGRESSION_RETAINED_CANDIDATE",
        "ZONE_GAIN_WITH_CONSTRUCTIVE_SUPPORT_BEFORE_HANDOVER_CANDIDATE": "TERMINAL_PROGRESSION_CANDIDATE",
        "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN": "PROGRESSION_CONTEXT_UNRESOLVED",
    }
    if source in mapping:
        return mapping[source]
    if "BACKWARD" in zone_delta:
        return "REVERSIBLE_PROGRESSION_CANDIDATE"
    return "PROGRESSION_CONTEXT_UNRESOLVED"


def _line_break_evidence(
    provider_support: str, axis: dict[str, Any], dimensions: dict[str, str]
) -> dict[str, Any]:
    components = {
        "provider_label_evidence": provider_support,
        "geometry_support": axis["coordinate_support"],
        "outcome_support": dimensions["outcome_support"],
        "consequence_support": dimensions["consequence_support"],
        "aggregate_support": dimensions["aggregate_support"],
    }
    full_support = (
        axis["coordinate_support"] == "SUPPORTED_CANDIDATE"
        and dimensions["outcome_support"] == "SUPPORTED_CANDIDATE"
        and dimensions["consequence_support"] == "SUPPORTED_CANDIDATE"
        and dimensions["aggregate_support"] == "SUPPORT_ONLY"
    )
    if provider_support not in {"EXACT_REVIEWED_RULE", "PREFIX_REVIEWED_RULE"}:
        result_class = "UNKNOWN"
    elif axis["coordinate_support"] == "CONFLICTED":
        result_class = "LABEL_CONFLICTED"
    elif full_support:
        result_class = "LABEL_FULLY_SUPPORTED"
    elif axis["coordinate_support"] == "SUPPORTED_CANDIDATE":
        result_class = "LABEL_GEOMETRY_SUPPORTED"
    elif dimensions["consequence_support"] == "SUPPORTED_CANDIDATE":
        result_class = "LABEL_CONSEQUENCE_SUPPORTED"
    else:
        result_class = "LABEL_ONLY"
    return {
        "components": components,
        "result_class": result_class,
        "line_break_evidence_score_candidate": None,
        "weights_exposed": True,
        "component_only_fallback": True,
        "line_break_truth": False,
        "packing_truth": False,
        "opponent_structure_truth": False,
    }


def _progression_metric_gate(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in sequence_payload.get("metric_records") or []
        if isinstance(row, dict) and clean(row.get("metric_id")) in PROGRESSION_METRICS
    ]
    return {
        "source_progression_metric_record_count": len(rows),
        "source_progression_metric_status_counts": dict(sorted(Counter(clean(row.get("status")) for row in rows).items())),
        "metric_rate_output_allowed": False,
        "denominator_gate_status": "METRIC_BLOCKED",
        "reason": "implementation_v1_emits_component_evidence_only; progression rates remain closed",
    }


def build_event_label_structural_progression_evidence(
    provider_labels: dict[str, Any],
    action_bundles: dict[str, Any],
    selected_action: dict[str, Any],
    selected_event: dict[str, Any],
    sequence_consequence: dict[str, Any],
    aggregate_alignment: dict[str, Any],
) -> dict[str, Any]:
    payloads = {
        "provider_labels": provider_labels,
        "action_bundles": action_bundles,
        "selected_action": selected_action,
        "selected_event": selected_event,
        "sequence_consequence": sequence_consequence,
        "aggregate_alignment": aggregate_alignment,
    }
    blocks: list[str] = []
    reviews: list[str] = []
    for name, payload in payloads.items():
        found_blocks, found_reviews = _input_guard(name, payload)
        blocks.extend(found_blocks)
        reviews.extend(found_reviews)

    bundle_rows, found = _records(action_bundles, "action_bundle_candidates", "action_bundle_candidate_count", "action_bundle")
    blocks.extend(found)
    action_nodes, found = _records(selected_action, "selected_action_nodes", "selected_action_node_count", "selected_action_node")
    blocks.extend(found)
    event_rows, found = _records(selected_event, "selected_event_consequence_candidates", "selected_event_consequence_candidate_count", "selected_event_consequence")
    blocks.extend(found)
    provider_rows, found = _records(provider_labels, "provider_label_records", "provider_label_record_count", "provider_label")
    blocks.extend(found)
    alignment_rows, found = _records(aggregate_alignment, "alignment_rows", "definition_candidate_count", "aggregate_alignment")
    blocks.extend(found)

    bindings = {
        clean(action_bundles.get("match_surface_binding_id")),
        clean(selected_action.get("match_surface_binding_id")),
        clean(selected_event.get("match_surface_binding_id")),
        clean(sequence_consequence.get("match_surface_binding_id")),
    }
    bindings.discard("")
    if len(bindings) != 1:
        blocks.append("match_surface_binding_mismatch_or_missing")
    binding = next(iter(bindings), "")

    bundle_by_id: dict[str, dict[str, Any]] = {}
    for row in bundle_rows:
        bundle_id = clean(row.get("action_bundle_candidate_id"))
        if not bundle_id or bundle_id in bundle_by_id:
            blocks.append(f"action_bundle_id_invalid_or_duplicate:{bundle_id or 'NONE'}")
        else:
            bundle_by_id[bundle_id] = row

    action_by_id: dict[str, dict[str, Any]] = {}
    for node in action_nodes:
        node_id = clean(node.get("selected_action_node_id"))
        if not node_id or node_id in action_by_id:
            blocks.append(f"selected_action_node_id_invalid_or_duplicate:{node_id or 'NONE'}")
        else:
            action_by_id[node_id] = node

    frame = selected_event.get("coordinate_frame_candidate")
    if not isinstance(frame, dict):
        frame = {}
        blocks.append("coordinate_frame_candidate_invalid")

    label_index = _label_index(provider_rows)
    output_records: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for event in event_rows:
        event_id = clean(event.get("selected_event_consequence_candidate_id"))
        anchor_id = clean(event.get("anchor_selected_action_node_id"))
        if not event_id or event_id in seen_event_ids:
            blocks.append(f"selected_event_candidate_id_invalid_or_duplicate:{event_id or 'NONE'}")
            continue
        seen_event_ids.add(event_id)
        node = action_by_id.get(anchor_id)
        if node is None:
            blocks.append(f"selected_event_anchor_missing:{event_id}:{anchor_id or 'NONE'}")
            continue
        if clean(event.get("match_surface_binding_id")) != binding or clean(node.get("match_surface_binding_id")) != binding:
            blocks.append(f"record_binding_mismatch:{event_id}")
            continue

        anchor_labels, bundle_ids, lineage_blocks = _anchor_label_lineage(node, bundle_by_id, binding)
        blocks.extend(lineage_blocks)
        lineage_pre_status = "LABEL_UNKNOWN" if not anchor_labels else ""
        if not anchor_labels:
            reviews.append(f"action_anchor_label_lineage_review:{event_id}")
        matches = _provider_matches(clean(node.get("source_role")), anchor_labels, label_index)
        provider_support, provider_pre_status = _provider_support(matches)
        pre_status = lineage_pre_status or provider_pre_status
        axis = _axis_eligibility(event, frame)
        aggregate_support, definition_ids, alignment_reasons = _alignment_support(matches, alignment_rows)
        dimensions = {
            "coordinate_support": axis["coordinate_support"],
            "outcome_support": _outcome_support(node),
            "duration_support": _duration_support(node),
            "consequence_support": _consequence_support(event),
            "aggregate_support": aggregate_support,
        }
        profile = _label_progression_profile(matches)
        verification_status, downstream = _verification(provider_support, pre_status, profile, event, dimensions)
        structural_class, structural_evidence = _structural_progression(
            verification_status,
            axis["axis_eligibility_state"],
            event,
            dimensions["consequence_support"],
            dimensions["outcome_support"],
        )
        persistence_class = _persistence(event)
        line_break = _line_break_evidence(provider_support, axis, dimensions)
        if verification_status in {"LABEL_UNKNOWN", "LABEL_AMBIGUOUS", "LABEL_CONFLICTED"}:
            reviews.append(f"label_verification_review:{event_id}:{verification_status}")
        if axis["axis_eligibility_state"] != "AXIS_ELIGIBLE_CANDIDATE":
            reviews.append(f"axis_not_fully_eligible:{event_id}:{axis['axis_eligibility_state']}")

        output_records.append(
            {
                "evidence_record_id": "elspe_" + digest(binding, event_id, anchor_id)[:24],
                "match_surface_binding_id": binding,
                "source_selected_event_consequence_candidate_id": event_id,
                "anchor_selected_action_node_id": anchor_id,
                "source_action_bundle_candidate_ids": bundle_ids,
                "team_identity_candidate_id": event.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": event.get("actor_identity_candidate_id"),
                "source_role": event.get("source_role"),
                "period_candidate": event.get("period_candidate"),
                "action_family_candidates": event.get("anchor_action_family_candidates") or [],
                "action_anchor_normalized_labels": anchor_labels,
                "support_normalized_labels": node.get("support_normalized_labels") or [],
                "provider_label_record_ids": sorted(clean(row.get("record_id")) for row in matches if clean(row.get("record_id"))),
                "provider_source_support": provider_support,
                **profile,
                **dimensions,
                "verification_status": verification_status,
                "downstream_eligibility": downstream,
                "axis_eligibility": axis,
                "zone_delta_class": event.get("zone_delta_class"),
                "structural_progression_classification": structural_class,
                "structural_progression_evidence": structural_evidence,
                "persistence_classification": persistence_class,
                "source_false_progression_candidate": event.get("false_progression_candidate"),
                "source_consequence_class_candidate": event.get("consequence_class_candidate"),
                "label_assisted_line_break_evidence": line_break,
                "aggregate_definition_support_ids": definition_ids,
                "aggregate_alignment_reasons": alignment_reasons,
                "component_only_evidence": True,
                "progression_truth": False,
                "line_break_truth": False,
                "packing_truth": False,
                "possession_truth": False,
                "sequence_truth": False,
                "tactical_truth": False,
                "causality_truth": False,
                "claim_allowed": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )

    if len(output_records) != len(event_rows):
        blocks.append("selected_event_evidence_coverage_mismatch")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else "REVIEW_REQUIRED" if reviews else "PASS"

    def counts(field: str) -> dict[str, int]:
        return dict(sorted(Counter(clean(row.get(field)) for row in output_records).items()))

    axis_counts = dict(
        sorted(Counter(clean((row.get("axis_eligibility") or {}).get("axis_eligibility_state")) for row in output_records).items())
    )
    return {
        "module_id": MODULE_ID,
        "version": "1.1.1",
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "source_module_ids": dict(INPUT_MODULES),
        "evidence_records": output_records,
        "evidence_record_count": len(output_records),
        "verification_status_counts": counts("verification_status"),
        "axis_eligibility_state_counts": axis_counts,
        "structural_progression_classification_counts": counts("structural_progression_classification"),
        "persistence_classification_counts": counts("persistence_classification"),
        "progression_metric_gate": _progression_metric_gate(sequence_consequence),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "component_first": True,
        "metric_rate_output_allowed": False,
        "analysis_sentence_generated": False,
        "claim_allowed": False,
        "progression_truth": False,
        "line_break_truth": False,
        "packing_truth": False,
        "opponent_structure_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "causality_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def summary(payload: dict[str, Any]) -> str:
    keys = (
        "status",
        "evidence_record_count",
        "verification_status_counts",
        "axis_eligibility_state_counts",
        "structural_progression_classification_counts",
        "persistence_classification_counts",
        "hard_block_hits",
        "review_hits",
    )
    return "\n".join(
        ["HPFA EVENT LABEL STRUCTURAL PROGRESSION EVIDENCE LITE V1"]
        + [f"{key}={payload.get(key)}" for key in keys]
        + ["metric_rate_output_allowed=false", "canonical_event_count=UNKNOWN", "production_release=false"]
    ) + "\n"


def analyst_audit(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA ANALYST AUDIT — EVENT LABEL STRUCTURAL PROGRESSION EVIDENCE",
            f"Status: {payload.get('status')}",
            f"Visible evidence records: {payload.get('evidence_record_count', 0)}",
            f"Label verification: {payload.get('verification_status_counts')}",
            f"Axis eligibility: {payload.get('axis_eligibility_state_counts')}",
            f"Structural progression candidates: {payload.get('structural_progression_classification_counts')}",
            f"Persistence candidates: {payload.get('persistence_classification_counts')}",
            "Analyst-safe meaning: action-anchor label lineage, visible coordinate/zone relations and existing consequence windows were combined into component-first progression evidence candidates.",
            "These outputs do not establish true progression, a defensive line break, players bypassed, possession, sequence, tactical quality, causality or dominance.",
            "Progression rates remain blocked until denominator and eligibility gates are separately opened.",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
        ]
    ) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-labels", required=True)
    parser.add_argument("--action-bundles", required=True)
    parser.add_argument("--selected-action", required=True)
    parser.add_argument("--selected-event", required=True)
    parser.add_argument("--sequence-consequence", required=True)
    parser.add_argument("--aggregate-alignment", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = build_event_label_structural_progression_evidence(
        load_json(args.provider_labels, "provider_label_input_unreadable_or_malformed"),
        load_json(args.action_bundles, "action_bundle_input_unreadable_or_malformed"),
        load_json(args.selected_action, "selected_action_input_unreadable_or_malformed"),
        load_json(args.selected_event, "selected_event_input_unreadable_or_malformed"),
        load_json(args.sequence_consequence, "sequence_consequence_input_unreadable_or_malformed"),
        load_json(args.aggregate_alignment, "aggregate_alignment_input_unreadable_or_malformed"),
    )
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "evidence_record_count",
                    "verification_status_counts",
                    "axis_eligibility_state_counts",
                    "structural_progression_classification_counts",
                    "hard_block_hits",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
