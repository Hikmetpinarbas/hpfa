from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


SHORT_ACTION_FAMILIES = {
    "PASS", "DRIBBLE", "DUEL", "TACKLE", "RECOVERY", "TURNOVER",
    "SHOT", "CARRY", "CROSS", "CLEARANCE", "INTERCEPTION", "FOUL",
    "GOALKEEPER_ACTION", "RESTART",
}
LONG_INTERVAL_FAMILIES = {
    "POSITIONAL_ATTACK", "INVOLVEMENT_IN_POSITIONAL_ATTACK",
    "COUNTERATTACK", "ATTACK_EPISODE", "TEAM_ATTACK",
}
PASS_LENGTH_MAP = {
    "Goal kicks short (0-15 m)": "PASS_LENGTH_SHORT_CANDIDATE",
    "Goal kicks medium (15-40 m)": "PASS_LENGTH_MEDIUM_CANDIDATE",
    "Goal kicks long (40+ m)": "PASS_LENGTH_LONG_CANDIDATE",
}
SPATIAL_ROLE_BY_FAMILY = {
    "SHOT": "SHOT_LOCATION_ANCHOR_CANDIDATE",
    "DRIBBLE": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "DUEL": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "TACKLE": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "RECOVERY": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "TURNOVER": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "PASS": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "CARRY": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "CROSS": "ACTION_LOCATION_ANCHOR_CANDIDATE",
    "TEAM_ATTACK": "EPISODE_SPATIAL_ANCHOR_CANDIDATE",
    "POSITIONAL_ATTACK": "EPISODE_SPATIAL_ANCHOR_CANDIDATE",
    "INVOLVEMENT_IN_POSITIONAL_ATTACK": "INHERITED_EPISODE_ANCHOR_CANDIDATE",
}


@dataclass(frozen=True)
class TimeSemanticResult:
    semantic_family: str
    interval_role: str
    midpoint_anchor_candidate: float | None
    chronology_relation: str
    physical_action_duration: bool = False


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def admit_time_semantics(
    *,
    semantic_family: str,
    start: float | int | str | None,
    end: float | int | str | None,
    family_admitted: bool,
    same_timestamp_peer: bool = False,
) -> TimeSemanticResult:
    """Precision-first family semantics for provider annotation intervals.

    This function never promotes row order to football chronology and never treats
    annotation-window length as physical action duration.
    """
    family = _norm(semantic_family)
    chronology_relation = "SAME_TIME_UNORDERED" if same_timestamp_peer else "ORDER_INDETERMINATE"
    start_f = _finite_float(start)
    end_f = _finite_float(end)

    if family in LONG_INTERVAL_FAMILIES:
        return TimeSemanticResult(
            semantic_family=family,
            interval_role="EPISODE_ANNOTATION_INTERVAL_CANDIDATE",
            midpoint_anchor_candidate=None,
            chronology_relation=chronology_relation,
        )

    if not family_admitted or family not in SHORT_ACTION_FAMILIES or start_f is None or end_f is None:
        return TimeSemanticResult(
            semantic_family=family,
            interval_role="ANNOTATION_INTERVAL_REVIEW_REQUIRED",
            midpoint_anchor_candidate=None,
            chronology_relation=chronology_relation,
        )

    duration = end_f - start_f
    if duration < 0 or abs(duration - 12.0) > 0.25:
        return TimeSemanticResult(
            semantic_family=family,
            interval_role="ANNOTATION_INTERVAL_REVIEW_REQUIRED",
            midpoint_anchor_candidate=None,
            chronology_relation=chronology_relation,
        )

    return TimeSemanticResult(
        semantic_family=family,
        interval_role="SHORT_ACTION_ANNOTATION_WINDOW_CANDIDATE",
        midpoint_anchor_candidate=(start_f + end_f) / 2.0,
        chronology_relation=chronology_relation,
    )


def admit_spatial_semantics(*, semantic_family: str, pos_x: Any, pos_y: Any) -> dict[str, Any]:
    family = _norm(semantic_family)
    role = SPATIAL_ROLE_BY_FAMILY.get(family, "SPATIAL_ANCHOR_REVIEW_REQUIRED")
    x = _finite_float(pos_x)
    y = _finite_float(pos_y)
    numeric = x is not None and y is not None

    return {
        "semantic_family": family,
        "spatial_role": role,
        "pos_x": x,
        "pos_y": y,
        "numeric_coordinate_pair": numeric,
        "coordinate_frame_status": "STRONGLY_SUPPORTED_CANDIDATE" if numeric else "UNRESOLVED",
        "coordinate_frame_candidate": "105x68_ATTACKING_DIRECTION_NORMALIZED_CANDIDATE" if numeric else None,
        "physical_player_coordinate": False,
        "endpoint_geometry": False,
        "player_trajectory": False,
        "physical_speed": False,
    }


