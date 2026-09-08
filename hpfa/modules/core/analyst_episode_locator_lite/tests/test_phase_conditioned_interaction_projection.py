from hpfa.modules.core.analyst_episode_locator_lite.src.phase_conditioned_interaction_projection import (
    build_phase_conditioned_interactions,
)


def _episode_payload():
    return {
        "module_id": "analyst_episode_locator_lite_v1",
        "episode_candidates": [
            {"episode_candidate_id": "ep_1"},
            {"episode_candidate_id": "ep_2"},
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _rich_payload():
    return {
        "module_id": "rich_multiformat_analysis_lattice_v1",
        "phase_state_candidates": [
            {
                "phase_state_candidate_id": "psc_0000",
                "episode_index": 0,
                "labels": ["RECOVERY_TRANSITION_ACTIVITY_CANDIDATE", "CIRCULATION_ACTIVITY_CANDIDATE"],
            },
            {
                "phase_state_candidate_id": "psc_0001",
                "episode_index": 1,
                "labels": ["TERMINAL_ACTIVITY_CANDIDATE"],
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_payload():
    return {
        "module_id": "analyst_episode_process_participation_projection_v1",
        "process_participation_candidates": [
            {
                "episode_candidate_id": "ep_1",
                "actor_identity_candidate_id": "actor_a",
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "BUILDUP_PROCESS_CANDIDATE",
                "shot_present_annotation_candidate": False,
                "dependency_group": "dep_1",
                "provenance_root": "ea_1",
            },
            {
                "episode_candidate_id": "ep_1",
                "actor_identity_candidate_id": "actor_b",
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "BUILDUP_PROCESS_CANDIDATE",
                "shot_present_annotation_candidate": True,
                "dependency_group": "dep_2",
                "provenance_root": "ea_2",
            },
            {
                "episode_candidate_id": "ep_1",
                "actor_identity_candidate_id": "actor_c",
                "team_identity_candidate_id": "team_b",
                "process_family_candidate": "DEFENSIVE_RESPONSE_PROCESS_CANDIDATE",
                "shot_present_annotation_candidate": False,
                "dependency_group": "dep_3",
                "provenance_root": "ea_3",
            },
        ],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_groups_same_episode_without_promoting_phase_or_interaction_truth():
    result = build_phase_conditioned_interactions(_process_payload(), _episode_payload(), _rich_payload())
    assert result["status"] == "PASS"
    assert result["interaction_episode_candidate_count"] == 1
    row = result["interaction_episode_candidates"][0]
    assert row["episode_candidate_id"] == "ep_1"
    assert row["multi_actor_visible"] is True
    assert row["multi_team_visible"] is True
    assert row["team_identity_candidate_ids"] == ["team_a", "team_b"]
    assert row["process_family_annotation_counts"] == {
        "BUILDUP_PROCESS_CANDIDATE": 2,
        "DEFENSIVE_RESPONSE_PROCESS_CANDIDATE": 1,
    }
    assert row["shot_present_process_family_annotation_counts"] == {"BUILDUP_PROCESS_CANDIDATE": 1}
    assert row["phase_truth"] is False
    assert row["reciprocal_phase_truth"] is False
    assert row["interaction_truth"] is False
    assert row["causal_truth"] is False
    assert row["independent_support_vote_count"] == 0


def test_missing_phase_state_is_review_required_not_fabricated():
    rich = _rich_payload()
    rich["phase_state_candidates"] = []
    result = build_phase_conditioned_interactions(_process_payload(), _episode_payload(), rich)
    assert result["status"] == "REVIEW_REQUIRED"
    row = result["interaction_episode_candidates"][0]
    assert row["phase_state_candidate_id"] is None
    assert row["phase_activity_labels"] == []
    assert result["phase_truth"] is False


def test_unknown_episode_reference_fails_closed():
    process = _process_payload()
    process["process_participation_candidates"][0]["episode_candidate_id"] = "ep_unknown"
    result = build_phase_conditioned_interactions(process, _episode_payload(), _rich_payload())
    assert result["status"] == "FAIL_CLOSED"
    assert "process_episode_reference_unknown:ep_unknown" in result["hard_block_hits"]


def test_absence_is_not_counterevidence_and_no_sample_identity_is_embedded():
    result = build_phase_conditioned_interactions(_process_payload(), _episode_payload(), _rich_payload())
    assert result["absence_is_counterevidence"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    rendered = repr(result)
    assert "Genclerbirligi" not in rendered
    assert "Fenerbahce" not in rendered
