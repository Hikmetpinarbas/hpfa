from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import Counter
import math
from typing import Any


SHORT_ACTION_FAMILIES = {
    "PASS", "DRIBBLE", "DUEL", "TACKLE", "RECOVERY", "TURNOVER",
    "SHOT", "CARRY", "CROSS", "CLEARANCE", "INTERCEPTION", "FOUL",
    "GOALKEEPER_ACTION", "RESTART",
}
LONG_INTERVAL_FAMILIES = {
    "POSITIONAL_ATTACK", "INVOLVEMENT_IN_POSITIONAL_ATTACK",
    "COUNTERATTACK", "INVOLVEMENT_IN_COUNTERATTACK", "ATTACK_EPISODE", "TEAM_ATTACK",
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
    "COUNTERATTACK": "EPISODE_SPATIAL_ANCHOR_CANDIDATE",
    "INVOLVEMENT_IN_POSITIONAL_ATTACK": "INHERITED_EPISODE_ANCHOR_CANDIDATE",
    "INVOLVEMENT_IN_COUNTERATTACK": "INHERITED_EPISODE_ANCHOR_CANDIDATE",
}


@dataclass(frozen=True)
class TimeSemanticResult:
    semantic_family: str
    interval_role: str
    midpoint_anchor_candidate: float | None
    chronology_relation: str
    physical_action_duration: bool = False


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _same_time_key(row: dict[str, Any]) -> tuple[str, str, str] | None:
    period = str(row.get("period_candidate") or "").strip()
    start = _finite_float(row.get("start_candidate"))
    end = _finite_float(row.get("end_candidate"))
    if not period or start is None or end is None:
        return None
    return period, f"{start:.6f}", f"{end:.6f}"


def _family_from_non_action_atom(atom: dict[str, Any]) -> str:
    family_values = [str(item or "").strip() for item in (atom.get("action_family_candidates") or [])]
    for value in family_values:
        if value:
            return _norm(value)
    label = _norm(atom.get("raw_label"))
    if "INVOLVEMENT IN POSITIONAL ATTACK" in label:
        return "INVOLVEMENT_IN_POSITIONAL_ATTACK"
    if "INVOLVEMENT IN COUNTERATTACK" in label:
        return "INVOLVEMENT_IN_COUNTERATTACK"
    if "POSITIONAL ATTACK" in label:
        return "POSITIONAL_ATTACK"
    if "COUNTERATTACK" in label:
        return "COUNTERATTACK"
    return ""


def admit_time_semantics(
    *,
    semantic_family: str,
    start: float | int | str | None,
    end: float | int | str | None,
    family_admitted: bool,
    same_timestamp_peer: bool = False,
) -> TimeSemanticResult:
    family = _norm(semantic_family)
    chronology_relation = "SAME_TIME_UNORDERED" if same_timestamp_peer else "ORDER_INDETERMINATE"
    start_f = _finite_float(start)
    end_f = _finite_float(end)

    if family in LONG_INTERVAL_FAMILIES:
        if start_f is None or end_f is None or end_f < start_f:
            return TimeSemanticResult(
                semantic_family=family,
                interval_role="ANNOTATION_INTERVAL_REVIEW_REQUIRED",
                midpoint_anchor_candidate=None,
                chronology_relation=chronology_relation,
            )
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
    finite_pair = x is not None and y is not None
    in_declared_candidate_frame = bool(finite_pair and 0.0 <= x <= 105.0 and 0.0 <= y <= 68.0)

    return {
        "semantic_family": family,
        "spatial_role": role,
        "pos_x": x,
        "pos_y": y,
        "numeric_coordinate_pair": in_declared_candidate_frame,
        "coordinate_frame_status": "STRONGLY_SUPPORTED_CANDIDATE" if in_declared_candidate_frame else "UNRESOLVED",
        "coordinate_frame_candidate": "105x68_ATTACKING_DIRECTION_NORMALIZED_CANDIDATE" if in_declared_candidate_frame else None,
        "coordinate_range_valid_candidate": in_declared_candidate_frame,
        "physical_player_coordinate": False,
        "endpoint_geometry": False,
        "player_trajectory": False,
        "physical_speed": False,
    }


