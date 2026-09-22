from pathlib import Path

from hpfa.modules.core.state_transition_dynamics_lite.src.state_transition_dynamics import build_state_transition_dynamics

BINDING = "msb_" + "a" * 24


def spatial(trace_id="tat_a", progression=True, zone="FINAL_THIRD", direction="FORWARD"):
    return {
        "module_id": "spatial_transition_candidate_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "spatial_transition_candidate_count": 1,
        "spatial_transition_candidates": [{
            "spatial_transition_candidate_id": "stc_a",
            "trackable_action_trace_candidate_id": trace_id,
            "match_surface_binding_id": BINDING,
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "actor_a",
            "action_family_candidates": ["PASS"],
            "provider_progression_candidates": ["PROGRESSIVE_CANDIDATE"] if progression else [],
            "provider_zone_candidates": [zone] if zone else [],
            "provider_context_candidates": [],
            "provider_direction_candidates": [direction] if direction else [],
            "provider_outcome_candidates": ["SUCCESS"],
            "spatial_admission_state": "PROVIDER_SPATIAL_CONTEXT_CANDIDATE_ONLY",
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def consequence(trace_id="tat_a", primary="SHOT_FOLLOW_UP_CANDIDATE", admitted=True, status="PASS_CANDIDATE_CLASSIFICATION"):
    return {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "status": "PASS",
        "module_status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidate_count": 1,
        "trackable_action_consequence_candidates": [{
            "trackable_action_consequence_candidate_id": "tacc_a",
            "anchor_trackable_action_trace_candidate_id": trace_id,
            "match_surface_binding_id": BINDING,
            "primary_consequence_candidate": primary,
            "admitted_after_follow_up_trace_ids": ["tat_b"] if admitted else [],
            "record_status": status,
        }],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_progressive_to_shot_follow_up_is_projected():
    result = build_state_transition_dynamics(spatial(), consequence())
    row = result["state_transition_dynamics_candidates"][0]
    assert result["status"] == "PASS"
    assert row["transition_class_candidate"] == "PROGRESSIVE_TO_SHOT_FOLLOW_UP_CANDIDATE"
    assert "AFTER_CONFIRMED_FOLLOW_UP_PRESENT" in row["support_candidates"]


def test_progressive_to_opponent_handover_is_adverse_not_causal():
    result = build_state_transition_dynamics(spatial(), consequence(primary="OPPONENT_HANDOVER_CANDIDATE"))
    row = result["state_transition_dynamics_candidates"][0]
    assert row["transition_class_candidate"] == "PROGRESSIVE_TO_ADVERSE_HANDOVER_CANDIDATE"
    assert row["adverse_consequence_candidates"] == ["OPPONENT_HANDOVER_CANDIDATE"]
    assert row["transition_is_causal_truth"] is False


def test_directional_consequence_without_after_admission_fails_closed():
    result = build_state_transition_dynamics(spatial(), consequence(admitted=False))
    assert result["status"] == "FAIL_CLOSED"
    assert any("directional_consequence_without_after_admission" in hit for hit in result["hard_block_hits"])


def test_no_visible_follow_up_is_not_counterevidence():
    result = build_state_transition_dynamics(
        spatial(),
        consequence(primary="NO_VISIBLE_FOLLOW_UP_CANDIDATE", admitted=False),
    )
    row = result["state_transition_dynamics_candidates"][0]
    assert row["transition_class_candidate"] == "NO_VISIBLE_FOLLOW_UP_ASSOCIATION_CANDIDATE"
    assert row["adverse_consequence_candidates"] == []


def test_progression_to_continuation_gets_bounded_state_advancement_function():
    result = build_state_transition_dynamics(
        spatial(progression=True, zone="MIDDLE_THIRD"),
        consequence(primary="SAME_TEAM_CONTINUATION_CANDIDATE"),
    )
    row = result["state_transition_dynamics_candidates"][0]
    assert row["visible_state_change_function_candidate"] == "VISIBLE_STATE_ADVANCEMENT_CONTINUATION_CANDIDATE"
    assert row["state_change_function_is_player_causal_credit"] is False
    assert row["state_change_function_is_opponent_organization_truth"] is False


def test_backward_action_to_same_team_continuation_is_not_automatically_negative():
    result = build_state_transition_dynamics(
        spatial(progression=False, zone="MIDDLE_THIRD", direction="BACKWARD"),
        consequence(primary="SAME_TEAM_CONTINUATION_CANDIDATE"),
    )
    row = result["state_transition_dynamics_candidates"][0]
    assert row["visible_state_change_function_candidate"] == "BACKWARD_OR_LATERAL_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    assert row["backward_or_lateral_action_is_automatically_negative"] is False
    assert row["adverse_consequence_candidates"] == []


def test_shot_follow_up_is_visible_exploitation_candidate_not_value_truth():
    result = build_state_transition_dynamics(
        spatial(progression=False, zone="FINAL_THIRD", direction="LATERAL"),
        consequence(primary="SHOT_FOLLOW_UP_CANDIDATE"),
    )
    row = result["state_transition_dynamics_candidates"][0]
    assert row["visible_state_change_function_candidate"] == "VISIBLE_ADVANTAGE_EXPLOITATION_CANDIDATE"
    assert row["state_change_function_is_value_model_output"] is False
    assert result["state_change_function_is_value_model_output"] is False


def test_adverse_handover_is_visible_advantage_loss_candidate_not_causality():
    result = build_state_transition_dynamics(
        spatial(progression=True),
        consequence(primary="OPPONENT_HANDOVER_CANDIDATE"),
    )
    row = result["state_transition_dynamics_candidates"][0]
    assert row["visible_state_change_function_candidate"] == "VISIBLE_ADVANTAGE_LOSS_OR_HANDOVER_CANDIDATE"
    assert row["transition_is_causal_truth"] is False


def test_trace_coverage_mismatch_fails_closed():
    result = build_state_transition_dynamics(spatial(trace_id="tat_a"), consequence(trace_id="tat_b"))
    assert result["status"] == "FAIL_CLOSED"
    assert "spatial_consequence_trace_coverage_mismatch" in result["hard_block_hits"]


def test_claim_locks_remain_closed():
    result = build_state_transition_dynamics(spatial(), consequence())
    assert result["metric_value_output_allowed"] is False
    assert result["state_transition_truth"] is False
    assert result["possession_truth"] is False
    assert result["sequence_truth"] is False
    assert result["tactical_pattern_truth"] is False
    assert result["causality_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    source = Path("hpfa/modules/core/state_transition_dynamics_lite/src/state_transition_dynamics.py").read_text(encoding="utf-8")
    forbidden = ("Genclerbirligi", "Fenerbahce", "15.08.2026", "Galatasaray")
    assert not any(token in source for token in forbidden)
