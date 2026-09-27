import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from user_output_bundle import _human_score_state_process_outcome_cards


def _identity():
    return {
        "team_identity_candidates": [
            {"team_identity_candidate_id": "A", "team_aliases_raw": ["Team A"]},
            {"team_identity_candidate_id": "B", "team_aliases_raw": ["Team B"]},
        ]
    }


def _profile(team, start, score_a, score_b, n, shot, loss, recovery, rate, shot_rate):
    return {
        "team_identity_candidate_id": team,
        "score_state_candidate": {"Team A": score_a, "Team B": score_b},
        "segment_start_second_candidate": start,
        "segment_end_second_candidate": start + 600,
        "eligible_visible_process_n": n,
        "shot_ending_process_n": shot,
        "visible_loss_process_n": loss,
        "visible_recovery_process_n": recovery,
        "eligible_visible_process_rate_per_10_minutes": rate,
        "shot_ending_process_rate_per_10_minutes": shot_rate,
    }


def test_score_state_cards_collapse_each_team_into_one_readable_card_pair():
    rich = {
        "score_state_visible_process_outcome_context": {
            "status": "PASS",
            "profiles": [
                _profile("A", 0, 0, 0, 4, 1, 2, 1, 4.0, 1.0),
                _profile("A", 600, 0, 1, 8, 2, 3, 1, 8.0, 2.0),
                _profile("B", 0, 0, 0, 5, 1, 1, 0, 5.0, 1.0),
                _profile("B", 600, 0, 1, 6, 0, 4, 1, 6.0, 0.0),
            ],
        }
    }

    cards = _human_score_state_process_outcome_cards(rich, _identity(), "tr")

    assert len(cards) == 4
    assert "Team A" in cards[0]
    assert "süreç 4" in cards[0]
    assert "süreç 8" in cards[0]
    assert "şut-sonlanma 2" in cards[0]
    assert "süreç/10dk 4.00" in cards[1]
    assert "ayrı evidence gerekir" in cards[1]
    assert "Team B" in cards[2]


def test_score_state_cards_do_not_emit_when_context_is_not_available():
    rich = {
        "score_state_visible_process_outcome_context": {
            "status": "NOT_AVAILABLE",
            "profiles": [_profile("A", 0, 0, 0, 4, 1, 2, 1, 4.0, 1.0)],
        }
    }

    assert _human_score_state_process_outcome_cards(rich, _identity(), "tr") == []
