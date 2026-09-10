from hpfa.modules.core.temporal_episode_signature_lite.src.observed_match_dynamics_projection import build_observed_match_dynamics


def _feature_payload():
    return {
        "module_id": "episode_feature_vector_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "episode_feature_vectors": [
            {
                "episode_candidate_id": "ep_1",
                "period_candidate": "1",
                "start_second_candidate": 0,
                "end_second_candidate": 60,
                "duration_seconds_candidate": 60,
                "eligible_action_candidate_count": 30,
                "shot_candidate_count": 1,
                "turnover_candidate_count": 2,
                "recovery_candidate_count": 2,
            },
            {
                "episode_candidate_id": "ep_2",
                "period_candidate": "1",
                "start_second_candidate": 60,
                "end_second_candidate": 90,
                "duration_seconds_candidate": 30,
                "eligible_action_candidate_count": 30,
                "shot_candidate_count": 3,
                "turnover_candidate_count": 4,
                "recovery_candidate_count": 5,
            },
            {
                "episode_candidate_id": "ep_3",
                "period_candidate": "1",
                "start_second_candidate": 90,
                "end_second_candidate": 150,
                "duration_seconds_candidate": 60,
                "eligible_action_candidate_count": 15,
                "shot_candidate_count": 0,
                "turnover_candidate_count": 1,
                "recovery_candidate_count": 1,
            },
        ],
    }


def _temporal_payload():
    return {
        "module_id": "temporal_episode_signature_lite_v1",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "hard_block_hits": [],
        "temporal_episode_signatures": [
            {"episode_candidate_id": "ep_1", "comparison_status": "NO_PRIOR_EPISODE_IN_PERIOD"},
            {"episode_candidate_id": "ep_2", "comparison_status": "AVAILABLE"},
            {"episode_candidate_id": "ep_3", "comparison_status": "AVAILABLE"},
        ],
    }


def test_donor_tempo_is_rehabilitated_as_observed_activity_not_momentum_truth():
    payload = build_observed_match_dynamics(_feature_payload(), _temporal_payload())
    assert payload["status"] == "PASS"
    assert payload["observed_match_dynamics_candidate_count"] == 3
    assert payload["activity_regime_is_tempo_truth"] is False
    assert payload["activity_delta_is_momentum_truth"] is False
    assert payload["volatility_is_chaos_truth"] is False
    rows = payload["observed_match_dynamics_candidates"]
    assert rows[1]["activity_rate_per_minute_candidate"] == 60.0
    assert rows[1]["episode_activity_rate_delta_candidate"] == 30.0
    assert rows[1]["terminal_turnover_recovery_activity_count_candidate"] == 12
    assert payload["donor_adaptation"]["episode_defined_windows_preferred"] is True


def test_zero_duration_does_not_become_zero_tempo():
    feature = _feature_payload()
    feature["episode_feature_vectors"][1]["duration_seconds_candidate"] = 0
    temporal = _temporal_payload()
    temporal["temporal_episode_signatures"][1]["comparison_status"] = "CURRENT_ZERO_DURATION_RATE_NA"
    payload = build_observed_match_dynamics(feature, temporal)
    assert payload["status"] == "REVIEW_REQUIRED"
    row = payload["observed_match_dynamics_candidates"][1]
    assert row["activity_rate_per_minute_candidate"] is None
    assert row["activity_regime_candidate"] == "RATE_NOT_AVAILABLE"


def test_unknown_truth_counts_fail_closed():
    feature = _feature_payload()
    feature["canonical_event_count"] = 999
    payload = build_observed_match_dynamics(feature, _temporal_payload())
    assert payload["status"] == "FAIL_CLOSED"
    assert payload["observed_match_dynamics_candidates"] == []


def test_no_sample_match_identity_leak():
    payload = build_observed_match_dynamics(_feature_payload(), _temporal_payload())
    rendered = str(payload)
    assert "Genclerbirligi" not in rendered
    assert "Fenerbahce" not in rendered
    assert "Manchester City" not in rendered
    assert "Galatasaray" not in rendered
