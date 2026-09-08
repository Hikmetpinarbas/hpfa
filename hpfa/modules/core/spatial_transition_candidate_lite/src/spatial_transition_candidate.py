from __future__ import annotations

import hashlib
import json
from typing import Any

MODULE_ID = "spatial_transition_candidate_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_SPATIAL_TRANSITION_CANDIDATE_ONLY"
ALLOWED_DIRECTIONS = {"ATTACK_POS_X", "ATTACK_NEG_X"}
PROGRESSION_FAMILIES = {"PASS", "CARRY", "DRIBBLE", "CROSS"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_spatial_transition_candidates(
    trace_payload: dict[str, Any],
    spatial_admission: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_input_module_id_mismatch")
    if trace_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("trace_canonical_event_count_claimed")
    if trace_payload.get("production_release") is True:
        blocks.append("trace_production_release_claimed")
    if trace_payload.get("hard_block_hits"):
        blocks.append("trace_hard_blocks_present")

    binding = _clean(trace_payload.get("match_surface_binding_id"))
    if not binding or _clean(spatial_admission.get("match_surface_binding_id")) != binding:
        blocks.append("match_surface_binding_mismatch")

    coordinate_semantics = _clean(spatial_admission.get("coordinate_semantics_state"))
    pitch_frame = _clean(spatial_admission.get("pitch_frame_state"))
    direction_state = _clean(spatial_admission.get("direction_normalization_state"))
    attack_direction = _clean(spatial_admission.get("attack_direction"))
    if coordinate_semantics != "ACTION_LOCATION_ADMITTED":
        reviews.append("action_location_semantics_not_admitted")
    if pitch_frame != "PITCH_FRAME_ADMITTED":
        reviews.append("pitch_frame_not_admitted")
    if direction_state != "ATTACK_DIRECTION_ADMITTED" or attack_direction not in ALLOWED_DIRECTIONS:
        reviews.append("attack_direction_not_admitted")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    if not isinstance(traces, list):
        blocks.append("trackable_action_trace_candidates_invalid")
        traces = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_candidate_count_mismatch")

    records: list[dict[str, Any]] = []
    if not blocks:
        for trace in traces:
            if not isinstance(trace, dict):
                blocks.append("trace_record_invalid")
                continue
            trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
            x = _number(trace.get("pos_x_candidate"))
            y = _number(trace.get("pos_y_candidate"))
            families = sorted({_clean(v) for v in trace.get("action_family_candidates") or [] if _clean(v)})
            coordinate_present = trace.get("coordinate_evidence_status") == "COORDINATE_PRESENT" and x is not None and y is not None
            spatial_ready = (
                coordinate_present
                and coordinate_semantics == "ACTION_LOCATION_ADMITTED"
                and pitch_frame == "PITCH_FRAME_ADMITTED"
                and direction_state == "ATTACK_DIRECTION_ADMITTED"
                and attack_direction in ALLOWED_DIRECTIONS
            )
            normalized_x = None
            zone = None
            if spatial_ready:
                normalized_x = x if attack_direction == "ATTACK_POS_X" else -x
                thirds = spatial_admission.get("third_boundaries") or []
                if isinstance(thirds, list) and len(thirds) == 2 and all(_number(v) is not None for v in thirds):
                    low, high = sorted(float(v) for v in thirds)
                    if normalized_x < low:
                        zone = "DEFENSIVE_THIRD_LOCATION_CANDIDATE"
                    elif normalized_x < high:
                        zone = "MIDDLE_THIRD_LOCATION_CANDIDATE"
                    else:
                        zone = "FINAL_THIRD_LOCATION_CANDIDATE"
                else:
                    reviews.append("third_boundaries_not_admitted")
            progression_family_visible = bool(PROGRESSION_FAMILIES & set(families))
            records.append({
                "spatial_transition_candidate_id": "stc_" + _digest(binding, trace_id)[:24],
                "trackable_action_trace_candidate_id": trace_id,
                "match_surface_binding_id": binding,
                "team_identity_candidate_id": trace.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": trace.get("actor_identity_candidate_id"),
                "action_family_candidates": families,
                "observed_location_x_candidate": x,
                "observed_location_y_candidate": y,
                "attack_normalized_x_candidate": normalized_x,
                "location_zone_candidate": zone,
                "progression_family_visible": progression_family_visible,
                "spatial_admission_state": "ADMITTED_LOCATION_ONLY" if spatial_ready else "REVIEW_REQUIRED",
                "displacement_candidate": None,
                "net_progression_candidate": None,
                "vertical_progress_rate_candidate": None,
                "line_break_candidate": None,
                "physical_speed_candidate": None,
                "coordinate_is_action_location_truth": spatial_ready,
                "single_location_is_displacement_truth": False,
                "provider_progressive_label_is_measured_displacement_truth": False,
                "location_distribution_is_team_shape_truth": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "match_surface_binding_id": binding or None,
        "spatial_transition_candidates": records,
        "spatial_transition_candidate_count": len(records),
        "spatial_location_admitted_count": sum(r.get("spatial_admission_state") == "ADMITTED_LOCATION_ONLY" for r in records),
        "progression_family_visible_count": sum(bool(r.get("progression_family_visible")) for r in records),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "coordinate_semantics_state": coordinate_semantics,
        "pitch_frame_state": pitch_frame,
        "direction_normalization_state": direction_state,
        "attack_direction": attack_direction or None,
        "displacement_computation_allowed": False,
        "vertical_progress_rate_allowed": False,
        "line_break_truth_allowed": False,
        "physical_speed_truth_allowed": False,
        "team_shape_truth_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
