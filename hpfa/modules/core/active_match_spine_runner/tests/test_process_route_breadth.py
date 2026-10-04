from hpfa.modules.core.active_match_spine_runner.src.process_route_breadth import (
    CLAIM_CEILING,
    build_visible_process_route_breadth_profile,
)


def _sig(team, family, starts, ends):
    return {
        "team_identity_candidate_id": team,
        "process_family_candidate": family,
        "process_start_zone_candidates": starts,
        "process_end_zone_candidates": ends,
    }


def test_route_breadth_counts_unique_recurring_and_top_routes():
    rows = [
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", ["DEFENSIVE_THIRD"], ["MIDDLE_THIRD"]),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", ["DEFENSIVE_THIRD"], ["MIDDLE_THIRD"]),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", ["MIDDLE_THIRD"], ["FINAL_THIRD"]),
        _sig("A", "POSITIONAL_ATTACK_CANDIDATE", ["MIDDLE_THIRD", "FINAL_THIRD"], ["FINAL_THIRD"]),
    ]

    result = build_visible_process_route_breadth_profile(rows)

    assert result["status"] == "PASS"
    assert result["claim_ceiling"] == CLAIM_CEILING
    profile = result["profiles"][0]
    assert profile["eligible_process_n"] == 4
    assert profile["eligible_unambiguous_route_process_n"] == 3
    assert profile["ambiguous_or_unresolved_route_process_n"] == 1
    assert profile["unique_visible_route_candidate_n"] == 2
    assert profile["recurring_visible_route_candidate_n"] == 1
    assert profile["singleton_visible_route_candidate_n"] == 1
    assert profile["top_visible_route_candidate"] == "DEFENSIVE_THIRD->MIDDLE_THIRD"
    assert profile["top_visible_route_process_n"] == 2
    assert profile["top_visible_route_share_candidate"] == 0.666667
    assert profile["route_coverage_share_candidate"] == 0.75
    assert profile["route_breadth_is_tactical_flexibility_truth"] is False
    assert profile["route_breadth_is_unpredictability_truth"] is False
    assert profile["route_breadth_is_superiority_truth"] is False
    assert result["creates_independent_support"] is False


def test_ambiguous_routes_remain_in_denominator_burden_not_route_identity():
    rows = [
        _sig("A", "COUNTERATTACK_CANDIDATE", [], ["FINAL_THIRD"]),
        _sig("A", "COUNTERATTACK_CANDIDATE", ["MIDDLE_THIRD"], []),
    ]

    result = build_visible_process_route_breadth_profile(rows)
    profile = result["profiles"][0]

    assert profile["eligible_process_n"] == 2
    assert profile["eligible_unambiguous_route_process_n"] == 0
    assert profile["ambiguous_or_unresolved_route_process_n"] == 2
    assert profile["unique_visible_route_candidate_n"] == 0
    assert profile["top_visible_route_share_candidate"] is None
    assert profile["route_coverage_share_candidate"] == 0.0


def test_no_process_signatures_is_not_available():
    result = build_visible_process_route_breadth_profile([])

    assert result["status"] == "NOT_AVAILABLE"
    assert result["profiles"] == []
    assert result["route_is_physical_trajectory_truth"] is False
