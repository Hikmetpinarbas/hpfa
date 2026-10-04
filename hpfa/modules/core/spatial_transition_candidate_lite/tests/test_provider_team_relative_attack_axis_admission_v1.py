from hpfa.modules.core.spatial_transition_candidate_lite.src.spatial_transition_candidate import (
    build_spatial_transition_candidates,
)

BINDING = "msb_" + "c" * 24
SEMANTICS = {
    "OWN_HALF": ("plvs_v2_lost_balls_in_own_half", "TURNOVER"),
    "OPPONENT_HALF": ("plvs_v2_ball_recoveries_in_opponent_s_half", "RECOVERY"),
    "FINAL_THIRD": ("plvs_v2_dribbling_in_the_final_third_successful", "DRIBBLE"),
    "PENALTY_AREA": ("plvs_v2_passes_into_the_penalty_box_accurate", "PASS"),
}


def _trace(trace_id, team, actor, start, x, evidence_id, family):
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": "1",
        "start_candidate": str(start),
        "end_candidate": str(start + 1),
        "pos_x_candidate": str(x),
        "pos_y_candidate": "30",
        "coordinate_evidence_status": "COORDINATE_PRESENT",
        "action_family_candidates": [family],
        "supporting_evidence_atom_ids": [evidence_id],
    }


def _atom(evidence_id, zone):
    rule_id, _family = SEMANTICS[zone]
    return {
        "evidence_atom_id": evidence_id,
        "match_surface_binding_id": BINDING,
        "atom_status": "PASS",
        "semantic_rule_id": rule_id,
        "raw_label": zone,
        "zone_candidate": zone,
        "progression_candidate": None,
        "direction_candidate": None,
        "distance_candidate": None,
        "context_candidate": None,
        "relation_candidate": None,
        "outcome_candidates": [],
    }


def _occurrence(trace):
    return {
        "action_occurrence_candidate_id": f"aoc_{trace['trackable_action_trace_candidate_id']}",
        "action_occurrence_candidate_is_event_truth": False,
        "validated_event_identity": False,
        "provider_semantics_binding_status": "PASS",
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": trace["team_identity_candidate_id"],
        "actor_identity_candidate_id": trace["actor_identity_candidate_id"],
        "temporal_relation": {
            "period_candidate": trace["period_candidate"],
            "start_candidate": trace["start_candidate"],
            "end_candidate": trace["end_candidate"],
            "relation": "EXACT_SINGLE_ACTION_ANCHOR_CORE",
            "internal_order": "UNKNOWN",
        },
        "location": {
            "pos_x_candidate": trace["pos_x_candidate"],
            "pos_y_candidate": trace["pos_y_candidate"],
            "semantic_role": "ANNOTATION_ANCHOR_LOCATION_CANDIDATE",
            "physical_player_position_truth": False,
        },
    }


