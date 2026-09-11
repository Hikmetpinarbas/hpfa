import pytest

from hpfa.modules.core.active_match_spine_runner.src import user_output_bundle as bundle


def test_distribution_accounting_accepts_strict_nonnegative_integers():
    cards = [
        {"eligible_action_count_by_team_candidate": {"TEAM_A": 2, "TEAM_B": 0}},
        {"eligible_action_count_by_team_candidate": {"TEAM_A": 3}},
    ]
    assert bundle._counter_sum(cards, "eligible_action_count_by_team_candidate") == {
        "TEAM_A": 5,
        "TEAM_B": 0,
    }


@pytest.mark.parametrize("invalid", [True, False, -1, 1.0, "1"])
def test_distribution_accounting_rejects_non_strict_counts(invalid):
    cards = [{"eligible_action_count_by_team_candidate": {"TEAM_A": invalid}}]
    with pytest.raises(ValueError, match="analyst_report_distribution_count_invalid"):
        bundle._counter_sum(cards, "eligible_action_count_by_team_candidate")


def test_distribution_accounting_does_not_upgrade_boolean_to_one():
    cards = [{"eligible_action_zone_counts": {"FINAL_THIRD": True}}]
    with pytest.raises(ValueError, match="eligible_action_zone_counts:FINAL_THIRD"):
        bundle._counter_sum(cards, "eligible_action_zone_counts")
