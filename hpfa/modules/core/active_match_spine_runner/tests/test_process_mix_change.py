from hpfa.modules.core.active_match_spine_runner.src.process_mix_change import (
    CLAIM_CEILING,
    build_time_window_process_mix_change_context,
)


def _interval(team, family, start, end, period="1"):
    return {
        "semantic_role": "CONTEXT_INTERVAL",
        "team_identity_candidate_id": team,
        "process_family_candidate": family,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
    }


def test_process_mix_comparison_exposes_visible_composition_shift_without_momentum_truth():
    payload = {
        "process_participation_candidates": [
            _interval("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 100, 180),
            _interval("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 220, 300),
            _interval("TEAM_A", "COUNTERATTACK_CANDIDATE", 700, 760),
            _interval("TEAM_A", "COUNTERATTACK_CANDIDATE", 820, 880),
        ]
    }

    result = build_time_window_process_mix_change_context(payload, window_seconds=600)

    assert result["status"] == "PASS"
    assert result["profile_count"] == 2
    assert result["comparison_count"] == 1
    assert result["claim_ceiling"] == CLAIM_CEILING

    first, second = result["profiles"]
    assert first["process_family_counts"] == {"POSITIONAL_ATTACK_CANDIDATE": 2}
    assert second["process_family_counts"] == {"COUNTERATTACK_CANDIDATE": 2}

    comparison = result["comparisons"][0]
    assert comparison["process_family_share_delta"] == {
        "COUNTERATTACK_CANDIDATE": 1.0,
        "POSITIONAL_ATTACK_CANDIDATE": -1.0,
    }
    assert comparison["composition_total_variation_distance_candidate"] == 1.0
    assert comparison["composition_distance_range"] == [0.0, 1.0]
    assert comparison["composition_distance_is_change_point_truth"] is False
    assert comparison["comparison_is_momentum_truth"] is False
    assert comparison["comparison_is_tactical_adaptation_truth"] is False
    assert comparison["comparison_is_causal_truth"] is False
    assert result["creates_independent_support"] is False


def test_duplicate_context_interval_does_not_inflate_window_count():
    repeated = _interval("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 100, 180)
    payload = {"process_participation_candidates": [repeated, dict(repeated)]}

    result = build_time_window_process_mix_change_context(payload, window_seconds=600)

    assert result["deduplicated_context_interval_count"] == 1
    assert result["profiles"][0]["eligible_visible_process_n"] == 1


def test_non_adjacent_visible_windows_are_not_compared_across_unobserved_gap():
    payload = {
        "process_participation_candidates": [
            _interval("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 100, 180),
            _interval("TEAM_A", "COUNTERATTACK_CANDIDATE", 1300, 1380),
        ]
    }

    result = build_time_window_process_mix_change_context(payload, window_seconds=600)

    assert result["profile_count"] == 2
    assert result["comparison_count"] == 0
    assert result["skipped_non_adjacent_visible_window_pair_count"] == 1
    assert result["empty_window_is_process_absence_truth"] is False


def test_periods_are_never_cross_compared():
    payload = {
        "process_participation_candidates": [
            _interval("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 100, 180, period="1"),
            _interval("TEAM_A", "COUNTERATTACK_CANDIDATE", 100, 180, period="2"),
        ]
    }

    result = build_time_window_process_mix_change_context(payload, window_seconds=600)

    assert result["profile_count"] == 2
    assert result["comparison_count"] == 0


def test_invalid_window_width_fails_closed():
    result = build_time_window_process_mix_change_context(
        {"process_participation_candidates": []},
        window_seconds=0,
    )

    assert result["status"] == "FAIL_CLOSED"
    assert result["hard_block_hits"] == ["window_seconds_must_be_positive"]
    assert result["process_mix_change_is_momentum_truth"] is False