def map_team_pass_length_candidate(
    *,
    raw_label: str,
    surface_role: str,
    action_family: str,
) -> dict[str, Any]:
    """Reinterpret the calibrated provider label only in Team+Pass context.

    Raw provider label is always preserved. Goalkeeper/restart surfaces are never
    remapped by this rule.
    """
    surface = _norm(surface_role)
    family = _norm(action_family)
    team_surface = surface == "TEAM" or surface.startswith("TEAM_SURFACE")
    candidate = PASS_LENGTH_MAP.get(raw_label) if team_surface and family == "PASS" else None
    return {
        "raw_provider_label": raw_label,
        "semantic_candidate": candidate,
        "mapping_status": "CALIBRATED_CANDIDATE" if candidate else "NOT_APPLIED",
        "literal_goal_kick": False if candidate else None,
        "goalkeeper_surface_remapped": False,
    }


def apply_calibrated_semantics_to_admission_payload(
    *,
    action_payload: dict[str, Any],
    admission_payload: dict[str, Any],
) -> dict[str, Any]:
    """Attach calibrated, claim-safe semantics to the current occurrence output.

    This is a sidecar enrichment of already-produced candidate objects. It does not
    create occurrences, does not change occurrence counts, and does not establish
    chronology, possession, phase, tracking, tactical or causal truth.
    """
    bundles = [
        row for row in action_payload.get("action_bundle_candidates") or []
        if isinstance(row, dict)
    ]
    semantics_by_bundle: dict[str, dict[str, Any]] = {}
    for bundle in bundles:
        bundle_id = str(bundle.get("action_bundle_candidate_id") or "").strip()
        if not bundle_id:
            continue
        family = _norm(bundle.get("action_family_candidate"))
        family_admitted = family in SHORT_ACTION_FAMILIES or family in LONG_INTERVAL_FAMILIES
        time_semantics = admit_time_semantics(
            semantic_family=family,
            start=bundle.get("start_candidate"),
            end=bundle.get("end_candidate"),
            family_admitted=family_admitted,
            same_timestamp_peer=bool(bundle.get("same_time_order_truth_admitted")),
        )
        spatial_semantics = admit_spatial_semantics(
            semantic_family=family,
            pos_x=bundle.get("pos_x_candidate"),
            pos_y=bundle.get("pos_y_candidate"),
        )
        pass_length_candidates = []
        for raw_label in bundle.get("raw_labels") or []:
            mapped = map_team_pass_length_candidate(
                raw_label=str(raw_label),
                surface_role=str(bundle.get("source_role") or ""),
                action_family=family,
            )
            if mapped.get("semantic_candidate"):
                pass_length_candidates.append(mapped)
        semantics_by_bundle[bundle_id] = {
            "action_bundle_candidate_id": bundle_id,
            "semantic_family": family,
            "time_semantics": asdict(time_semantics),
            "spatial_semantics": spatial_semantics,
            "pass_length_candidates": pass_length_candidates,
            "raw_labels_preserved": list(bundle.get("raw_labels") or []),
            "source_role": bundle.get("source_role"),
            "claim_locks": calibrated_claim_locks(),
        }

    enriched_occurrences = []
    for candidate in admission_payload.get("action_occurrence_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        candidate_copy = dict(candidate)
        refs = []
        for raw_id in candidate.get("supporting_action_bundle_candidate_ids") or []:
            bundle_id = str(raw_id or "").strip()
            if bundle_id in semantics_by_bundle:
                refs.append(bundle_id)
        candidate_copy["supporting_calibrated_semantics_bundle_ids"] = refs
        candidate_copy["calibrated_source_semantics_attached"] = bool(refs)
        enriched_occurrences.append(candidate_copy)

    output = dict(admission_payload)
    output["action_occurrence_candidates"] = enriched_occurrences
    output["calibrated_source_semantics_registry_status"] = "ATTACHED_CANDIDATE"
    output["calibrated_source_semantics_by_bundle"] = semantics_by_bundle
    output["calibrated_source_semantics_bundle_count"] = len(semantics_by_bundle)
    output["calibrated_source_semantics_occurrence_attachment_count"] = sum(
        bool(row.get("calibrated_source_semantics_attached")) for row in enriched_occurrences
    )
    output.update(calibrated_claim_locks())
    return output


def calibrated_claim_locks() -> dict[str, Any]:
    return {
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "causal_truth": False,
    }
