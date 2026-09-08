from pathlib import Path

from hpfa.modules.core.spatial_transition_candidate_lite.src.spatial_transition_candidate import build_spatial_transition_candidates

BINDING = "msb_" + "a" * 24


def trace(x="60", y="30", family="PASS"):
    return {
        "trackable_action_trace_candidate_id": "tat_a",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidates": [family],
    }


def payload(row=None):
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


def test_admitted_coordinate_produces_location_not_displacement():
    result = build_spatial_transition_candidates(payload(), admission())
    row = result["spatial_transition_candidates"][0]
    assert result["status"] == "PASS"
    assert row["spatial_admission_state"] == "ADMITTED_LOCATION_ONLY"
    assert row["attack_normalized_x_candidate"] == 60.0
    assert row["location_zone_candidate"] == "MIDDLE_THIRD_LOCATION_CANDIDATE"
    assert row["displacement_candidate"] is None
    assert result["vertical_progress_rate_allowed"] is False


def test_unknown_coordinate_semantics_blocks_spatial_promotion():
    result = build_spatial_transition_candidates(payload(), admission(coordinate_semantics_state="UNKNOWN"))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["spatial_location_admitted_count"] == 0


def test_unknown_direction_blocks_verticality_truth():
    result = build_spatial_transition_candidates(payload(), admission(direction_normalization_state="UNKNOWN", attack_direction=None))
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["spatial_transition_candidates"][0]
    assert row["attack_normalized_x_candidate"] is None
    assert result["vertical_progress_rate_allowed"] is False


def test_negative_x_attack_is_normalized_without_claiming_displacement():
    result = build_spatial_transition_candidates(payload(trace(x="-70")), admission(attack_direction="ATTACK_NEG_X", third_boundaries=[33.33, 66.67]))
    row = result["spatial_transition_candidates"][0]
    assert row["attack_normalized_x_candidate"] == 70.0
    assert row["location_zone_candidate"] == "FINAL_THIRD_LOCATION_CANDIDATE"
    assert row["single_location_is_displacement_truth"] is False


def test_progressive_family_or_label_cannot_become_measured_displacement():
    result = build_spatial_transition_candidates(payload(trace(family="PASS")), admission())
    row = result["spatial_transition_candidates"][0]
    assert row["progression_family_visible"] is True
    assert row["provider_progressive_label_is_measured_displacement_truth"] is False
    assert row["net_progression_candidate"] is None


def test_missing_coordinate_is_review_required():
    result = build_spatial_transition_candidates(payload(trace(x=None)), admission())
    row = result["spatial_transition_candidates"][0]
    assert row["spatial_admission_state"] == "REVIEW_REQUIRED"
    assert row["coordinate_is_action_location_truth"] is False


def test_claim_locks_remain_closed():
    result = build_spatial_transition_candidates(payload(), admission())
    assert result["displacement_computation_allowed"] is False
    assert result["vertical_progress_rate_allowed"] is False
    assert result["line_break_truth_allowed"] is False
    assert result["physical_speed_truth_allowed"] is False
    assert result["team_shape_truth_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/spatial_transition_candidate_lite/src/spatial_transition_candidate.py").read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray")
    assert not any(token in source for token in forbidden)
