from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MODULE_ID = "spatial_transition_candidate_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
OCCURRENCE_MODULE_ID = "action_occurrence_admission_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_SPATIAL_TRANSITION_CANDIDATE_ONLY"
ALLOWED_DIRECTIONS = {"ATTACK_POS_X", "ATTACK_NEG_X"}
PROGRESSION_FAMILIES = {"PASS", "CARRY", "DRIBBLE", "CROSS"}
OUTPUTS = {
    "json": "spatial_transition_candidate_lite_v1.json",
    "summary": "spatial_transition_candidate_lite_v1.txt",
    "analyst": "spatial_transition_candidate_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _number_key(value: Any) -> str:
    number = _number(value)
    return "" if number is None else f"{number:.6f}"


def _digest(*values: Any) -> str:
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


def _semantic_values(atoms: list[dict[str, Any]], field: str) -> list[str]:
    values: set[str] = set()
    for atom in atoms:
        raw = atom.get(field)
        if isinstance(raw, list):
            values.update(_clean(value) for value in raw if _clean(value))
        elif _clean(raw):
            values.add(_clean(raw))
    return sorted(values)


def _trace_location_core(trace: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(trace.get("team_identity_candidate_id")),
        _clean(trace.get("actor_identity_candidate_id")),
        _clean(trace.get("period_candidate")),
        _number_key(trace.get("start_candidate")),
        _number_key(trace.get("end_candidate")),
        _number_key(trace.get("pos_x_candidate")),
        _number_key(trace.get("pos_y_candidate")),
    )


def _occurrence_location_core(row: dict[str, Any]) -> tuple[str, ...]:
    temporal = row.get("temporal_relation") if isinstance(row.get("temporal_relation"), dict) else {}
    location = row.get("location") if isinstance(row.get("location"), dict) else {}
    return (
        _clean(row.get("team_identity_candidate_id")),
        _clean(row.get("actor_identity_candidate_id")),
        _clean(temporal.get("period_candidate")),
        _number_key(temporal.get("start_candidate")),
        _number_key(temporal.get("end_candidate")),
        _number_key(location.get("pos_x_candidate")),
        _number_key(location.get("pos_y_candidate")),
    )


def _occurrence_action_location_cores(
    payload: dict[str, Any] | None,
    binding: str,
    blocks: list[str],
) -> set[tuple[str, ...]]:
    if not payload:
        return set()
    if payload.get("module_id") != OCCURRENCE_MODULE_ID:
        blocks.append("occurrence_input_module_id_mismatch")
        return set()
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("occurrence_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("occurrence_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append("occurrence_hard_blocks_present")
    occurrence_binding = _clean(payload.get("match_surface_binding_id"))
    if not occurrence_binding or occurrence_binding != binding:
        blocks.append("occurrence_match_surface_binding_mismatch")

    cores: set[tuple[str, ...]] = set()
    for inventory_key in (
        "action_occurrence_candidates",
        "single_action_anchor_occurrence_candidates",
    ):
        rows = payload.get(inventory_key) or []
        if not isinstance(rows, list):
            blocks.append(f"occurrence_inventory_invalid:{inventory_key}")
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                blocks.append(f"occurrence_record_invalid:{inventory_key}:{index}")
                continue
            if _clean(row.get("match_surface_binding_id")) != binding:
                blocks.append(f"occurrence_record_binding_mismatch:{inventory_key}:{index}")
                continue
            location = row.get("location")
            if not isinstance(location, dict):
                continue
            if location.get("semantic_role") != "ANNOTATION_ANCHOR_LOCATION_CANDIDATE":
                continue
            if location.get("physical_player_position_truth") is not False:
                continue
            if row.get("action_occurrence_candidate_is_event_truth") is not False:
                continue
            if row.get("validated_event_identity") is not False:
                continue
            if row.get("provider_semantics_binding_status") != "PASS":
                continue
            core = _occurrence_location_core(row)
            if all(core):
                cores.add(core)
    return cores


def build_spatial_transition_candidates(
    trace_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    spatial_admission: dict[str, Any] | None = None,
    occurrence_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    spatial_admission = dict(spatial_admission or {})

    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_input_module_id_mismatch")
    if evidence_payload.get("module_id") != EVIDENCE_MODULE_ID:
        blocks.append("evidence_input_module_id_mismatch")
    for prefix, payload in (("trace", trace_payload), ("evidence", evidence_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    trace_binding = _clean(trace_payload.get("match_surface_binding_id"))
    evidence_binding = _clean(evidence_payload.get("match_surface_binding_id"))
    if not trace_binding or trace_binding != evidence_binding:
        blocks.append("match_surface_binding_mismatch")
    binding = trace_binding
    admission_binding = _clean(spatial_admission.get("match_surface_binding_id"))
    if admission_binding and admission_binding != binding:
        blocks.append("spatial_admission_binding_mismatch")

    coordinate_semantics = _clean(spatial_admission.get("coordinate_semantics_state")) or "UNKNOWN"
    pitch_frame = _clean(spatial_admission.get("pitch_frame_state")) or "UNKNOWN"
    direction_state = _clean(spatial_admission.get("direction_normalization_state")) or "UNKNOWN"
    attack_direction = _clean(spatial_admission.get("attack_direction"))
    explicit_action_location_admission = coordinate_semantics == "ACTION_LOCATION_ADMITTED"
    if pitch_frame != "PITCH_FRAME_ADMITTED":
        reviews.append("pitch_frame_not_admitted")
    if direction_state != "ATTACK_DIRECTION_ADMITTED" or attack_direction not in ALLOWED_DIRECTIONS:
        reviews.append("attack_direction_not_admitted")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    atoms = evidence_payload.get("evidence_atoms") or []
    if not isinstance(traces, list):
        blocks.append("trackable_action_trace_candidates_invalid")
        traces = []
    if not isinstance(atoms, list):
        blocks.append("evidence_atoms_invalid")
        atoms = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_candidate_count_mismatch")
    if evidence_payload.get("evidence_atom_count") != len(atoms):
        blocks.append("evidence_atom_count_mismatch")

    occurrence_location_cores = _occurrence_action_location_cores(
        occurrence_payload,
        binding,
        blocks,
    )

    atom_by_id: dict[str, dict[str, Any]] = {}
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_invalid:{index}")
            continue
        atom_id = _clean(atom.get("evidence_atom_id"))
        if not atom_id or atom_id in atom_by_id:
            blocks.append(f"evidence_atom_id_invalid_or_duplicate:{index}")
            continue
        if _clean(atom.get("match_surface_binding_id")) != binding:
            blocks.append(f"evidence_atom_binding_mismatch:{index}")
        atom_by_id[atom_id] = atom

    records: list[dict[str, Any]] = []
    if not blocks:
        for index, trace in enumerate(traces):
            if not isinstance(trace, dict):
                blocks.append(f"trace_record_invalid:{index}")
                continue
            trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
            if not trace_id:
                blocks.append(f"trace_id_missing:{index}")
                continue
            evidence_ids = [_clean(value) for value in trace.get("supporting_evidence_atom_ids") or [] if _clean(value)]
            support_atoms: list[dict[str, Any]] = []
            for evidence_id in evidence_ids:
                atom = atom_by_id.get(evidence_id)
                if atom is None:
                    blocks.append(f"trace_evidence_reference_missing:{trace_id}:{evidence_id}")
                else:
                    support_atoms.append(atom)

            x = _number(trace.get("pos_x_candidate"))
            y = _number(trace.get("pos_y_candidate"))
            families = sorted({_clean(v) for v in trace.get("action_family_candidates") or [] if _clean(v)})
            coordinate_present = trace.get("coordinate_evidence_status") == "COORDINATE_PRESENT" and x is not None and y is not None
            occurrence_action_location_admitted = (
                coordinate_present
                and _trace_location_core(trace) in occurrence_location_cores
            )
            action_location_admitted = bool(
                coordinate_present
                and (explicit_action_location_admission or occurrence_action_location_admitted)
            )
            spatial_ready = (
                action_location_admitted
                and pitch_frame == "PITCH_FRAME_ADMITTED"
                and direction_state == "ATTACK_DIRECTION_ADMITTED"
                and attack_direction in ALLOWED_DIRECTIONS
            )

            normalized_x = None
            coordinate_zone = None
            if spatial_ready:
                normalized_x = x if attack_direction == "ATTACK_POS_X" else -x
                thirds = spatial_admission.get("third_boundaries") or []
                if isinstance(thirds, list) and len(thirds) == 2 and all(_number(v) is not None for v in thirds):
                    low, high = sorted(float(v) for v in thirds)
                    if normalized_x < low:
                        coordinate_zone = "DEFENSIVE_THIRD_LOCATION_CANDIDATE"
                    elif normalized_x < high:
                        coordinate_zone = "MIDDLE_THIRD_LOCATION_CANDIDATE"
                    else:
                        coordinate_zone = "FINAL_THIRD_LOCATION_CANDIDATE"
                else:
                    reviews.append("third_boundaries_not_admitted")

            zone_candidates = _semantic_values(support_atoms, "zone_candidate")
            progression_candidates = _semantic_values(support_atoms, "progression_candidate")
            direction_candidates = _semantic_values(support_atoms, "direction_candidate")
            distance_candidates = _semantic_values(support_atoms, "distance_candidate")
            context_candidates = _semantic_values(support_atoms, "context_candidate")
            relation_candidates = _semantic_values(support_atoms, "relation_candidate")
            outcome_candidates = _semantic_values(support_atoms, "outcome_candidates")
            semantic_rule_ids = _semantic_values(support_atoms, "semantic_rule_id")
            raw_labels = _semantic_values(support_atoms, "raw_label")
            semantic_candidate_visible = bool(
                zone_candidates
                or progression_candidates
                or direction_candidates
                or distance_candidates
                or context_candidates
                or relation_candidates
            )
            progression_family_visible = bool(PROGRESSION_FAMILIES & set(families))

            if spatial_ready:
                spatial_admission_state = "ADMITTED_LOCATION_ONLY"
            elif occurrence_action_location_admitted:
                spatial_admission_state = "ANNOTATION_ANCHOR_LOCATION_ADMITTED"
            elif explicit_action_location_admission and coordinate_present:
                spatial_admission_state = "ACTION_LOCATION_SEMANTICS_ADMITTED"
            else:
                spatial_admission_state = "PROVIDER_SPATIAL_CONTEXT_CANDIDATE_ONLY"

            records.append({
                "spatial_transition_candidate_id": "stc_" + _digest(binding, trace_id)[:24],
                "trackable_action_trace_candidate_id": trace_id,
                "match_surface_binding_id": binding,
                "team_identity_candidate_id": trace.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": trace.get("actor_identity_candidate_id"),
                "action_family_candidates": families,
                "supporting_evidence_atom_ids": evidence_ids,
                "provider_semantic_rule_ids": semantic_rule_ids,
                "raw_labels": raw_labels,
                "provider_zone_candidates": zone_candidates,
                "provider_progression_candidates": progression_candidates,
                "provider_direction_candidates": direction_candidates,
                "provider_distance_candidates": distance_candidates,
                "provider_context_candidates": context_candidates,
                "provider_relation_candidates": relation_candidates,
                "provider_outcome_candidates": outcome_candidates,
                "provider_semantic_spatial_context_visible": semantic_candidate_visible,
                "provider_coordinate_anchor_x_candidate": x,
                "provider_coordinate_anchor_y_candidate": y,
                "coordinate_anchor_present": coordinate_present,
                "occurrence_annotation_anchor_location_admitted": occurrence_action_location_admitted,
                "action_location_semantics_admitted": action_location_admitted,
                "attack_normalized_x_candidate": normalized_x,
                "coordinate_derived_zone_candidate": coordinate_zone,
                "progression_family_visible": progression_family_visible,
                "spatial_admission_state": spatial_admission_state,
                "displacement_candidate": None,
                "net_progression_candidate": None,
                "vertical_progress_rate_candidate": None,
                "line_break_candidate": None,
                "physical_speed_candidate": None,
                "coordinate_is_action_location_truth": spatial_ready,
                "coordinate_is_admitted_annotation_anchor_location": occurrence_action_location_admitted,
                "annotation_anchor_is_physical_player_position_truth": False,
                "single_location_is_displacement_truth": False,
                "provider_zone_label_is_coordinate_geometry_truth": False,
                "provider_progressive_label_is_measured_displacement_truth": False,
                "provider_direction_label_is_attack_direction_normalization_truth": False,
                "location_distribution_is_team_shape_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    coordinate_anchor_count = sum(bool(r.get("coordinate_anchor_present")) for r in records)
    action_location_admitted_count = sum(bool(r.get("action_location_semantics_admitted")) for r in records)
    occurrence_anchor_admitted_count = sum(bool(r.get("occurrence_annotation_anchor_location_admitted")) for r in records)
    if not blocks and not explicit_action_location_admission:
        if coordinate_anchor_count and action_location_admitted_count == coordinate_anchor_count:
            coordinate_semantics = "ANNOTATION_ANCHOR_LOCATION_ADMITTED"
        elif action_location_admitted_count:
            coordinate_semantics = "ANNOTATION_ANCHOR_LOCATION_PARTIALLY_ADMITTED"
            reviews.append("action_location_semantics_partially_admitted")
        else:
            reviews.append("action_location_semantics_not_admitted")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding or None,
        "spatial_transition_candidates": records,
        "spatial_transition_candidate_count": len(records),
        "provider_semantic_spatial_context_visible_count": sum(bool(r.get("provider_semantic_spatial_context_visible")) for r in records),
        "coordinate_anchor_present_count": coordinate_anchor_count,
        "action_location_semantics_admitted_count": action_location_admitted_count,
        "occurrence_annotation_anchor_location_admitted_count": occurrence_anchor_admitted_count,
        "spatial_location_admitted_count": sum(r.get("spatial_admission_state") == "ADMITTED_LOCATION_ONLY" for r in records),
        "progression_family_visible_count": sum(bool(r.get("progression_family_visible")) for r in records),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "coordinate_semantics_state": coordinate_semantics,
        "pitch_frame_state": pitch_frame,
        "direction_normalization_state": direction_state,
        "attack_direction": attack_direction or None,
        "occurrence_annotation_anchor_admission_is_physical_position_truth": False,
        "occurrence_annotation_anchor_admission_is_tracking_truth": False,
        "provider_semantics_can_enrich_without_geometry_truth": True,
        "displacement_computation_allowed": False,
        "vertical_progress_rate_allowed": False,
        "line_break_truth_allowed": False,
        "physical_speed_truth_allowed": False,
        "team_shape_truth_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA SPATIAL TRANSITION CANDIDATE LITE V1",
        f"status={payload.get('status')}",
        f"spatial_transition_candidate_count={payload.get('spatial_transition_candidate_count')}",
        f"provider_semantic_spatial_context_visible_count={payload.get('provider_semantic_spatial_context_visible_count')}",
        f"coordinate_anchor_present_count={payload.get('coordinate_anchor_present_count')}",
        f"action_location_semantics_admitted_count={payload.get('action_location_semantics_admitted_count')}",
        f"occurrence_annotation_anchor_location_admitted_count={payload.get('occurrence_annotation_anchor_location_admitted_count')}",
        f"spatial_location_admitted_count={payload.get('spatial_location_admitted_count')}",
        f"review_hits={payload.get('review_hits')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — SPATIAL TRANSITION CANDIDATE",
        f"Provider-semantic spatial/context candidates visible: {payload.get('provider_semantic_spatial_context_visible_count', 0)}",
        f"Coordinate anchors visible: {payload.get('coordinate_anchor_present_count', 0)}",
        f"Occurrence-bound annotation-anchor locations admitted: {payload.get('occurrence_annotation_anchor_location_admitted_count', 0)}",
        f"Coordinate locations fully admitted: {payload.get('spatial_location_admitted_count', 0)}",
        "SAFE_MEANING: an occurrence-bound annotation anchor can establish that a visible coordinate pair belongs to that admitted occurrence candidate without establishing physical player position, pitch frame or attack direction.",
        "FORBIDDEN_INFERENCE: one pos_x/pos_y annotation anchor is not tracking, physical player position, start/end displacement, physical speed, line-break geometry, team shape, compactness or pitch control.",
        "ANALYST_ACTION: use admitted annotation anchors for occurrence-local evidence drill-down; require explicit pitch-frame and attack-direction admission before geometric progression claims.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trackable-action-trace", required=True)
    parser.add_argument("--evidence-atoms", required=True)
    parser.add_argument("--spatial-admission")
    parser.add_argument("--action-occurrence-admission")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    trace_payload = load_json(args.trackable_action_trace, "trackable_action_trace_input_unreadable_or_malformed")
    evidence_payload = load_json(args.evidence_atoms, "evidence_atom_input_unreadable_or_malformed")
    admission = load_json(args.spatial_admission, "spatial_admission_input_unreadable_or_malformed") if args.spatial_admission else None
    occurrence = load_json(args.action_occurrence_admission, "action_occurrence_admission_input_unreadable_or_malformed") if args.action_occurrence_admission else None
    payload = build_spatial_transition_candidates(trace_payload, evidence_payload, admission, occurrence)
    write_outputs(payload, args.out)
    print(json.dumps({
        "status": payload.get("status"),
        "spatial_transition_candidate_count": payload.get("spatial_transition_candidate_count"),
        "provider_semantic_spatial_context_visible_count": payload.get("provider_semantic_spatial_context_visible_count"),
        "coordinate_anchor_present_count": payload.get("coordinate_anchor_present_count"),
        "action_location_semantics_admitted_count": payload.get("action_location_semantics_admitted_count"),
        "occurrence_annotation_anchor_location_admitted_count": payload.get("occurrence_annotation_anchor_location_admitted_count"),
        "spatial_location_admitted_count": payload.get("spatial_location_admitted_count"),
        "hard_block_hits": payload.get("hard_block_hits") or [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())