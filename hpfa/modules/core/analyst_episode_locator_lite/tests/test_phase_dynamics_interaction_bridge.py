from hpfa.modules.core.analyst_episode_locator_lite.src.phase_dynamics_interaction_bridge import (
    build_phase_dynamics_interaction_bridge,
)


def _interaction_payload():
    return {
        "module_id": "phase_conditioned_interaction_projection_v1",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "interaction_episode_candidates": [
            {
                "interaction_episode_candidate_id": "iec_0000",
                "episode_candidate_id": "ep_1",
                "phase_state_candidate_id": "psc_1",
                "phase_activity_labels": ["RECOVERY_ACTIVITY", "SHOT_ACTIVITY"],
                "actor_identity_candidate_ids": ["p_1", "p_2"],
                "team_identity_candidate_ids": ["t_1", "t_2"],
                "process_family_annotation_counts": {"PRESSING": 1},
                "multi_actor_visible": True,
                "multi_team_visible": True,
                "provenance_roots": ["root_1"],
                "dependency_groups": ["dep_1"],
            }
        ],
    }


def _dynamics_payload():
    return {
        "module_id": "observed_match_dynamics_projection_v1",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "observed_match_dynamics_candidates": [
            {
                "episode_candidate_id": "ep_1",
                "activity_rate_per_minute_candidate": 42.5,
                "activity_regime_candidate": "HIGH_ACTIVITY_CANDIDATE",
                "episode_activity_rate_delta_candidate": 7.5,
                "terminal_turnover_recovery_activity_count_candidate": 9,
            }
        ],
    }


def test_bridge_combines_phase_interaction_and_dynamics_without_truth_inflation():
    payload = build_phase_dynamics_interaction_bridge(_interaction_payload(), _dynamics_payload())
    assert payload["status"] == "PASS"
    assert payload["phase_dynamics_interaction_candidate_count"] == 1
    row = payload["phase_dynamics_interaction_candidates"][0]
    assert row["episode_candidate_id"] == "ep_1"
    assert row["activity_regime_candidate"] == "HIGH_ACTIVITY_CANDIDATE"
    assert row["multi_actor_visible"] is True
    assert row["multi_team_visible"] is True
    assert row["independent_support_vote_count"] == 0
    assert row["phase_truth"] is False
    assert row["reciprocal_phase_truth"] is False
    assert row["interaction_truth"] is False
    assert row["tempo_truth"] is False
    assert row["momentum_truth"] is False
    assert row["causal_truth"] is False


def test_missing_dynamics_for_visible_interaction_requires_review_not_zero_fill():
    dynamics = _dynamics_payload()
    dynamics["observed_match_dynamics_candidates"] = []
    payload = build_phase_dynamics_interaction_bridge(_interaction_payload(), dynamics)
    assert payload["status"] == "REVIEW_REQUIRED"
    row = payload["phase_dynamics_interaction_candidates"][0]
    assert row["activity_rate_per_minute_candidate"] is None
    assert "dynamics_missing_for_interaction_episode:ep_1" in payload["review_hits"]


def test_upstream_truth_claim_fails_closed():
    interaction = _interaction_payload()
    interaction["canonical_event_count"] = 1
    payload = build_phase_dynamics_interaction_bridge(interaction, _dynamics_payload())
    assert payload["status"] == "FAIL_CLOSED"
    assert payload["phase_dynamics_interaction_candidates"] == []


def test_no_sample_match_identity_leak():
    payload = build_phase_dynamics_interaction_bridge(_interaction_payload(), _dynamics_payload())
    rendered = str(payload)
    assert "Genclerbirligi" not in rendered
    assert "Fenerbahce" not in rendered
    assert "Galatasaray" not in rendered
