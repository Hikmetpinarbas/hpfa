from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from full_spine_runner import _spatial_progression_analyst_evidence


def _sidecar(*, progression_count: int = 3, adverse_count: int = 1) -> dict:
    return {
        "state_transition_dynamics": {
            "module_id": "state_transition_dynamics_lite_v1",
            "status": "REVIEW_REQUIRED",
            "match_surface_binding_id": "msb_generic",
            "state_transition_dynamics_candidate_count": 5,
            "provider_progression_semantic_transition_count": progression_count,
            "adverse_consequence_transition_count": adverse_count,
            "admitted_directional_transition_count": 0,
            "transition_class_counts": {
                "PROGRESSIVE_TO_SAME_TEAM_CONTINUATION_CANDIDATE": 2,
                "PROGRESSIVE_TO_ADVERSE_HANDOVER_CANDIDATE": adverse_count,
            },
            "claim_ceiling": "SEMANTIC_SPATIAL_CONSEQUENCE_ASSOCIATION_ONLY",
            "hard_block_hits": [],
        },
        "spatial_transition_candidate": {
            "module_id": "spatial_transition_candidate_lite_v1",
            "status": "REVIEW_REQUIRED",
            "match_surface_binding_id": "msb_generic",
            "coordinate_anchor_present_count": 10,
            "action_location_semantics_admitted_count": 8,
            "occurrence_annotation_anchor_location_admitted_count": 8,
            "spatial_location_admitted_count": 0,
            "coordinate_semantics_state": "ANNOTATION_ANCHOR_LOCATION_PARTIALLY_ADMITTED",
            "provider_team_relative_attack_axis_state": "ADMITTED",
            "attack_direction": "ATTACK_POS_X",
            "attack_direction_admission_basis": "CROSS_TEAM_REVIEWED_ANCHOR_ZONE_COORDINATE_ORDER",
            "pitch_frame_state": "UNKNOWN",
            "direction_normalization_state": "ATTACK_DIRECTION_ADMITTED",
            "hard_block_hits": [],
        },
    }


def test_main_spine_projection_preserves_visible_progression_consequence_counts():
    evidence = _spatial_progression_analyst_evidence(_sidecar())

    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["provider_progression_semantic_transition_count"] == 3
    assert evidence["adverse_consequence_transition_count"] == 1
    assert evidence["state_transition_dynamics_candidate_count"] == 5
    assert evidence["transition_class_counts"]["PROGRESSIVE_TO_SAME_TEAM_CONTINUATION_CANDIDATE"] == 2
    assert evidence["claim_ceiling"] == "SEMANTIC_SPATIAL_CONSEQUENCE_ASSOCIATION_ONLY"


def test_main_spine_projection_exposes_admitted_location_and_provider_attack_axis():
    evidence = _spatial_progression_analyst_evidence(_sidecar())

    assert evidence["coordinate_anchor_present_count"] == 10
    assert evidence["action_location_semantics_admitted_count"] == 8
    assert evidence["occurrence_annotation_anchor_location_admitted_count"] == 8
    assert evidence["coordinate_semantics_state"] == "ANNOTATION_ANCHOR_LOCATION_PARTIALLY_ADMITTED"
    assert evidence["provider_team_relative_attack_axis_state"] == "ADMITTED"
    assert evidence["attack_direction"] == "ATTACK_POS_X"
    assert evidence["attack_direction_admission_basis"] == "CROSS_TEAM_REVIEWED_ANCHOR_ZONE_COORDINATE_ORDER"
    assert evidence["pitch_frame_state"] == "UNKNOWN"
    assert evidence["direction_normalization_state"] == "ATTACK_DIRECTION_ADMITTED"
    assert evidence["spatial_location_admitted_count"] == 0


def test_main_spine_projection_does_not_promote_spatial_semantics_to_geometry_tracking_or_causality():
    evidence = _spatial_progression_analyst_evidence(_sidecar())

    assert evidence["provider_progression_is_measured_displacement_truth"] is False
    assert evidence["coordinate_is_tracking_truth"] is False
    assert evidence["occurrence_annotation_anchor_is_physical_position_truth"] is False
    assert evidence["team_relative_attack_axis_is_absolute_pitch_frame_truth"] is False
    assert evidence["provider_semantic_zone_coordinate_order_is_tactical_truth"] is False
    assert evidence["possession_truth"] is False
    assert evidence["sequence_truth"] is False
    assert evidence["tactical_pattern_truth"] is False
    assert evidence["causality_truth"] is False
    assert evidence["production_release"] is False


def test_zero_visible_progression_count_is_not_counterevidence():
    evidence = _spatial_progression_analyst_evidence(
        _sidecar(progression_count=0, adverse_count=0)
    )

    assert evidence["provider_progression_semantic_transition_count"] == 0
    assert evidence["adverse_consequence_transition_count"] == 0
    assert evidence["zero_count_is_counterevidence"] is False


def test_missing_state_transition_surface_stays_not_evaluated():
    evidence = _spatial_progression_analyst_evidence({})

    assert evidence["status"] == "NOT_EVALUATED"
    assert evidence["provider_progression_semantic_transition_count"] is None
    assert evidence["adverse_consequence_transition_count"] is None
    assert evidence["coordinate_anchor_present_count"] is None
    assert evidence["provider_team_relative_attack_axis_state"] == "NOT_EVALUATED"
    assert evidence["zero_count_is_counterevidence"] is False
