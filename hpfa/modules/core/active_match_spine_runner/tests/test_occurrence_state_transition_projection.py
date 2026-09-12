from hpfa.modules.core.active_match_spine_runner.src.occurrence_state_transition_projection import (
    build_occurrence_state_transition_projection,
)


def _spatial_payload():
    return {
        "module_id": "spatial_transition_candidate_lite_v1",
        "status": "REVIEW_REQUIRED",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "spatial_transition_candidate_count": 3,
        "spatial_transition_candidates": [
            {
                "spatial_transition_candidate_id": "stc_1",
                "trackable_action_trace_candidate_id": "tat_1",
                "provider_progression_candidates": ["PROGRESSIVE_CANDIDATE"],
                "provider_zone_candidates": ["FINAL_THIRD"],
                "provider_context_candidates": [],
                "provider_direction_candidates": ["FORWARD"],
                "provider_outcome_candidates": ["SUCCESS"],
                "provider_semantic_rule_ids": ["r1"],
                "coordinate_derived_zone_candidate": "FINAL_THIRD_LOCATION_CANDIDATE",
                "spatial_admission_state": "ADMITTED_LOCATION_ONLY",
            },
            {
                "spatial_transition_candidate_id": "stc_2",
                "trackable_action_trace_candidate_id": "tat_2",
                "provider_progression_candidates": [],
                "provider_zone_candidates": ["FINAL_THIRD"],
                "provider_context_candidates": [],
                "provider_direction_candidates": [],
                "provider_outcome_candidates": ["SUCCESS"],
                "provider_semantic_rule_ids": ["r2"],
                "spatial_admission_state": "PROVIDER_SPATIAL_CONTEXT_CANDIDATE_ONLY",
            },
            {
                "spatial_transition_candidate_id": "stc_3",
                "trackable_action_trace_candidate_id": "tat_3",
                "provider_progression_candidates": [],
                "provider_zone_candidates": [],
                "provider_context_candidates": [],
                "provider_direction_candidates": [],
                "provider_outcome_candidates": ["FAILURE"],
                "provider_semantic_rule_ids": ["r3"],
                "spatial_admission_state": "PROVIDER_SPATIAL_CONTEXT_CANDIDATE_ONLY",
            },
        ],
    }


def _occurrence_payload():
    return {
        "module_id": "occurrence_consequence_projection_v1",
        "status": "REVIEW_REQUIRED",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "occurrence_consequence_projection_count": 2,
        "occurrence_consequence_projections": [
            {
                "occurrence_consequence_projection_id": "ocp_1",
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "TWO_PARTICIPANT_INTERACTION",
                "required_participant_scope": "ACTOR_AND_OPPONENT",
                "binding_state": "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE",
                "supporting_trackable_action_trace_candidate_ids": ["tat_1", "tat_2"],
                "supporting_consequence_candidate_ids": ["tacc_1", "tacc_2"],
                "actor_identity_candidate_ids": ["actor_1", "actor_2"],
                "team_identity_candidate_ids": ["team_1", "team_2"],
                "action_family_candidates": ["DRIBBLE", "TACKLE"],
                "period_candidates": ["1"],
                "start_candidates": ["100.0"],
                "end_candidates": ["104.0"],
                "primary_consequence_candidates": ["SHOT_FOLLOW_UP_CANDIDATE"],
                "admitted_after_follow_up_trace_ids": ["tat_after"],
                "record_status": "PASS",
            },
            {
                "occurrence_consequence_projection_id": "ocp_2",
                "action_occurrence_candidate_id": "aoc_2",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "ACTOR_TRACE_VISIBLE_CANDIDATE",
                "supporting_trackable_action_trace_candidate_ids": ["tat_3"],
                "supporting_consequence_candidate_ids": ["tacc_3"],
                "actor_identity_candidate_ids": ["actor_3"],
                "team_identity_candidate_ids": ["team_1"],
                "action_family_candidates": ["PASS"],
                "period_candidates": ["2"],
                "start_candidates": ["200.0"],
                "end_candidates": ["201.0"],
                "primary_consequence_candidates": ["PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE"],
                "admitted_after_follow_up_trace_ids": [],
                "record_status": "REVIEW_REQUIRED",
            },
        ],
    }


