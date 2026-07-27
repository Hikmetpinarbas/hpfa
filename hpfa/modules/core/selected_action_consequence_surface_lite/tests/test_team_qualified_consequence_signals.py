from __future__ import annotations

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from consequence import consequence_class  # noqa: E402

TEAM_A = "teamc_a"
TEAM_B = "teamc_b"


def node(node_id: str, *, team: str | None, start: float, families: list[str]) -> dict:
    return {
        "selected_action_node_id": node_id,
        "team_identity_candidate_id": team,
        "start_candidate": str(start),
        "action_family_candidates": families,
        "terminal_outcome_support_visible": False,
        "derived_consequence_support_visible": False,
    }


def test_opponent_shot_plus_later_same_team_action_does_not_become_same_team_shot_follow_up():
    anchor = node("a", team=TEAM_A, start=10, families=["PASS"])
    future = [
        node("b-shot", team=TEAM_B, start=12, families=["SHOT"]),
        node("a-pass", team=TEAM_A, start=14, families=["PASS"]),
    ]

    primary, signals = consequence_class(anchor, future)

    assert primary == "OPPONENT_HANDOVER_CANDIDATE"
    assert "OPPONENT_SHOT_FOLLOW_UP_VISIBLE" in signals
    assert "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE" not in signals


def test_opponent_recovery_plus_later_same_team_action_does_not_become_recovery_response():
    anchor = node("loss", team=TEAM_A, start=10, families=["TURNOVER"])
    future = [
        node("b-recovery", team=TEAM_B, start=12, families=["RECOVERY"]),
        node("a-pass", team=TEAM_A, start=14, families=["PASS"]),
    ]

    primary, signals = consequence_class(anchor, future)

    assert primary == "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"
    assert "OPPONENT_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE" in signals
    assert "SAME_TEAM_RECOVERY_OR_INTERCEPTION_FOLLOW_UP_VISIBLE" not in signals


def test_mixed_team_same_time_first_layer_is_review_required_not_order_dependent():
    anchor = node("a", team=TEAM_A, start=10, families=["PASS"])
    same = node("a-pass", team=TEAM_A, start=12, families=["PASS"])
    opponent = node("b-shot", team=TEAM_B, start=12, families=["SHOT"])

    first_primary, first_signals = consequence_class(anchor, [same, opponent])
    second_primary, second_signals = consequence_class(anchor, [opponent, same])

    assert first_primary == "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    assert second_primary == first_primary
    assert first_signals == second_signals
    assert "MIXED_TEAM_FIRST_LAYER_VISIBLE" in first_signals


def test_missing_follow_up_team_identity_fails_closed_to_uncertain_candidate():
    anchor = node("a", team=TEAM_A, start=10, families=["PASS"])
    future = [node("unknown-shot", team=None, start=12, families=["SHOT"])]

    primary, signals = consequence_class(anchor, future)

    assert primary == "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    assert "FOLLOW_UP_TEAM_IDENTITY_MISSING" in signals
    assert "SAME_TEAM_SHOT_FOLLOW_UP_VISIBLE" not in signals


def test_missing_anchor_team_identity_fails_closed_to_uncertain_candidate():
    anchor = node("a", team=None, start=10, families=["PASS"])
    future = [node("shot", team=TEAM_A, start=12, families=["SHOT"])]

    primary, signals = consequence_class(anchor, future)

    assert primary == "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE"
    assert signals == ["ANCHOR_TEAM_IDENTITY_MISSING"]