def map_team_pass_length_candidate(*, raw_label: str, surface_role: str, action_family: str) -> dict[str, Any]:
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


def _bundle_semantics(action_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bundles = [row for row in action_payload.get("action_bundle_candidates") or [] if isinstance(row, dict)]
    key_counts = Counter(key for row in bundles if (key := _same_time_key(row)) is not None)
    semantics_by_bundle: dict[str, dict[str, Any]] = {}

    for bundle in bundles:
        bundle_id = str(bundle.get("action_bundle_candidate_id") or "").strip()
        if not bundle_id:
            continue
        family = _norm(bundle.get("action_family_candidate"))
        family_admitted = family in SHORT_ACTION_FAMILIES or family in LONG_INTERVAL_FAMILIES
        same_time_peer = bool((key := _same_time_key(bundle)) is not None and key_counts.get(key, 0) > 1)
        time_semantics = admit_time_semantics(
            semantic_family=family,
            start=bundle.get("start_candidate"),
            end=bundle.get("end_candidate"),
            family_admitted=family_admitted,
            same_timestamp_peer=same_time_peer,
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
    return semantics_by_bundle


def _non_action_semantics(evidence_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for atom in (evidence_payload or {}).get("evidence_atoms") or []:
        if not isinstance(atom, dict):
            continue
        semantic_role = _norm(atom.get("semantic_role_candidate"))
        if semantic_role not in {"ATTRIBUTE_REFERENCE", "CONTEXT_INTERVAL", "PARTICIPATION_INTERVAL"}:
            continue
        atom_id = str(atom.get("evidence_atom_id") or "").strip()
        if not atom_id:
            continue
        family = _family_from_non_action_atom(atom)
        time_result = None
        if semantic_role in {"CONTEXT_INTERVAL", "PARTICIPATION_INTERVAL"} and family in LONG_INTERVAL_FAMILIES:
            time_result = asdict(admit_time_semantics(
                semantic_family=family,
                start=atom.get("start_candidate"),
                end=atom.get("end_candidate"),
                family_admitted=True,
                same_timestamp_peer=False,
            ))

        pass_length = None
        raw_label = str(atom.get("raw_label") or "")
        if semantic_role == "ATTRIBUTE_REFERENCE" and raw_label in PASS_LENGTH_MAP:
            pass_length = map_team_pass_length_candidate(
                raw_label=raw_label,
                surface_role=str(atom.get("source_role") or ""),
                action_family="PASS",
            )

        if time_result is None and not (pass_length and pass_length.get("semantic_candidate")):
            continue
        records[atom_id] = {
            "evidence_atom_id": atom_id,
            "semantic_role_candidate": semantic_role,
            "semantic_family": family or None,
            "time_semantics": time_result,
            "pass_length_candidate": pass_length,
            "raw_label_preserved": raw_label,
            "source_role": atom.get("source_role"),
            "claim_locks": calibrated_claim_locks(),
        }
    return records


def apply_calibrated_semantics_to_admission_payload(
    *,
    action_payload: dict[str, Any],
    admission_payload: dict[str, Any],
    evidence_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach calibrated semantics without creating action occurrences.

    ACTION_ANCHOR semantics are attached from the existing action-bundle surface.
    Attribute/context/participation semantics are read from the evidence inventory,
    because those rows are intentionally excluded from action bundles.
    """
    semantics_by_bundle = _bundle_semantics(action_payload)
    non_action_semantics = _non_action_semantics(evidence_payload)

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
    output["calibrated_non_action_semantics_by_evidence_atom"] = non_action_semantics
    output["calibrated_non_action_semantics_count"] = len(non_action_semantics)
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