def _payloads(rows):
    traces = []
    atoms = []
    occurrences = []
    for index, (team, zone, x) in enumerate(rows, start=1):
        _rule_id, family = SEMANTICS[zone]
        trace = _trace(
            f"tat_{index}",
            team,
            f"actor_{index}",
            index * 10,
            x,
            f"ea_{index}",
            family,
        )
        traces.append(trace)
        atoms.append(_atom(f"ea_{index}", zone))
        occurrences.append(_occurrence(trace))
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": len(traces),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    evidence_payload = {
        "module_id": "evidence_atom_inventory_lite_v1",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
        "evidence_atom_count": len(atoms),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    occurrence_payload = {
        "module_id": "action_occurrence_admission_lite_v1",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": BINDING,
        "action_occurrence_candidates": [],
        "single_action_anchor_occurrence_candidates": occurrences,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    return trace_payload, evidence_payload, occurrence_payload


def _run(rows):
    trace_payload, evidence_payload, occurrence_payload = _payloads(rows)
    return build_spatial_transition_candidates(
        trace_payload,
        evidence_payload,
        None,
        occurrence_payload,
    )


def test_cross_team_strict_anchor_zone_coordinate_order_admits_provider_attack_axis_only():
    result = _run([
        ("team_a", "OWN_HALF", 20),
        ("team_a", "OPPONENT_HALF", 80),
        ("team_b", "OWN_HALF", 25),
        ("team_b", "FINAL_THIRD", 75),
    ])

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["provider_team_relative_attack_axis_state"] == "ADMITTED"
    assert result["direction_normalization_state"] == "ATTACK_DIRECTION_ADMITTED"
    assert result["attack_direction"] == "ATTACK_POS_X"
    assert result["attack_direction_admission_basis"] == "CROSS_TEAM_REVIEWED_ANCHOR_ZONE_COORDINATE_ORDER"
    assert "attack_direction_not_admitted" not in result["review_hits"]
    assert "pitch_frame_not_admitted" in result["review_hits"]
    assert result["spatial_location_admitted_count"] == 0
    assert all(row["attack_normalized_x_candidate"] is None for row in result["spatial_transition_candidates"])
    assert all(row["coordinate_derived_zone_candidate"] is None for row in result["spatial_transition_candidates"])
    assert result["team_relative_attack_axis_is_absolute_pitch_frame_truth"] is False
    assert result["provider_semantic_zone_coordinate_order_is_tactical_truth"] is False
    assert result["occurrence_annotation_anchor_admission_is_tracking_truth"] is False
    assert result["provider_attack_axis_requires_anchor_zone_semantic_referent"] is True


def test_single_team_semantic_order_is_not_cross_team_attack_axis_authority():
    result = _run([
        ("team_a", "OWN_HALF", 20),
        ("team_a", "OPPONENT_HALF", 80),
    ])

    assert result["provider_team_relative_attack_axis_state"] == "REVIEW_REQUIRED"
    assert result["direction_normalization_state"] == "UNKNOWN"
    assert result["attack_direction"] is None
    assert "attack_direction_not_admitted" in result["review_hits"]


def test_overlapping_anchor_zone_coordinates_do_not_admit_direction():
    result = _run([
        ("team_a", "OWN_HALF", 60),
        ("team_a", "OPPONENT_HALF", 40),
        ("team_b", "OWN_HALF", 25),
        ("team_b", "OPPONENT_HALF", 75),
    ])

    assert result["provider_team_relative_attack_axis_state"] == "REVIEW_REQUIRED"
    assert result["attack_direction"] is None
    assert "attack_direction_not_admitted" in result["review_hits"]


def test_cross_team_opposite_coordinate_orders_do_not_admit_team_relative_direction():
    result = _run([
        ("team_a", "OWN_HALF", 20),
        ("team_a", "OPPONENT_HALF", 80),
        ("team_b", "OWN_HALF", 80),
        ("team_b", "OPPONENT_HALF", 20),
    ])

    assert result["provider_team_relative_attack_axis_state"] == "REVIEW_REQUIRED"
    assert result["provider_team_relative_attack_axis_inference"]["reason"] == "cross_team_direction_conflict"
    assert result["attack_direction"] is None
    assert "attack_direction_not_admitted" in result["review_hits"]


def test_destination_penalty_area_semantics_do_not_calibrate_anchor_attack_axis():
    result = _run([
        ("team_a", "OWN_HALF", 20),
        ("team_a", "PENALTY_AREA", 80),
        ("team_b", "OWN_HALF", 25),
        ("team_b", "PENALTY_AREA", 75),
    ])

    inference = result["provider_team_relative_attack_axis_inference"]
    assert result["provider_team_relative_attack_axis_state"] == "REVIEW_REQUIRED"
    assert result["direction_normalization_state"] == "UNKNOWN"
    assert result["attack_direction"] is None
    assert inference["eligible_team_count"] == 0
    assert inference["destination_zone_semantics_can_admit_attack_axis"] is False
    assert "plvs_v2_passes_into_the_penalty_box_accurate" in inference[
        "excluded_destination_zone_semantic_rule_ids"
    ]
    assert "attack_direction_not_admitted" in result["review_hits"]
