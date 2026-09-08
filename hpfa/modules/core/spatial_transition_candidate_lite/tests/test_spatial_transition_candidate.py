from pathlib import Path

import pytest

from hpfa.modules.core.spatial_transition_candidate_lite.src.spatial_transition_candidate import (
    build_spatial_transition_candidates,
    validate_out,
)

BINDING = "msb_" + "a" * 24


def trace(x="60", y="30", family="PASS", evidence_ids=None):
    return {
        "trackable_action_trace_candidate_id": "tat_a",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidates": [family],
        "supporting_evidence_atom_ids": evidence_ids or ["ea_a"],
    }


def trace_payload(row=None):
    rows = [row or trace()]
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": rows,
        "trackable_action_trace_candidate_count": len(rows),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def atom(**updates):
    base = {
        "evidence_atom_id": "ea_a",
        "match_surface_binding_id": BINDING,
        "atom_status": "PASS",
        "semantic_rule_id": "plvs_v2_progressive_passes_accurate",
        "raw_label": "Progressive passes accurate",
        "zone_candidate": None,
        "progression_candidate": "PROGRESSIVE_CANDIDATE",
        "direction_candidate": None,
        "distance_candidate": None,
        "context_candidate": None,
        "relation_candidate": None,
        "outcome_candidates": ["SUCCESS"],
    }
    base.update(updates)
    return base


def evidence_payload(rows=None):
    atoms = rows or [atom()]
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def admission(**updates):
    base = {
        "match_surface_binding_id": BINDING,
        "coordinate_semantics_state": "ACTION_LOCATION_ADMITTED",
        "pitch_frame_state": "PITCH_FRAME_ADMITTED",
        "direction_normalization_state": "ATTACK_DIRECTION_ADMITTED",
        "attack_direction": "ATTACK_POS_X",
        "third_boundaries": [33.33, 66.67],
    }
    base.update(updates)
    return base


def test_provider_semantics_survive_without_geometry_admission():
    result = build_spatial_transition_candidates(trace_payload(), evidence_payload())
    row = result["spatial_transition_candidates"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["provider_progression_candidates"] == ["PROGRESSIVE_CANDIDATE"]
    assert row["provider_outcome_candidates"] == ["SUCCESS"]
    assert row["provider_semantic_spatial_context_visible"] is True
    assert row["provider_coordinate_anchor_x_candidate"] == 60.0
    assert row["spatial_admission_state"] == "PROVIDER_SPATIAL_CONTEXT_CANDIDATE_ONLY"
    assert row["coordinate_is_action_location_truth"] is False
    assert row["net_progression_candidate"] is None


def test_provider_zone_semantics_are_candidate_not_geometry_truth():
    result = build_spatial_transition_candidates(
        trace_payload(),
        evidence_payload([atom(zone_candidate="FINAL_THIRD")]),
    )
    row = result["spatial_transition_candidates"][0]
    assert row["provider_zone_candidates"] == ["FINAL_THIRD"]
    assert row["provider_zone_label_is_coordinate_geometry_truth"] is False
    assert row["coordinate_derived_zone_candidate"] is None


def test_admitted_coordinate_produces_location_not_displacement():
    result = build_spatial_transition_candidates(trace_payload(), evidence_payload(), admission())
    row = result["spatial_transition_candidates"][0]
    assert result["status"] == "PASS"
    assert row["spatial_admission_state"] == "ADMITTED_LOCATION_ONLY"
    assert row["attack_normalized_x_candidate"] == 60.0
    assert row["coordinate_derived_zone_candidate"] == "MIDDLE_THIRD_LOCATION_CANDIDATE"
    assert row["displacement_candidate"] is None
    assert result["vertical_progress_rate_allowed"] is False


def test_unknown_coordinate_semantics_blocks_spatial_promotion_but_keeps_provider_semantics():
    result = build_spatial_transition_candidates(
        trace_payload(), evidence_payload(), admission(coordinate_semantics_state="UNKNOWN")
    )
    row = result["spatial_transition_candidates"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["spatial_location_admitted_count"] == 0
    assert row["provider_progression_candidates"] == ["PROGRESSIVE_CANDIDATE"]


def test_unknown_direction_blocks_verticality_truth():
    result = build_spatial_transition_candidates(
        trace_payload(),
        evidence_payload(),
        admission(direction_normalization_state="UNKNOWN", attack_direction=None),
    )
    row = result["spatial_transition_candidates"][0]
    assert result["status"] == "REVIEW_REQUIRED"
    assert row["attack_normalized_x_candidate"] is None
    assert result["vertical_progress_rate_allowed"] is False


def test_negative_x_attack_is_normalized_without_claiming_displacement():
    result = build_spatial_transition_candidates(
        trace_payload(trace(x="-70")),
        evidence_payload(),
        admission(attack_direction="ATTACK_NEG_X", third_boundaries=[33.33, 66.67]),
    )
    row = result["spatial_transition_candidates"][0]
    assert row["attack_normalized_x_candidate"] == 70.0
    assert row["coordinate_derived_zone_candidate"] == "FINAL_THIRD_LOCATION_CANDIDATE"
    assert row["single_location_is_displacement_truth"] is False


def test_missing_coordinate_does_not_destroy_provider_semantic_candidate():
    result = build_spatial_transition_candidates(trace_payload(trace(x=None)), evidence_payload())
    row = result["spatial_transition_candidates"][0]
    assert row["coordinate_anchor_present"] is False
    assert row["provider_semantic_spatial_context_visible"] is True
    assert row["provider_progression_candidates"] == ["PROGRESSIVE_CANDIDATE"]


def test_missing_trace_evidence_reference_fails_closed():
    result = build_spatial_transition_candidates(
        trace_payload(trace(evidence_ids=["missing"])), evidence_payload()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("trace_evidence_reference_missing") for hit in result["hard_block_hits"])


def test_claim_locks_remain_closed():
    result = build_spatial_transition_candidates(trace_payload(), evidence_payload(), admission())
    row = result["spatial_transition_candidates"][0]
    assert row["provider_progressive_label_is_measured_displacement_truth"] is False
    assert row["provider_direction_label_is_attack_direction_normalization_truth"] is False
    assert result["displacement_computation_allowed"] is False
    assert result["vertical_progress_rate_allowed"] is False
    assert result["line_break_truth_allowed"] is False
    assert result["physical_speed_truth_allowed"] is False
    assert result["team_shape_truth_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_nested_phone_output_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/spatial_transition_candidate_lite/src/spatial_transition_candidate.py").read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray")
    assert not any(token in source for token in forbidden)
