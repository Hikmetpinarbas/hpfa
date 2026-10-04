from hpfa.modules.core.spatial_transition_candidate_lite.src.spatial_transition_candidate import (
    build_spatial_transition_candidates,
)

BINDING = "msb_" + "b" * 24


def _trace_payload(*, x="60", y="30"):
    row = {
        "trackable_action_trace_candidate_id": "tat_a",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "12.0",
        "pos_x_candidate": x,
        "pos_y_candidate": y,
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidates": ["PASS"],
        "supporting_evidence_atom_ids": ["ea_a"],
    }
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": [row],
        "trackable_action_trace_candidate_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _evidence_payload():
    atom = {
        "evidence_atom_id": "ea_a",
        "match_surface_binding_id": BINDING,
        "atom_status": "PASS",
        "semantic_rule_id": "plvs_v2_passes_accurate",
        "raw_label": "Passes accurate",
        "zone_candidate": None,
        "progression_candidate": None,
        "direction_candidate": None,
        "distance_candidate": None,
        "context_candidate": None,
        "relation_candidate": None,
        "outcome_candidates": ["SUCCESS"],
    }
    return {
        "module_id": "evidence_atom_inventory_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": [atom],
        "evidence_atom_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrence_payload(*, x="60", physical_truth=False):
    row = {
        "action_occurrence_candidate_id": "aoc_anchor_a",
        "action_occurrence_candidate_is_event_truth": False,
        "validated_event_identity": False,
        "provider_semantics_binding_status": "PASS",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": "actor_a",
        "temporal_relation": {
            "period_candidate": "1",
            "start_candidate": "10.0",
            "end_candidate": "12.0",
            "relation": "EXACT_SINGLE_ACTION_ANCHOR_CORE",
            "internal_order": "UNKNOWN",
        },
        "location": {
            "pos_x_candidate": x,
            "pos_y_candidate": "30",
            "semantic_role": "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
            "physical_player_position_truth": physical_truth,
        },
    }
    return {
        "module_id": "action_occurrence_admission_lite_v1",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "action_occurrence_candidates": [],
        "single_action_anchor_occurrence_candidates": [row],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_occurrence_bound_annotation_anchor_closes_action_location_semantics_only():
    result = build_spatial_transition_candidates(
        _trace_payload(),
        _evidence_payload(),
        None,
        _occurrence_payload(),
    )
    row = result["spatial_transition_candidates"][0]

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["action_location_semantics_admitted_count"] == 1
    assert result["occurrence_annotation_anchor_location_admitted_count"] == 1
    assert result["coordinate_semantics_state"] == "ANNOTATION_ANCHOR_LOCATION_ADMITTED"
    assert "action_location_semantics_not_admitted" not in result["review_hits"]
    assert "pitch_frame_not_admitted" in result["review_hits"]
    assert "attack_direction_not_admitted" in result["review_hits"]

    assert row["spatial_admission_state"] == "ANNOTATION_ANCHOR_LOCATION_ADMITTED"
    assert row["occurrence_annotation_anchor_location_admitted"] is True
    assert row["coordinate_is_admitted_annotation_anchor_location"] is True
    assert row["coordinate_is_action_location_truth"] is False
    assert row["annotation_anchor_is_physical_player_position_truth"] is False
    assert row["attack_normalized_x_candidate"] is None
    assert row["coordinate_derived_zone_candidate"] is None
    assert row["displacement_candidate"] is None
    assert result["occurrence_annotation_anchor_admission_is_tracking_truth"] is False
    assert result["production_release"] is False


def test_unmatched_occurrence_core_does_not_admit_action_location():
    result = build_spatial_transition_candidates(
        _trace_payload(),
        _evidence_payload(),
        None,
        _occurrence_payload(x="61"),
    )
    row = result["spatial_transition_candidates"][0]

    assert result["action_location_semantics_admitted_count"] == 0
    assert "action_location_semantics_not_admitted" in result["review_hits"]
    assert row["occurrence_annotation_anchor_location_admitted"] is False
    assert row["coordinate_is_admitted_annotation_anchor_location"] is False


def test_physical_position_truth_claim_is_not_consumed_as_annotation_anchor_admission():
    result = build_spatial_transition_candidates(
        _trace_payload(),
        _evidence_payload(),
        None,
        _occurrence_payload(physical_truth=True),
    )

    assert result["action_location_semantics_admitted_count"] == 0
    assert "action_location_semantics_not_admitted" in result["review_hits"]
    assert result["occurrence_annotation_anchor_admission_is_physical_position_truth"] is False
    assert result["occurrence_annotation_anchor_admission_is_tracking_truth"] is False