def test_two_trace_interaction_projects_to_one_occurrence_state_record():
    payload = build_occurrence_state_transition_projection(
        _spatial_payload(),
        _occurrence_payload(),
    )
    assert payload["occurrence_state_transition_projection_count"] == 2
    first = next(
        row
        for row in payload["occurrence_state_transition_projections"]
        if row["action_occurrence_candidate_id"] == "aoc_1"
    )
    assert first["supporting_trackable_action_trace_candidate_ids"] == ["tat_1", "tat_2"]
    assert first["supporting_spatial_transition_candidate_ids"] == ["stc_1", "stc_2"]
    assert first["transition_class_candidates"] == ["PROGRESSIVE_TO_SHOT_FOLLOW_UP_CANDIDATE"]
    assert payload["legacy_trace_records_are_support_evidence_not_action_universe"] is True


def test_occurrence_context_is_carried_forward_without_promoting_truth():
    payload = build_occurrence_state_transition_projection(
        _spatial_payload(),
        _occurrence_payload(),
    )
    first = next(
        row
        for row in payload["occurrence_state_transition_projections"]
        if row["action_occurrence_candidate_id"] == "aoc_1"
    )
    assert first["actor_identity_candidate_ids"] == ["actor_1", "actor_2"]
    assert first["period_candidates"] == ["1"]
    assert first["start_candidates"] == ["100.0"]
    assert first["occurrence_topology"] == "TWO_PARTICIPANT_INTERACTION"
    assert first["coordinate_derived_zone_candidates"] == ["FINAL_THIRD_LOCATION_CANDIDATE"]
    assert "ADMITTED_COORDINATE_ZONE_CANDIDATE_VISIBLE" in first["support_candidates"]
    assert first["coordinate_derived_zone_is_team_shape_truth"] is False
    assert first["transition_is_causal_truth"] is False


def test_occurrence_count_is_projection_denominator_not_trace_count():
    payload = build_occurrence_state_transition_projection(
        _spatial_payload(),
        _occurrence_payload(),
    )
    assert payload["source_legacy_spatial_candidate_count"] == 3
    assert payload["source_action_occurrence_candidate_count"] == 2
    assert payload["occurrence_state_transition_projection_count"] == 2
    assert payload["occurrence_projection_is_primary_action_member_candidate_surface"] is True
    assert payload["sequence_truth"] is False


def test_missing_spatial_support_downgrades_record_without_inventing_geometry():
    occurrence = _occurrence_payload()
    occurrence["occurrence_consequence_projections"][1]["supporting_trackable_action_trace_candidate_ids"] = ["tat_missing"]
    payload = build_occurrence_state_transition_projection(_spatial_payload(), occurrence)
    assert payload["status"] == "REVIEW_REQUIRED"
    second = next(
        row
        for row in payload["occurrence_state_transition_projections"]
        if row["action_occurrence_candidate_id"] == "aoc_2"
    )
    assert "supporting_spatial_trace_missing" in second["review_hits"]
    assert second["provider_progression_candidates"] == []
    assert second["provider_zone_candidates"] == []


def test_declared_occurrence_count_mismatch_fails_closed():
    occurrence = _occurrence_payload()
    occurrence["occurrence_consequence_projection_count"] = 3
    payload = build_occurrence_state_transition_projection(_spatial_payload(), occurrence)
    assert payload["status"] == "FAIL_CLOSED"
    assert "occurrence_consequence_projection_count_mismatch" in payload["hard_block_hits"]
    assert payload["occurrence_state_transition_projections"] == []
