from hpfa.modules.core.analyst_episode_locator_lite.src.episode_consequence_projection import (
    build_episode_consequence_projection,
)


def _episode_payload():
    return {
        "module_id": "analyst_episode_locator_lite_v1",
        "episode_candidates": [
            {
                "episode_candidate_id": "ep_1",
                "period_candidate": "1",
                "start_second_candidate": 10.0,
                "end_second_candidate": 20.0,
            },
            {
                "episode_candidate_id": "ep_2",
                "period_candidate": "1",
                "start_second_candidate": 30.0,
                "end_second_candidate": 40.0,
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _trace_payload():
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "t1",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "period_candidate": "1",
                "start_candidate": "12.0",
                "end_candidate": "12.5",
                "action_family_candidates": ["RECOVERY"],
            },
            {
                "trackable_action_trace_candidate_id": "t2",
                "source_role": "PLAYER_SURFACE_CANDIDATE",
                "team_identity_candidate_id": "team_b",
                "actor_identity_candidate_id": "actor_b",
                "period_candidate": "1",
                "start_candidate": "50.0",
                "end_candidate": "50.5",
                "action_family_candidates": ["PASS"],
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence_payload():
    return {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "c1",
                "anchor_trackable_action_trace_candidate_id": "t1",
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "primary_consequence_candidate": "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE",
                "terminal_outcome_support_visible": False,
            },
            {
                "trackable_action_consequence_candidate_id": "c2",
                "anchor_trackable_action_trace_candidate_id": "t2",
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "terminal_outcome_support_visible": False,
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _interaction_payload():
    return {
        "module_id": "phase_conditioned_interaction_projection_v1",
        "interaction_episode_candidates": [
            {
                "interaction_episode_candidate_id": "iec_1",
                "episode_candidate_id": "ep_1",
                "phase_activity_labels": ["RECOVERY_ACTIVITY_CANDIDATE"],
                "process_family_annotation_counts": {"COUNTERATTACK": 1},
            },
            {
                "interaction_episode_candidate_id": "iec_2",
                "episode_candidate_id": "ep_2",
                "phase_activity_labels": [],
                "process_family_annotation_counts": {},
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_binds_visible_consequence_to_single_episode_navigation_window():
    result = build_episode_consequence_projection(
        _episode_payload(), _trace_payload(), _consequence_payload(), _interaction_payload()
    )
    assert result["status"] == "REVIEW_REQUIRED"
    first = result["episode_consequence_candidates"][0]
    assert first["episode_candidate_id"] == "ep_1"
    assert first["actor_identity_candidate_id"] == "actor_a"
    assert first["team_identity_candidate_id"] == "team_a"
    assert first["primary_consequence_candidate"] == "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    assert first["phase_activity_labels"] == ["RECOVERY_ACTIVITY_CANDIDATE"]
    assert result["episode_primary_consequence_candidate_counts"]["ep_1"] == {
        "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE": 1
    }


def test_unbound_trace_remains_review_not_false_absence():
    result = build_episode_consequence_projection(
        _episode_payload(), _trace_payload(), _consequence_payload(), _interaction_payload()
    )
    second = result["episode_consequence_candidates"][1]
    assert second["episode_candidate_id"] is None
    assert second["episode_binding_state"] == "UNBOUND_REVIEW_REQUIRED"
    assert result["absence_is_counterevidence"] is False
    assert result["unbound_or_ambiguous_episode_consequence_candidate_count"] == 1


def test_duplicate_consequence_anchor_fails_closed():
    consequence = _consequence_payload()
    duplicate = dict(consequence["trackable_action_consequence_candidates"][0])
    duplicate["trackable_action_consequence_candidate_id"] = "c3"
    consequence["trackable_action_consequence_candidates"].append(duplicate)
    result = build_episode_consequence_projection(
        _episode_payload(), _trace_payload(), consequence, _interaction_payload()
    )
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("consequence_anchor_invalid_or_duplicate") for hit in result["hard_block_hits"])


def test_claim_locks_remain_closed():
    result = build_episode_consequence_projection(
        _episode_payload(), _trace_payload(), _consequence_payload(), _interaction_payload()
    )
    assert result["episode_binding_is_possession_truth"] is False
    assert result["episode_binding_is_sequence_truth"] is False
    assert result["consequence_candidate_is_causal_truth"] is False
    assert result["phase_truth"] is False
    assert result["reciprocal_phase_truth"] is False
    assert result["interaction_truth"] is False
    assert result["same_provider_support_is_independent_vote"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_no_sample_match_identity_leak():
    import pathlib

    source = pathlib.Path(
        "hpfa/modules/core/analyst_episode_locator_lite/src/episode_consequence_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "Roma", "Atalanta", "15.08.2026"):
        assert token not in source
